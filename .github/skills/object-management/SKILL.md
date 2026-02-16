---
name: object-management
description: Query, inspect, and manage geoscience objects in Evo workspaces. Use when user wants to list objects, get object details, view object content, copy objects between workspaces, or query object versions.
---

# Object Management

## Purpose

This skill guides you through discovering, inspecting, and managing geoscience objects within Evo workspaces using consolidated generic tools.

## When to Use

Use this skill when users want to:
- List objects in a workspace
- Search for specific objects
- Get object metadata
- View object content
- Copy objects between workspaces
- Check object versions
- Filter objects by type

## Available Generic Tools

### 1. List Objects

**Tool:** `evo_query`

```python
# List all objects in workspace
await evo_query(
    entity_type="object",
    workspace_id="workspace-uuid",
    limit=100
)

# Filter by schema type
await evo_query(
    entity_type="object",
    workspace_id="workspace-uuid",
    schema_filter="pointset",
    limit=50
)

# Include deleted objects
await evo_query(
    entity_type="object",
    workspace_id="workspace-uuid",
    include_deleted=True
)
```

### 2. Get Object Metadata

**Tool:** `evo_get`

```python
# Get by object ID
await evo_get(
    entity_type="object",
    workspace_id="workspace-uuid",
    object_id="object-uuid"
)

# Get by object path
await evo_get(
    entity_type="object",
    workspace_id="workspace-uuid",
    object_path="/data/my_object.json"
)

# Get specific version
await evo_get(
    entity_type="object",
    workspace_id="workspace-uuid",
    object_id="object-uuid",
    version="version-id"
)
```

### 3. Get Object Content

**Tool:** `evo_get`

```python
# Get full object including content
await evo_get(
    entity_type="object_content",
    workspace_id="workspace-uuid",
    object_id="object-uuid"
)
```

### 4. List Object Versions

**Tool:** `evo_query`

```python
# Get version history
await evo_query(
    entity_type="version",
    workspace_id="workspace-uuid",
    object_id="object-uuid"
)
```

### 5. Copy Object Between Workspaces

**Tool:** `evo_manage`

```python
# Copy by object ID
await evo_manage(
    operation="copy_object",
    source_workspace_id="source-uuid",
    target_workspace_id="target-uuid",
    object_id="object-uuid"
)

# Copy by path
await evo_manage(
    operation="copy_object",
    source_workspace_id="source-uuid",
    target_workspace_id="target-uuid",
    object_path="/data/my_object.json"
)
```

## Common Workflows

### Workflow 1: Discover Objects

```python
# Step 1: Find workspace
workspaces = await evo_query(
    entity_type="workspace",
    name_filter="Exploration"
)
workspace_id = workspaces[0]["id"]

# Step 2: List all objects
objects = await evo_query(
    entity_type="object",
    workspace_id=workspace_id,
    limit=100
)

# Step 3: Filter to specific type
pointsets = await evo_query(
    entity_type="object",
    workspace_id=workspace_id,
    schema_filter="pointset"
)

print(f"Found {len(pointsets)} pointsets")
for obj in pointsets:
    print(f"  - {obj['name']} at {obj['path']}")
```

### Workflow 2: Inspect Object Details

```python
# Get metadata
metadata = await evo_get(
    entity_type="object",
    workspace_id="workspace-uuid",
    object_id="object-uuid"
)

print(f"Name: {metadata['name']}")
print(f"Type: {metadata['schema_id']}")
print(f"Created: {metadata['created_at']}")

# Get full content if needed
content = await evo_get(
    entity_type="object_content",
    workspace_id="workspace-uuid",
    object_id="object-uuid"
)

# Analyze content structure
print("Content keys:", content['content'].keys())
```

### Workflow 3: Copy Objects to New Workspace

```python
# Step 1: Query source objects
source_objects = await evo_query(
    entity_type="object",
    workspace_id="source-workspace-uuid",
    schema_filter="pointset"
)

# Step 2: Create target workspace
target_ws = await evo_create(
    entity_type="workspace",
    name="Copied Data Workspace",
    description="Objects copied from exploration workspace"
)

# Step 3: Copy each object
for obj in source_objects:
    result = await evo_manage(
        operation="copy_object",
        source_workspace_id="source-workspace-uuid",
        target_workspace_id=target_ws["id"],
        object_id=obj["id"]
    )
    print(f"Copied: {obj['name']}")
```

### Workflow 4: Version History Analysis

```python
# Get object metadata
obj = await evo_get(
    entity_type="object",
    workspace_id="workspace-uuid",
    object_path="/data/samples.json"
)

# List all versions
versions = await evo_query(
    entity_type="version",
    workspace_id="workspace-uuid",
    object_id=obj["id"]
)

print(f"Object has {len(versions)} versions")
for v in versions:
    print(f"  Version: {v['version_id']}")
    print(f"  Created: {v['created_at']}")
    print(f"  By: {v['created_by']}")

# Get specific version
old_version = await evo_get(
    entity_type="object",
    workspace_id="workspace-uuid",
    object_id=obj["id"],
    version=versions[-1]["version_id"]  # Oldest version
)
```

## Schema Types Reference

Common schema types for filtering:

| Schema ID | Description | Typical Use |
|-----------|-------------|-------------|
| `pointset` | Point cloud data | Samples, sensors, observations |
| `line-segments` | Connected lines | Faults, contacts, polylines |
| `downhole-collection` | Drillhole data | Collar, survey, intervals |
| `downhole-intervals` | Interval data | Composites, assays, lithology |
| `triangle-mesh` | 3D mesh | Surfaces, geological models |
| `regular-3d-grid` | Block model | Resource blocks, grade shells |

## Best Practices

### 1. Start Broad, Then Filter

```python
# First, see what's there
all_objects = await evo_query(
    entity_type="object",
    workspace_id="workspace-uuid",
    limit=200
)

# Analyze schema types present
schema_types = set(obj["schema_id"] for obj in all_objects)
print("Available types:", schema_types)

# Then filter to what you need
specific = await evo_query(
    entity_type="object",
    workspace_id="workspace-uuid",
    schema_filter="pointset"
)
```

### 2. Use Object Paths for Organization

Good path structure:
```
/data/exploration/samples_q1.json
/data/exploration/samples_q2.json
/geology/faults/major_faults.json
/geology/faults/minor_faults.json
/drilling/campaign_01/collars.json
```

Query by path prefix patterns using client-side filtering after retrieval.

### 3. Check Versions Before Overwriting

```python
# Before updating, check if object exists
try:
    existing = await evo_get(
        entity_type="object",
        workspace_id="workspace-uuid",
        object_path="/data/my_object.json"
    )
    
    # Get version history
    versions = await evo_query(
        entity_type="version",
        workspace_id="workspace-uuid",
        object_id=existing["id"]
    )
    
    print(f"Object exists with {len(versions)} versions")
    print("Updating will create new version")
    
except Exception:
    print("Object doesn't exist, will create new")
```

### 4. Batch Operations with Context

```python
# Copy multiple related objects together
objects_to_copy = [
    "collar_data",
    "survey_data",
    "lithology"
]

for obj_name in objects_to_copy:
    path = f"/drilling/{obj_name}.json"
    
    result = await evo_manage(
        operation="copy_object",
        source_workspace_id="source-uuid",
        target_workspace_id="target-uuid",
        object_path=path
    )
    
    print(f"Copied {obj_name}")
```

## Common Patterns

| User Request | Tool Chain |
|--------------|-----------|
| "List all objects" | `evo_query` entity_type="object" |
| "Show me pointsets" | `evo_query` with schema_filter="pointset" |
| "Get object details" | `evo_get` entity_type="object" |
| "Show object content" | `evo_get` entity_type="object_content" |
| "Copy object to workspace Y" | `evo_manage` operation="copy_object" |
| "Check object versions" | `evo_query` entity_type="version" |

## Error Handling

**"workspace_id required"**
- Always query workspace first to get UUID
- Don't assume workspace IDs

**"Object not found"**
- Check spelling of object_path (case-sensitive)
- Verify object exists: list objects first
- Object may be deleted (check with include_deleted=True)

**"Permission denied"**
- User may not have access to workspace
- Check user role with workspace_get
- Some operations require specific permissions

**Copy failures:**
- Target path may already exist
- Check target workspace exists
- Verify sufficient permissions

## Advanced: Bulk Object Analysis

```python
# Analyze all objects in workspace
objects = await evo_query(
    entity_type="object",
    workspace_id="workspace-uuid",
    limit=500
)

# Group by schema type
from collections import defaultdict
by_type = defaultdict(list)

for obj in objects:
    by_type[obj["schema_id"]].append(obj)

# Report
for schema_type, objs in by_type.items():
    print(f"{schema_type}: {len(objs)} objects")
    
# Find recently created
import datetime
recent = [
    obj for obj in objects
    if obj["created_at"] and 
    datetime.datetime.fromisoformat(obj["created_at"]) > 
    datetime.datetime.now() - datetime.timedelta(days=7)
]

print(f"{len(recent)} objects created in last 7 days")
```

## Integration Points

- **Workspace Management**: Use workspace skills to get workspace_id
- **CSV Import**: After building objects, use this skill to verify they were created
- **Data Analysis**: Get object content for downstream analysis

## Technical Notes

- Object IDs are UUIDs as strings
- Paths are case-sensitive
- Schema filters are case-insensitive substring matches (client-side)
- Version history ordered newest first
- Object content can be very large - use metadata queries when possible
- Copy operations preserve object schema and content
