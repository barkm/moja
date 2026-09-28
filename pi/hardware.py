from dataclasses import dataclass
import logging
from typing import Callable

from sensor import cpu_temperature_available, hdc302x_connected
from stream import camera_available, get_microphone

logger = logging.getLogger(__name__)


@dataclass
class Hardware:
    camera: bool
    microphone: str | None
    temperature_humidity: bool
    cpu_temperature: bool


def detect_hardware(test_stream: bool, test_sensor: bool) -> Hardware:
    # Detection only checks that the hardware is connected, without starting a
    # stream or taking a measurement, so it's cheap enough to run on startup.
    # The Pis reboot nightly, which keeps the result reasonably fresh.
    microphone = None if test_stream else _safe(get_microphone)
    return Hardware(
        camera=test_stream or bool(_safe(camera_available)),
        microphone=microphone.name if microphone else None,
        temperature_humidity=test_sensor or bool(_safe(hdc302x_connected)),
        cpu_temperature=test_sensor or bool(_safe(cpu_temperature_available)),
    )


def _safe[T](detect: Callable[[], T]) -> T | None:
    try:
        return detect()
    except Exception as e:
        logger.info(f"Failed to detect hardware with {detect.__name__}: {e}")
        return None
