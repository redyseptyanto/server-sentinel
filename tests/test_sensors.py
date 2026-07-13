from datetime import UTC, datetime, timedelta
import unittest
from unittest.mock import patch

from sentinel_core import InMemoryEventBus, LinuxCommonSensorPack, Scheduler, SimulatedCpuSensor
from sentinel_core.sensors import SensorReading


class SimulatedCpuSensorTests(unittest.TestCase):
    def test_observe_publishes_temperature_event(self) -> None:
        bus = InMemoryEventBus()
        sensor = SimulatedCpuSensor(event_bus=bus, starting_temp=85.0)

        sensor.observe()

        self.assertEqual(bus.events[-1].type, "sensor.metric_observed")
        self.assertEqual(bus.events[-1].data["temperature_celsius"], 85.0)

    def test_sensor_can_be_scheduled(self) -> None:
        bus = InMemoryEventBus()
        scheduler = Scheduler(bus)
        sensor = SimulatedCpuSensor(event_bus=bus, starting_temp=72.5)
        now = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)

        scheduler.register(sensor.scheduled_job(5), now=now)
        scheduler.run_due(now=now + timedelta(seconds=5))

        metric_events = [event for event in bus.events if event.type == "sensor.metric_observed"]
        self.assertEqual(len(metric_events), 1)
        self.assertEqual(metric_events[0].data["temperature_celsius"], 72.5)


class LinuxCommonSensorPackTests(unittest.TestCase):
    def test_observe_publishes_common_linux_readings(self) -> None:
        bus = InMemoryEventBus()
        pack = LinuxCommonSensorPack(event_bus=bus, disk_paths=("/", "/var"))

        with patch.object(
            LinuxCommonSensorPack,
            "_collect_readings",
            return_value=[
                SensorReading(
                    subject="host.cpu",
                    source="sentinel.sensor.linux.cpu",
                    data={"temperature_celsius": 67.5, "cpu_count": 8},
                ),
                SensorReading(
                    subject="host.memory",
                    source="sentinel.sensor.linux.memory",
                    data={"used_percent": 42.5},
                ),
            ],
        ):
            emitted = pack.observe()

        self.assertEqual(len(emitted), 2)
        self.assertEqual([event.subject for event in bus.events], ["host.cpu", "host.memory"])
        self.assertEqual(bus.events[0].data["temperature_celsius"], 67.5)

    def test_sensor_pack_can_be_scheduled(self) -> None:
        bus = InMemoryEventBus()
        scheduler = Scheduler(bus)
        pack = LinuxCommonSensorPack(event_bus=bus)
        now = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)

        with patch.object(
            LinuxCommonSensorPack,
            "_collect_readings",
            return_value=[
                SensorReading(
                    subject="host.processes",
                    source="sentinel.sensor.linux.processes",
                    data={"process_count": 123},
                )
            ],
        ):
            scheduler.register(pack.scheduled_job(10), now=now)
            scheduler.run_due(now=now + timedelta(seconds=10))

        metric_events = [event for event in bus.events if event.type == "sensor.metric_observed"]
        self.assertEqual(len(metric_events), 1)
        self.assertEqual(metric_events[0].data["process_count"], 123)

    def test_parse_meminfo_returns_expected_fields(self) -> None:
        parsed = LinuxCommonSensorPack._parse_meminfo(
            "\n".join(
                [
                    "MemTotal:       16384 kB",
                    "MemAvailable:    4096 kB",
                ]
            )
        )

        self.assertEqual(parsed["MemTotal"], 16384)
        self.assertEqual(parsed["MemAvailable"], 4096)

    def test_parse_proc_net_dev_reads_rx_and_tx_bytes(self) -> None:
        parsed = LinuxCommonSensorPack._parse_proc_net_dev(
            "\n".join(
                [
                    "Inter-|   Receive                                                |  Transmit",
                    " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed",
                    "eth0: 1234 0 0 0 0 0 0 0 5678 0 0 0 0 0 0 0",
                ]
            )
        )

        self.assertEqual(parsed["eth0"]["rx_bytes"], 1234)
        self.assertEqual(parsed["eth0"]["tx_bytes"], 5678)

    def test_cpu_metrics_include_temperature_when_available(self) -> None:
        pack = LinuxCommonSensorPack(event_bus=InMemoryEventBus())

        with patch.object(LinuxCommonSensorPack, "_read_cpu_temperature", return_value=81.2), patch.object(
            LinuxCommonSensorPack, "_read_cpu_frequency_mhz", return_value=2300.0
        ), patch("sentinel_core.sensors.os.cpu_count", return_value=4), patch(
            "sentinel_core.sensors.os.getloadavg",
            return_value=(2.0, 1.0, 0.5),
            create=True,
        ):
            reading = pack._read_cpu_metrics()

        assert reading is not None
        self.assertEqual(reading.data["temperature_celsius"], 81.2)
        self.assertEqual(reading.data["frequency_mhz"], 2300.0)
        self.assertEqual(reading.data["cpu_count"], 4)


if __name__ == "__main__":
    unittest.main()
