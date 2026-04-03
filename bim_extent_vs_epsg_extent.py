"""
DISCLAIMER:
-----------
This script inspects and validates only the spatial reference and coordinate
extents recorded in a BIM georeferencing report.

It does NOT verify real-world alignment, survey accuracy, authoring intent,
nor correctness of transformations applied in upstream software.

Passing validation indicates that recorded extents fall within expected CRS
domains — not that the BIM model is correctly georeferenced.

The data producer remains responsible for ensuring spatial correctness.

BIM Georeferencing Validation (TXT → JSON)
------------------------------------------
Parses an ArcGIS BIM georeferencing report (.txt),
validates extents against CRS domain,
and writes structured JSON output.

"""

import os
import json
from datetime import datetime
from pyproj import CRS
from pyproj.exceptions import CRSError
from pyproj import Transformer

# Optional pyproj for reprojection diagnostics
try:
    from pyproj import Transformer
    PYPROJ_AVAILABLE = True
except Exception:
    PYPROJ_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────────────────
# CRS Lookup Tables
# ──────────────────────────────────────────────────────────────────────────────

ESRI_TO_EPSG = {
    "ETRS_1989_UTM_Zone_31N": 25831,
    "GCS_ETRS_1989": 4258,
}

CRS_BOUNDS = {
    25831: {
        "type": "Projected",
        "unit": "metres",
        "XMin": 166022.0,
        "YMin": 0.0,
        "XMax": 833978.0,
        "YMax": 9329005.0,
    },
    4258: {
        "type": "Geographic",
        "unit": "degrees",
        "XMin": -16.1,
        "YMin": 32.88,
        "XMax": 40.18,
        "YMax": 84.17,
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# Auto‑load CRS bounds
# ──────────────────────────────────────────────────────────────────────────────

from pyproj import CRS
from pyproj.exceptions import CRSError

def load_crs_bounds(epsg_code):
    try:
        crs = CRS.from_epsg(epsg_code)
    except CRSError:
        return None

    area = crs.area_of_use
    axis_info = crs.axis_info

    auth = crs.to_authority()
    authority = auth[0] if auth else None

    return {
        "type": "Projected" if crs.is_projected else "Geographic",
        "unit": axis_info[0].unit_name if axis_info else None,
        "LonMin": area.west,
        "LatMin": area.south,
        "LonMax": area.east,
        "LatMax": area.north,
        "name": area.name,
        "authority": authority,
    }

# ──────────────────────────────────────────────────────────────────────────────
# Project bounds when CRS is projected
# ──────────────────────────────────────────────────────────────────────────────   
    
def geographic_bounds_to_projected(epsg_code, bounds):
    """
    Convert geographic Area of Use bounds into projected CRS space.
    """
    transformer = Transformer.from_crs(
        "EPSG:4326", f"EPSG:{epsg_code}", always_xy=True
    )

    corners = [
        (bounds["LonMin"], bounds["LatMin"]),
        (bounds["LonMin"], bounds["LatMax"]),
        (bounds["LonMax"], bounds["LatMin"]),
        (bounds["LonMax"], bounds["LatMax"]),
    ]

    xs, ys = [], []
    for lon, lat in corners:
        x, y = transformer.transform(lon, lat)
        xs.append(x)
        ys.append(y)

    return min(xs), min(ys), max(xs), max(ys)
    
# ──────────────────────────────────────────────────────────────────────────────
# EPSG from WKT
# ──────────────────────────────────────────────────────────────────────────────
    
def infer_epsg_from_wkt(wkt):
    """
    Attempt to infer EPSG code from WKT definition.
    Returns EPSG integer or None.
    """
    if not wkt:
        return None

    try:
        crs = CRS.from_wkt(wkt)
    except CRSError:
        return None

    auth = crs.to_authority()
    if auth and auth[0] == "EPSG":
        try:
            return int(auth[1])
        except ValueError:
            return None

    return None

# ──────────────────────────────────────────────────────────────────────────────
# TXT Report Parser (MATCHES YOUR FILE EXACTLY)
# ──────────────────────────────────────────────────────────────────────────────

def parse_bim_report(txt_path):
    if not os.path.exists(txt_path):
        raise FileNotFoundError(txt_path)

    records = []
    current = {}

    with open(txt_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()

            # Skip separators / headers
            if not line or line.startswith("=") or line.startswith("-"):
                continue

            if line.startswith("BIM File"):
                if current:
                    records.append(current)
                current = {
                    "BIM_File": line.split(":", 1)[1].strip()
                }
                continue

            if ":" not in line:
                continue

            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()

            # Normalize keys we care about
            KEY_MAP = {
                "DataType": "DataType",
                "Georeference Status": "Georeference_Status",
                "SpatialReference": "SpatialReference",
                "SpatialReference WKT": "SpatialReference_WKT",
                "ExteriorShell Extent (XMin)": "XMin",
                "ExteriorShell Extent (YMin)": "YMin",
                "ExteriorShell Extent (XMax)": "XMax",
                "ExteriorShell Extent (YMax)": "YMax",
                "ExteriorShell Extent (ZMin)": "ZMin",
                "ExteriorShell Extent (ZMax)": "ZMax",
            }

            if key in KEY_MAP:
                norm_key = KEY_MAP[key]
                try:
                    val = float(val)
                except ValueError:
                    pass
                current[norm_key] = val

    if current:
        records.append(current)

    return records


# ──────────────────────────────────────────────────────────────────────────────
# Validation Logic
# ──────────────────────────────────────────────────────────────────────────────

def validate_extent(rec):
    sr = rec.get("SpatialReference")
    wkt = rec.get("SpatialReference_WKT")

    xmin = rec.get("XMin")
    ymin = rec.get("YMin")
    xmax = rec.get("XMax")
    ymax = rec.get("YMax")

    # Initialize result FIRST
    result = {
        "BIM_File": rec.get("BIM_File"),
        "Declared_SpatialReference": sr,
        "EPSG": None,
        "CRS_Type": None,
        "Unit": None,
        "CRS_AreaOfUse": None,
        "Extent_Status": None,
        "Diagnostics": [],
    }

    # 1) Try ESRI name → EPSG
    epsg = ESRI_TO_EPSG.get(sr)

    # 2) Fallback: infer EPSG from WKT
    if epsg is None and wkt:
        epsg = infer_epsg_from_wkt(wkt)
        if epsg:
            result["Diagnostics"].append(
                f"EPSG inferred from WKT definition (EPSG:{epsg})."
            )

    # 3) Fail cleanly if CRS unresolved
    if not epsg:
        result["Extent_Status"] = "UNKNOWN_CRS"
        result["Diagnostics"].append(
            "Unable to resolve CRS via ESRI name or WKT."
        )
        return result

    # 4) Load CRS bounds from EPSG registry
    bounds = load_crs_bounds(epsg)
    if not bounds:
        result["Extent_Status"] = "UNKNOWN_EPSG"
        result["Diagnostics"].append(
            "Unable to load CRS bounds from EPSG registry."
        )
        return result

    result["EPSG"] = epsg
    result["CRS_Type"] = bounds["type"]
    result["Unit"] = bounds["unit"]
    result["CRS_AreaOfUse"] = bounds["name"]

    # 5) Validate extents
    if bounds["type"] == "Geographic":
        inside = (
            bounds["LonMin"] <= xmin <= bounds["LonMax"]
            and bounds["LonMin"] <= xmax <= bounds["LonMax"]
            and bounds["LatMin"] <= ymin <= bounds["LatMax"]
            and bounds["LatMin"] <= ymax <= bounds["LatMax"]
        )
    else:
        pxmin, pymin, pxmax, pymax = geographic_bounds_to_projected(epsg, bounds)
        inside = (
            pxmin <= xmin <= pxmax
            and pxmin <= xmax <= pxmax
            and pymin <= ymin <= pymax
            and pymin <= ymax <= pymax
        )

    result["Extent_Status"] = "INSIDE" if inside else "OUTSIDE"

    if not inside:
        result["Diagnostics"].append(
            "Extent outside CRS Area of Use."
        )

    return result

# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main(report_path=None):
    print("\n=== BIM GEOREFERENCING VALIDATION ===\n")

    if report_path is None:
        report_path = (
            input("Path to BIM report (.txt): ")
            .strip()
            .strip('"')
            .strip("'")
        )

    if not report_path:
        raise ValueError("No report path provided.")

    if not os.path.exists(report_path):
        raise FileNotFoundError(f"Input report not found: {report_path}")

    records = parse_bim_report(report_path)
    print(f"Parsed {len(records)} BIM records.")

    results = [validate_extent(r) for r in records]

    output = {
        "metadata": {
            "source_report": report_path,
            "generated_on": datetime.now().isoformat(),
            "record_count": len(results),
        },
        "results": results,
    }

    output_path = os.path.splitext(report_path)[0] + "_validation.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ JSON report written to:\n{output_path}")
    
if __name__ == "__main__":
    main()
