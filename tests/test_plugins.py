import unittest
import tempfile
from pathlib import Path

from sentinel_core import (
    PluginCategory,
    PluginManifestError,
    discover_plugin_manifests,
    load_plugin_manifest,
    plugin_manifest_from_mapping,
)


class PluginManifestTests(unittest.TestCase):
    def test_manifest_from_mapping_validates_required_fields(self) -> None:
        manifest = plugin_manifest_from_mapping(
            {
                "name": "cpu-sensor",
                "version": "0.1.0",
                "category": "sensor",
                "entrypoint": "sentinel_plugins.cpu:create_plugin",
                "capabilities": ["metrics.cpu"],
                "required_permissions": ["host.metrics.read"],
                "supported_platforms": ["linux"],
                "config_schema": {"type": "object"},
            }
        )

        self.assertEqual(manifest.name, "cpu-sensor")
        self.assertEqual(manifest.category, PluginCategory.SENSOR)
        self.assertEqual(manifest.capabilities, ("metrics.cpu",))
        self.assertEqual(manifest.supported_platforms, ("linux",))

    def test_manifest_rejects_unknown_category(self) -> None:
        with self.assertRaises(PluginManifestError):
            plugin_manifest_from_mapping(
                {
                    "name": "bad",
                    "version": "0.1.0",
                    "category": "unknown",
                    "entrypoint": "bad:create_plugin",
                    "capabilities": ["bad"],
                    "required_permissions": ["bad"],
                    "supported_platforms": ["any"],
                }
            )

    def test_manifest_rejects_unknown_platform(self) -> None:
        with self.assertRaises(PluginManifestError):
            plugin_manifest_from_mapping(
                {
                    "name": "bad",
                    "version": "0.1.0",
                    "category": "sensor",
                    "entrypoint": "bad:create_plugin",
                    "capabilities": ["bad"],
                    "required_permissions": ["bad"],
                    "supported_platforms": ["solaris"],
                }
            )

    def test_manifest_rejects_empty_capabilities(self) -> None:
        with self.assertRaises(PluginManifestError):
            plugin_manifest_from_mapping(
                {
                    "name": "bad",
                    "version": "0.1.0",
                    "category": "sensor",
                    "entrypoint": "bad:create_plugin",
                    "capabilities": [],
                    "required_permissions": ["bad"],
                    "supported_platforms": ["any"],
                }
            )

    def test_load_plugin_manifest_reads_plugin_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "sentinel-plugin.toml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "[plugin]",
                        'name = "cpu-sensor"',
                        'version = "0.1.0"',
                        'category = "sensor"',
                        'entrypoint = "sentinel_plugins.cpu:create_plugin"',
                        'capabilities = ["metrics.cpu"]',
                        'required_permissions = ["host.metrics.read"]',
                        'supported_platforms = ["linux"]',
                        "",
                        "[plugin.config_schema]",
                        'type = "object"',
                    ]
                ),
                encoding="utf-8",
            )

            discovered = load_plugin_manifest(manifest_path)

            self.assertEqual(discovered.path, manifest_path)
            self.assertEqual(discovered.manifest.name, "cpu-sensor")
            self.assertEqual(discovered.manifest.config_schema["type"], "object")

    def test_discover_plugin_manifests_finds_nested_manifest_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            alpha = root / "alpha" / "sentinel-plugin.toml"
            beta = root / "nested" / "beta" / "sentinel-plugin.toml"
            alpha.parent.mkdir(parents=True)
            beta.parent.mkdir(parents=True)
            alpha.write_text(_manifest_text("alpha-sensor"), encoding="utf-8")
            beta.write_text(_manifest_text("beta-sensor"), encoding="utf-8")

            discovered = discover_plugin_manifests([root])

            self.assertEqual(
                [item.manifest.name for item in discovered],
                ["alpha-sensor", "beta-sensor"],
            )

    def test_load_plugin_manifest_requires_plugin_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "sentinel-plugin.toml"
            manifest_path.write_text('name = "missing-table"', encoding="utf-8")

            with self.assertRaises(PluginManifestError):
                load_plugin_manifest(manifest_path)


def _manifest_text(name: str) -> str:
    return "\n".join(
        [
            "[plugin]",
            f'name = "{name}"',
            'version = "0.1.0"',
            'category = "sensor"',
            'entrypoint = "sentinel_plugins.test:create_plugin"',
            'capabilities = ["metrics.test"]',
            'required_permissions = ["host.metrics.read"]',
            'supported_platforms = ["any"]',
        ]
    )


if __name__ == "__main__":
    unittest.main()
