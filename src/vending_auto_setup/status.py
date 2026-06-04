from __future__ import annotations

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


TOOLS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Git", "git", ("git", "--version")),
    ("Node.js", "node", ("node", "--version")),
    ("npm", "npm", ("npm", "--version")),
    ("Docker", "docker", ("docker", "--version")),
)


def collect_status() -> tuple[ToolStatus, ...]:
    return tuple(_check_tool(name, command, version_args) for name, command, version_args in TOOLS)


def print_status() -> None:
    print("Vending Auto Setup Status")
    for status in collect_status():
        marker = "OK" if status.installed else "MISSING"
        detail = status.version if status.version is not None else "not installed"
        print(f"{marker:7} {status.name:7} {detail}")


def main() -> int:
    statuses = collect_status()
    print("Vending Auto Setup Status")
    for status in statuses:
        marker = "OK" if status.installed else "MISSING"
        detail = status.version if status.version is not None else "not installed"
        print(f"{marker:7} {status.name:7} {detail}")

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
