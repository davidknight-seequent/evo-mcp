---
name: workspace-lister
description: Lists and discovers Evo platform workspaces with filtering capabilities. Use when user asks to list, find, search, show, or discover workspaces in Evo.
---

# Workspace Lister

## Purpose

This skill helps users discover and list workspaces in the Seequent Evo platform. It provides filtering capabilities by workspace name and deletion status, making it easy to find specific workspaces or browse all available workspaces.

## When to Use

Use this skill when users ask to:
- List workspaces
- Find workspaces by name
- Show all available workspaces
- Discover workspaces in their Evo instance
- Check which workspaces they have access to
- Search for specific workspace names

## Core Functionality

### List Workspaces

The primary function lists workspaces with optional filtering.

**Parameters:**
- `name` (optional): Filter workspaces by name. Leave empty to show all workspaces.
- `deleted` (optional): Include deleted workspaces in results (default: false)
- `limit` (optional): Maximum number of results to return (default: 50)

**Returns:**
A list of workspace objects containing:
- `id`: Workspace UUID
- `name`: Display name of the workspace
- `description`: Workspace description
- `user_role`: User's role in the workspace (e.g., VIEWER, CONTRIBUTOR, ADMINISTRATOR)
- `created_at`: Timestamp when workspace was created
- `updated_at`: Timestamp when workspace was last updated

## Usage Examples

### Example 1: List All Workspaces
```python
from evo_mcp.tools.general_tools import register_general_tools
from evo_mcp.context import get_evo_context

# Initialize context
evo_context = get_evo_context()

# List all workspaces (up to 50)
workspaces = await evo_context.workspace_client.list_workspaces(limit=50)

# Display results
for ws in workspaces.items():
    print(f"{ws.display_name} ({ws.id})")
```

### Example 2: Find Workspace by Name
```python
# Search for workspaces with "Mining" in the name
workspaces = await evo_context.workspace_client.list_workspaces(
    name="Mining",
    limit=50
)

# Display matching workspaces
for ws in workspaces.items():
    print(f"Found: {ws.display_name}")
    print(f"  ID: {ws.id}")
    print(f"  Role: {ws.user_role.name if ws.user_role else 'None'}")
```

### Example 3: Include Deleted Workspaces
```python
# List both active and deleted workspaces
workspaces = await evo_context.workspace_client.list_workspaces(
    deleted=True,
    limit=100
)

for ws in workspaces.items():
    status = "DELETED" if ws.deleted_at else "ACTIVE"
    print(f"{ws.display_name} - {status}")
```

## Best Practices

1. **Start Broad, Then Filter**: When users are unsure of workspace names, list all workspaces first, then apply filters based on what they see.

2.  **Check User Roles**: Pay attention to the `user_role` field - users may have different permissions in different workspaces.

3. **Handle Empty Results**: If filtering returns no results, suggest removing filters or checking spelling.

4. **Use Appropriate Limits**: Default limit of 50 is usually sufficient. Increase only if user explicitly needs more results.

## Common User Requests

| User Says | What To Do |
|-----------|------------|
| "Show me all my workspaces" | List with no filters, default limit |
| "Find workspace named X" | List with `name=X` filter |
| "Do I have any deleted workspaces?" | List with `deleted=True` |
| "Show me the first 10 workspaces" | List with `limit=10` |

## Integration Points

This skill integrates with:
- **Workspace Context**: All workspace operations require knowing the workspace ID, which this skill provides
- **Object Operations**: Once a workspace is identified, users can query objects within it
- **Workspace Management**: Admin users can manage workspace settings after identifying the workspace

## Error Handling

Common issues and solutions:
- **Authentication errors**: Ensure Evo credentials are configured (check `EVO_CLIENT_ID` environment variable)
- **No workspaces found**: User may not have access to any workspaces yet
- **Name filter too specific**: Suggest using partial names or removing filter

## Technical Details

**API Endpoint**: Uses Evo Workspace API  
**Authentication**: Requires valid OAuth tokens (managed by `evo_mcp.context`)  
**Rate Limits**: Follows standard Evo API rate limits  
**Pagination**: Controlled by `limit` parameter

## Next Steps After Listing

Once workspaces are listed, users typically want to:
1. Get detailed workspace information (use `get_workspace` tool)
2. List objects within a workspace (use `list_objects` tool)
3. Create new objects in a workspace (use object creation tools)
4. Copy objects between workspaces (use `copy_object` tool)
