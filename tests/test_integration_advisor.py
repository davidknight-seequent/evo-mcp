# SPDX-FileCopyrightText: 2026 Bentley Systems, Incorporated
#
# SPDX-License-Identifier: Apache-2.0

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from evo_mcp.utils.integration_advisor import (
    build_integration_plan,
    expand_version_specs,
    load_schema_catalog_from_directory,
    normalize_goal,
)


class ExpandVersionSpecsTests(unittest.TestCase):
    def test_expands_exact_and_wildcard_versions(self):
        available_versions = ["2.2.0", "2.1.0", "1.1.0", "1.0.1"]

        expanded = expand_version_specs(["1.X.X", "2.1.0"], available_versions)

        self.assertEqual(expanded, ["2.1.0", "1.1.0", "1.0.1"])


class LoadSchemaCatalogFromDirectoryTests(unittest.TestCase):
    def test_loads_local_schema_versions(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "downhole-collection" / "1.0.1").mkdir(parents=True)
            (root / "downhole-collection" / "1.2.0").mkdir(parents=True)
            (root / "downhole-collection" / "notes").mkdir(parents=True)
            (root / "geological-model-meshes" / "2.2.0").mkdir(parents=True)

            catalog = load_schema_catalog_from_directory(root)

        self.assertEqual(catalog["downhole-collection"], ["1.2.0", "1.0.1"])
        self.assertEqual(catalog["geological-model-meshes"], ["2.2.0"])


class BuildIntegrationPlanTests(unittest.TestCase):
    def test_prefers_latest_released_source_version_for_consume_goal(self):
        app_catalog = [
            {
                "id": "source-app",
                "name": "Source App",
                "publisherName": "Seequent",
                "publisherType": "first-party",
                "integrationStatus": "connected",
                "productUrl": "https://example.com/source",
                "support": [
                    {
                        "schema": "downhole-collection",
                        "directions": ["export"],
                        "versionSpecs": ["1.2.0"],
                        "appVersionSpecs": [{"version": "2025.1.0", "released": True}],
                    }
                ],
            },
            {
                "id": "validation-app",
                "name": "Validation App",
                "publisherName": "Seequent",
                "publisherType": "first-party",
                "integrationStatus": "connected",
                "productUrl": "https://example.com/validation",
                "support": [
                    {
                        "schema": "downhole-collection",
                        "directions": ["import"],
                        "versionSpecs": ["1.2.0", "1.3.0"],
                        "appVersionSpecs": [{"version": "2025.2.0", "released": True}],
                    },
                    {
                        "schema": "downhole-collection",
                        "directions": ["import"],
                        "versionSpecs": ["1.3.1"],
                        "appVersionSpecs": [{"version": "2026.1.0", "released": False}],
                    },
                ],
            },
        ]
        schema_catalog = {"downhole-collection": ["1.3.1", "1.3.0", "1.2.0"]}

        plan = build_integration_plan(
            goal="consume",
            development_environment="Python",
            app_catalog=app_catalog,
            schema_catalog=schema_catalog,
            schema_catalog_source={"kind": "repo-backup", "description": "Repository-backed evo-schemas snapshot"},
            data_types=["Drillholes & boreholes"],
            schema_names=[],
        )

        self.assertEqual(plan["schemas"][0]["recommended_build_version"], "1.2.0")
        self.assertEqual(
            plan["schemas"][0]["recommendation_quality"],
            "released-source-coverage",
        )

    def test_rejects_both_goal(self):
        with self.assertRaisesRegex(ValueError, "goal must be one of: consume, create"):
            normalize_goal("both")

    def test_uses_wildcard_support_to_pick_latest_validation_version(self):
        app_catalog = [
            {
                "id": "validator",
                "name": "Validator",
                "publisherName": "Seequent",
                "publisherType": "first-party",
                "integrationStatus": "connected",
                "productUrl": "https://example.com/validator",
                "support": [
                    {
                        "schema": "design-geometry",
                        "directions": ["import"],
                        "versionSpecs": ["1.X.X"],
                        "appVersionSpecs": [{"version": "2025.2.1", "released": True}],
                    }
                ],
            }
        ]
        schema_catalog = {"design-geometry": ["1.1.0", "1.0.1"]}

        plan = build_integration_plan(
            goal="create",
            development_environment="Other / REST API",
            app_catalog=app_catalog,
            schema_catalog=schema_catalog,
            schema_catalog_source={"kind": "installed-package", "description": "Installed evo_schemas package data"},
            data_types=[],
            schema_names=["design-geometry"],
        )

        self.assertEqual(plan["schemas"][0]["recommended_build_version"], "1.1.0")
        self.assertTrue(plan["schemas"][0]["export_workflow"]["recommended_apps"][0]["supports_recommended_version"])
        self.assertEqual(plan["schema_catalog_source"]["kind"], "installed-package")
        self.assertIn("not coming from the repository backup", plan["warnings"][0])


if __name__ == "__main__":
    unittest.main()