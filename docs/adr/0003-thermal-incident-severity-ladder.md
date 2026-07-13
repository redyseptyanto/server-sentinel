# ADR 0003: Thermal Incident Severity Ladder

Date: 2026-07-13

## Status
Accepted

## Context
The first Sentinel thermal recovery slice used a single threshold and a single
simulated `cool_down` action. That was useful for proving the event-policy-
action loop, but it was too coarse for real host monitoring.

For compact Linux hosts such as a Geekom A8 class mini PC, thermal recovery
needs more than one state:
- operators need early warning before the host is in danger
- hot NVMe storage should be visible separately from CPU overheating
- destructive mitigations must remain approval-gated and auditable
- emergency shutdown must never happen on the first hot sample

The SDS also requires incident-based notifications, protected process rules,
verification before escalation, and a stable interface between Sentinel and
Hermes.

## Decision
Sentinel will model thermal recovery as a severity ladder with separate warning,
critical, and emergency states driven by a dedicated `[thermal_policy]`
configuration table.

Default reference thresholds are:
- CPU warning: 70 C
- NVMe warning: 80 C
- CPU critical: 85 C
- CPU emergency: 95 C after a 30 second hold period
- re-arm below: 60 C

The reference policy behavior is:
1. Warning emits an incident event once per incident and includes diagnostic
   context.
2. Critical emits an incident event and requests graceful mitigation of the
   highest CPU processes that are not protected by policy.
3. Emergency emits an incident event after the hold period, requests workload
   reduction, and may request a clean shutdown after the configured approval
   timeout if the host remains overheated.

## Consequences
Positive:
- Sentinel can warn earlier without immediately escalating to destructive
  recovery.
- Recovery actions now carry richer diagnostics, including CPU usage, memory
  usage, top processes, Docker summary, and storage health context.
- Protected process filtering is explicit and configurable.
- Hermes receives clearer incident stages and approval requests.

Tradeoffs:
- The runtime becomes stateful across incidents and re-arm transitions.
- Configuration is broader and needs clearer documentation.
- Simulation without an approval provider no longer implies destructive action
  success; those actions remain deferred by design.

Follow-up:
- Add real verifiers for process mitigation, workload reduction, and shutdown
  flows.
- Add Compose-aware Docker monitoring and container resource sampling.
- Add suppression windows and operator policy packs.
