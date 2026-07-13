# Event Specification

Events are immutable facts. They are the primary contract between Sentinel
subsystems and plugins.

## Envelope
Required fields:
- id: UUID string.
- type: namespaced event type such as `runtime.state_changed`.
- source: component or plugin that emitted the event.
- subject: resource the event is about.
- occurred_at: UTC timestamp in ISO 8601 format.
- severity: debug, info, warning, error, or critical.
- correlation_id: workflow identifier shared by related events.
- causation_id: identifier of the event that directly caused this event.
- data: JSON-compatible object.

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
