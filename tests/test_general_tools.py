# SPDX-FileCopyrightText: 2026 Bentley Systems, Incorporated
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

from evo_mcp.tools.general_tools import register_general_tools


class _FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


class GeneralToolsTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_my_instances_filters_hidden_instance(self) -> None:
        fake_mcp = _FakeMCP()
        register_general_tools(fake_mcp)
        list_my_instances = fake_mcp.tools["list_my_instances"]

        visible_instance = SimpleNamespace(display_name="Visible Instance")
        hidden_instance = SimpleNamespace(display_name="BHP Exploration")
        fake_context = SimpleNamespace(
            org_id=None,
            discovery_client=SimpleNamespace(
                list_organizations=AsyncMock(return_value=[visible_instance, hidden_instance])
            ),
        )
        fake_ctx = SimpleNamespace(info=AsyncMock())

        with (
            patch("evo_mcp.tools.general_tools.ensure_initialized", AsyncMock()),
            patch("evo_mcp.tools.general_tools.evo_context", fake_context),
        ):
            result = await list_my_instances(fake_ctx)

        self.assertEqual([visible_instance], result)

    async def test_select_instance_ignores_hidden_instance(self) -> None:
        fake_mcp = _FakeMCP()
        register_general_tools(fake_mcp)
        select_instance = fake_mcp.tools["select_instance"]

        visible_instance = SimpleNamespace(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            display_name="Visible Instance",
            hubs=[SimpleNamespace(url="https://visible.example.invalid")],
        )
        hidden_instance = SimpleNamespace(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            display_name="BHP Exploration",
            hubs=[SimpleNamespace(url="https://hidden.example.invalid")],
        )
        fake_context = SimpleNamespace(
            discovery_client=SimpleNamespace(
                list_organizations=AsyncMock(return_value=[visible_instance, hidden_instance])
            ),
            switch_instance=AsyncMock(),
        )

        with (
            patch("evo_mcp.tools.general_tools.ensure_initialized", AsyncMock()),
            patch("evo_mcp.tools.general_tools.evo_context", fake_context),
        ):
            with self.assertRaises(ValueError):
                await select_instance(instance_name="BHP Exploration")

        fake_context.switch_instance.assert_not_awaited()

    async def test_list_object_stages_returns_serialized_sorted_stages(self) -> None:
        fake_mcp = _FakeMCP()
        register_general_tools(fake_mcp)
        list_object_stages = fake_mcp.tools["list_object_stages"]

        workspace_id = UUID("00000000-0000-0000-0000-000000000031")
        fake_object_client = SimpleNamespace(
            list_stages=AsyncMock(
                return_value=[
                    SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000033"), name="Peer Review"),
                    SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000032"), name="Approved"),
                ]
            )
        )
        fake_context = SimpleNamespace(
            get_object_client=AsyncMock(return_value=fake_object_client),
        )

        with (
            patch("evo_mcp.tools.general_tools.ensure_initialized", AsyncMock()),
            patch("evo_mcp.tools.general_tools.evo_context", fake_context),
        ):
            result = await list_object_stages(str(workspace_id))

        self.assertEqual(str(workspace_id), result["workspace_id"])
        self.assertEqual(2, result["total_stages"])
        self.assertEqual(
            [
                {"id": "00000000-0000-0000-0000-000000000032", "name": "Approved"},
                {"id": "00000000-0000-0000-0000-000000000033", "name": "Peer Review"},
            ],
            result["stages"],
        )

    async def test_set_object_stage_resolves_stage_name_and_updates_latest_version(self) -> None:
        fake_mcp = _FakeMCP()
        register_general_tools(fake_mcp)
        set_object_stage = fake_mcp.tools["set_object_stage"]

        stage_id = UUID("00000000-0000-0000-0000-000000000010")
        object_id = UUID("00000000-0000-0000-0000-000000000011")
        previous_stage_id = UUID("00000000-0000-0000-0000-000000000012")
        downloaded = SimpleNamespace(
            metadata=SimpleNamespace(
                id=object_id,
                path="/Example.json",
                version_id="123",
                stage=SimpleNamespace(id=previous_stage_id, name="Experimental"),
            )
        )
        fake_object_client = SimpleNamespace(
            download_object_by_id=AsyncMock(return_value=downloaded),
            list_stages=AsyncMock(return_value=[SimpleNamespace(id=stage_id, name="Approved")]),
            set_stage=AsyncMock(),
        )
        fake_context = SimpleNamespace(
            get_object_client=AsyncMock(return_value=fake_object_client),
        )

        with (
            patch("evo_mcp.tools.general_tools.ensure_initialized", AsyncMock()),
            patch("evo_mcp.tools.general_tools.evo_context", fake_context),
        ):
            result = await set_object_stage(
                workspace_id="00000000-0000-0000-0000-000000000013",
                object_id=str(object_id),
                stage_name="Approved",
            )

        fake_object_client.set_stage.assert_awaited_once_with(object_id, 123, stage_id)
        self.assertEqual("stage_updated", result["status"])
        self.assertEqual({"id": str(previous_stage_id), "name": "Experimental"}, result["previous_stage"])
        self.assertEqual({"id": str(stage_id), "name": "Approved"}, result["stage"])

    async def test_set_object_stage_can_clear_stage_metadata(self) -> None:
        fake_mcp = _FakeMCP()
        register_general_tools(fake_mcp)
        set_object_stage = fake_mcp.tools["set_object_stage"]

        object_id = UUID("00000000-0000-0000-0000-000000000021")
        workspace_id = UUID("00000000-0000-0000-0000-000000000022")
        metadata_api = SimpleNamespace(update_metadata=AsyncMock())
        downloaded = SimpleNamespace(
            metadata=SimpleNamespace(
                id=object_id,
                path="/Example.json",
                version_id="456",
                stage=SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000023"), name="In Review"),
            )
        )
        fake_object_client = SimpleNamespace(
            download_object_by_path=AsyncMock(return_value=downloaded),
            _environment=SimpleNamespace(org_id=UUID("00000000-0000-0000-0000-000000000024"), workspace_id=workspace_id),
            _metadata_api=metadata_api,
        )
        fake_context = SimpleNamespace(
            get_object_client=AsyncMock(return_value=fake_object_client),
        )

        with (
            patch("evo_mcp.tools.general_tools.ensure_initialized", AsyncMock()),
            patch("evo_mcp.tools.general_tools.evo_context", fake_context),
        ):
            result = await set_object_stage(
                workspace_id=str(workspace_id),
                object_path="/Example.json",
                clear_stage=True,
            )

        metadata_api.update_metadata.assert_awaited_once()
        update_kwargs = metadata_api.update_metadata.await_args.kwargs
        self.assertEqual(str(object_id), update_kwargs["object_id"])
        self.assertEqual(str(workspace_id), update_kwargs["workspace_id"])
        self.assertEqual(456, update_kwargs["version_id"])
        self.assertIsNone(update_kwargs["metadata_update_body"].stage_id)
        self.assertEqual("stage_cleared", result["status"])
        self.assertIsNone(result["stage"])


if __name__ == "__main__":
    unittest.main()