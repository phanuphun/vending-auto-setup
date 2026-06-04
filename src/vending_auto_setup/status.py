from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ToolStatus:
    name: str
    command: str
    installed: bool
    version: str | None
    path: str | None


@dataclass(frozen=True)
class DisplaySessionStatus:
    session_type: str
    is_x11: bool
    source: str


TOOLS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Git", "git", ("git", "--version")),
    ("Node.js", "node", ("node", "--version")),
    ("npm", "npm", ("npm", "--version")),
    ("Docker", "docker", ("docker", "--version")),
)


def collect_status() -> tuple[ToolStatus, ...]:
    return tuple(_check_tool(name, command, version_args) for name, command, version_args in TOOLS)


def collect_display_session_status() -> DisplaySessionStatus:
    env_session_type = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
    if env_session_type:
        return DisplaySessionStatus(
            session_type=env_session_type,
            is_x11=env_session_type == "x11",
            source="XDG_SESSION_TYPE",
        )

    loginctl_session_type = _read_loginctl_session_type()
    if loginctl_session_type:
        normalized_session_type = loginctl_session_type.strip().lower()
        return DisplaySessionStatus(
            session_type=normalized_session_type,
            is_x11=normalized_session_type == "x11",
            source="loginctl",
        )

    return DisplaySessionStatus(session_type="unknown", is_x11=False, source="not detected")


def print_status() -> None:
    print("Vending Auto Setup Status")
    print()
    _print_display_session_status(collect_display_session_status())
    print()
    print("[Core Tools]")
    for status in collect_status():
        _print_tool_status(status)


def main() -> int:
    statuses = collect_status()
    print("Vending Auto Setup Status")
    print()
    _print_display_session_status(collect_display_session_status())
    print()
    print("[Core Tools]")
    for status in statuses:
        _print_tool_status(status)

    return 0 if all(status.installed for status in statuses) else 1


def _check_tool(name: str, command: str, version_args: Sequence[str]) -> ToolStatus:
    path = shutil.which(command)
    if path is None:
        return ToolStatus(name=name, command=command, installed=False, version=None, path=None)

    version = _read_version((path, *version_args[1:]))
    return ToolStatus(name=name, command=command, installed=True, version=version, path=path)


def _read_version(args: Sequence[str]) -> str | None:
    completed = subprocess.run(
        tuple(args),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return _first_output_line(completed.stderr)
    return _first_output_line(completed.stdout) or _first_output_line(completed.stderr)


def _first_output_line(output: str) -> str | None:
    stripped_output = output.strip()
    return stripped_output.splitlines()[0] if stripped_output else None


def _read_loginctl_session_type() -> str | None:
    session_id = os.environ.get("XDG_SESSION_ID", "").strip()
    if not session_id:
        return None

    completed = subprocess.run(
        ("loginctl", "show-session", session_id, "-p", "Type", "--value"),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return None
    return _first_output_line(completed.stdout)


def _print_display_session_status(status: DisplaySessionStatus) -> None:
    print("[Session]")
    marker = "OK" if status.is_x11 else "WARN"
    detail = f"{status.session_type} ({status.source})"
    print(f"{marker:7} {'Display':10} {detail}")


def _print_tool_status(status: ToolStatus) -> None:
    marker = "OK" if status.installed else "MISSING"
    detail = status.version if status.version is not None else "not installed"
    print(f"{marker:7} {status.name:10} {detail}")
