# Implementation Plan

## Phase -1: Research
Status: complete for foundation; ongoing as new subsystems are designed.

Goals:
- Identify useful OSS concepts without copying code.
- Document architectural influences and rejected approaches.
- Keep Sentinel's core boundary explicit: no AI reasoning in core.

## Phase 0: Foundation
Status: in progress.

Deliverables:
- Repository metadata. Done.
- Reference runtime scaffold. Done.
- Event envelope. Done.
- In-memory event bus. Done.
- Runtime lifecycle. Done.
- Append-only audit sink. Done.
- Unit tests. Done.
- ADR for initial runtime stack. Done.
- Configuration loader. Done.
- Runtime composition root. Done.
- Event subscription filtering. Done.
- Plugin manifest validation. Done.
- Destructive action audit sequence. Done.
- Plugin manifest discovery. Done.
- Scheduler contract. Done.
- Event schema versioning. Done.
- Event bus backpressure strategy. Done.

Exit criteria:
- Tests run locally with no external services.
- Runtime start and stop emit state-change events.
- Audit sink can persist emitted events as JSON Lines.

## Phase 1: Core Runtime
Deliverables:
- Configuration loader. Done.
- Runtime composition root. Done.
- Scheduler. Done.
- Graceful shutdown.
- Runtime diagnostics.

## Phase 2: Event Bus
Deliverables:
- Subscription filtering. Done.
- Backpressure strategy. Done.
- Durable event sink interface.
- Event schema versioning. Done.

## Phase 3: Plugin System
Deliverables:
- Plugin manifest schema. Done.
- Capability and permission declarations.
- Plugin lifecycle events.
- Local plugin discovery. Done.

## Phase 4: Sensors
Deliverables:
- CPU sensor. Partial: simulated CPU thermal sensor is done.
- Linux common sensor pack. Done.
- Memory sensor.
- Disk sensor.
- NVMe sensor.
- Docker sensor.
- System service sensor.

## Phase 5: Policy Engine
Deliverables:
- Deterministic policy model.
- Policy packs.
- Thermal recovery policy. Partial: simulated thermal policy is done.
- Suppression and maintenance windows.

## Phase 6: Action Engine
Deliverables:
- Action request schema. Partial: action audit request contract exists.
- Safety classification.
- Dry-run support.
- Pre-action and post-action audit events. Partial: destructive audit sequence exists.
- Simulated `cool_down` action flow. Done for the reference simulation slice.

## Phase 7: Notifications
Deliverables:
- Notification port.
- Telegram plugin.
- Delivery result events.

## Phase 8: Approval Providers
Deliverables:
- Approval provider port.
- Manual approval provider.
- Hermes approval provider.

## Phase 9: REST API
Deliverables:
- Health endpoint.
- Event stream endpoint.
- Action request endpoint.
- Audit query endpoint.

## Phase 10: Hermes Integration
Deliverables:
- Hermes HTTP push client (events + approval). Done.
- Hermes event bridge.
- Hermes approval provider. Done.
- Integration tests with mocked Hermes responses. Done.
- Hermes API endpoint (pull metrics, logs, state).

## Phase 11: CLI
Deliverables:
- Runtime start command. Done.
- Config validation command. Done.
- Audit inspection command.
- Plugin inspection command.

## Phase 12: Dashboard
Deliverables:
- Local status UI.
- Event timeline.
- Pending approvals view.
- Audit inspection view.

## Phase 13: Windows/macOS
Deliverables:
- Platform abstraction review.
- Windows service support.
- macOS launchd support.
- Platform-specific sensors.

## Phase 14: Multi-host
Deliverables:
- Remote host identity model.
- Multi-host event aggregation.
- Fleet-level policy packs.
