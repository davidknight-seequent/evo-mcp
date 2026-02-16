"""
Consolidated MCP tools - Generic tools with skills-based guidance.
"""

import logging
import json
from uuid import UUID
from pathlib import Path
from typing import Optional, Literal

import pandas as pd
from fastmcp import Context

from evo_mcp.context import evo_context, ensure_initialized
from evo_mcp.utils.object_builders import (
    PointsetBuilder,
    LineSegmentsBuilder,
    DownholeCollectionBuilder,
    DownholeIntervalsBuilder,
)

logger = logging.getLogger(__name__)


def register_consolidated_tools(mcp):
    """Register consolidated generic tools with the FastMCP server."""
    
    @mcp.tool()
    async def evo_query(
        ctx: Context,
        entity_type: Literal["workspace", "object", "instance", "version"],
        workspace_id: str = "",
        object_id: str = "",
        name_filter: str = "",
        schema_filter: str = "",
        include_deleted: bool = False,
        limit: int = 100
    ) -> list[dict] | dict:
        """Generic query tool for all Evo entities.
        
        Args:
            entity_type: Type of entity to query (workspace/object/instance/version)
            workspace_id: Required for object/version queries
            object_id: Required for version queries
            name_filter: Filter by name (optional)
            schema_filter: Filter by schema for objects (optional)
            include_deleted: Include deleted items
            limit: Maximum results
            
        Returns:
            List of entities or single entity details
        """
        await ensure_initialized()
        
        if entity_type == "workspace":
            workspaces = await evo_context.workspace_client.list_workspaces(
                name=name_filter if name_filter else None,
                deleted=include_deleted,
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
            
        elif entity_type == "object":
            if not workspace_id:
                raise ValueError("workspace_id required for object queries")
            
            object_client = await evo_context.get_object_client(UUID(workspace_id))
            objects = await object_client.list_objects(
                schema_id=None,
                deleted=include_deleted,
                limit=limit
            )
            
            result = [
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "path": obj.path,
                    "schema_id": obj.schema_id.sub_classification,
                    "version_id": obj.version_id,
                    "created_at": obj.created_at.isoformat() if obj.created_at else None,
                }
                for obj in objects.items()
            ]
            
            # Apply schema filter client-side
            if schema_filter:
                result = [obj for obj in result if schema_filter.lower() in obj["schema_id"].lower()]
            
            return result
            
        elif entity_type == "instance":
            instances = await evo_context.discovery_client.list_organizations()
            return instances
            
        elif entity_type == "version":
            if not workspace_id or not object_id:
                raise ValueError("workspace_id and object_id required for version queries")
            
            object_client = await evo_context.get_object_client(UUID(workspace_id))
            versions = await object_client.get_object_versions(UUID(object_id))
            
            return [
                {
                    "version_id": v.version_id,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                    "created_by": str(v.created_by) if v.created_by else None,
                }
                for v in versions
            ]
    
    @mcp.tool()
    async def evo_get(
        entity_type: Literal["workspace", "object", "object_content"],
        workspace_id: str = "",
        object_id: str = "",
        object_path: str = "",
        name: str = "",
        version: str = ""
    ) -> dict:
        """Get detailed information about a specific entity.
        
        Args:
            entity_type: Type of entity (workspace/object/object_content)
            workspace_id: Workspace UUID (required for objects)
            object_id: Object UUID (alternative to object_path)
            object_path: Object path (alternative to object_id)
            name: Entity name (alternative identifier for workspace)
            version: Specific version (optional for objects)
            
        Returns:
            Entity details including metadata
        """
        await ensure_initialized()
        
        if entity_type == "workspace":
            if workspace_id:
                workspace = await evo_context.workspace_client.get_workspace(UUID(workspace_id))
            elif name:
                workspaces = await evo_context.workspace_client.list_workspaces(name=name)
                matching = [ws for ws in workspaces.items() if ws.display_name == name]
                if not matching:
                    raise ValueError(f"Workspace '{name}' not found")
                workspace = matching[0]
            else:
                raise ValueError("Either workspace_id or name must be provided")
            
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
            
        elif entity_type == "object":
            if not workspace_id:
                raise ValueError("workspace_id required for object queries")
            
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
                "created_at": obj.metadata.created_at.isoformat() if obj.metadata.created_at else None,
            }
            
        elif entity_type == "object_content":
            if not workspace_id:
                raise ValueError("workspace_id required")
            
            object_client = await evo_context.get_object_client(UUID(workspace_id))
            
            if object_id:
                obj = await object_client.download_object_by_id(UUID(object_id), version=version)
            elif object_path:
                obj = await object_client.download_object_by_path(object_path, version=version)
            else:
                raise ValueError("Either object_id or object_path must be provided")
            
            return {
                "metadata": {
                    "id": str(obj.metadata.id),
                    "name": obj.metadata.name,
                    "path": obj.metadata.path,
                    "schema_id": obj.metadata.schema_id.sub_classification,
                },
                "content": obj.content.model_dump() if hasattr(obj.content, 'model_dump') else str(obj.content)
            }
    
    @mcp.tool()
    async def evo_create(
        ctx: Context,
        entity_type: Literal["workspace", "object"],
        name: str,
        workspace_id: str = "",
        object_path: str = "",
        description: str = "",
        object_json: str = "",
        csv_config: str = "",
        tags: str = "{}"
    ) -> dict:
        """Create new entities in Evo.
        
        Args:
            entity_type: Type to create (workspace/object)
            name: Entity name
            workspace_id: Required for object creation
            object_path: Path for object (e.g., /data/my_object.json)
            description: Optional description
            object_json: JSON string of object content
            csv_config: JSON config for CSV-based object creation
            tags: JSON string of tags
            
        Returns:
            Created entity details
        """
        await ensure_initialized()
        
        if entity_type == "workspace":
            workspace = await evo_context.workspace_client.create_workspace(
                name=name,
                description=description
            )
            await ctx.info(f"Created workspace: {workspace.display_name} ({workspace.id})")
            
            return {
                "id": str(workspace.id),
                "name": workspace.display_name,
                "description": workspace.description,
            }
            
        elif entity_type == "object":
            if not workspace_id or not object_path:
                raise ValueError("workspace_id and object_path required for object creation")
            
            object_client = await evo_context.get_object_client(UUID(workspace_id))
            
            # Parse object content
            if object_json:
                content_dict = json.loads(object_json)
            elif csv_config:
                # CSV-based creation handled by evo_build_object
                raise ValueError("Use evo_build_object for CSV-based object creation")
            else:
                raise ValueError("Either object_json or csv_config must be provided")
            
            # Create object
            result = await object_client.create_object(
                path=object_path,
                content=content_dict
            )
            
            await ctx.info(f"Created object: {name} at {object_path}")
            
            return {
                "id": str(result.id),
                "path": object_path,
                "version_id": result.version_id,
            }
    
    @mcp.tool()
    async def evo_build_object(
        ctx: Context,
        object_type: Literal["pointset", "line_segments", "downhole_collection", "downhole_intervals"],
        workspace_id: str,
        object_path: str,
        name: str,
        csv_files: str,  # JSON string mapping file purposes to paths
        column_mapping: str,  # JSON string with column names
        description: str = "",
        crs: str = "unspecified",
        dry_run: bool = False
    ) -> dict:
        """Build and create geoscience objects from CSV data.
        
        Args:
            object_type: Type of object to build
            workspace_id: Target workspace UUID
            object_path: Path for created object
            name: Object name
            csv_files: JSON mapping of file purposes to paths
            column_mapping: JSON with column name mappings
            description: Optional description
            crs: Coordinate reference system
            dry_run: Validate without creating
            
        Returns:
            Created object details or validation results
        """
        await ensure_initialized()
        object_client = await evo_context.get_object_client(UUID(workspace_id))
        
        files = json.loads(csv_files)
        columns = json.loads(column_mapping)
        
        if object_type == "pointset":
            df = pd.read_csv(files["points"])
            builder = PointsetBuilder()
            
            obj = builder.build(
                name=name,
                df=df,
                x_column=columns["x"],
                y_column=columns["y"],
                z_column=columns["z"],
                attribute_columns=columns.get("attributes"),
                description=description,
                crs=crs
            )
            
        elif object_type == "line_segments":
            vertices_df = pd.read_csv(files["vertices"])
            segments_df = pd.read_csv(files["segments"])
            builder = LineSegmentsBuilder()
            
            obj = builder.build(
                name=name,
                vertices_df=vertices_df,
                segments_df=segments_df,
                x_column=columns["x"],
                y_column=columns["y"],
                z_column=columns["z"],
                start_index_column=columns["start_index"],
                end_index_column=columns["end_index"],
                description=description,
                crs=crs
            )
            
        elif object_type == "downhole_collection":
            collar_df = pd.read_csv(files["collar"])
            survey_df = pd.read_csv(files["survey"])
            builder = DownholeCollectionBuilder()
            
            interval_configs = []
            if "intervals" in files:
                for interval_name, interval_file in files["intervals"].items():
                    interval_df = pd.read_csv(interval_file)
                    interval_configs.append({
                        "name": interval_name,
                        "df": interval_df,
                        "id_col": columns["intervals"][interval_name]["id"],
                        "from_col": columns["intervals"][interval_name]["from"],
                        "to_col": columns["intervals"][interval_name]["to"],
                        "attribute_columns": columns["intervals"][interval_name].get("attributes", []),
                    })
            
            obj = builder.build(
                name=name,
                collar_df=collar_df,
                survey_df=survey_df,
                collar_id_col=columns["collar"]["id"],
                collar_x_col=columns["collar"]["x"],
                collar_y_col=columns["collar"]["y"],
                collar_z_col=columns["collar"]["z"],
                survey_id_col=columns["survey"]["id"],
                survey_depth_col=columns["survey"]["depth"],
                survey_azimuth_col=columns["survey"]["azimuth"],
                survey_dip_col=columns["survey"]["dip"],
                interval_configs=interval_configs,
                description=description,
                crs=crs
            )
            
        elif object_type == "downhole_intervals":
            df = pd.read_csv(files["intervals"])
            builder = DownholeIntervalsBuilder()
            
            obj = builder.build(
                name=name,
                df=df,
                hole_id_column=columns["hole_id"],
                from_column=columns["from"],
                to_column=columns["to"],
                start_x_column=columns["start_x"],
                start_y_column=columns["start_y"],
                start_z_column=columns["start_z"],
                end_x_column=columns["end_x"],
                end_y_column=columns["end_y"],
                end_z_column=columns["end_z"],
                mid_x_column=columns["mid_x"],
                mid_y_column=columns["mid_y"],
                mid_z_column=columns["mid_z"],
                attribute_columns=columns.get("attributes"),
                is_composited=columns.get("is_composited", False),
                description=description,
                crs=crs
            )
        else:
            raise ValueError(f"Unsupported object_type: {object_type}")
        
        if dry_run:
            await ctx.info(f"Dry run successful - object validated but not created")
            return {
                "status": "validated",
                "object_name": name,
                "schema": obj.schema,
                "messages": builder.get_messages()
            }
        
        # Create the object
        obj_json = obj.model_dump(by_alias=True, exclude_none=True)
        result = await object_client.create_object(
            path=object_path,
            content=obj_json
        )
        
        await ctx.info(f"Created {object_type}: {name} at {object_path}")
        
        return {
            "id": str(result.id),
            "path": object_path,
            "version_id": result.version_id,
            "messages": builder.get_messages()
        }
    
    @mcp.tool()
    async def evo_manage(
        ctx: Context,
        operation: Literal["snapshot", "duplicate", "copy_object", "select_instance"],
        workspace_id: str = "",
        source_workspace_id: str = "",
        target_workspace_id: str = "",
        object_id: str = "",
        object_path: str = "",
        new_name: str = "",
        instance_id: str = "",
        instance_name: str = ""
    ) -> dict:
        """Management operations for workspaces and objects.
        
        Args:
            operation: Type of operation (snapshot/duplicate/copy_object/select_instance)
            workspace_id: Workspace UUID for snapshot
            source_workspace_id: Source workspace for copy/duplicate
            target_workspace_id: Target workspace for copy/duplicate
            object_id: Object to copy
            object_path: Object path to copy
            new_name: New name for duplicated workspace
            instance_id: Instance UUID to select
            instance_name: Instance name to select
            
        Returns:
            Operation results
        """
        await ensure_initialized()
        
        if operation == "snapshot":
            if not workspace_id:
                raise ValueError("workspace_id required for snapshot")
            
            object_client = await evo_context.get_object_client(UUID(workspace_id))
            snapshot = await object_client.create_workspace_snapshot()
            
            await ctx.info(f"Created snapshot: {snapshot.id}")
            return {"snapshot_id": str(snapshot.id)}
            
        elif operation == "duplicate":
            if not source_workspace_id or not new_name:
                raise ValueError("source_workspace_id and new_name required")
            
            # Create snapshot first
            source_client = await evo_context.get_object_client(UUID(source_workspace_id))
            snapshot = await source_client.create_workspace_snapshot()
            
            # Create new workspace and restore
            new_ws = await evo_context.workspace_client.create_workspace(
                name=new_name,
                description=f"Duplicate of workspace {source_workspace_id}"
            )
            
            target_client = await evo_context.get_object_client(new_ws.id)
            await target_client.restore_workspace_snapshot(snapshot.id)
            
            await ctx.info(f"Duplicated workspace to: {new_ws.display_name} ({new_ws.id})")
            
            return {
                "new_workspace_id": str(new_ws.id),
                "new_workspace_name": new_ws.display_name
            }
            
        elif operation == "copy_object":
            if not source_workspace_id or not target_workspace_id:
                raise ValueError("source_workspace_id and target_workspace_id required")
            if not object_id and not object_path:
                raise ValueError("Either object_id or object_path required")
            
            source_client = await evo_context.get_object_client(UUID(source_workspace_id))
            target_client = await evo_context.get_object_client(UUID(target_workspace_id))
            
            # Download from source
            if object_id:
                obj = await source_client.download_object_by_id(UUID(object_id))
            else:
                obj = await source_client.download_object_by_path(object_path)
            
            # Upload to target
            result = await target_client.create_object(
                path=obj.metadata.path,
                content=obj.content.model_dump() if hasattr(obj.content, 'model_dump') else obj.content
            )
            
            await ctx.info(f"Copied object to target workspace")
            
            return {
                "new_object_id": str(result.id),
                "path": obj.metadata.path
            }
            
        elif operation == "select_instance":
            instances = await evo_context.discovery_client.list_organizations()
            
            for instance in instances:
                if str(instance.id) == instance_id or instance.display_name == instance_name:
                    evo_context.org_id = instance.id
                    evo_context.hub_url = instance.hubs[0].url
                    evo_context.save_variables_to_cache()
                    
                    await ctx.info(f"Selected instance: {instance.display_name}")
                    return {"instance_id": str(instance.id), "instance_name": instance.display_name}
            
            raise ValueError("Instance not found")
    
    @mcp.tool()
    async def filesystem_ops(
        operation: Literal["configure", "list", "preview"],
        directory: str = "",
        file_pattern: str = "*.csv",
        file_path: str = "",
        max_rows: int = 10
    ) -> dict | list[str]:
        """Filesystem operations for local data access.
        
        Args:
            operation: Type of operation (configure/list/preview)
            directory: Directory path for configure
            file_pattern: Pattern for list operation
            file_path: File to preview
            max_rows: Max rows for preview
            
        Returns:
            Operation results
        """
        if operation == "configure":
            if not directory:
                raise ValueError("directory required for configure")
            
            dir_path = Path(directory)
            if not dir_path.exists():
                raise ValueError(f"Directory does not exist: {directory}")
            
            evo_context.data_directory = dir_path
            evo_context.save_variables_to_cache()
            
            return {
                "data_directory": str(dir_path.resolve()),
                "status": "configured"
            }
            
        elif operation == "list":
            if not evo_context.data_directory:
                raise ValueError("Data directory not configured. Use filesystem_ops with operation='configure' first.")
            
            files = list(evo_context.data_directory.glob(file_pattern))
            return [str(f.relative_to(evo_context.data_directory)) for f in files]
            
        elif operation == "preview":
            if not file_path:
                raise ValueError("file_path required for preview")
            
            if not evo_context.data_directory:
                raise ValueError("Data directory not configured")
            
            full_path = evo_context.data_directory / file_path
            if not full_path.exists():
                raise ValueError(f"File not found: {file_path}")
            
            df = pd.read_csv(full_path, nrows=max_rows)
            
            return {
                "file": file_path,
                "rows_shown": len(df),
                "total_columns": len(df.columns),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "sample_data": df.head(max_rows).to_dict(orient='records')
            }
    
    @mcp.tool()
    async def health_check(
        workspace_id: str = ""
    ) -> dict:
        """Check health status of Evo services.
        
        Args:
            workspace_id: Optional workspace UUID to check object service
            
        Returns:
            Health status of services
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
