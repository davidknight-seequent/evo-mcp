---
name: csv-to-geoscience-objects
description: Create geoscience objects from CSV files (pointsets, line segments, downhole data). Use when user wants to import data from CSV, create objects from files, or build geoscience objects.
---

# CSV to Geoscience Objects

## Purpose

This skill guides you through creating geoscience objects in Evo from CSV data using the consolidated `evo_build_object` tool.

## When to Use

Use this skill when users want to:
- Import CSV data into Evo
- Create pointsets from coordinate data
- Build line segments from vertices and segments
- Create downhole collections from collar/survey/interval data
- Build interval objects with spatial coordinates

## Supported Object Types

| Type | Description | CSV Files Needed |
|------|-------------|------------------|
| **pointset** | Points in 3D space with attributes | Single CSV with X/Y/Z coordinates |
| **line_segments** | Connected line segments | Vertices CSV + Segments CSV |
| **downhole_collection** | Drillhole data | Collar + Survey + Interval CSVs |
| **downhole_intervals** | Intervals with spatial coords | Single CSV with coordinates and depths |

## The Generic Tool: evo_build_object

**Tool:** `evo_build_object`

**Key Parameters:**
- `object_type`: Type of object to build
- `workspace_id`: Target workspace
- `object_path`: Where to store the object
- `name`: Object name
- `csv_files`: JSON mapping of file purposes to paths
- `column_mapping`: JSON with column name mappings
- `dry_run`: Validate before creating (recommended first step)

## Step-by-Step Workflows

### Workflow 1: Create Pointset from CSV

**Scenario:** User has a CSV with sample locations (X, Y, Z coordinates)

```python
# Step 1: Configure data directory
await filesystem_ops(
    operation="configure",
    directory="/path/to/data"
)

# Step 2: List available CSV files
files = await filesystem_ops(
    operation="list",
    file_pattern="*.csv"
)

# Step 3: Preview the CSV to understand columns
preview = await filesystem_ops(
    operation="preview",
    file_path="samples.csv",
    max_rows=5
)

# Step 4: Build pointset (dry run first)
import json

result = await evo_build_object(
    object_type="pointset",
    workspace_id="workspace-uuid",
    object_path="/data/my_samples.json",
    name="Exploration Samples Q1",
    csv_files=json.dumps({
        "points": "samples.csv"
    }),
    column_mapping=json.dumps({
        "x": "Easting",
        "y": "Northing",
        "z": "Elevation",
        "attributes": ["Au_ppm", "Cu_pct", "Sample_ID"]
    }),
    description="Q1 2026 exploration samples",
    crs="EPSG:32755",
    dry_run=True  # Validate first!
)

# Step 5: If validation passed, create for real
if result["status"] == "validated":
    final = await evo_build_object(
        # ... same parameters ...
        dry_run=False
    )
```

### Workflow 2: Create Line Segments

**Scenario:** User has structural geology lines (vertices + segments)

```python
# Build line segments
result = await evo_build_object(
    object_type="line_segments",
    workspace_id="workspace-uuid",
    object_path="/data/fault_traces.json",
    name="Major Fault Traces",
    csv_files=json.dumps({
        "vertices": "fault_vertices.csv",
        "segments": "fault_segments.csv"
    }),
    column_mapping=json.dumps({
        "x": "X",
        "y": "Y",
        "z": "Z",
        "start_index": "start_vertex_id",
        "end_index": "end_vertex_id",
        "attributes": ["fault_name", "confidence"]
    }),
    description="Interpreted fault traces from mapping",
    crs="EPSG:32755",
    dry_run=True
)
```

### Workflow 3: Create Downhole Collection

**Scenario:** User has drillhole data (collar, survey, lithology intervals)

```python
# Build downhole collection with intervals
result = await evo_build_object(
    object_type="downhole_collection",
    workspace_id="workspace-uuid",
    object_path="/data/drilling_campaign_2026.json",
    name="2026 Q1 Drilling Campaign",
    csv_files=json.dumps({
        "collar": "collars.csv",
        "survey": "surveys.csv",
        "intervals": {
            "lithology": "lithology.csv",
            "assay": "assay.csv"
        }
    }),
    column_mapping=json.dumps({
        "collar": {
            "id": "HOLEID",
            "x": "X",
            "y": "Y",
            "z": "Z"
        },
        "survey": {
            "id": "HOLEID",
            "depth": "DEPTH",
            "azimuth": "AZIMUTH",
            "dip": "DIP"
        },
        "intervals": {
            "lithology": {
                "id": "HOLEID",
                "from": "FROM",
                "to": "TO",
                "attributes": ["LITH_CODE", "DESCRIPTION"]
            },
            "assay": {
                "id": "HOLEID",
                "from": "FROM",
                "to": "TO",
                "attributes": ["Au_ppm", "Cu_pct", "Ag_ppm"]
            }
        }
    }),
    description="Q1 drilling with lithology and assay data",
    crs="MGA Zone 55",
    dry_run=True
)
```

### Workflow 4: Create Downhole Intervals

**Scenario:** User has interval data with pre-calculated spatial coordinates

```python
# Build downhole intervals
result = await evo_build_object(
    object_type="downhole_intervals",
    workspace_id="workspace-uuid",
    object_path="/data/composites.json",
    name="3m Composited Intervals",
    csv_files=json.dumps({
        "intervals": "composites.csv"
    }),
    column_mapping=json.dumps({
        "hole_id": "HOLEID",
        "from": "FROM",
        "to": "TO",
        "start_x": "START_X",
        "start_y": "START_Y",
        "start_z": "START_Z",
        "end_x": "END_X",
        "end_y": "END_Y",
        "end_z": "END_Z",
        "mid_x": "MID_X",
        "mid_y": "MID_Y",
        "mid_z": "MID_Z",
        "attributes": ["Au_ppm", "CU_pct"],
        "is_composited": True
    }),
    description="3m length composites for resource estimation",
    crs="EPSG:32755",
    dry_run=False
)
```

## Best Practices

### 1. Always Use Dry Run First

```python
# First validate
result = await evo_build_object(..., dry_run=True)

# Check messages
if result["status"] == "validated":
    print("Validation passed:", result["messages"])
    # Now create for real
    await evo_build_object(..., dry_run=False)
else:
    print("Validation failed:", result["messages"])
```

### 2. Preview CSV Before Processing

```python
# See what columns are available
preview = await filesystem_ops(
    operation="preview",
    file_path="mydata.csv",
    max_rows=10
)

print("Available columns:", preview["columns"])
print("Data types:", preview["dtypes"])
```

### 3. Use Meaningful Object Paths

```python
# Good paths - organized and descriptive
"/data/exploration/samples_2026_q1.json"
"/geology/faults/major_structures.json"
"/drilling/campaign_01/collars.json"

# Avoid - vague or cluttered
"/object1.json"
"/data.json"
```

### 4. Include CRS Information

Always specify the coordinate reference system:

```python
crs="EPSG:32755"  # MGA Zone 55
crs="EPSG:4326"   # WGS84
crs="Custom CRS"  # Project-specific
```

## Column Mapping Examples

### Simple Pointset
```json
{
  "x": "Easting",
  "y": "Northing",
  "z": "RL",
  "attributes": ["Au", "Cu", "Sample_Type"]
}
```

### Line Segments
```json
{
  "x": "X",
  "y": "Y",
  "z": "Z",
  "start_index": "vertex_start",
  "end_index": "vertex_end",
  "attributes": ["feature_type", "confidence"]
}
```

### Downhole Collection (Complex)
```json
{
  "collar": {
    "id": "HOLEID",
    "x": "EAST",
    "y": "NORTH",
    "z": "ELEV"
  },
  "survey": {
    "id": "HOLEID",
    "depth": "DEPTH_M",
    "azimuth": "AZIM",
    "dip": "DIP_ANGLE"
  },
  "intervals": {
    "lithology": {
      "id": "HOLEID",
      "from": "FROM_M",
      "to": "TO_M",
      "attributes": ["LITH", "ROCK_TYPE"]
    }
  }
}
```

## Common Errors and Solutions

**Error: "Column 'X' not found in CSV"**
- **Solution**: Preview the CSV first to see actual column names
- Column names are case-sensitive

**Error: "workspace_id required"**
- **Solution**: Query workspaces first to get the UUID

**Error: "Data directory not configured"**
- **Solution**: Run `filesystem_ops` with operation="configure" first

**Validation Warnings:**
- Review messages from dry run
- Common issues: missing required columns, invalid data types
- Fix CSV data and retry

## Workflow Template

Use this template for any CSV import:

```python
# 1. Setup
await filesystem_ops(operation="configure", directory="/data/path")

# 2. Discover
files = await filesystem_ops(operation="list")

# 3. Preview
preview = await filesystem_ops(operation="preview", file_path="myfile.csv")

# 4. Query workspace
workspaces = await evo_query(entity_type="workspace", name_filter="MyProject")
workspace_id = workspaces[0]["id"]

# 5. Validate
result = await evo_build_object(
    object_type="...",
    workspace_id=workspace_id,
    csv_files=json.dumps({...}),
    column_mapping=json.dumps({...}),
    dry_run=True
)

# 6. Create
if result["status"] == "validated":
    await evo_build_object(..., dry_run=False)
```

## Integration Points

- **Filesystem Operations**: Use `filesystem_ops` to discover and preview CSV files
- **Workspace Query**: Use `evo_query` to find target workspace
- **Object Query**: Use `evo_query` to verify created objects

## Technical Notes

- CSV files must be accessible in configured data directory
- Column mappings are case-sensitive
- JSON parameters must be valid JSON strings
- Dry run does NOT create the object - use for validation only
- All coordinates assumed to be in specified CRS
