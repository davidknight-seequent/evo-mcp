# SPDX-FileCopyrightText: 2026 Bentley Systems, Incorporated
#
# SPDX-License-Identifier: Apache-2.0

"""
A FastMCP server that provides tools for interacting with the Evo platform,
including workspace management, object ops, and data transfer.

Configuration:
    Set MCP_TOOL_FILTER environment variable to filter tools and prompts:
    - "admin"   : Workspace management tools
    - "data"    : Object query, file operations, and management tools
    - "compute" : Compute and geostatistics tools
    - "all"     : All tools (default)

    Set MCP_TRANSPORT environment variable to choose transport mode:
    - "stdio" (default): Standard input/output, used by VS Code, Cursor, Claude Desktop
    - "http": Streamable HTTP, accessible via HTTP requests

    For HTTP transport, configure:
    - MCP_HTTP_HOST: Host to bind to (default: localhost)
    - MCP_HTTP_PORT: Port to listen on (default: 5000)

The environment variables can be set in a .env file or
passed directly to the MCP server as input parameters.
"""

import logging
import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.utilities.logging import configure_logging
from starlette.middleware import Middleware

from evo_mcp.client_auth import AuthMetadataPatchMiddleware, create_auth_provider
from evo_mcp.tools import (
    register_admin_tools,
    register_compute_tools,
    register_file_tools,
    register_filesystem_tools,
    register_general_tools,
    register_instance_users_admin_tools,
    register_object_builder_tools,
    register_object_staging_tools,
)

logger = logging.getLogger(__name__)
OBJECTS_REFERENCE_UNAVAILABLE = "Objects reference information is currently unavailable."

TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").lower()
VALID_TRANSPORTS = ["stdio", "http"]

if TRANSPORT not in VALID_TRANSPORTS:
    logging.warning("Invalid MCP_TRANSPORT '%s', defaulting to 'stdio'", TRANSPORT)
    TRANSPORT = "stdio"

HTTP_HOST = os.getenv("MCP_HTTP_HOST", "localhost")
HTTP_PORT = int(os.getenv("MCP_HTTP_PORT", "5000"))

CLIENT_DELEGATED_AUTH = os.getenv("CLIENT_DELEGATED_AUTH", "").lower() in ("1", "true")

if CLIENT_DELEGATED_AUTH and TRANSPORT != "http":
    logging.warning(
        "CLIENT_DELEGATED_AUTH=true has no effect with MCP_TRANSPORT='%s' — "
        "OAuth authentication is only supported with HTTP transport. Ignoring.",
        TRANSPORT,
    )
    CLIENT_DELEGATED_AUTH = False

TOOL_FILTER = os.getenv(
    "MCP_TOOL_FILTER",
    os.getenv(
        "MCP_AGENT_TYPE",
        "all",
    ),
).lower()
VALID_TOOL_FILTERS = ["admin", "data", "compute", "all"]

if TOOL_FILTER not in VALID_TOOL_FILTERS:
    logging.warning("Invalid MCP_TOOL_FILTER '%s', defaulting to 'all'", TOOL_FILTER)
    TOOL_FILTER = "all"

server_name = "Evo MCP Server" if TOOL_FILTER == "all" else f"Evo MCP Server ({TOOL_FILTER})"
public_base_url = os.getenv("MCP_PUBLIC_BASE_URL", f"http://{HTTP_HOST}:{HTTP_PORT}")
auth_provider = create_auth_provider(public_base_url) if CLIENT_DELEGATED_AUTH else None
mcp = FastMCP(server_name, auth=auth_provider)

configure_logging(tracebacks_max_frames=20)


def _get_objects_reference_content() -> str:
    """Load the objects reference content from a markdown file."""
    reference_path = Path(__file__).parent / "OBJECTS.md"
    try:
        with open(reference_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logging.error("Reference file not found at %s", reference_path)
        return OBJECTS_REFERENCE_UNAVAILABLE


register_general_tools(mcp)

if TOOL_FILTER in ["all", "admin"]:
    register_admin_tools(mcp)
    register_instance_users_admin_tools(mcp)
if TOOL_FILTER in ["all", "data"]:
    register_filesystem_tools(mcp)
    register_object_builder_tools(mcp)
    register_file_tools(mcp)
    if TOOL_FILTER == "data":
        print("Evo MCP Server configured for Data Agent")
    else:
        print("Evo MCP Server configured - Data tools enabled")

if TOOL_FILTER in ["all", "compute"]:
    register_compute_tools(mcp)
    register_object_staging_tools(mcp)
    if TOOL_FILTER == "compute":
        print("Evo MCP Server configured for Compute Agent")
    else:
        print("Evo MCP Server configured - Compute tools enabled")


@mcp.resource("evo://objects/schema-reference")
def get_objects_reference() -> str:
    """
    Comprehensive technical reference for Evo Geoscience Objects (GOs).

    Provides detailed schema information for all available geoscience object types,
    including required and optional parameters for each object type.
    """
    return _get_objects_reference_content()


if TOOL_FILTER == "all":
    print("Registering prompt for all tool types.")

    @mcp.prompt(name="all_prompt")
    def all_prompt() -> str:
        """All prompt that encompasses the functionality of all tool without a filter applied."""
        return """\
        You are an assistant for the Evo platform created by Seequent.
        You can help users with:
        - Listing and discovering workspaces
        - Getting workspace details and statistics
        - Creating new workspaces
        - Managing workspace metadata
        - Managing user permissions and access control
        - Health checks and status monitoring
        - Selecting instances (organizations) to work with
        - Listing and searching for objects within workspaces
        - Retrieving object details and content
        - Creating new objects
        - Managing object versions
        - Extracting data blob references
        - Answering questions about data formats and schemas
        - Copying objects between workspaces
        - Duplicating entire workspaces with optional filtering
        - Bulk operations on multiple objects
        - Data migration and backup operations
        - Listing users in the instance and their roles
        - Adding or removing users from the instance
        - Updating user roles in the instance

        When a user asks about workspaces, use the available MCP tools to provide accurate information.
        Always be clear about what workspace you're working with.
        If you need a workspace_id, ask the user or list workspaces first.

        When working with objects, always verify workspace_id and object_id.
        Use the Object Information reference below to understand object schemas and required properties.
        Use the powerful bulk operation capabilities carefully. Always confirm the scope of operations with users.
        Available tools:

        Safety guidelines:
        - Confirm before deleting objects
        - Verify required properties when creating objects
        - Check object schema compatibility


        """


if TOOL_FILTER in ["all", "admin"]:

    @mcp.prompt(name="admin_prompt")
    def admin_prompt() -> str:
        """Prompt for management operations."""
        return """\
        You are an admin assistant for Evo workspace management created by Seequent.

        You can help users with:
        - Listing and discovering workspaces
        - Getting workspace details and statistics
        - Creating new workspaces
        - Managing workspace metadata
        - Managing user permissions and access control
        - Health checks and status monitoring
        - Selecting instances (organizations) to work with

        When a user asks about workspaces, use the available MCP tools to provide accurate information.
        Always be clear about what workspace you're working with.
        If you need a workspace_id, ask the user or list workspaces first.

        If an error occurs when calling a tool, return the full error message to help troubleshoot.
        """


if TOOL_FILTER in ["all", "data"]:

    @mcp.prompt(name="data_prompt")
    def data_prompt() -> str:
        """Prompt for local file system data connector and object creation operations."""
        return """\
        You are a local data import specialist for the Evo platform created by Seequent.

        You can help users create geoscience objects from CSV files.

        ## Supported Object Types

        | Type | File Pattern | Use Case |
        |------|--------------|----------|
        | **Pointset** | Single CSV with X/Y/Z | Sample locations, sensors |
        | **LineSegments** | Vertices CSV + Segments CSV | Faults, contacts, lines |
        | **DownholeCollection** | Collar + Survey + Intervals | Drillhole data |

        ## Recommended Workflow

        ### Step 1: Discover Files
        ```
        list_local_data_files(file_pattern="*.csv")
        ```

        ### Step 2: Analyze Files (Optional)
        ```
        preview_csv_file(file_path="file1.csv")
        ```
        This shows column names and data types to help determine column mappings.

        ### Step 3: Create Object (use the appropriate tool for your data type)

        #### For Pointset (single CSV with coordinates):
        ```
        build_and_create_pointset(
            workspace_id="<uuid>",
            object_path="/data/my_pointset.json",
            object_name="My Pointset",
            description="Sample locations",
            csv_file="points.csv",
            x_column="X",
            y_column="Y",
            z_column="Z",
            dry_run=True  # Validate first
        )
        ```

        #### For LineSegments (vertices + segments CSVs):
        ```
        build_and_create_line_segments(
            workspace_id="<uuid>",
            object_path="/data/my_lines.json",
            object_name="My Lines",
            description="Fault traces",
            vertices_file="vertices.csv",
            segments_file="segments.csv",
            x_column="X",
            y_column="Y",
            z_column="Z",
            start_index_column="start_idx",
            end_index_column="end_idx",
            dry_run=True  # Validate first
        )
        ```

        #### For DownholeCollection (collar + survey + intervals):
        ```
        build_and_create_downhole_collection(
            workspace_id="<uuid>",
            object_path="/drillholes/my_drillholes.json",
            object_name="My Drillholes",
            description="Exploration drilling",
            collar_file="collar.csv",
            survey_file="survey.csv",
            collar_id_column="HOLE_ID",
            survey_id_column="HOLE_ID",
            x_column="X",
            y_column="Y",
            z_column="Z",
            depth_column="DEPTH",
            azimuth_column="AZIMUTH",
            dip_column="DIP",
            interval_files=[
                {
                    "file": "assay.csv",
                    "name": "assay",
                    "id_column": "HOLE_ID",
                    "from_column": "FROM",
                    "to_column": "TO"
                }
            ],
            dry_run=True  # Validate first
        )
        ```

        ### Step 4: Create (after validation)
        Run the same command with `dry_run=False` to create the object.

        ## Best Practices

        1. **Always use dry_run=True first** - validates without creating
        2. **Check column names** - use preview_csv_file to see available columns
        3. **Review warnings** - understand data quality before proceeding

        If an error occurs when calling a tool, return the full error message.
        """


if TOOL_FILTER in ["all", "compute"]:

    @mcp.prompt(name="compute_prompt")
    def compute_prompt() -> str:
        """Prompt for geostatistics and compute operations."""
        return """\
        You are a compute assistant for the Evo platform created by Seequent.

        You can help users with:
        - Setting the active workspace for compute workflows
        - Discovering source and target objects for compute tasks
        - Building variograms and search neighborhoods
        - Running kriging workflows and scenario comparisons
        - Retrieving and summarizing output attributes

        Always confirm workspace context before running compute operations.
        Validate object IDs and attribute names before execution.
        If an error occurs when calling a tool, return the full error message.
        """


def main() -> None:
    """Run the Evo MCP server with the configured transport."""
    from fastmcp.utilities.logging import get_logger

    startup_logger = get_logger(__name__)
    startup_logger.info("Starting Evo MCP Server in %s mode", TRANSPORT.upper())

    if TRANSPORT == "http":
        startup_logger.info("HTTP server will listen on %s:%s", HTTP_HOST, HTTP_PORT)
        if CLIENT_DELEGATED_AUTH:
            oidcproxy_redirect_path = os.getenv("OIDCPROXY_REDIRECT_PATH", "/signin-callback")
            startup_logger.info(
                "OAuth upstream callback URL: %s%s — register this as an allowed redirect URI in your auth client.",
                public_base_url.rstrip("/"),
                oidcproxy_redirect_path,
            )
        middleware = [Middleware(AuthMetadataPatchMiddleware)] if CLIENT_DELEGATED_AUTH else []
        mcp.run(
            transport="http",
            host=HTTP_HOST,
            port=HTTP_PORT,
            middleware=middleware,
        )
        return

    mcp.run()


if __name__ == "__main__":
    main()