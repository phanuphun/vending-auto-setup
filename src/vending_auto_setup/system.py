from __future__ import annotations

import os
import platform
from pathlib import Path

from vending_auto_setup.runner import CommandRunner


def require_linux() -> None:
    if platform.system().lower() != "linux":
        raise RuntimeError("This installer is intended for Ubuntu Linux.")


def require_root() -> None:
    if os.geteuid() != 0:
        raise RuntimeError("Run this installer as root, for example: sudo vending-auto-setup install")


def detect_ubuntu_codename() -> str:
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return "jammy"

    values: dict[str, str] = {}
    for line in os_release.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        values[key] = raw_value.strip().strip('"')

    return values.get("VERSION_CODENAME", "jammy")


def command_exists(runner: CommandRunner, command: str) -> bool:
    result = runner.run(["bash", "-lc", f"command -v {command}"], check=False)
    return result.returncode == 0
