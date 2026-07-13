# Monitoring Specification

Sentinel monitors hosts through plugin-driven sensors. Linux is the first
delivery target, but the monitoring model must stay portable across Windows and
macOS.

## Monitoring Domains
- Hardware: CPU temperature, utilization, frequency, memory, disk usage, disk
  health through SMART or NVMe data, network, battery where available, and GPU
  through optional plugins.
- Operating system: processes, services, system logs, boot status, and login
  sessions.
- Containers: Docker Engine, Docker Compose projects, container health, logs,
  and resource usage.
- Applications: user-defined health checks, HTTP endpoints, TCP services, and
  background workers.

## Sensor Model
- Sensors are plugins.
- Sensors observe and emit facts; they do not execute recovery actions.
- Sensors emit metrics, diagnostics, and lifecycle events.
- Sensors should be independently configurable and schedulable.

## Event Expectations
Everything produces events.

Illustrative event types:
- `cpu.temperature.warning`
- `cpu.temperature.critical`
- `memory.high`
- `disk.almost_full`
- `docker.container.unhealthy`
- `service.failed`
- `network.offline`
- `application.healthcheck.failed`

## Linux-First Expectations
The first sensor set should prioritize:
- `sysfs`, `/proc`, and system tools for CPU, memory, disk, and thermal data.
- `systemd` service state.
- `journalctl` and relevant system logs.
- Docker daemon and Compose state.

Windows and macOS support should preserve the same domain model and event
contracts while changing only the platform-specific sensor implementations.
