# Plugin System Specification

Plugins extend Sentinel without expanding the core boundary.

## Categories
- Sensor.
- Policy.
- Action.
- Verifier.
- Approval provider.
- Notification.
- Diagnostic exporter.

## Manifest
Each plugin must declare:
- name.
- version.
- category.
- entrypoint.
- capabilities.
- required permissions.
- supported platforms.
- configuration schema.

Manifest files use TOML and place plugin metadata under a `[plugin]` table.
The conventional filename is `sentinel-plugin.toml`.

Example:

```toml
[plugin]
name = "cpu-sensor"
version = "0.1.0"
category = "sensor"
entrypoint = "sentinel_plugins.cpu:create_plugin"
capabilities = ["metrics.cpu"]
required_permissions = ["host.metrics.read"]
supported_platforms = ["linux"]

[plugin.config_schema]
type = "object"
```

Allowed categories:
- sensor.
- policy.
- action.
- verifier.
- approval_provider.
- notification.
- diagnostic_exporter.

Supported platforms:
- linux.
- windows.
- macos.
- any.

Validation rules:
- name, version, category, and entrypoint must be non-empty strings.
- category must be one of the allowed categories.
- capabilities, required permissions, and supported platforms must be lists of
  non-empty strings.
- supported platforms must contain only known platform names.
- configuration schema must be an object.

## Lifecycle Events
The plugin manager must emit events for:
- discovery.
- load start.
- load success.
- load failure.
- start.
- stop.
- crash or health failure.

## Isolation Direction
The reference runtime may support in-process plugins first. Destructive actions
and third-party plugins should move toward out-of-process execution so crashes,
dependency conflicts, and privilege boundaries are easier to control.

## Current Implementation
The reference runtime currently validates plugin manifest data only. It does not
import, instantiate, or execute plugin code yet. Manifest discovery reads
`sentinel-plugin.toml` files, validates their metadata, and returns manifest
objects with source paths.
