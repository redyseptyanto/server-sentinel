# Deployment (Linux)

This document describes how Sentinel is deployed on a Linux host using
systemd user services and a Telegram human-in-the-loop approval channel. It is
the **operational** view of a running instance — the parts that live around the
repository rather than inside it.

The repository itself remains cross-platform (Linux first, then Windows and
macOS per the project charter). Everything in this file is the Linux-specific
glue for one concrete deployment: a compact Ryzen mini-PC running Ubuntu with
Hermes on Telegram.

## The three layers

A running Sentinel deployment is best understood as three layers. Each has a
different job, and only one of them contains monitoring logic.

```
repo (the brain: senses + decides + acts)
   ^ run by
systemd (the heartbeat: keeps it alive, reboots it)
   ^ talks out to
receiver/poller (the mouth/ears: Telegram I/O the repo does not have)
```

### 1. The repository — the brain

`~/projects/server-sentinel` is the actual product. It is the only layer that
knows what a "critical temperature" means or how to read your CPU.

- `sentinel_core/sensors.py` — reads real host data (`/proc`, `sysfs`/hwmon,
  `docker`, `nvme`/`smartctl` where available).
- `sentinel_core/policies.py` — the thermal state machine
  (Warning / Critical / Emergency, rearm).
- `sentinel_core/actions.py` — executes or requests mitigations.
- `sentinel_core/scheduler.py`, `events.py`, `config.py`, `hermes_client.py`
  — the runtime engine.
- `tests/` — the test suite. `sentinel.example.toml` — the template.
  `cli.py` — the `run` / `validate-config` commands.

Without the repository there is no monitoring. The systemd service's
`ExecStart` literally points into this directory.

### 2. systemd user service — the heartbeat

This layer does exactly one thing: run
`python3 -m sentinel_core run --config sentinel.toml` and restart it if it
crashes, and start it on boot. It contains **zero monitoring logic**. Kill the
repository code and the service would only keep relaunching a dead thing.

On this host there are three always-on user services:

| Service | Role |
|---|---|
| `sentinel-monitor` | real host monitoring + thermal policy (the engine) |
| `sentinel-receiver` | event ingest + approval parking + Telegram HITL bridge |
| `sentinel-approval-poller` | Telegram tap listener + on-demand `/status`/`/top`/`/health` |

With `loginctl enable-linger` set, these survive reboots and run with no active
login session.

### 3. External glue scripts — the mouth and ears

`~/sentinel_receiver.py` and `~/sentinel_approval_poller.py` live in the home
directory, **outside** the repository. The reference design assumes a generic
"Hermes" endpoint for notifications and approvals; these scripts are that
endpoint, bridging the repository's HTTP output to your Telegram:

- The receiver implements the `/api/v1/events` and
  `/api/v1/approval-requests` endpoints the repo pushes to.
- The poller long-polls the dedicated `@sentinel_approvals_bot`, captures
  inline-button taps, and forwards decisions back to unblock parked approvals.
- It also answers `/status`, `/top`, and `/health` with a live host snapshot
  produced by calling the repository's `LinuxCommonSensorPack` directly — a
  fresh, read-only `/proc` read, no fork of the core.

This separation keeps the repository pristine and portable; the glue is local
to this host and Telegram account.

## Why the layers matter

- The **repo** is portable and upgradeable: `git pull` brings new sensor or
  policy features, the tests validate them, and the systemd service
  automatically runs whatever version is checked out.
- The **service** is meaningless without the repo but makes the repo
  hands-off: no manual relaunch after a reboot or crash.
- The **glue** is the only host-specific, non-portable piece — and it is kept
  out of the repo on purpose.

## systemd units (this host)

`~/.config/systemd/user/sentinel-monitor.service`:

```ini
[Unit]
Description=Sentinel Runtime (real host monitoring + thermal policy)
After=network.target sentinel-receiver.service sentinel-approval-poller.service
Wants=sentinel-receiver.service sentinel-approval-poller.service

[Service]
Type=simple
WorkingDirectory=%h/projects/server-sentinel
ExecStart=/usr/bin/python3 -m sentinel_core run --config sentinel.toml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

`~/.config/systemd/user/sentinel-receiver.service` and
`~/.config/systemd/user/sentinel-approval-poller.service` follow the same
shape, loading secrets from `~/.config/sentinel/receiver.env` (mode `600`).

Enable and start:

```bash
loginctl enable-linger "$USER"
systemctl --user daemon-reload
systemctl --user enable --now sentinel-monitor.service
systemctl --user enable --now sentinel-receiver.service
systemctl --user enable --now sentinel-approval-poller.service
```

## On-demand host status

Send a message to the approval bot on Telegram:

- `/status` — CPU temp/load/util, memory, disks, Docker, services, uptime,
  sessions, top-3 CPU processes.
- `/top` — top-3 processes by CPU and by RAM.
- `/health` — threshold-state check (OK / WARNING / CRITICAL / EMERGENCY)
  against the configured `[thermal_policy]` thresholds.

A chat-id gate restricts these to the operator's chat.

## Caveats

- The mitigations themselves remain simulated in the reference core: the
  repository records and verifies the workflow but does not yet terminate
  processes, stop containers, or shut down the host for real.
- The external glue scripts are not part of the repository and are not covered
  by the repository's tests.
