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

## Current Reference Slice
The reference runtime includes a simulated CPU sensor for thermal recovery
development. It publishes `sensor.metric_observed` events with a
`temperature_celsius` field on a scheduler cadence so policy and action flows
can be tested without host-specific integrations.

The next Linux-first slice also includes a common sensor pack that emits
best-effort host facts for the most common monitoring domains without requiring
third-party Python dependencies.

Current implementation status:
- Simulated thermal sensor: done.
- Linux common sensor pack: done.
- Real Docker, SMART, NVMe, battery, GPU, and service probes: best-effort and
  optional.

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

## Linux Common Sensor Pack
The common Linux pack should probe:
- CPU temperature, load average, and frequency where exposed.
- Memory totals and available memory from `/proc/meminfo`.
- Disk usage for configured filesystem paths.
- Network interface operstate and byte counters.
- Process count, boot time, and uptime.
- Login sessions from `who`.

Optional probes should run only when the host exposes them:
- `systemctl` service summary.
- Docker container summary.
- SMART and NVMe health.
- Battery status.
- GPU status through commands such as `nvidia-smi`.

Missing commands or host capabilities must not crash the runtime. They should
either skip the probe or emit a deterministic diagnostic event.

Windows and macOS support should preserve the same domain model and event
contracts while changing only the platform-specific sensor implementations.
