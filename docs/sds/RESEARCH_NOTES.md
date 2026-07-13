# Research Notes

This file records conceptual research only. Sentinel must not copy code from
other projects.

## Netdata
Source: https://learn.netdata.cloud/docs/alerts-%26-notifications

Relevant concepts:
- Health evaluation is tied to metrics and state transitions.
- Notifications are actions derived from alert state.
- Alert configuration supports tuning without changing collector code.

Sentinel application:
- Policies should produce explicit state-transition events.
- Notification plugins should consume events instead of owning policy logic.

## Telegraf
Source: https://docs.influxdata.com/telegraf/v1/plugins/

Relevant concepts:
- Plugin-driven agent architecture.
- Distinct plugin categories such as input, output, aggregator, and processor.
- External plugins can be run outside the core process.

Sentinel application:
- Sentinel plugins should be categorized by responsibility.
- The long-term plugin contract should support out-of-process execution.

## Prometheus node_exporter
Source: https://github.com/prometheus/node_exporter

Relevant concepts:
- Collector model for host metrics.
- Collectors can be enabled or disabled by configuration.
- Hardware and kernel metrics are exposed through consistent metric families.

Sentinel application:
- Sensors should be independently enabled and configured.
- Sensor events should use stable names and tags.

## osquery
Source: https://osquery.readthedocs.io/en/stable/deployment/configuration/

Relevant concepts:
- Scheduled host-state collection.
- Query packs group related checks.
- State changes can be logged over time.

Sentinel application:
- Policy and sensor packs should group related host checks.
- Scheduled sensors should emit events that can be audited and replayed.
