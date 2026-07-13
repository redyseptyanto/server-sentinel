"""Sensor implementations for the Sentinel reference runtime."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess

from sentinel_core.events import Event, EventBus
from sentinel_core.scheduler import ScheduledJob


@dataclass(frozen=True, slots=True)
class SimulatedCpuSensor:
    """Publishes a fixed CPU temperature on a scheduler cadence."""

    event_bus: EventBus
    starting_temp: float = 85.0
    subject: str = "host.cpu"
    source: str = "sentinel.sensor.simulated_cpu"

    def observe(self) -> Event:
        """Emit a placeholder CPU metric event."""
        return self.event_bus.publish(
            Event(
                type="sensor.metric_observed",
                source=self.source,
                subject=self.subject,
                data={"temperature_celsius": float(self.starting_temp)},
            )
        )

    def scheduled_job(self, interval_seconds: int) -> ScheduledJob:
        """Return the recurring scheduler job for this sensor."""
        return ScheduledJob(
            id="simulated_cpu_sensor",
            interval_seconds=interval_seconds,
            handler=self.observe,
        )


@dataclass(frozen=True, slots=True)
class SensorReading:
    """A single sensor fact ready to be emitted as an event."""

    subject: str
    source: str
    data: dict[str, object]


@dataclass(slots=True)
class LinuxCommonSensorPack:
    """Best-effort Linux-first host sensor pack using stdlib and common tools."""

    event_bus: EventBus
    disk_paths: tuple[str, ...] = ("/",)
    include_optional: bool = True
    command_timeout_seconds: float = 2.0

    def observe(self) -> tuple[Event, ...]:
        """Probe common host facts and emit metric events."""
        emitted: list[Event] = []
        for reading in self._collect_readings():
            emitted.append(
                self.event_bus.publish(
                    Event(
                        type="sensor.metric_observed",
                        source=reading.source,
                        subject=reading.subject,
                        data=reading.data,
                    )
                )
            )
        return tuple(emitted)

    def scheduled_job(self, interval_seconds: int) -> ScheduledJob:
        """Return the recurring scheduler job for this sensor pack."""
        return ScheduledJob(
            id="linux_common_sensor_pack",
            interval_seconds=interval_seconds,
            handler=self.observe,
        )

    def _collect_readings(self) -> list[SensorReading]:
        readings: list[SensorReading] = []
        maybe_reading = self._read_cpu_metrics()
        if maybe_reading is not None:
            readings.append(maybe_reading)

        maybe_reading = self._read_memory_metrics()
        if maybe_reading is not None:
            readings.append(maybe_reading)

        readings.extend(self._read_disk_metrics())
        readings.extend(self._read_network_metrics())

        maybe_reading = self._read_process_metrics()
        if maybe_reading is not None:
            readings.append(maybe_reading)

        maybe_reading = self._read_boot_metrics()
        if maybe_reading is not None:
            readings.append(maybe_reading)

        maybe_reading = self._read_session_metrics()
        if maybe_reading is not None:
            readings.append(maybe_reading)

        if self.include_optional:
            for maybe_reading in (
                self._read_service_metrics(),
                self._read_docker_metrics(),
                self._read_storage_health_metrics(),
                self._read_gpu_metrics(),
            ):
                if maybe_reading is not None:
                    readings.append(maybe_reading)
            readings.extend(self._read_battery_metrics())

        return readings

    def _read_cpu_metrics(self) -> SensorReading | None:
        cpu_count = os.cpu_count() or 1
        try:
            load_1m, load_5m, load_15m = os.getloadavg()
        except OSError:
            load_1m = load_5m = load_15m = 0.0

        data: dict[str, object] = {
            "cpu_count": cpu_count,
            "load_1m": round(load_1m, 4),
            "load_5m": round(load_5m, 4),
            "load_15m": round(load_15m, 4),
            "utilization_ratio_1m": round(load_1m / cpu_count, 4),
        }

        temperature = self._read_cpu_temperature()
        if temperature is not None:
            data["temperature_celsius"] = temperature

        frequency = self._read_cpu_frequency_mhz()
        if frequency is not None:
            data["frequency_mhz"] = frequency

        return SensorReading(
            subject="host.cpu",
            source="sentinel.sensor.linux.cpu",
            data=data,
        )

    def _read_memory_metrics(self) -> SensorReading | None:
        meminfo = self._parse_meminfo(self._read_text("/proc/meminfo"))
        if not meminfo:
            return None

        total_kb = meminfo.get("MemTotal")
        available_kb = meminfo.get("MemAvailable")
        if total_kb is None or available_kb is None or total_kb == 0:
            return None

        used_kb = total_kb - available_kb
        return SensorReading(
            subject="host.memory",
            source="sentinel.sensor.linux.memory",
            data={
                "total_kb": total_kb,
                "available_kb": available_kb,
                "used_kb": used_kb,
                "used_percent": round((used_kb / total_kb) * 100.0, 2),
            },
        )

    def _read_disk_metrics(self) -> list[SensorReading]:
        readings: list[SensorReading] = []
        for path in self.disk_paths:
            try:
                usage = shutil.disk_usage(path)
            except OSError:
                continue
            readings.append(
                SensorReading(
                    subject=f"filesystem:{path}",
                    source="sentinel.sensor.linux.disk",
                    data={
                        "path": path,
                        "total_bytes": usage.total,
                        "used_bytes": usage.used,
                        "free_bytes": usage.free,
                        "used_percent": round((usage.used / usage.total) * 100.0, 2)
                        if usage.total
                        else 0.0,
                    },
                )
            )
        return readings

    def _read_network_metrics(self) -> list[SensorReading]:
        by_interface = self._parse_proc_net_dev(self._read_text("/proc/net/dev"))
        if not by_interface:
            return []

        readings: list[SensorReading] = []
        for interface, counters in by_interface.items():
            if interface == "lo":
                continue
            operstate = self._read_text(f"/sys/class/net/{interface}/operstate")
            readings.append(
                SensorReading(
                    subject=f"network:{interface}",
                    source="sentinel.sensor.linux.network",
                    data={
                        "interface": interface,
                        "operstate": (operstate or "unknown").strip(),
                        "rx_bytes": counters["rx_bytes"],
                        "tx_bytes": counters["tx_bytes"],
                    },
                )
            )
        return readings

    def _read_process_metrics(self) -> SensorReading | None:
        try:
            process_count = sum(1 for entry in os.listdir("/proc") if entry.isdigit())
        except OSError:
            return None
        return SensorReading(
            subject="host.processes",
            source="sentinel.sensor.linux.processes",
            data={"process_count": process_count},
        )

    def _read_boot_metrics(self) -> SensorReading | None:
        stat_text = self._read_text("/proc/stat")
        uptime_text = self._read_text("/proc/uptime")
        boot_time_epoch = self._parse_boot_time_epoch(stat_text)
        uptime_seconds = self._parse_uptime_seconds(uptime_text)
        if boot_time_epoch is None and uptime_seconds is None:
            return None

        data: dict[str, object] = {}
        if boot_time_epoch is not None:
            data["boot_time_epoch"] = boot_time_epoch
        if uptime_seconds is not None:
            data["uptime_seconds"] = uptime_seconds
        return SensorReading(
            subject="host.boot",
            source="sentinel.sensor.linux.boot",
            data=data,
        )

    def _read_session_metrics(self) -> SensorReading | None:
        output = self._run_command(("who",))
        if output is None:
            return None
        sessions = [line for line in output.splitlines() if line.strip()]
        return SensorReading(
            subject="host.sessions",
            source="sentinel.sensor.linux.sessions",
            data={"session_count": len(sessions)},
        )

    def _read_service_metrics(self) -> SensorReading | None:
        output = self._run_command(
            ("systemctl", "list-units", "--type=service", "--all", "--plain", "--no-legend", "--no-pager")
        )
        if output is None:
            return None

        total = 0
        failed = 0
        active = 0
        for line in output.splitlines():
            if not line.strip():
                continue
            total += 1
            parts = line.split()
            if len(parts) >= 4:
                active_state = parts[2]
                sub_state = parts[3]
                if active_state == "active":
                    active += 1
                if active_state == "failed" or sub_state == "failed":
                    failed += 1

        return SensorReading(
            subject="host.services",
            source="sentinel.sensor.linux.services",
            data={
                "service_count": total,
                "active_count": active,
                "failed_count": failed,
            },
        )

    def _read_docker_metrics(self) -> SensorReading | None:
        output = self._run_command(("docker", "ps", "-a", "--format", "{{.Status}}"))
        if output is None:
            return None

        statuses = [line.strip() for line in output.splitlines() if line.strip()]
        running = 0
        exited = 0
        unhealthy = 0
        for status in statuses:
            lowered = status.lower()
            if lowered.startswith("up"):
                running += 1
            if lowered.startswith("exited"):
                exited += 1
            if "unhealthy" in lowered:
                unhealthy += 1

        return SensorReading(
            subject="host.docker",
            source="sentinel.sensor.linux.docker",
            data={
                "container_count": len(statuses),
                "running_count": running,
                "exited_count": exited,
                "unhealthy_count": unhealthy,
            },
        )

    def _read_battery_metrics(self) -> list[SensorReading]:
        readings: list[SensorReading] = []
        for battery_path in sorted(Path("/sys/class/power_supply").glob("BAT*")):
            capacity_text = self._read_text(str(battery_path / "capacity"))
            status_text = self._read_text(str(battery_path / "status"))
            if capacity_text is None and status_text is None:
                continue

            data: dict[str, object] = {"name": battery_path.name}
            if capacity_text is not None:
                try:
                    data["capacity_percent"] = float(capacity_text.strip())
                except ValueError:
                    pass
            if status_text is not None:
                data["status"] = status_text.strip()

            readings.append(
                SensorReading(
                    subject=f"battery:{battery_path.name}",
                    source="sentinel.sensor.linux.battery",
                    data=data,
                )
            )
        return readings

    def _read_storage_health_metrics(self) -> SensorReading | None:
        smart_output = self._run_command(("smartctl", "--scan-open"))
        nvme_output = self._run_command(("nvme", "list", "-o", "json"))

        data: dict[str, object] = {}
        if smart_output is not None:
            devices = []
            for line in smart_output.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                devices.append(stripped.split()[0])

            passed = 0
            failed = 0
            unknown = 0
            for device in devices:
                health = self._run_command(("smartctl", "-H", device))
                if health is None:
                    unknown += 1
                    continue
                lowered = health.lower()
                if "passed" in lowered:
                    passed += 1
                elif "failed" in lowered or "bad" in lowered:
                    failed += 1
                else:
                    unknown += 1
            data.update(
                {
                    "smart_device_count": len(devices),
                    "smart_passed_count": passed,
                    "smart_failed_count": failed,
                    "smart_unknown_count": unknown,
                }
            )

        if nvme_output is not None:
            try:
                payload = json.loads(nvme_output)
                devices = payload.get("Devices", [])
                if isinstance(devices, list):
                    data["nvme_device_count"] = len(devices)
            except json.JSONDecodeError:
                pass

        if not data:
            return None
        return SensorReading(
            subject="host.storage_health",
            source="sentinel.sensor.linux.storage",
            data=data,
        )

    def _read_gpu_metrics(self) -> SensorReading | None:
        output = self._run_command(
            (
                "nvidia-smi",
                "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            )
        )
        if output is None:
            return None

        gpu_count = 0
        max_temp: float | None = None
        max_util: float | None = None
        total_memory_used = 0.0
        total_memory = 0.0
        for line in output.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 4:
                continue
            try:
                temperature = float(parts[0])
                utilization = float(parts[1])
                memory_used = float(parts[2])
                memory_total = float(parts[3])
            except ValueError:
                continue
            gpu_count += 1
            max_temp = temperature if max_temp is None else max(max_temp, temperature)
            max_util = utilization if max_util is None else max(max_util, utilization)
            total_memory_used += memory_used
            total_memory += memory_total

        if gpu_count == 0:
            return None

        data: dict[str, object] = {"gpu_count": gpu_count}
        if max_temp is not None:
            data["max_temperature_celsius"] = max_temp
        if max_util is not None:
            data["max_utilization_percent"] = max_util
        if total_memory:
            data["memory_used_mib"] = total_memory_used
            data["memory_total_mib"] = total_memory
        return SensorReading(
            subject="host.gpu",
            source="sentinel.sensor.linux.gpu",
            data=data,
        )

    def _read_cpu_temperature(self) -> float | None:
        candidates: list[float] = []
        for thermal_path in sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp")):
            value = self._parse_millidegree_temperature(self._read_text(str(thermal_path)))
            if value is not None:
                candidates.append(value)
        for hwmon_path in sorted(Path("/sys/class/hwmon").glob("hwmon*/temp*_input")):
            value = self._parse_millidegree_temperature(self._read_text(str(hwmon_path)))
            if value is not None:
                candidates.append(value)
        if not candidates:
            return None
        return max(candidates)

    def _read_cpu_frequency_mhz(self) -> float | None:
        cpuinfo = self._read_text("/proc/cpuinfo")
        if cpuinfo is None:
            return None
        frequencies: list[float] = []
        for line in cpuinfo.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            if key.strip() != "cpu MHz":
                continue
            try:
                frequencies.append(float(value.strip()))
            except ValueError:
                continue
        if not frequencies:
            return None
        return round(sum(frequencies) / len(frequencies), 2)

    def _read_text(self, path: str) -> str | None:
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            return None

    def _run_command(self, command: tuple[str, ...]) -> str | None:
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.command_timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout.strip()

    @staticmethod
    def _parse_millidegree_temperature(raw: str | None) -> float | None:
        if raw is None or not raw:
            return None
        try:
            value = float(raw)
        except ValueError:
            return None
        if value > 1000:
            value /= 1000.0
        return round(value, 2)

    @staticmethod
    def _parse_meminfo(raw: str | None) -> dict[str, int]:
        if raw is None:
            return {}
        parsed: dict[str, int] = {}
        for line in raw.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields = value.strip().split()
            if not fields:
                continue
            try:
                parsed[key] = int(fields[0])
            except ValueError:
                continue
        return parsed

    @staticmethod
    def _parse_proc_net_dev(raw: str | None) -> dict[str, dict[str, int]]:
        if raw is None:
            return {}
        readings: dict[str, dict[str, int]] = {}
        for line in raw.splitlines()[2:]:
            if ":" not in line:
                continue
            interface, payload = line.split(":", 1)
            parts = payload.split()
            if len(parts) < 16:
                continue
            try:
                readings[interface.strip()] = {
                    "rx_bytes": int(parts[0]),
                    "tx_bytes": int(parts[8]),
                }
            except ValueError:
                continue
        return readings

    @staticmethod
    def _parse_boot_time_epoch(raw: str | None) -> int | None:
        if raw is None:
            return None
        for line in raw.splitlines():
            if not line.startswith("btime "):
                continue
            _, value = line.split(maxsplit=1)
            try:
                return int(value.strip())
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_uptime_seconds(raw: str | None) -> float | None:
        if raw is None:
            return None
        parts = raw.split()
        if not parts:
            return None
        try:
            return float(parts[0])
        except ValueError:
            return None
