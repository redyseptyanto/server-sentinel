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
- Runtime composition with optional audit logging.
- Destructive action audit sequencing.
- Tick-driven scheduler contract.
- Event schema versioning.
- Plugin manifest validation.
- Plugin manifest file discovery.
- Unit tests for events, runtime lifecycle, configuration, audit logging,
  action audit sequencing, scheduler behavior, and plugin manifests.

## Run Tests
```powershell
python -m unittest discover -s tests
```

## Minimal Runtime Example
```python
from sentinel_core import config_from_mapping, create_application

config = config_from_mapping({
    "runtime": {"id": "edge-node-1"},
    "audit": {"enabled": True, "path": "var/sentinel/audit.jsonl"},
})

app = create_application(config)
app.start()
app.stop()
```

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

Architecture decisions live in `docs/adr`.
