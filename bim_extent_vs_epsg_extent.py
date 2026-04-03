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
    xmin, ymin, xmax, ymax = rec.get("XMin"), rec.get("YMin"), rec.get("XMax"), rec.get("YMax")

    result = {
        "BIM_File": rec.get("BIM_File"),
        "Declared_SpatialReference": sr,
        "EPSG": None,
        "CRS_Type": None,
        "Unit": None,
        "Extent_Status": None,
        "SR_Mismatch": False,
        "Diagnostics": []
    }

    epsg = ESRI_TO_EPSG.get(sr)
    if epsg is None:
        result["Extent_Status"] = "UNKNOWN_SPATIAL_REFERENCE"
        result["Diagnostics"].append("SpatialReference not mapped to EPSG.")
        return result

    bounds = CRS_BOUNDS[epsg]
    result["EPSG"] = epsg
    result["CRS_Type"] = bounds["type"]
    result["Unit"] = bounds["unit"]

    inside = (
        bounds["XMin"] <= xmin <= bounds["XMax"] and
        bounds["XMin"] <= xmax <= bounds["XMax"] and
        bounds["YMin"] <= ymin <= bounds["YMax"] and
        bounds["YMin"] <= ymax <= bounds["YMax"]
    )

    # CRS mismatch heuristic
    if bounds["type"] == "Geographic":
        if abs(xmin) > 360 or abs(ymin) > 90:
            result["SR_Mismatch"] = True
            result["Extent_Status"] = "SR_MISMATCH"
            result["Diagnostics"].append(
                "Geographic CRS declared but extents are metric (UTM-like)."
            )

            if PYPROJ_AVAILABLE:
                try:
                    t = Transformer.from_crs(25831, 4258, always_xy=True)
                    lon, lat = t.transform((xmin + xmax) / 2, (ymin + ymax) / 2)
                    result["Diagnostics"].append(
                        f"Reprojected as EPSG:25831 → center ≈ ({lon:.5f}°, {lat:.5f}°)"
                    )
                except Exception:
                    pass

            return result

    result["Extent_Status"] = "INSIDE" if inside else "OUTSIDE"

    if not inside:
        result["Diagnostics"].append("Extent outside valid CRS domain.")

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("\n=== BIM GEOREFERENCING VALIDATION ===\n")
    report_path = input("Path to BIM report (.txt): ").strip()

    # ── Input validation ────────────────────────────────────────────────────
    if not os.path.isfile(report_path):
        print("\n❌ ERROR: Input report not found.")
        print(f"   Path provided: {report_path}")
        print("   Please verify the file exists and try again.\n")
        return

    try:
        records = parse_bim_report(report_path)
    except Exception as e:
        print("\n❌ ERROR: Failed to read or parse the report.")
        print(f"   Reason: {e}\n")
        return

    if not records:
        print("\n⚠️ WARNING: No BIM records were found in the report.")
        print("   The file may be empty or not in the expected format.\n")
        return

    print(f"Parsed {len(records)} BIM records.\n")

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

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
    except Exception as e:
        print("\n❌ ERROR: Failed to write output JSON.")
        print(f"   Reason: {e}\n")
        return

    print(f"✅ Validation complete.")
    print(f"✅ JSON report written to:\n{output_path}\n")
