# SPDX-FileCopyrightText: 2026 Bentley Systems, Incorporated
#
# SPDX-License-Identifier: Apache-2.0

"""MCP tools for planning new Evo integrations."""

from __future__ import annotations

from pathlib import Path

from evo_mcp.utils.integration_advisor import (
    DATA_TYPE_GROUPS,
    build_integration_plan,
    get_schema_catalog,
    load_app_catalog,
)


def register_integration_advisor_tools(mcp):
    """Register integration planning tools."""

    @mcp.tool()
    async def plan_evo_integration(
        goal: str,
        development_environment: str,
        data_type: str = "",
        schema_names: list[str] = [],
        include_unreleased_app_versions: bool = True,
        refresh_schema_catalog: bool = False,
    ) -> dict:
        """Plan how a user could build an Evo integration.

        The agent should ask the user what they need to consume or create, then call this
        planning tool with either broad data types or exact schema names.

        This tool is for planning only. It should recommend schemas, schema versions,
        and compatible apps for testing. It should not inspect the user's workspace
        for data files or try to build the integration directly.

        Each planning run accepts exactly one direction: consume or create.
        There is no both mode.

        Supported goals:
        - consume
        - create

        Supported data type options:
        - 2D grids & rasters
        - Block models & grids
        - Drillholes & boreholes
        - Geological models
        - Geophysical surveys
        - Geostatistics & variograms
        - Lines & polylines
        - Points & point clouds
        - Structural measurements
        - Surfaces & meshes

        Supported environments:
        - Python
        - JavaScript / TypeScript
        - .NET (C#)
        - Other / REST API

        Args:
            goal: Whether this planning run is for consuming or creating Evo objects
            development_environment: The user's implementation environment
            data_type: One high-level geoscience data type label to map to Evo schemas
            schema_names: Exact Evo schema names, used in addition to or instead of data_types
            include_unreleased_app_versions: Include planned app builds in the recommendations
            refresh_schema_catalog: Force a fresh reload of the schema catalog source chain
        """
        apps_directory = Path(__file__).parent.parent.parent.parent / "data" / "apps"
        app_catalog = load_app_catalog(apps_directory)
        schema_catalog_data = await get_schema_catalog(refresh=refresh_schema_catalog)
        schema_catalog = schema_catalog_data["schemas"]

        plan = build_integration_plan(
            goal=goal,
            development_environment=development_environment,
            app_catalog=app_catalog,
            schema_catalog=schema_catalog,
            schema_catalog_source=schema_catalog_data["source"],
            data_type=data_type,
            schema_names=schema_names,
            include_unreleased_app_versions=include_unreleased_app_versions,
        )
        plan["supported_data_types"] = list(DATA_TYPE_GROUPS.keys())
        return plan