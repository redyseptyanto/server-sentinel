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
- capacity: optional positive integer bounding the retained event history. When
  omitted (default), the bus retains every published event.
- backpressure_strategy: behavior when the retained buffer reaches `capacity`.
  One of `drop_oldest` (default), `drop_newest`, or `reject`.

### Backpressure Strategies
- `drop_oldest`: evict the oldest retained event and keep the new one. Live
  subscribers are still notified of the new event.
- `drop_newest`: keep the buffer unchanged and skip retaining the new event, but
  still deliver it to live subscribers.
- `reject`: refuse to publish and raise an error. Use when event loss is
  unacceptable and the caller must handle saturation explicitly.

Backpressure only governs the retained history used for diagnostics and replay.
It never blocks or drops delivery to live subscribers except under `reject`,
where the publish call itself fails.

## Audit Table
- enabled: whether to subscribe an audit sink to the event bus.
- path: JSON Lines audit file path. Required when audit is enabled.

## Hermes Table
- enabled: whether to subscribe the Hermes notification handler and approval
  provider to the event bus. Default false.
- base_url: Hermes endpoint base URL (e.g. `http://hermes:8000`). Required when
  enabled.
- token: Bearer token sent in the `Authorization` header.
- timeout_seconds: HTTP request timeout. Default 10.0. Must be positive.
- notify_on: list of severity strings that trigger event push. Default
  `["warning", "error", "critical"]`.
- require_approval: whether to use the Hermes approval provider for action
  decisions. Default true.

### Hermes Defaults
```toml
[hermes]
enabled = false
base_url = ""
token = ""
timeout_seconds = 10.0
notify_on = ["warning", "error", "critical"]
require_approval = true
```

## Validation Rules
- Unknown event bus kinds are invalid.
- Event bus capacity must be a positive integer or omitted.
- Event bus backpressure_strategy must be one of the supported values.
- Runtime id must be a non-empty string.
- Audit enabled must be a boolean.
- Audit path must be a non-empty string when audit is enabled.
- Hermes enabled must be a boolean.
- Hermes base_url must be a non-empty string when hermes is enabled.
- Hermes timeout_seconds must be a positive number.
- Hermes notify_on must be a list of strings.
- Hermes require_approval must be a boolean.
- Configuration errors must fail before runtime startup emits running state.

## Future Tables
Future phases will add plugin discovery, sensors, policies, actions,
notifications, approvals, API, and scheduler configuration.

## Current Implementation
The reference runtime implements this configuration contract in
`sentinel_core.config` and wires it through `sentinel_core.application`.
