# SPDX-FileCopyrightText: 2026 Bentley Systems, Incorporated
#
# SPDX-License-Identifier: Apache-2.0

"""Backward-compatible script entrypoint for the Evo MCP server."""

from evo_mcp.server import *  # noqa: F403
from evo_mcp.server import main


if __name__ == "__main__":
    main()
