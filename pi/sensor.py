from dataclasses import dataclass
import logging
from pathlib import Path
import random

logger = logging.getLogger(__name__)

try:
    import board  # pyright: ignore[reportMissingImports]
    import adafruit_hdc302x  # pyright: ignore[reportMissingImports]
except ImportError:
    logger.warning(
        "Failed to import sensor libraries; sensor functionality will be disabled."
    )
    pass


@dataclass
class SensorData:
    temperature: float | None
    humidity: float | None
    cpu_temperature: float | None

    def __add__(self, other: "SensorData") -> "SensorData":
        return SensorData(
            temperature=_safe_add(self.temperature, other.temperature),
            humidity=_safe_add(self.humidity, other.humidity),
            cpu_temperature=_safe_add(self.cpu_temperature, other.cpu_temperature),
        )

    def __truediv__(self, divisor: float) -> "SensorData":
        return SensorData(
            temperature=_safe_divide(self.temperature, divisor),
            humidity=_safe_divide(self.humidity, divisor),
            cpu_temperature=_safe_divide(self.cpu_temperature, divisor),
        )


def _safe_add(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return a + b


def _safe_divide(a: float | None, divisor: float) -> float | None:
    if a is None:
        return None
    return a / divisor


@dataclass
class SensorStatus:
    raw_value: int
    alert_active: bool
    heater_on: bool
    relative_humidity_alert: bool
    temperature_alert: bool
    reset_detected: bool
    checksum_error: bool


# The HDC302x address is set by its ADDR pins.
_HDC302X_ADDRESSES = {0x44, 0x45, 0x46, 0x47}
_CPU_TEMPERATURE_PATH = Path("/sys/class/thermal/thermal_zone0/temp")


def hdc302x_connected() -> bool:
    """Whether a HDC302x answers on the I2C bus, without taking a measurement."""
    i2c = board.I2C()  # pyright: ignore[reportPossiblyUnboundVariable]
    while not i2c.try_lock():
        pass
    try:
        return not _HDC302X_ADDRESSES.isdisjoint(i2c.scan())
    finally:
        i2c.unlock()


def cpu_temperature_available() -> bool:
    return _CPU_TEMPERATURE_PATH.exists()


def read_sensor_data(mock_data: bool) -> SensorData:
    read_sensor = _mock_sensor_data if mock_data else _read_pi_sensor
    sensor_readings = [read_sensor() for _ in range(5)]
    return sum(sensor_readings, SensorData(0.0, 0.0, 0.0)) / len(sensor_readings)


def _get_sensor():
    try:
        i2c = board.I2C()  # pyright: ignore[reportPossiblyUnboundVariable]
        return adafruit_hdc302x.HDC302x(i2c)  # pyright: ignore[reportPossiblyUnboundVariable]
    except Exception:
        logger.error("Failed to initialize sensor", exc_info=True)
        return None


def read_pi_sensor_status() -> SensorStatus | None:
    sensor = _get_sensor()
    if sensor is None:
        return None
    return _parse_hdc302x_status(sensor.status)


def _parse_hdc302x_status(status_int: int) -> SensorStatus:
    """
    Parses the 16-bit integer status from the HDC302x into a readable dataclass.
    """
    return SensorStatus(
        raw_value=status_int,
        alert_active=bool(status_int & (1 << 15)),
        heater_on=bool(status_int & (1 << 13)),
        relative_humidity_alert=bool(status_int & (1 << 11)),
        temperature_alert=bool(status_int & (1 << 10)),
        reset_detected=bool(status_int & (1 << 4)),
        checksum_error=bool(status_int & (1 << 0)),
    )


def _read_pi_sensor() -> SensorData:
    sensor = _get_sensor()
    return SensorData(
        temperature=sensor.temperature if sensor else None,
        humidity=sensor.relative_humidity if sensor else None,
        cpu_temperature=_read_cpu_temperature(),
    )


def _read_cpu_temperature() -> float | None:
    try:
        return float(_CPU_TEMPERATURE_PATH.read_text().strip()) / 1000.0
    except Exception:
        logger.error("Failed to read CPU temperature", exc_info=True)
        return None


def _mock_sensor_data() -> SensorData:
    temperature = 25 + random.random()
    humidity = 40 + random.random()
    cpu_temperature = 50 + random.random()
    return SensorData(
        temperature=temperature, humidity=humidity, cpu_temperature=cpu_temperature
    )
