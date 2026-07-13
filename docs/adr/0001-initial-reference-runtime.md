# ADR 0001: Initial Reference Runtime

Date: 2026-07-13

## Status
Accepted

## Context
Sentinel needs a first executable foundation that contributors can inspect and
test immediately. The local project workspace currently has Python 3.13
available, while Rust, Go, Node.js, and .NET toolchains are not installed.

The long-term runtime must remain cross-platform, event-driven, plugin-first,
and safe for host automation. Sentinel core must not perform AI reasoning.

## Decision
Build the initial reference runtime in stdlib-only Python.

The first implementation will define:
- Runtime lifecycle.
- Structured event envelope.
- In-memory event bus.
- Append-only JSON Lines audit sink.
- Unit tests using `unittest`.

## Consequences
Positive:
- Contributors can run tests with the available local toolchain.
- The first foundation can avoid external services and dependencies.
- Domain contracts can stabilize before native platform work begins.

Tradeoffs:
- Python may not be the final implementation language for privileged,
  performance-sensitive host operations.
- Some future sensors or actions may need native adapters.

Follow-up:
- Keep domain ports narrow so a future native runtime or native adapters can
  preserve the same event and audit contracts.
