# BIM CRS Extent Validator

A lightweight Python utility that validates BIM model extents against their declared Coordinate Reference System (CRS).

The script parses an ArcGIS Pro BIM georeferencing report (`.txt`), checks whether spatial extents fall within valid EPSG domain bounds, detects CRS mismatches, and outputs a structured JSON validation report.

**`The report is genearated from this script https://github.com/GeospatialBIM/CRS_Extent`**

---

## Requirements

- **ArcGIS Pro** (3.6 recommended)
- **Python 3.x** (installed with ArcGIS Pro)
- **ArcPy** (comes with ArcGIS Pro)

**Optional:** pyproj (for reprojection diagnostics)

---

## What This Tool Solves

BIM data often appears *georeferenced* but may:
- Use the wrong CRS declaration
- Contain UTM coordinates declared as geographic (or vice‑versa)
- Fall outside valid EPSG domain extents
- Be un‑georeferenced or incorrectly shifted

This tool **flags those issues automatically** before the data is consumed in GIS workflows.

---

## Features

✅ Parses ArcGIS BIM georeferencing reports  
✅ Maps ESRI spatial references to EPSG codes  
✅ Validates extents against EPSG domain bounds  
✅ Detects CRS mismatches (degrees vs meters)  
✅ Optional reprojection diagnostics (via `pyproj`)  
✅ Outputs clean, structured JSON  
✅ Works across multiple BIM files in a single report  

---

## Input

- ArcGIS Pro BIM Georeferencing Report (`.txt`) https://github.com/GeospatialBIM/CRS_Extent
- Typically generated when inspecting BIM / IFC layers in ArcGIS Pro

---

## Output

A JSON file with:
- Source metadata
- Spatial reference details
- Extent validity (`INSIDE`, `OUTSIDE`, `SR_MISMATCH`, `UNKNOWN`)
- Diagnostics and warnings

---

## License

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy...

---

## Disclaimer

This tool validates only the **spatial reference (CRS) and coordinate extents explicitly recorded in the input BIM file or report**.

The results do **not** guarantee that the BIM data is correctly georeferenced in real‑world space.  
Incorrect origins, offsets, rotations, unit assumptions, or authoring‑tool errors may still exist even if extents appear valid.

It is the responsibility of the **data author, vendor, or data owner** to ensure that the BIM data is:
- Correctly georeferenced
- Aligned with the intended coordinate reference system
- Suitable for downstream GIS, engineering, or asset‑management workflows

This tool should be used as a **diagnostic aid**, not as authoritative geospatial validation.


Example:

```json
{
  "Extent_Status": "SR_MISMATCH",
  "Diagnostics": [
    "Geographic CRS declared but extents are metric (UTM-like)."
  ]
}


