# Runtime Specification

The runtime is the composition root for Sentinel. It owns lifecycle state,
module wiring, event routing, and plugin coordination.

## States
- created.
- starting.
- running.
- stopping.
- stopped.
- failed.

## Lifecycle Rules
- `start` transitions `created` or `stopped` to `starting`, then `running`.
- `stop` transitions `running` to `stopping`, then `stopped`.
- `fail` transitions any non-stopped state to `failed`.
- Every transition emits `runtime.state_changed`.
- Calling `start` while already running is a no-op.
- Calling `stop` while already stopped is a no-op.

## Core Responsibilities
- Compose configured modules.
- Emit lifecycle events.
- Route events through the event bus.
- Expose runtime diagnostics.
- Shut down safely.

## Composition Root
The composition root validates configuration and wires the initial runtime:
- In-memory event bus.
- Optional JSON Lines audit sink subscribed before runtime startup.
- Runtime instance using the configured runtime id.

Startup must not transition to `running` if configuration validation fails.

## Core Non-Responsibilities
- AI reasoning.
- Notification formatting.
- Host-specific action implementation.
- Platform-specific sensor implementation.
- Long-term event storage beyond configured audit sinks.

## Failure Behavior
Runtime failures must emit a critical event when the event bus is available.
If the event bus itself is unavailable, the runtime must expose the failure to
the caller and avoid pretending the transition succeeded.
