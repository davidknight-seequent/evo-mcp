# SPDX-FileCopyrightText: 2026 Bentley Systems, Incorporated
#
# SPDX-License-Identifier: Apache-2.0

"""Utilities for planning new Evo integrations."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import re
import time
from pathlib import Path
from typing import Any

import aiohttp


GITHUB_SCHEMA_OWNER = "SeequentEvo"
GITHUB_SCHEMA_REPO = "evo-schemas"
GITHUB_SCHEMA_REF = "main"
GITHUB_OBJECTS_API_URL = (
    "https://api.github.com/repos/"
    f"{GITHUB_SCHEMA_OWNER}/{GITHUB_SCHEMA_REPO}/contents/schema/objects?ref={GITHUB_SCHEMA_REF}"
)
SCHEMA_DOCS_BASE_URL = (
    "https://developer.seequent.com/docs/data-structures/"
    "geoscience-objects/schemas/objects"
)
SCHEMA_REPO_BASE_URL = (
    f"https://github.com/{GITHUB_SCHEMA_OWNER}/{GITHUB_SCHEMA_REPO}/tree/"
    f"{GITHUB_SCHEMA_REF}/schema/objects"
)

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
WILDCARD_VERSION_PARTS = {"X", "*"}
CACHE_TTL_SECONDS = 3600

DATA_TYPE_GROUPS = {
    "2D grids & rasters": ["regular-2d-grid", "tensor-2d-grid"],
    "Block models & grids": [
        "block-model",
        "regular-3d-grid",
        "regular-masked-3d-grid",
        "tensor-3d-grid",
        "unstructured-grid",
        "unstructured-hex-grid",
        "unstructured-quad-grid",
        "unstructured-tet-grid",
    ],
    "Drillholes & boreholes": [
        "downhole-collection",
        "downhole-intervals",
        "drilling-campaign",
    ],
    "Geological models": ["geological-model-meshes", "geological-sections"],
    "Geophysical surveys": [
        "gravity",
        "magnetics",
        "frequency-domain-electromagnetic",
        "time-domain-electromagnetic",
        "radiometric",
        "resistivity-ip",
        "geophysical-records-1d",
    ],
    "Geostatistics & variograms": [
        "variogram",
        "experimental-variogram",
        "local-ellipsoids",
        "global-ellipsoid",
        "non-parametric-continuous-cumulative-distribution",
    ],
    "Lines & polylines": ["line-segments", "design-geometry"],
    "Points & point clouds": ["pointset"],
    "Structural measurements": ["planar-data-pointset", "lineations-data-pointset"],
    "Surfaces & meshes": ["triangle-mesh"],
}

ENVIRONMENT_GUIDANCE = {
    "python": {
        "label": "Python",
        "summary": "Use the Evo Python SDK to authenticate, publish objects, and download fixtures for validation.",
        "resources": [
            {
                "title": "Python SDK reference",
                "url": "https://developer.seequent.com/docs/sdk/evo-python-sdk/evo-objects",
            },
            {
                "title": "Python code samples",
                "url": "https://github.com/SeequentEvo/evo-python-sdk/tree/main/code-samples/geoscience-objects",
            },
            {
                "title": "Evo developer portal",
                "url": "https://developer.seequent.com/",
            },
        ],
    },
    "javascript-typescript": {
        "label": "JavaScript / TypeScript",
        "summary": "Plan around the Evo HTTP APIs and the schema payloads directly; use the developer portal and schema specs as the primary references.",
        "resources": [
            {
                "title": "Evo developer portal",
                "url": "https://developer.seequent.com/",
            },
        ],
    },
    "dotnet": {
        "label": ".NET (C#)",
        "summary": "Plan around the Evo HTTP APIs and schema payloads directly, then wrap that in your .NET client or service layer.",
        "resources": [
            {
                "title": "Evo developer portal",
                "url": "https://developer.seequent.com/",
            },
        ],
    },
    "other-rest-api": {
        "label": "Other / REST API",
        "summary": "Treat the schema specifications as the contract and use the Evo HTTP APIs from your existing stack.",
        "resources": [
            {
                "title": "Evo developer portal",
                "url": "https://developer.seequent.com/",
            },
        ],
    },
}

GOAL_LABELS = {
    "consume": "Consume existing Evo objects",
    "create": "Create new Evo objects",
}

_SCHEMA_CATALOG_CACHE: dict[str, list[str]] | None = None
_SCHEMA_CATALOG_SOURCE_CACHE: dict[str, Any] | None = None
_SCHEMA_CATALOG_FETCHED_AT = 0.0


def get_repo_schema_backup_directory() -> Path:
    """Return the repository-managed schema backup directory."""
    return Path(__file__).parent.parent.parent.parent / "data" / "evo-schemas" / "schema" / "objects"


def get_installed_schema_directory() -> Path | None:
    """Return the installed evo_schemas schema directory when available."""
    spec = importlib.util.find_spec("evo_schemas")
    if spec is None or spec.origin is None:
        return None

    package_root = Path(spec.origin).resolve().parent
    schema_directory = package_root / "schema" / "objects"
    if schema_directory.exists():
        return schema_directory
    return None


def load_schema_catalog_from_directory(schema_directory: Path) -> dict[str, list[str]]:
    """Load schema versions from a local schema/objects directory."""
    if not schema_directory.exists():
        return {}

    catalog: dict[str, list[str]] = {}
    for schema_path in sorted(path for path in schema_directory.iterdir() if path.is_dir()):
        versions = [
            version_path.name
            for version_path in schema_path.iterdir()
            if version_path.is_dir() and SEMVER_PATTERN.match(version_path.name)
        ]
        catalog[schema_path.name] = sort_versions_desc(versions)
    return catalog


def load_app_catalog(data_directory: Path) -> list[dict[str, Any]]:
    """Load app compatibility data from the local catalog."""
    apps: list[dict[str, Any]] = []
    for path in sorted(data_directory.glob("*.json")):
        with open(path, encoding="utf-8") as handle:
            apps.append(json.load(handle))
    return apps


async def get_schema_catalog(refresh: bool = False) -> dict[str, Any]:
    """Get available schema versions with local-first fallback and source metadata."""
    global _SCHEMA_CATALOG_CACHE
    global _SCHEMA_CATALOG_SOURCE_CACHE
    global _SCHEMA_CATALOG_FETCHED_AT

    if (
        not refresh
        and _SCHEMA_CATALOG_CACHE is not None
        and _SCHEMA_CATALOG_SOURCE_CACHE is not None
        and time.time() - _SCHEMA_CATALOG_FETCHED_AT < CACHE_TTL_SECONDS
    ):
        return {
            "schemas": _SCHEMA_CATALOG_CACHE,
            "source": _SCHEMA_CATALOG_SOURCE_CACHE,
        }

    repo_backup_directory = get_repo_schema_backup_directory()
    repo_catalog = load_schema_catalog_from_directory(repo_backup_directory)
    if repo_catalog:
        source = {
            "kind": "repo-backup",
            "description": "Repository-backed evo-schemas snapshot",
            "path": str(repo_backup_directory),
        }
        _SCHEMA_CATALOG_CACHE = repo_catalog
        _SCHEMA_CATALOG_SOURCE_CACHE = source
        _SCHEMA_CATALOG_FETCHED_AT = time.time()
        return {"schemas": repo_catalog, "source": source}

    installed_schema_directory = get_installed_schema_directory()
    if installed_schema_directory is not None:
        installed_catalog = load_schema_catalog_from_directory(installed_schema_directory)
        if installed_catalog:
            source = {
                "kind": "installed-package",
                "description": "Installed evo_schemas package data",
                "path": str(installed_schema_directory),
            }
            _SCHEMA_CATALOG_CACHE = installed_catalog
            _SCHEMA_CATALOG_SOURCE_CACHE = source
            _SCHEMA_CATALOG_FETCHED_AT = time.time()
            return {"schemas": installed_catalog, "source": source}

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "evo-mcp-integration-advisor",
    }
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        object_entries = await _fetch_json(session, GITHUB_OBJECTS_API_URL)
        tasks = [
            _fetch_schema_versions(session, entry)
            for entry in object_entries
            if entry.get("type") == "dir"
        ]
        schema_results = await asyncio.gather(*tasks)

    catalog = {schema_name: versions for schema_name, versions in schema_results}
    source = {
        "kind": "github-api",
        "description": "Live SeequentEvo/evo-schemas GitHub API",
        "url": GITHUB_OBJECTS_API_URL,
    }
    _SCHEMA_CATALOG_CACHE = catalog
    _SCHEMA_CATALOG_SOURCE_CACHE = source
    _SCHEMA_CATALOG_FETCHED_AT = time.time()
    return {"schemas": catalog, "source": source}


async def _fetch_json(session: aiohttp.ClientSession, url: str) -> Any:
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.json()


async def _fetch_schema_versions(
    session: aiohttp.ClientSession,
    entry: dict[str, Any],
) -> tuple[str, list[str]]:
    contents = await _fetch_json(session, entry["url"])
    versions = [
        item["name"]
        for item in contents
        if item.get("type") == "dir" and SEMVER_PATTERN.match(item.get("name", ""))
    ]
    return entry["name"], sort_versions_desc(versions)


def build_integration_plan(
    *,
    goal: str,
    development_environment: str,
    app_catalog: list[dict[str, Any]],
    schema_catalog: dict[str, list[str]],
    schema_catalog_source: dict[str, Any] | None = None,
    data_type: str | None = None,
    data_types: list[str] | None = None,
    schema_names: list[str] | None = None,
    include_unreleased_app_versions: bool = True,
) -> dict[str, Any]:
    """Build a structured integration plan from app and schema metadata."""
    normalized_goal = normalize_goal(goal)
    normalized_environment = normalize_environment(development_environment)
    requested_data_types = [data_type] if data_type else (data_types or [])
    resolved = resolve_requested_schemas(
        data_types=requested_data_types,
        schema_names=schema_names or [],
        known_schemas=set(schema_catalog),
    )
    selected_schemas = resolved["schemas"]
    if not selected_schemas:
        raise ValueError("At least one supported data type or schema name must be provided")

    guidance = ENVIRONMENT_GUIDANCE[normalized_environment]
    schema_reports = [
        build_schema_report(
            schema_name=schema_name,
            goal=normalized_goal,
            app_catalog=app_catalog,
            available_versions=schema_catalog.get(schema_name, []),
            include_unreleased_app_versions=include_unreleased_app_versions,
        )
        for schema_name in selected_schemas
    ]

    warnings = []
    if resolved["unknown_data_types"]:
        warnings.append(
            "Unrecognized data types were ignored: "
            + ", ".join(sorted(resolved["unknown_data_types"]))
        )
    if resolved["unknown_schema_names"]:
        warnings.append(
            "Unrecognized schema names were ignored: "
            + ", ".join(sorted(resolved["unknown_schema_names"]))
        )

    report = {
        "goal": normalized_goal,
        "goal_label": GOAL_LABELS[normalized_goal],
        "development_environment": {
            "id": normalized_environment,
            "label": guidance["label"],
            "summary": guidance["summary"],
            "resources": guidance["resources"],
        },
        "selected_data_type": resolved["data_types"][0] if resolved["data_types"] else None,
        "selected_data_types": resolved["data_types"],
        "selected_schemas": selected_schemas,
        "schemas": schema_reports,
        "schema_catalog_source": schema_catalog_source,
        "warnings": warnings,
        "supported_data_types": list(DATA_TYPE_GROUPS.keys()),
        "supported_environments": [item["label"] for item in ENVIRONMENT_GUIDANCE.values()],
    }
    if schema_catalog_source is not None and schema_catalog_source.get("kind") != "repo-backup":
        report["warnings"].append(
            "Schema catalog is not coming from the repository backup. Refresh the local backup for the most reliable offline planning behavior."
        )
    report["report_markdown"] = render_markdown_report(report)
    return report


def build_schema_report(
    *,
    schema_name: str,
    goal: str,
    app_catalog: list[dict[str, Any]],
    available_versions: list[str],
    include_unreleased_app_versions: bool,
) -> dict[str, Any]:
    support_entries = collect_schema_support(
        app_catalog=app_catalog,
        schema_name=schema_name,
        available_versions=available_versions,
        include_unreleased_app_versions=include_unreleased_app_versions,
    )
    source_apps = sort_app_supports(
        filter_support_by_direction(support_entries, "export"),
        preferred_version=None,
    )
    validation_apps = sort_app_supports(
        filter_support_by_direction(support_entries, "import"),
        preferred_version=None,
    )
    recommended_version, recommendation_reason, recommendation_quality = recommend_build_version(
        goal=goal,
        available_versions=available_versions,
        source_apps=source_apps,
        validation_apps=validation_apps,
    )
    source_apps = sort_app_supports(source_apps, preferred_version=recommended_version)
    validation_apps = sort_app_supports(validation_apps, preferred_version=recommended_version)

    warnings = []
    if not available_versions:
        warnings.append(
            "This schema was not found in the live evo-schemas GitHub catalog at planning time."
        )
    if recommended_version is None:
        warnings.append("No documented schema version could be recommended.")
    elif goal == "consume" and not any_app_supports_version(source_apps, recommended_version):
        warnings.append(
            f"No source app is documented to publish schema version {recommended_version}."
        )
    elif goal == "create" and not any_app_supports_version(validation_apps, recommended_version):
        warnings.append(
            f"No validation app is documented to import schema version {recommended_version}."
        )
    return {
        "schema": schema_name,
        "schema_repo_url": f"{SCHEMA_REPO_BASE_URL}/{schema_name}",
        "schema_docs_url": f"{SCHEMA_DOCS_BASE_URL}/{schema_name}",
        "available_versions": available_versions,
        "latest_schema_version": available_versions[0] if available_versions else None,
        "recommended_build_version": recommended_version,
        "recommendation_quality": recommendation_quality,
        "recommendation_reason": recommendation_reason,
        "import_workflow": {
            "workflow_label": "Source apps for consume workflows",
            "recommended_apps": source_apps,
        },
        "export_workflow": {
            "workflow_label": "Validation apps for create workflows",
            "recommended_apps": validation_apps,
        },
        "warnings": warnings,
    }


def collect_schema_support(
    *,
    app_catalog: list[dict[str, Any]],
    schema_name: str,
    available_versions: list[str],
    include_unreleased_app_versions: bool,
) -> list[dict[str, Any]]:
    supports: list[dict[str, Any]] = []
    for app in app_catalog:
        for support in app.get("support", []):
            if support.get("schema") != schema_name:
                continue

            app_versions = normalize_app_versions(support.get("appVersionSpecs"))
            release_state = get_release_state(app_versions)
            if release_state == "unreleased" and not include_unreleased_app_versions:
                continue

            supported_schema_versions = expand_version_specs(
                support.get("versionSpecs", []),
                available_versions,
            )
            supports.append(
                {
                    "app_id": app.get("id"),
                    "app_name": app.get("name"),
                    "app_display_name": format_app_display_name(
                        app.get("publisherName"),
                        app.get("name"),
                    ),
                    "publisher_name": app.get("publisherName"),
                    "publisher_type": app.get("publisherType"),
                    "category": app.get("category"),
                    "product_url": app.get("productUrl"),
                    "integration_status": app.get("integrationStatus"),
                    "support_level": support.get("supportLevel", "full"),
                    "directions": sorted(set(support.get("directions", []))),
                    "version_specs": support.get("versionSpecs", []),
                    "supported_schema_versions": supported_schema_versions,
                    "note": support.get("note") or app.get("note"),
                    "app_versions": app_versions,
                    "release_state": release_state,
                }
            )
    return supports


def expand_version_specs(
    version_specs: list[str] | None,
    available_versions: list[str],
) -> list[str]:
    """Expand exact and wildcard version specs into concrete schema versions."""
    if not version_specs:
        return []

    expanded: set[str] = set()
    for spec in version_specs:
        normalized = spec.strip()
        if not normalized:
            continue
        if SEMVER_PATTERN.match(normalized):
            expanded.add(normalized)
            continue
        spec_parts = [part.upper() for part in normalized.replace("*", "X").split(".")]
        for version in available_versions:
            version_parts = version.split(".")
            if len(version_parts) != len(spec_parts):
                continue
            if all(
                spec_part in WILDCARD_VERSION_PARTS or spec_part == version_part.upper()
                for spec_part, version_part in zip(spec_parts, version_parts, strict=False)
            ):
                expanded.add(version)
    return sort_versions_desc(expanded)


def format_app_display_name(
    publisher_name: str | None,
    app_name: str | None,
) -> str:
    publisher = (publisher_name or "").strip()
    name = (app_name or "").strip()
    if not publisher:
        return name
    if not name:
        return publisher
    if name.casefold().startswith(f"{publisher.casefold()} "):
        return name
    return f"{publisher} {name}"


def resolve_requested_schemas(
    *,
    data_types: list[str],
    schema_names: list[str],
    known_schemas: set[str],
) -> dict[str, list[str]]:
    resolved_schemas: set[str] = set()
    resolved_data_types: list[str] = []
    unknown_data_types: list[str] = []
    unknown_schema_names: list[str] = []

    data_type_lookup = {normalize_key(label): label for label in DATA_TYPE_GROUPS}
    schema_lookup = {normalize_key(schema): schema for schema in known_schemas}

    for data_type in data_types:
        normalized = normalize_key(data_type)
        if normalized in data_type_lookup:
            label = data_type_lookup[normalized]
            resolved_data_types.append(label)
            resolved_schemas.update(DATA_TYPE_GROUPS[label])
            continue
        if normalized in schema_lookup:
            resolved_schemas.add(schema_lookup[normalized])
            continue
        unknown_data_types.append(data_type)

    for schema_name in schema_names:
        normalized = normalize_key(schema_name)
        if normalized in schema_lookup:
            resolved_schemas.add(schema_lookup[normalized])
        else:
            unknown_schema_names.append(schema_name)

    return {
        "data_types": sorted(set(resolved_data_types)),
        "schemas": sort_schema_names(resolved_schemas),
        "unknown_data_types": unknown_data_types,
        "unknown_schema_names": unknown_schema_names,
    }


def filter_support_by_direction(
    supports: list[dict[str, Any]],
    direction: str,
) -> list[dict[str, Any]]:
    return [support for support in supports if direction in support["directions"]]


def recommend_build_version(
    *,
    goal: str,
    available_versions: list[str],
    source_apps: list[dict[str, Any]],
    validation_apps: list[dict[str, Any]],
) -> tuple[str | None, str, str]:
    if not available_versions:
        return None, "No live schema versions were found in evo-schemas.", "no-schema-catalog"

    released_source = collect_supported_versions(source_apps, release_states={"released", "unspecified"})
    released_validation = collect_supported_versions(validation_apps, release_states={"released", "unspecified"})
    all_source = collect_supported_versions(source_apps, release_states=None)
    all_validation = collect_supported_versions(validation_apps, release_states=None)

    if goal == "consume":
        version = first_matching_version(available_versions, released_source)
        if version:
            return (
                version,
                "Latest schema version with documented source-app coverage for consume workflows.",
                "released-source-coverage",
            )
        version = first_matching_version(available_versions, all_source)
        if version:
            return (
                version,
                "Latest schema version with documented source-app coverage, but only via unreleased or partially specified app builds.",
                "planned-source-coverage",
            )
        return (
            available_versions[0],
            "Latest schema version in evo-schemas; no source app is currently documented to publish it.",
            "latest-without-source-coverage",
        )

    if goal == "create":
        version = first_matching_version(available_versions, released_validation)
        if version:
            return (
                version,
                "Latest schema version with documented validation-app coverage for create workflows.",
                "released-validation-coverage",
            )
        version = first_matching_version(available_versions, all_validation)
        if version:
            return (
                version,
                "Latest schema version with documented validation-app coverage, but only via unreleased or partially specified app builds.",
                "planned-validation-coverage",
            )
        return (
            available_versions[0],
            "Latest schema version in evo-schemas; no validation app is currently documented to import it.",
            "latest-without-validation-coverage",
        )

    raise ValueError("goal must be one of: consume, create")


def collect_supported_versions(
    supports: list[dict[str, Any]],
    release_states: set[str] | None,
) -> set[str]:
    versions: set[str] = set()
    for support in supports:
        if release_states is not None and support["release_state"] not in release_states:
            continue
        versions.update(support["supported_schema_versions"])
    return versions


def any_app_supports_version(supports: list[dict[str, Any]], version: str) -> bool:
    return any(version in support["supported_schema_versions"] for support in supports)


def sort_app_supports(
    supports: list[dict[str, Any]],
    *,
    preferred_version: str | None,
) -> list[dict[str, Any]]:
    def sort_key(support: dict[str, Any]) -> tuple[Any, ...]:
        return (
            0 if preferred_version and preferred_version in support["supported_schema_versions"] else 1,
            release_rank(support["release_state"]),
            0 if support.get("publisher_type") == "first-party" else 1,
            version_sort_key(support["supported_schema_versions"][0])
            if support["supported_schema_versions"]
            else (-1, -1, -1),
            support.get("app_name") or "",
        )

    ranked = []
    for support in sorted(supports, key=sort_key):
        ranked.append(
            {
                **support,
                "supports_recommended_version": (
                    preferred_version in support["supported_schema_versions"]
                    if preferred_version
                    else False
                ),
            }
        )
    return ranked


def render_markdown_report(plan: dict[str, Any]) -> str:
    lines = [
        "# Evo integration plan",
        "",
        f"- Goal: {plan['goal_label']}",
        f"- Environment: {plan['development_environment']['label']}",
        f"- Schemas: {', '.join(plan['selected_schemas'])}",
    ]

    if plan.get("schema_catalog_source"):
        source = plan["schema_catalog_source"]
        lines.append(
            f"- Schema catalog source: {source['description']}"
            + (f" ({source['path']})" if source.get("path") else "")
        )

    if plan["warnings"]:
        lines.append("- Warnings: " + " | ".join(plan["warnings"]))

    lines.extend([
        "",
        "## Environment guidance",
        plan["development_environment"]["summary"],
        "",
    ])

    for resource in plan["development_environment"]["resources"]:
        lines.append(f"- {resource['title']}: {resource['url']}")

    for schema in plan["schemas"]:
        lines.extend(
            [
                "",
                f"## {schema['schema']}",
                f"- Recommended build version: {schema['recommended_build_version']}",
                f"- Latest schema version: {schema['latest_schema_version']}",
                f"- Recommendation reason: {schema['recommendation_reason']}",
                f"- Schema repo: {schema['schema_repo_url']}",
                f"- Schema docs: {schema['schema_docs_url']}",
            ]
        )

        if schema["warnings"]:
            lines.append("- Warnings: " + " | ".join(schema["warnings"]))

        lines.append("- Source apps for consume workflows:")
        lines.extend(render_app_lines(schema["import_workflow"]["recommended_apps"]))
        lines.append("- Validation apps for create workflows:")
        lines.extend(render_app_lines(schema["export_workflow"]["recommended_apps"]))

    return "\n".join(lines)


def render_app_lines(apps: list[dict[str, Any]]) -> list[str]:
    if not apps:
        return ["  - None documented."]

    lines = []
    for app in apps:
        app_label = app.get("app_display_name") or app.get("app_name") or "Unknown app"
        schema_versions = ", ".join(app["supported_schema_versions"]) or "Version unspecified"
        app_versions = ", ".join(
            app_version["version"] + (" (released)" if app_version["released"] is True else " (planned)" if app_version["released"] is False else "")
            for app_version in app["app_versions"]
        )
        if not app_versions:
            app_versions = "Version unspecified"
        line = (
            f"  - {app_label}: schema {schema_versions}; "
            f"app {app_versions}; release state {app['release_state']}"
        )
        if app.get("product_url"):
            line += f"; url: {app['product_url']}"
        if app.get("note"):
            line += f"; note: {app['note']}"
        lines.append(line)
    return lines


def normalize_goal(goal: str) -> str:
    normalized = normalize_key(goal)
    if normalized in {"consume", "import", "read"}:
        return "consume"
    if normalized in {"create", "export", "publish", "write"}:
        return "create"
    raise ValueError(
        "goal must be one of: consume, create. If the integration does both, run the planner once for each direction."
    )


def normalize_environment(environment: str) -> str:
    normalized = normalize_key(environment)
    mapping = {
        "python": "python",
        "javascripttypescript": "javascript-typescript",
        "javascripttypescript": "javascript-typescript",
        "javascript": "javascript-typescript",
        "typescript": "javascript-typescript",
        "dotnetc": "dotnet",
        "dotnet": "dotnet",
        "c": "dotnet",
        "otherrestapi": "other-rest-api",
        "restapi": "other-rest-api",
        "other": "other-rest-api",
    }
    if normalized not in mapping:
        raise ValueError(
            "development_environment must be one of: Python, JavaScript / TypeScript, .NET (C#), Other / REST API"
        )
    return mapping[normalized]


def normalize_app_versions(app_version_specs: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not app_version_specs:
        return []
    normalized = []
    for app_version in app_version_specs:
        normalized.append(
            {
                "version": app_version.get("version", "unspecified"),
                "released": app_version.get("released"),
            }
        )
    return normalized


def get_release_state(app_versions: list[dict[str, Any]]) -> str:
    if not app_versions:
        return "unspecified"
    if any(app_version["released"] is True for app_version in app_versions):
        return "released"
    if all(app_version["released"] is False for app_version in app_versions):
        return "unreleased"
    return "unspecified"


def release_rank(release_state: str) -> int:
    if release_state == "released":
        return 0
    if release_state == "unspecified":
        return 1
    return 2


def first_matching_version(available_versions: list[str], candidates: set[str]) -> str | None:
    for version in available_versions:
        if version in candidates:
            return version
    return None


def sort_versions_desc(versions: set[str] | list[str]) -> list[str]:
    return sorted(set(versions), key=version_sort_key, reverse=True)


def sort_schema_names(schema_names: set[str] | list[str]) -> list[str]:
    return sorted(set(schema_names))


def version_sort_key(version: str) -> tuple[int, int, int]:
    if not SEMVER_PATTERN.match(version):
        return (-1, -1, -1)
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())