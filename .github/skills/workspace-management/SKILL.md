---
name: workspace-management
description: Lists, discovers, creates, and manages Evo workspaces. Use when user asks to list, find, search, create, get details, snapshot, duplicate workspaces, or select instances.
---

# Workspace Management

## Purpose

This skill provides comprehensive workspace management for the Seequent Evo platform, including discovering and listing workspaces, viewing details, creating new workspaces, creating snapshots for backup and recovery, and duplicating workspaces for testing or archival purposes.

## When to Use

Use this skill when users ask to:
- List all workspaces or filter by name
- Find or search for specific workspaces
- Show available workspaces in their Evo instance
- Discover what workspaces they have access to
- Get detailed workspace information
- Create new workspaces
- Create workspace snapshots for backup
- Duplicate workspaces for testing or archival
- Select or switch Evo instances

## Available Generic Tools

### 1. Query Workspaces

**Tool:** `evo_query`

```python
# List all workspaces
await evo_query(
    entity_type="workspace",
    limit=50
)

# Find workspaces by name
await evo_query(
    entity_type="workspace",
    name_filter="Mining",
    limit=50
)

# Include deleted workspaces
await evo_query(
    entity_type="workspace",
    include_deleted=True,
    limit=100
)
```

### 2. Get Workspace Details

**Tool:** `evo_get`

```python
# Get by ID
await evo_get(
    entity_type="workspace",
    workspace_id="uuid-here"
)

# Get by name
await evo_get(
    entity_type="workspace",
    name="My Workspace"
)
```

### 3. Create Workspace

**Tool:** `evo_create`

```python
await evo_create(
    entity_type="workspace",
    name="New Project Workspace",
    description="Workspace for Q1 2026 exploration data"
)
```

### 4. Snapshot Workspace

**Tool:** `evo_manage`

```python
await evo_manage(
    operation="snapshot",
    workspace_id="uuid-here"
)
```

### 5. Duplicate Workspace

**Tool:** `evo_manage`

```python
await evo_manage(
    operation="duplicate",
    source_workspace_id="uuid-here",
    new_name="Copy of My Workspace"
)
```

### 6. Select Instance

**Tool:** `evo_manage`

```python
# By name
await evo_manage(
    operation="select_instance",
    instance_name="My Organization"
)

# By ID
await evo_manage(
    operation="select_instance",
    instance_id="uuid-here"
)
```

## Common Workflows

### Workflow 1: Find and Inspect a Workspace

```python
# Step 1: List workspaces to find the one you need
workspaces = await evo_query(
    entity_type="workspace",
    name_filter="Exploration",
    limit=20
)

# Step 2: Get detailed information
workspace = await evo_get(
    entity_type="workspace",
    workspace_id=workspaces[0]["id"]
)
```

### Workflow 2: Create and Archive Pattern

```python
# Step 1: Create snapshot before making changes
snapshot = await evo_manage(
    operation="snapshot",
    workspace_id="workspace-uuid"
)

# Step 2: Make changes (create objects, etc.)
# ... your work here ...

# Step 3: Create another snapshot after changes
final_snapshot = await evo_manage(
    operation="snapshot",
    workspace_id="workspace-uuid"
)
```

### Workflow 3: Duplicate for Testing

```python
# Create a test copy of production workspace
test_workspace = await evo_manage(
    operation="duplicate",
    source_workspace_id="prod-workspace-uuid",
    new_name="Test Environment - 2026-02"
)

# Now work in test workspace
workspace_id = test_workspace["new_workspace_id"]
```
Start Broad, Then Filter**: When users are unsure of workspace names, list all workspaces first without filters, then apply name filtering based on results

2. **Check User Roles**: Pay attention to `user_role` in workspace details - different permissions in different workspaces

3. **Snapshot Before Major Changes**: Always create snapshots before bulk operations or significant changes to preserve current state

4. **Handle Empty Results**: If filtering returns no results, suggest removing filters or checking workspace name spelling

5. **Meaningful Names**: Use descriptive names for duplicated workspaces with dates or purpose

6. **Instance Selection**: Select the correct Evo instance before performing any workspace operations

7. **Use Appropriate Limits**: Default limit is usually sufficient; increase only if user explicitly needs more result
4. **Meaningful Names**: Use descriptive names for duplicated workspaces with dates or purpose

5. **Instance Selection**: Select the correct Evo instance before performing any workspace operations

## Common Patterns

| User Request | Tool Chain |
|--------------|-----------|
| "Show my workspaces" | `evo_query` with entity_type="workspace" |
| "Create workspace X" | `evo_create` with entity_type="workspace" |
| "Get details on workspace Y" | `evo_get` with entity_type="workspace" |
| "Backup workspace Z" | `evo_manage` with operation="snapshot" |
| "Copy workspace A to B" | `evo_manage` with operation="duplicate" |
| "Switch to instance X" | `evo_manage` with operation="select_instance" |

## Error Handling

**No workspaces found:**
- User may not have access
- Check if correct instance is selected
- Try without name filter

**Permission denied:**
- Check user_role - may need CONTRIBUTOR or ADMINISTRATOR role
- Some operations require higher privileges

**Snapshot failed:**
- Workspace may be in use
- Check workspace health first
- Retry after a moment

## Integration with Other Skills

This skill provides foundational workspace operations that other skills build upon:

- **Object Management**: Once you have workspace_id, use object skills
- **Data Import**: Need workspace_id for creating objects from CSV
- **Collaboration**: Workspace details show who has access

## Technical Notes

- All UUIDs are strings in query results
- Timestamps are ISO 8601 format
- Empty strings in parameters are treated as None
- `limit` parameter defaults vary by entity type
