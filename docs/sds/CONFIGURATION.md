# Configuration Specification

Sentinel configuration is human-readable, versionable, and validated before the
runtime starts.

## Format
The initial reference runtime reads TOML using Python's standard library.

## Defaults
If no configuration file is supplied, the reference runtime uses:

```toml
[runtime]
id = "sentinel-runtime"

[event_bus]
kind = "in_memory"

[audit]
enabled = true
path = "var/sentinel/audit.jsonl"
```

## Runtime Table
- id: non-empty runtime identifier used as the subject of runtime lifecycle
  events.

## Event Bus Table
- kind: event bus implementation. Initially only `in_memory` is supported.

## Audit Table
- enabled: whether to subscribe an audit sink to the event bus.
- path: JSON Lines audit file path. Required when audit is enabled.

## Validation Rules
- Unknown event bus kinds are invalid.
- Runtime id must be a non-empty string.
- Audit enabled must be a boolean.
- Audit path must be a non-empty string when audit is enabled.
- Configuration errors must fail before runtime startup emits running state.

## Future Tables
Future phases will add plugin discovery, sensors, policies, actions,
notifications, approvals, API, and scheduler configuration.

## Current Implementation
The reference runtime implements this configuration contract in
`sentinel_core.config` and wires it through `sentinel_core.application`.
