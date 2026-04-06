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
            data_type="Drillholes & boreholes",
            schema_names=[],
        )

        self.assertEqual(plan["selected_data_type"], "Drillholes & boreholes")
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

    def test_report_markdown_includes_recommended_app_urls(self):
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
                        "schema": "downhole-collection",
                        "directions": ["import"],
                        "versionSpecs": ["1.2.0"],
                        "appVersionSpecs": [{"version": "2025.2.1", "released": True}],
                    }
                ],
            }
        ]
        schema_catalog = {"downhole-collection": ["1.2.0", "1.0.1"]}

        plan = build_integration_plan(
            goal="create",
            development_environment="JavaScript / TypeScript",
            app_catalog=app_catalog,
            schema_catalog=schema_catalog,
            schema_catalog_source={"kind": "repo-backup", "description": "Repository-backed evo-schemas snapshot"},
            data_type="Drillholes & boreholes",
            schema_names=[],
        )

        self.assertEqual(
            plan["schemas"][0]["export_workflow"]["recommended_apps"][0]["app_display_name"],
            "Seequent Validator",
        )
        self.assertEqual(
            plan["schemas"][0]["best_documented_validation_target"],
            "Seequent Validator 2025.2.1",
        )
        self.assertEqual(
            plan["schemas"][0]["best_documented_validation_target_name"],
            "Seequent Validator",
        )
        self.assertEqual(
            plan["schemas"][0]["best_documented_validation_target_versions"],
            "2025.2.1",
        )
        self.assertEqual(
            plan["schemas"][0]["best_documented_validation_target_product_page_url"],
            "https://example.com/validator",
        )
        self.assertIn(
            {
                "schema": "downhole-collection",
                "recommended_build_version": "1.2.0",
                "latest_schema_version": "1.2.0",
                "best_documented_source_app": "None documented",
                "best_documented_source_app_name": "None documented",
                "best_documented_source_app_versions": "(version unspecified)",
                "best_documented_source_app_product_page_url": "",
                "best_documented_validation_app": "Seequent Validator 2025.2.1",
                "best_documented_validation_app_name": "Seequent Validator",
                "best_documented_validation_app_versions": "2025.2.1",
                "best_documented_validation_app_product_page_url": "https://example.com/validator",
            },
            plan["schema_recommendations"],
        )
        self.assertIn(
            {
                "label": "downhole-collection docs",
                "url": "https://developer.seequent.com/docs/data-structures/geoscience-objects/schemas/objects/downhole-collection",
            },
            plan["reference_links"],
        )
        self.assertIn(
            {
                "label": "Seequent Validator product page (downhole-collection validation app)",
                "url": "https://example.com/validator",
            },
            plan["reference_links"],
        )
        self.assertIn(
            {
                "schema": "downhole-collection",
                "workflow": "validation app",
                "app_name": "Seequent Validator",
                "product_page_url": "https://example.com/validator",
            },
            plan["app_product_pages"],
        )
        self.assertIn(
            {
                "schema": "downhole-collection",
                "workflow": "validation app",
                "app_name": "Seequent Validator",
                "app_versions": "2025.2.1",
                "release_state": "released",
                "supports_recommended_version": True,
                "schema_versions": "1.2.0",
                "product_page_url": "https://example.com/validator",
                "url": "https://example.com/validator",
            },
            plan["app_version_requirements"],
        )
        self.assertIn("Seequent Validator", plan["report_markdown"])
        self.assertIn("## Schema summary", plan["report_markdown"])
        self.assertIn(
            "| downhole-collection | 1.2.0 | None documented | Seequent Validator 2025.2.1 |",
            plan["report_markdown"],
        )
        self.assertIn("## App product pages", plan["report_markdown"])
        self.assertIn("product page https://example.com/validator", plan["report_markdown"])
        self.assertIn("## App version requirements", plan["report_markdown"])
        self.assertIn("app 2025.2.1", plan["report_markdown"])
        self.assertIn("## Quick links", plan["report_markdown"])
        self.assertIn(
            "https://developer.seequent.com/docs/data-structures/geoscience-objects/schemas/objects/downhole-collection",
            plan["report_markdown"],
        )
        self.assertIn("product page: https://example.com/validator", plan["report_markdown"])

    def test_uses_parenthesized_placeholder_for_unspecified_app_versions(self):
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
                    }
                ],
            }
        ]
        schema_catalog = {"downhole-collection": ["1.2.0"]}

        plan = build_integration_plan(
            goal="consume",
            development_environment="Python",
            app_catalog=app_catalog,
            schema_catalog=schema_catalog,
            schema_catalog_source={"kind": "repo-backup", "description": "Repository-backed evo-schemas snapshot"},
            data_type="Drillholes & boreholes",
            schema_names=[],
        )

        self.assertEqual(
            plan["schema_recommendations"][0]["best_documented_source_app"],
            "Seequent Source App (version unspecified)",
        )
        self.assertEqual(
            plan["app_version_requirements"][0]["app_versions"],
            "(version unspecified)",
        )
        self.assertIn("(version unspecified)", plan["report_markdown"])


if __name__ == "__main__":
    unittest.main()