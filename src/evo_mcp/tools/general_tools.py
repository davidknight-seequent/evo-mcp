# SPDX-FileCopyrightText: 2026 Bentley Systems, Incorporated
#
# SPDX-License-Identifier: Apache-2.0

"""
MCP tools for general operations (health checks, object CRUD, etc).
"""

import logging
from typing import Any
from uuid import UUID

from fastmcp import Context
from evo.objects.endpoints.models import MetadataUpdateBody

from evo_mcp.context import evo_context, ensure_initialized

logger = logging.getLogger(__name__)

HIDDEN_INSTANCE_NAMES = {"BHP Exploration"}


def _instance_display_name(instance: object) -> str:
    if isinstance(instance, dict):
        return str(instance.get("display_name") or instance.get("name") or "")
    return str(getattr(instance, "display_name", getattr(instance, "name", "")) or "")


def _visible_instances(instances: list[object]) -> list[object]:
    return [
        instance
        for instance in instances
        if _instance_display_name(instance) not in HIDDEN_INSTANCE_NAMES
    ]


def _stage_name(stage: Any) -> str:
    if isinstance(stage, dict):
        return str(stage.get("name") or "")
    return str(getattr(stage, "name", "") or "")


def _stage_id(stage: Any) -> str:
    if isinstance(stage, dict):
        return str(stage.get("id") or stage.get("stage_id") or "")
    return str(getattr(stage, "id", getattr(stage, "stage_id", "")) or "")


def _serialize_stage(stage: Any) -> dict[str, str] | None:
    if not stage:
        return None
    return {
        "id": _stage_id(stage),
        "name": _stage_name(stage),
    }


def _available_stage_names(stages: list[Any]) -> str:
    names = sorted({_stage_name(stage) for stage in stages if _stage_name(stage)})
    return ", ".join(names) if names else "none"


def _resolve_target_stage(stages: list[Any], *, stage_id: str = "", stage_name: str = "") -> Any:
    if bool(stage_id) == bool(stage_name):
        raise ValueError("Provide exactly one of stage_id or stage_name.")

    if stage_id:
        matching_stage = next((stage for stage in stages if _stage_id(stage) == stage_id), None)
        if matching_stage is None:
            raise ValueError(
                f"Unknown stage_id '{stage_id}'. Available stages: {_available_stage_names(stages)}"
            )
        return matching_stage

    normalized_name = stage_name.strip().casefold()
    matches = [stage for stage in stages if _stage_name(stage).strip().casefold() == normalized_name]
    if not matches:
        raise ValueError(
            f"Unknown stage_name '{stage_name}'. Available stages: {_available_stage_names(stages)}"
        )
    if len(matches) > 1:
        raise ValueError(f"Stage name '{stage_name}' matched multiple stages; use stage_id instead.")
    return matches[0]


def register_general_tools(mcp):
    """Register all general tools with the FastMCP server."""
    
    @mcp.tool()
    async def workspace_health_check(workspace_id: str = "") -> dict:
        """Check health status of Evo services.
        
        Args:
            workspace_id: Workspace UUID to check object service (optional)
        """
        results = {}
        
        if evo_context.workspace_client:
            workspace_health = await evo_context.workspace_client.get_service_health()
            results["workspace_service"] = {
                "service": workspace_health.service,
                "status": workspace_health.status,
            }
        
        if workspace_id:
            await ensure_initialized()
            object_client = await evo_context.get_object_client(UUID(workspace_id))
            object_health = await object_client.get_service_health()
            results["object_service"] = {
                "service": object_health.service,
                "status": object_health.status,
            }
        
        return results

    @mcp.tool()
    async def list_workspaces(
        name: str = "",
        deleted: bool = False,
        limit: int = 50
    ) -> list[dict]:
        """List workspaces with optional filtering by name or deleted status.
        
        Args:
            name: Filter by workspace name (leave empty for no filter)
            deleted: Include deleted workspaces
            limit: Maximum number of results
        """
        await ensure_initialized()
        
        workspaces = await evo_context.workspace_client.list_workspaces(
            name=name if name else None,
            deleted=deleted,
            limit=limit
        )
        
        return [
            {
                "id": str(ws.id),
                "name": ws.display_name,
                "description": ws.description,
                "user_role": ws.user_role.name if ws.user_role else None,
                "created_at": ws.created_at.isoformat() if ws.created_at else None,
                "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
            }
            for ws in workspaces.items()
        ]

    @mcp.tool()
    async def get_workspace(
        workspace_id: str = "",
        workspace_name: str = ""
    ) -> dict:
        """Get workspace details by ID or name.
        
        Args:
            workspace_id: Workspace UUID (provide either this or workspace_name)
            workspace_name: Workspace name (provide either this or workspace_id)
        """
        await ensure_initialized()
        
        if workspace_id:
            workspace = await evo_context.workspace_client.get_workspace(UUID(workspace_id))
        elif workspace_name:
            workspaces = await evo_context.workspace_client.list_workspaces(name=workspace_name)
            matching = [ws for ws in workspaces.items() if ws.display_name == workspace_name]
            if not matching:
                raise ValueError(f"Workspace '{workspace_name}' not found")
            workspace = matching[0]
        else:
            raise ValueError("Either workspace_id or workspace_name must be provided")
        
        return {
            "id": str(workspace.id),
            "name": workspace.display_name,
            "description": workspace.description,
            "user_role": workspace.user_role.name if workspace.user_role else None,
            "created_at": workspace.created_at.isoformat() if workspace.created_at else None,
            "updated_at": workspace.updated_at.isoformat() if workspace.updated_at else None,
            "created_by": workspace.created_by.id if workspace.created_by else None,
            "default_coordinate_system": workspace.default_coordinate_system,
            "labels": workspace.labels,
        }
    
    @mcp.tool()
    async def list_objects(
        workspace_id: str,
        schema_id: str = "",
        deleted: bool = False,
        limit: int = 100
    ) -> list[dict]:
        """List objects in a workspace with optional filtering.
        
        Args:
            workspace_id: Workspace UUID
            schema_id: Filter by schema/object type (leave empty for no filter)
            deleted: Include deleted objects
            limit: Maximum number of results
        """
        logger.info(f"evo_list_objects called with workspace_id={workspace_id}, schema_id={schema_id}")
        
        try:
            logger.debug("Calling ensure_initialized()")
            await ensure_initialized()
            logger.debug("ensure_initialized() completed successfully")
            
            logger.debug(f"Getting object client for workspace {workspace_id}")
            object_client = await evo_context.get_object_client(UUID(workspace_id))
            logger.debug(f"Got object_client: {object_client}")
            
            service_health = await object_client.get_service_health()
            service_health.raise_for_status()
            logger.debug("Object client health check passed")
            
            logger.debug("Calling list_objects()")
            objects = await object_client.list_objects(
                schema_id=None, # [schema_id] if schema_id else None,
                deleted=deleted,
                limit=limit
            )

            logger.debug(f"list_objects() returned {len(objects.items())} objects")
            
            result = [
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "path": obj.path,
                    "schema_id": obj.schema_id.sub_classification,
                    "version_id": obj.version_id,
                    "created_at": obj.created_at,
                    "created_by": obj.created_by,
                    "modified_at": obj.modified_at,
                    "modified_by": obj.modified_by,
                    "stage": obj.stage
                }
                for obj in objects.items()
            ]
            logger.info(f"evo_list_objects completed successfully with {len(result)} objects")
            return result
            
        except Exception as e:
            logger.error(f"Error in evo_list_objects: {type(e).__name__}: {str(e)}", exc_info=True)
            raise

    @mcp.tool()
    async def get_object(
        workspace_id: str,
        object_id: str = "",
        object_path: str = "",
        version: str = ""
    ) -> dict:
        """Get object metadata by ID or path.
        
        Args:
            workspace_id: Workspace UUID
            object_id: Object UUID (provide either this or object_path)
            object_path: Object path (provide either this or object_id)
            version: Specific version ID (optional)
        """
        await ensure_initialized()
        object_client = await evo_context.get_object_client(UUID(workspace_id))
        
        if object_id:
            obj = await object_client.download_object_by_id(UUID(object_id), version=version)
        elif object_path:
            obj = await object_client.download_object_by_path(object_path, version=version)
        else:
            raise ValueError("Either object_id or object_path must be provided")
        
        return {
            "id": str(obj.metadata.id),
            "name": obj.metadata.name,
            "path": obj.metadata.path,
            "schema_id": obj.metadata.schema_id.sub_classification,
            "version_id": obj.metadata.version_id,
            "created_at": obj.metadata.created_at,
            "created_by": obj.metadata.created_by,
            "modified_at": obj.metadata.modified_at,
            "modified_by": obj.metadata.modified_by,
            "stage": obj.metadata.stage,
        }

    @mcp.tool()
    async def list_object_stages(workspace_id: str) -> dict:
        """List the available object stages for the selected Evo instance.

        Args:
            workspace_id: Workspace UUID used to resolve the current instance
        """
        await ensure_initialized()

        object_client = await evo_context.get_object_client(UUID(workspace_id))
        stages = await object_client.list_stages()
        serialized_stages = sorted(
            [_serialize_stage(stage) for stage in stages if _serialize_stage(stage) is not None],
            key=lambda stage: stage["name"].casefold(),
        )

        return {
            "workspace_id": workspace_id,
            "total_stages": len(serialized_stages),
            "stages": serialized_stages,
        }

    @mcp.tool()
    async def set_object_stage(
        workspace_id: str,
        object_id: str = "",
        object_path: str = "",
        stage_id: str = "",
        stage_name: str = "",
        version: str = "",
        clear_stage: bool = False,
    ) -> dict:
        """Set or clear the stage metadata for an Evo object version.

        Args:
            workspace_id: Workspace UUID
            object_id: Object UUID (provide either this or object_path)
            object_path: Object path (provide either this or object_id)
            stage_id: Target stage UUID (provide either this or stage_name)
            stage_name: Target stage name (provide either this or stage_id)
            version: Specific version ID to update (optional, defaults to latest)
            clear_stage: Clear the stage metadata instead of setting it
        """
        await ensure_initialized()

        if bool(object_id) == bool(object_path):
            raise ValueError("Provide exactly one of object_id or object_path.")

        if clear_stage:
            if stage_id or stage_name:
                raise ValueError("Do not provide stage_id or stage_name when clear_stage=True.")
        else:
            if not stage_id and not stage_name:
                raise ValueError("Provide stage_id or stage_name, or set clear_stage=True.")
            if stage_id and stage_name:
                raise ValueError("Provide only one of stage_id or stage_name.")

        object_client = await evo_context.get_object_client(UUID(workspace_id))

        if object_id:
            downloaded = await object_client.download_object_by_id(UUID(object_id), version=version or None)
        else:
            downloaded = await object_client.download_object_by_path(object_path, version=version or None)

        resolved_object_id = UUID(str(downloaded.metadata.id))
        resolved_version_id = int(version or downloaded.metadata.version_id)
        previous_stage = _serialize_stage(downloaded.metadata.stage)

        if clear_stage:
            await object_client._metadata_api.update_metadata(
                object_id=str(resolved_object_id),
                org_id=str(object_client._environment.org_id),
                workspace_id=str(object_client._environment.workspace_id),
                metadata_update_body=MetadataUpdateBody(stage_id=None),
                version_id=resolved_version_id,
            )
            return {
                "status": "stage_cleared",
                "workspace_id": workspace_id,
                "object_id": str(resolved_object_id),
                "path": downloaded.metadata.path,
                "version_id": resolved_version_id,
                "previous_stage": previous_stage,
                "stage": None,
            }

        stages = await object_client.list_stages()
        target_stage = _resolve_target_stage(stages, stage_id=stage_id, stage_name=stage_name)
        target_stage_id = UUID(_stage_id(target_stage))

        await object_client.set_stage(resolved_object_id, resolved_version_id, target_stage_id)

        return {
            "status": "stage_updated",
            "workspace_id": workspace_id,
            "object_id": str(resolved_object_id),
            "path": downloaded.metadata.path,
            "version_id": resolved_version_id,
            "previous_stage": previous_stage,
            "stage": _serialize_stage(target_stage),
        }


    @mcp.tool()
    async def list_my_instances(
        ctx: Context,
    ) -> list[dict]:
        """List instances the user has access to."""
        await ensure_initialized()

        if evo_context.org_id:
            await ctx.info(f"Selected instance ID {evo_context.org_id}")
        instances = await evo_context.discovery_client.list_organizations()
        return _visible_instances(instances)

    @mcp.tool()
    async def select_instance(
        instance_name: str | None = None,
        instance_id: UUID | None = None,
    ) -> dict | None:
        """Select an instance to connect to.

        Subsequent tool invocations like "list workspaces" will act on this
        Evo Instance.

        The provided argument must match an instance returned by list_my_instances.

        Args:
            instance_id: Instance UUID (provide either this or instance_name)
            instance_name: Instance name (provide either this or instance_id)
        """
        await ensure_initialized()

        instances = _visible_instances(
            await evo_context.discovery_client.list_organizations()
        )
        for instance in instances:
            if instance.id == instance_id or instance.display_name == instance_name:
                await evo_context.switch_instance(instance.id, instance.hubs[0].url)
                return instance

        raise ValueError(
            f"No instance found for parameters {instance_id=} {instance_name=}. "
            "Check that the arguments match an instance returned by `list_my_instances`."
        )
