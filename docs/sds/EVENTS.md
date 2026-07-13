# Event Specification

Events are immutable facts. They are the primary contract between Sentinel
subsystems and plugins.

## Envelope
Required fields:
- schema_version: stable event schema version string.
- id: UUID string.
- type: namespaced event type such as `runtime.state_changed`.
- source: component or plugin that emitted the event.
- subject: resource the event is about.
- occurred_at: UTC timestamp in ISO 8601 format.
- severity: debug, info, warning, error, or critical.
- correlation_id: workflow identifier shared by related events.
- causation_id: identifier of the event that directly caused this event.
- data: JSON-compatible object.

## Schema Versioning
The event envelope is versioned explicitly so integrations can evolve without
guessing from payload shape.

Rules:
- Every event MUST include `schema_version`.
- A new required top-level envelope field requires a schema version change.
- Additive changes to event-specific `data` should preserve backwards
  compatibility where practical.
- Consumers should reject unknown major versions and may accept newer minor
  versions when the required fields they depend on are still present.

Initial reference version:
- `1.0`

## Type Naming
Event types use lowercase dotted names:
- `runtime.state_changed`.
- `scheduler.job_registered`.
- `scheduler.job_unregistered`.
- `scheduler.job_due`.
- `scheduler.job_started`.
- `scheduler.job_completed`.
- `scheduler.job_failed`.
- `plugin.loaded`.
- `sensor.metric_observed`.
- `action.requested`.
- `action.approval_required`.
- `policy.action_requested`.
- `approval.decision_recorded`.
- `action.started`.
- `action.succeeded`.
- `action.failed`.
- `verification.started`.
- `verification.succeeded`.
- `verification.failed`.
- `audit.record_written`.
- `notification.delivery_failed`.

## Severity
- debug: useful during local development.
- info: expected state transition or successful operation.
- warning: degraded behavior that does not stop the runtime.
- error: failed operation that needs attention.
- critical: unsafe state or unavailable core runtime.

## State Changes
Every state change MUST emit an event. A state-change event payload should
include `from_state`, `to_state`, and any deterministic reason available.

## Correlation and Causation
Correlation groups a workflow. Causation points to the immediate triggering
event. A sensor event that causes a policy decision and action request should
share one correlation id while each event references its direct parent by
causation id.

## Subscription Filtering
Subscribers may provide deterministic predicates to receive only matching
events. Filters must not mutate events and must not perform AI reasoning.

Common filters:
- event type.
- event source.
- severity.
- subject.

## Backpressure
The reference event bus retains a bounded history of published events for
diagnostics and replay. When the retained buffer reaches its configured
`capacity`, the bus applies a deterministic `backpressure_strategy`:

- `drop_oldest`: evict the oldest retained event and keep the new one.
- `drop_newest`: skip retaining the new event but still deliver it to live
  subscribers.
- `reject`: refuse to publish and raise an error so the caller can handle
  saturation explicitly.

Backpressure only governs the retained history. Live subscribers are always
notified for events that are not rejected, regardless of retention. This keeps
the bus deterministic and prevents unbounded memory growth under event storms
without silently dropping events that active handlers still need.

The bus exposes `capacity`, `backpressure_strategy`, and a monotonic
`dropped_count` for observability. The default configuration is unbounded
(`capacity = null`) to preserve the existing behavior of retaining every event.
