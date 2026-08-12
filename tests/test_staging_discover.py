# SPDX-FileCopyrightText: 2026 Bentley Systems, Incorporated
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the merged ``staging_discover`` tool (Option C).

``staging_discover`` replaces the previous ``staging_list_object_types`` +
``staging_list_interactions`` pair with a single discovery entry point:

- no argument  -> list all stageable object types + lifecycle capabilities
- object_type  -> list the interactions (and their param schemas) for that type
"""

from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from evo_mcp.tools import register_object_staging_tools


def _build_staging_server() -> FastMCP:
    mcp = FastMCP("staging-test")
    register_object_staging_tools(mcp)
    return mcp


def _call(mcp: FastMCP, **kwargs) -> dict:
    result = asyncio.run(mcp.call_tool("staging_discover", kwargs))
    return result.structured_content


def test_discover_without_argument_lists_object_types():
    mcp = _build_staging_server()
    payload = _call(mcp)
    assert "object_types" in payload
    types = {o["object_type"] for o in payload["object_types"]}
    # The registry ships these built-in stageable types.
    assert {"variogram", "point_set"} <= types
    # Each entry advertises its lifecycle capabilities.
    sample = payload["object_types"][0]
    assert {"object_type", "display_name", "supports_create", "supports_import", "publish_modes"} <= sample.keys()
    capabilities = {item["object_type"]: item["supports_create"] for item in payload["object_types"]}
    assert capabilities["block_model"] is False
    assert capabilities["variogram"] is True


def test_discover_with_object_type_lists_interactions():
    mcp = _build_staging_server()
    payload = _call(mcp, object_type="variogram")
    assert payload["object_type"] == "variogram"
    assert "display_name" in payload
    interactions = {item["name"]: item for item in payload["interactions"]}
    assert "get_structure_details" in interactions
    assert "parameters_schema" in interactions["get_structure_details"]
    assert "structure_index" in interactions["get_structure_details"]["parameters_schema"]["properties"]


def test_old_discovery_tools_are_removed():
    mcp = _build_staging_server()
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "staging_discover" in names
    # The two tools merged into staging_discover must no longer be registered.
    assert "staging_list_object_types" not in names
    assert "staging_list_interactions" not in names
