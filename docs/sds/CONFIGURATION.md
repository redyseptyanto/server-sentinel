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

[simulation]
enabled = false
interval_seconds = 5
starting_temp_celsius = 85.0

[monitoring]
enabled = false
interval_seconds = 30
include_optional = true
disk_paths = ["/"]

[thermal_policy]
warning_cpu_threshold_celsius = 70.0
warning_nvme_threshold_celsius = 80.0
rearm_below_celsius = 60.0
critical_cpu_threshold_celsius = 85.0
emergency_cpu_threshold_celsius = 95.0
emergency_hold_seconds = 30
approval_timeout_seconds = 30
protected_process_patterns = ["systemd", "sshd", "NetworkManager", "dbus-daemon", "dockerd", "containerd", "postgres", "mysqld", "mongod"]
top_process_count = 3
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

## Simulation Table
- enabled: whether to wire the thermal recovery simulation into the application.
- interval_seconds: scheduler cadence for the simulated CPU sensor. Default 5.
- starting_temp_celsius: temperature emitted by the simulated sensor. Default
  85.0.
- temp_threshold_celsius: legacy compatibility field from the first simulation
  slice. The severity ladder now uses `[thermal_policy]` thresholds instead.

### Simulation Defaults
```toml
[simulation]
enabled = false
interval_seconds = 5
starting_temp_celsius = 85.0
```

## Monitoring Table
- enabled: whether to wire the Linux common sensor pack into the application.
- interval_seconds: scheduler cadence for the common sensor pack. Default 30.
- include_optional: whether to probe optional integrations such as Docker,
  `systemctl`, SMART, NVMe, battery, and GPU where available. Default true.
- disk_paths: list of filesystem paths to inspect with disk usage probes.
  Default `["/"]`.
- temp_threshold_celsius: legacy compatibility field from the first monitoring
  slice. The severity ladder now uses `[thermal_policy]` thresholds instead.

## Thermal Policy Table
- warning_cpu_threshold_celsius: CPU warning threshold. Default 70.0.
- warning_nvme_threshold_celsius: NVMe warning threshold. Default 80.0.
- rearm_below_celsius: incident clear threshold for re-arming notifications and
  escalations. Default 60.0.
- critical_cpu_threshold_celsius: CPU critical threshold. Default 85.0.
- emergency_cpu_threshold_celsius: CPU emergency threshold. Default 95.0.
- emergency_hold_seconds: how long CPU temperature must remain at or above the
  emergency threshold before the emergency state is entered. Default 30.
- approval_timeout_seconds: approval timeout value published in policy action
  requests and recovery recommendations. Default 30.
- protected_process_patterns: process name fragments that must not be selected
  as termination candidates by the thermal policy.
- top_process_count: number of top CPU and memory processes to include in
  diagnostics and recovery context. Default 3.

### Thermal Policy Defaults
```toml
[thermal_policy]
warning_cpu_threshold_celsius = 70.0
warning_nvme_threshold_celsius = 80.0
rearm_below_celsius = 60.0
critical_cpu_threshold_celsius = 85.0
emergency_cpu_threshold_celsius = 95.0
emergency_hold_seconds = 30
approval_timeout_seconds = 30
protected_process_patterns = ["systemd", "sshd", "NetworkManager", "dbus-daemon", "dockerd", "containerd", "postgres", "mysqld", "mongod"]
top_process_count = 3
```

### Monitoring Defaults
```toml
[monitoring]
enabled = false
interval_seconds = 30
include_optional = true
disk_paths = ["/"]
```

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
- Simulation enabled must be a boolean.
- Simulation interval_seconds must be a positive integer.
- Simulation temp_threshold_celsius must be numeric.
- Simulation starting_temp_celsius must be numeric.
- Monitoring enabled must be a boolean.
- Monitoring interval_seconds must be a positive integer.
- Monitoring include_optional must be a boolean.
- Monitoring disk_paths must be a list of non-empty strings.
- Monitoring temp_threshold_celsius must be numeric.
- Thermal policy thresholds must be numeric.
- Thermal policy thresholds must preserve escalation order: re-arm below warning,
  warning below critical, and critical below emergency.
- Thermal policy hold and timeout values must be positive numbers.
- Thermal policy protected_process_patterns must be a list of non-empty strings.
- Thermal policy top_process_count must be a positive integer.
- Configuration errors must fail before runtime startup emits running state.

## Current Implementation
The reference runtime implements this configuration contract in
`sentinel_core.config` and wires it through `sentinel_core.application`.

## Future Tables
Future phases will add plugin discovery, richer sensors, policies, actions,
notifications, approvals, API, and scheduler configuration.
