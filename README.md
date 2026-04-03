# BIM Georeferencing Validation

**Spatial Reference & Extent Validation for BIM (IFC / Revit) Reports**

---

## Overview

This repository contains a Python utility that inspects and validates **BIM georeferencing metadata** as reported by ArcGIS Pro (or similar tools).

The script checks whether the recorded **coordinate reference system (CRS)** and **model extents** fall within the valid **EPSG Area of Use** for the declared CRS. It supports both **projected and geographic coordinate systems** and produces a structured JSON report suitable for QA workflows.

---

## Disclaimer

**This tool validates only what is recorded in the file.**

It does **NOT** verify:
- Real‑world alignment
- Survey accuracy
- Authoring intent
- Correctness of transformations applied in upstream software

Passing validation indicates that *recorded extents* fall within the expected CRS domain — **not** that the BIM model is correctly georeferenced in reality.

The data producer remains responsible for spatial correctness.

---

## Features

- Parses BIM georeferencing reports (`.txt`)
- Resolves CRS using:
  - ESRI spatial reference names
  - Automatic EPSG inference from WKT (fallback)
- Dynamically loads CRS **Area of Use** from the EPSG registry
- Validates extents against CRS domain
- Supports projected and geographic CRSs
- Outputs structured JSON results with diagnostics

---

## Input

A plain‑text BIM georeferencing report (typically from ArcGIS Pro) containing fields such as:

- `BIM File`
- `SpatialReference`
- `SpatialReference WKT` (optional)
- `ExteriorShell Extent (XMin, YMin, XMax, YMax, ZMin, ZMax)`

---

## Output

A JSON file written alongside the input report:

### Example Output

```json
{
  "BIM_File": "bridge.ifc",
  "Declared_SpatialReference": "ETRS_1989_UTM_Zone_31N",
  "EPSG": 25831,
  "CRS_Type": "Projected",
  "Unit": "metre",
  "CRS_AreaOfUse": "Between 0°E and 6°E, northern hemisphere",
  "Extent_Status": "INSIDE",
  "Diagnostics": [
    "EPSG inferred from WKT definition (EPSG:25831)."
  ]
}
