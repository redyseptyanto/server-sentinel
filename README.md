# Sentinel

Sentinel is an AI-native, event-driven, cross-platform Host Monitoring & Autonomous Recovery Runtime.

## Vision
Observe intelligently. Act safely.

Sentinel is not an AI assistant.
It is the trusted execution and observability layer for AI-managed systems.

AI agents such as Hermes perform reasoning.
Sentinel observes, validates, recommends, executes approved actions, verifies outcomes, and records audit history.

## Core Principles
- AI decides. Sentinel executes.
- Plugin-first.
- Event-driven.
- Cross-platform.
- Human override always wins.
- Security first.

## Responsibilities
- Continuously observe the operating system and applications.
- Collect metrics, diagnostics, logs, and system state.
- Emit structured events.
- Evaluate configurable policies.
- Recommend safe recovery actions.
- Request approval from Hermes or another approval provider when required.
- Execute approved actions.
- Verify whether the action solved the problem.
- Record everything in an audit log.

## Scope
- Linux first, then Windows and macOS without changing the core architecture.
- Hardware, operating system, container, and application monitoring.
- Hermes integration through stable APIs instead of direct system access.
- Telegram notifications and approval workflows through plugins.

## Safety Rules
- Never blindly execute AI-generated shell commands.
- Never delete files without explicit approval.
- Never stop SSH by default.
- Never stop databases by default.
- Never perform irreversible actions without confirmation.
- Never trust AI reasoning without validation.

## Current Status
Sentinel is in foundation development. The repository now contains:
- Baseline SDS documentation.
- ADR 0001 for the initial reference runtime.
- A stdlib-only Python reference core.
- Configuration loading and validation.
- A stdlib-only CLI entrypoint for runtime start and config validation.
- Runtime composition with optional audit logging.
- Destructive action audit sequencing.
- Tick-driven scheduler contract.
- Event schema versioning.
- Simulated thermal recovery sensor, policy, and action loop.
- Linux common sensor pack for real host monitoring on Ubuntu/Linux.
- Severity-based thermal incident policy with warning, critical, and emergency
  escalation.
- Top CPU and memory process summaries plus Docker engine/container status in
  host diagnostics.
- Plugin manifest validation.
- Plugin manifest file discovery.
- Event bus backpressure strategy (bounded retention with drop_oldest,
  drop_newest, or reject).
- NotificationPort and ApprovalProviderPort core integration contracts.
- Hermes HTTP push client (events + approval requests) with configurable
  endpoint, token, timeout, and severity filter.
- Unit tests for events, runtime lifecycle, configuration, audit logging,
  action audit sequencing, scheduler behavior, plugin manifests,
  Hermes client, Hermes config, thermal recovery simulation, and CLI commands.

## Run Tests
```bash
python -m unittest discover -s tests
```

## How It Works
Sentinel now has two useful runtime slices:

- `simulation.enabled = true`
  A simulated CPU sensor repeatedly emits the configured starting temperature.
  This is still fake thermal input, but it exercises the real event, policy,
  approval, and audit path.
- `monitoring.enabled = true`
  The Linux common sensor pack reads real host facts from `/proc`, `sysfs`, and
  common system tools, then emits them as structured events.

The thermal policy is incident-based and stateful:

- `Normal`
  below thresholds, no recovery action
- `Warning`
  notify once per incident and include CPU, memory, top processes, Docker, and
  storage summary
- `Critical`
  request approval for graceful mitigation of non-protected hot processes
- `Emergency`
  after the configured hold period, escalate to workload reduction and then a
  clean shutdown request if the host stays too hot

In simulation mode the temperature source is fake, but the approvals, audit
trail, policy decisions, and emitted events are real runtime behavior.

## Run Sentinel
Start from the tracked example config:

```bash
cp sentinel.example.toml sentinel.toml
```

Then edit `sentinel.toml` in the repository root and replace the Hermes token
with your real local value.

There are two practical modes today:

- `simulation.enabled = true` and `monitoring.enabled = false`
  Use this to prove the workflow with fake CPU temperature events.
- `simulation.enabled = false` and `monitoring.enabled = true`
  Use this to probe real Linux host state with the common sensor pack.

Example config:

```toml
[runtime]
id = "ubuntu-hermes-host"

[audit]
enabled = true
path = "var/sentinel/audit.jsonl"

[simulation]
enabled = false
interval_seconds = 5
starting_temp_celsius = 85.0

[monitoring]
enabled = true
interval_seconds = 30
include_optional = true
disk_paths = ["/", "/var"]

[thermal_policy]
warning_cpu_threshold_celsius = 70.0
warning_nvme_threshold_celsius = 80.0
rearm_below_celsius = 60.0
critical_cpu_threshold_celsius = 85.0
emergency_cpu_threshold_celsius = 95.0
emergency_hold_seconds = 30
approval_timeout_seconds = 30
protected_process_patterns = [
  "systemd",
  "sshd",
  "NetworkManager",
  "dbus-daemon",
  "dockerd",
  "containerd",
  "postgres",
  "mysqld",
  "mongod",
]
top_process_count = 3

[hermes]
enabled = true
base_url = "http://127.0.0.1:8787"
token = "YOUR_HERMES_BEARER_TOKEN"
timeout_seconds = 10.0
notify_on = ["warning", "error", "critical"]
require_approval = true
```

Validate the config:

```bash
python -m sentinel_core validate-config --config sentinel.toml
```

Start Sentinel:

```bash
python -m sentinel_core run --config sentinel.toml
```

For a short test run that exits on its own:

```bash
python -m sentinel_core run --config sentinel.toml --duration-seconds 15
```

If you install the project as a package, the same commands are available
through the `sentinel` executable:

```bash
sentinel validate-config --config sentinel.toml
sentinel run --config sentinel.toml
```

## Tune Thermal Thresholds
Change CPU and NVMe thresholds in `[thermal_policy]`.

For a compact mini PC such as a Geekom A8 with a Ryzen 7 8xxx CPU and 16 GB
RAM, the current example defaults are a sensible starting point:

- warning CPU: `70C`
- critical CPU: `85C`
- emergency CPU: `95C`
- warning NVMe: `80C`
- re-arm: `60C`

## What To Expect
- Sentinel starts and stays in the foreground until `Ctrl+C` or the optional
  duration expires.
- Audit records are written to `var/sentinel/audit.jsonl`.
- With simulation enabled, you should see `sensor.metric_observed` plus thermal
  warning, critical, and possibly emergency events depending on the configured
  starting temperature and runtime duration.
- With Linux monitoring enabled, Sentinel emits best-effort host facts for CPU,
  memory, disk, network, process count, top CPU and memory processes, boot
  state, and login sessions, plus optional service, Docker, storage health,
  battery, and GPU summaries when the host exposes them.
- With Hermes enabled and reachable, Sentinel pushes warning and higher events
  plus approval requests to Hermes.
- With Hermes disabled, destructive mitigation actions remain deferred after
  the approval request is audited. This is intentional.

Watch the audit log while it runs:

```bash
tail -f var/sentinel/audit.jsonl
```

## Current Caveats
- The thermal sensor is simulated, not reading real CPU hardware yet.
- All actions are still simulated. Sentinel records and verifies the workflow,
  but it does not yet terminate processes, stop containers, or shut down the
  host for real.
- The Linux common sensor pack is best-effort. Optional probes for Docker,
  `systemctl`, SMART, NVMe, battery, and GPU only emit data when the host has
  those capabilities and commands available.
- Hermes integration depends on Hermes exposing the expected HTTP endpoints on
  the configured `base_url`.

## Documentation
The SDS is the source of truth:
- `docs/sds/PRD.md`
- `docs/sds/ARCHITECTURE.md`
- `docs/sds/DOMAIN_MODEL.md`
- `docs/sds/IMPLEMENTATION_PLAN.md`
- `docs/sds/CONFIGURATION.md`
- `docs/sds/MONITORING.md`
- `docs/sds/INTEGRATIONS.md`
- `docs/sds/SCHEDULER.md`
- `docs/sds/EVENTS.md`
- `docs/sds/RUNTIME.md`
- `docs/sds/AUDIT.md`
- `docs/sds/PLUGIN_SYSTEM.md`
- `docs/sds/SAFETY.md`
- `docs/DEPLOYMENT.md` (Linux systemd + Telegram deployment: the three layers
  of repo / systemd / external glue)

Architecture decisions live in `docs/adr`.
