from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class SystemInfo:
    hostname: str | None
    model: str | None
    os: str | None
    kernel: str | None
    architecture: str | None
    python: str | None
    commit: str | None
    boot_time: datetime | None
    load_average: tuple[float, float, float] | None
    memory_total: int | None
    memory_available: int | None
    disk_total: int | None
    disk_free: int | None


def read_system_info() -> SystemInfo:
    # Each field is read independently, so that a field that can't be read on
    # this machine (e.g. the device tree model when running in Docker) doesn't
    # take the rest down with it.
    meminfo = _safe(_read_meminfo) or {}
    disk = _safe(lambda: shutil.disk_usage("/"))
    return SystemInfo(
        hostname=_safe(socket.gethostname),
        model=_safe(_read_model),
        os=_safe(_read_os),
        kernel=_safe(platform.release),
        architecture=_safe(platform.machine),
        python=_safe(platform.python_version),
        commit=_safe(_read_commit),
        boot_time=_safe(_read_boot_time),
        load_average=_safe(os.getloadavg),
        memory_total=meminfo.get("MemTotal"),
        memory_available=meminfo.get("MemAvailable"),
        disk_total=disk.total if disk else None,
        disk_free=disk.free if disk else None,
    )


def _safe(read: Callable[[], T]) -> T | None:
    try:
        return read() or None
    except Exception as e:
        logger.debug(f"Failed to read system info: {e}")
        return None


def _read_model() -> str:
    # The device tree strings are null terminated.
    return Path("/proc/device-tree/model").read_text().rstrip("\x00").strip()


def _read_os() -> str | None:
    for line in Path("/etc/os-release").read_text().splitlines():
        key, _, value = line.partition("=")
        if key == "PRETTY_NAME":
            return value.strip('"')
    return None


def _read_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        check=True,
        timeout=2,
    ).stdout.strip()


def _read_boot_time() -> datetime:
    uptime = float(Path("/proc/uptime").read_text().split()[0])
    return (datetime.now(timezone.utc) - timedelta(seconds=uptime)).replace(
        microsecond=0
    )


def _read_meminfo() -> dict[str, int]:
    # Values are reported in kB; convert to bytes to match the disk figures.
    meminfo = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, value = line.partition(":")
        parts = value.split()
        if parts and parts[0].isdigit():
            meminfo[key] = int(parts[0]) * 1024
    return meminfo
