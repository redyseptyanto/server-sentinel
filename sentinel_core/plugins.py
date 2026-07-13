"""Plugin manifest contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any
import tomllib


class PluginManifestError(ValueError):
    """Raised when a plugin manifest is invalid."""


class PluginCategory(StrEnum):
    SENSOR = "sensor"
    POLICY = "policy"
    ACTION = "action"
    VERIFIER = "verifier"
    APPROVAL_PROVIDER = "approval_provider"
    NOTIFICATION = "notification"
    DIAGNOSTIC_EXPORTER = "diagnostic_exporter"


SUPPORTED_PLATFORMS = frozenset({"linux", "windows", "macos", "any"})
PLUGIN_MANIFEST_FILENAME = "sentinel-plugin.toml"


@dataclass(frozen=True, slots=True)
class PluginManifest:
    name: str
    version: str
    category: PluginCategory
    entrypoint: str
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    required_permissions: tuple[str, ...] = field(default_factory=tuple)
    supported_platforms: tuple[str, ...] = ("any",)
    config_schema: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("name", self.name)
        _require_non_empty("version", self.version)
        _require_non_empty("entrypoint", self.entrypoint)
        _require_string_tuple("capabilities", self.capabilities)
        _require_string_tuple("required_permissions", self.required_permissions)
        _require_string_tuple("supported_platforms", self.supported_platforms)

        unknown_platforms = set(self.supported_platforms) - SUPPORTED_PLATFORMS
        if unknown_platforms:
            joined_platforms = ", ".join(sorted(unknown_platforms))
            raise PluginManifestError(f"unsupported platforms: {joined_platforms}")

        if not isinstance(self.config_schema, dict):
            raise PluginManifestError("config_schema must be an object")

        object.__setattr__(self, "config_schema", MappingProxyType(dict(self.config_schema)))


@dataclass(frozen=True, slots=True)
class DiscoveredPluginManifest:
    """A validated plugin manifest and its source path."""

    path: Path
    manifest: PluginManifest


def plugin_manifest_from_mapping(raw_manifest: dict[str, Any]) -> PluginManifest:
    """Create and validate a plugin manifest from a mapping."""

    if not isinstance(raw_manifest, dict):
        raise PluginManifestError("plugin manifest must be an object")

    try:
        category = PluginCategory(raw_manifest["category"])
    except KeyError as error:
        raise PluginManifestError("category is required") from error
    except ValueError as error:
        raise PluginManifestError("category is invalid") from error

    return PluginManifest(
        name=_string_field(raw_manifest, "name"),
        version=_string_field(raw_manifest, "version"),
        category=category,
        entrypoint=_string_field(raw_manifest, "entrypoint"),
        capabilities=_string_sequence_field(raw_manifest, "capabilities", default=()),
        required_permissions=_string_sequence_field(
            raw_manifest,
            "required_permissions",
            default=(),
        ),
        supported_platforms=_string_sequence_field(
            raw_manifest,
            "supported_platforms",
            default=("any",),
        ),
        config_schema=raw_manifest.get("config_schema", {}),
    )


def load_plugin_manifest(path: str | Path) -> DiscoveredPluginManifest:
    """Load and validate a plugin manifest file."""

    manifest_path = Path(path)
    with manifest_path.open("rb") as manifest_file:
        raw_file = tomllib.load(manifest_file)

    raw_plugin = raw_file.get("plugin")
    if not isinstance(raw_plugin, dict):
        raise PluginManifestError("plugin manifest file must contain a [plugin] table")

    return DiscoveredPluginManifest(
        path=manifest_path,
        manifest=plugin_manifest_from_mapping(raw_plugin),
    )


def discover_plugin_manifests(paths: list[str | Path] | tuple[str | Path, ...]) -> tuple[DiscoveredPluginManifest, ...]:
    """Discover `sentinel-plugin.toml` files from files or directories."""

    manifest_paths: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            raise PluginManifestError(f"plugin discovery path does not exist: {path}")
        if path.is_file():
            manifest_paths.append(path)
            continue
        manifest_paths.extend(path.rglob(PLUGIN_MANIFEST_FILENAME))

    return tuple(load_plugin_manifest(path) for path in sorted(set(manifest_paths)))


def _string_field(raw_manifest: dict[str, Any], field_name: str) -> str:
    try:
        value = raw_manifest[field_name]
    except KeyError as error:
        raise PluginManifestError(f"{field_name} is required") from error

    if not isinstance(value, str):
        raise PluginManifestError(f"{field_name} must be a string")
    return value


def _string_sequence_field(
    raw_manifest: dict[str, Any],
    field_name: str,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = raw_manifest.get(field_name, default)
    if not isinstance(value, list | tuple):
        raise PluginManifestError(f"{field_name} must be a list of strings")
    return tuple(value)


def _require_non_empty(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PluginManifestError(f"{field_name} must be a non-empty string")


def _require_string_tuple(field_name: str, values: tuple[str, ...]) -> None:
    if not values:
        raise PluginManifestError(f"{field_name} must include at least one value")
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise PluginManifestError(f"{field_name} must contain non-empty strings")
