from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


PROGRAM_LOG_NAME = "events.jsonl"
SYSTEM_SOURCE_PATHS = (
    Path("/var/log/auth.log"),
    Path("/var/log/syslog"),
    Path("/var/log/messages"),
    Path("/var/log/kern.log"),
)
SYSTEM_TAIL_LINES = 500


def default_log_dir() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config_home) if config_home else Path.home() / ".config"
    return root / "vending-auto-setup" / "logs"


def program_log_path(log_dir: Path | None = None) -> Path:
    return (log_dir or default_log_dir()) / "program" / PROGRAM_LOG_NAME


def system_snapshot_dir(log_dir: Path | None = None) -> Path:
    return (log_dir or default_log_dir()) / "system" / "snapshots"


def log_program_event(
    *,
    source: str,
    action: str,
    status: str = "ok",
    details: Mapping[str, object] | None = None,
    log_dir: Path | None = None,
) -> None:
    path = program_log_path(log_dir)
    event = {
        "timestamp": _utc_timestamp(),
        "source": source,
        "action": action,
        "status": status,
        "details": dict(details or {}),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        return


def log_cli_invocation(
    *,
    argv: Sequence[str],
    command: str,
    dry_run: bool,
    status: str = "started",
    exit_code: int | None = None,
    log_dir: Path | None = None,
) -> None:
    details: dict[str, object] = {
        "argv": tuple(argv),
        "command": command,
        "dry_run": dry_run,
    }
    if exit_code is not None:
        details["exit_code"] = exit_code
    log_program_event(
        source="cli",
        action="cli.invoke",
        status=status,
        details=details,
        log_dir=log_dir,
    )


def log_runner_command(
    *,
    args: Sequence[str],
    dry_run: bool,
    returncode: int,
    status: str = "ok",
    log_dir: Path | None = None,
) -> None:
    log_program_event(
        source="cli",
        action="runner.command",
        status=status,
        details={
            "args": tuple(args),
            "dry_run": dry_run,
            "returncode": returncode,
        },
        log_dir=log_dir,
    )


def log_web_event(
    *,
    action: str,
    status: str = "ok",
    details: Mapping[str, object] | None = None,
    log_dir: Path | None = None,
) -> None:
    log_program_event(
        source="web",
        action=action,
        status=status,
        details=details,
        log_dir=log_dir,
    )


def read_program_events(limit: int = 100, log_dir: Path | None = None) -> tuple[dict[str, object], ...]:
    path = program_log_path(log_dir)
    if not path.exists():
        return ()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()

    events: list[dict[str, object]] = []
    for line in lines[-limit:]:
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            parsed = {"timestamp": "", "source": "program", "action": "unreadable", "status": "error", "details": {"raw": line}}
        if isinstance(parsed, dict):
            events.append(parsed)
    return tuple(reversed(events))


def create_system_log_snapshot(log_dir: Path | None = None) -> dict[str, object]:
    snapshot_dir = system_snapshot_dir(log_dir)
    snapshot_id = _utc_timestamp(compact=True)
    path = snapshot_dir / f"{snapshot_id}.log"
    body = _render_system_snapshot()
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return {
        "id": snapshot_id,
        "path": path.as_posix(),
        "size": path.stat().st_size,
        "created": _utc_timestamp(),
    }


def list_system_snapshots(limit: int = 50, log_dir: Path | None = None) -> tuple[dict[str, object], ...]:
    snapshot_dir = system_snapshot_dir(log_dir)
    if not snapshot_dir.exists():
        return ()
    snapshots: list[dict[str, object]] = []
    for path in sorted(snapshot_dir.glob("*.log"), reverse=True)[:limit]:
        try:
            stat = path.stat()
        except OSError:
            continue
        snapshots.append(
            {
                "id": path.stem,
                "path": path.as_posix(),
                "size": stat.st_size,
            }
        )
    return tuple(snapshots)


def read_system_snapshot(snapshot_id: str, log_dir: Path | None = None) -> dict[str, object]:
    safe_id = sanitize_snapshot_id(snapshot_id)
    path = system_snapshot_dir(log_dir) / f"{safe_id}.log"
    if not path.exists():
        raise FileNotFoundError(f"System log snapshot not found: {safe_id}")
    return {
        "id": safe_id,
        "path": path.as_posix(),
        "content": path.read_text(encoding="utf-8", errors="replace"),
    }


def sanitize_snapshot_id(snapshot_id: str) -> str:
    safe = "".join(char for char in snapshot_id if char.isalnum() or char in {"-", "_", "T", "Z"})
    if not safe:
        raise ValueError("Snapshot id is required.")
    return safe


def _render_system_snapshot() -> str:
    sections = [
        "# vending-auto-setup system log snapshot",
        f"# collected_at = {_utc_timestamp()}",
        "",
    ]
    found_source = False
    for path in SYSTEM_SOURCE_PATHS:
        if not path.exists():
            continue
        found_source = True
        sections.extend((f"## {path.as_posix()}", _tail_file(path, SYSTEM_TAIL_LINES), ""))

    journal = _journalctl_tail(SYSTEM_TAIL_LINES)
    if journal is not None:
        found_source = True
        sections.extend(("## journalctl", journal, ""))

    if not found_source:
        sections.append("No supported system log sources were found on this machine.")
    return "\n".join(sections)


def _tail_file(path: Path, lines: int) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as error:
        return f"# read error: {error}"
    return "\n".join(content[-lines:])


def _journalctl_tail(lines: int) -> str | None:
    try:
        completed = subprocess.run(
            ["journalctl", "-n", str(lines), "--no-pager"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0 and not completed.stdout:
        return f"# journalctl error: {completed.stderr.strip()}"
    return completed.stdout.strip()


def _utc_timestamp(*, compact: bool = False) -> str:
    now = datetime.now(timezone.utc)
    if compact:
        return now.strftime("%Y%m%dT%H%M%SZ")
    return now.isoformat(timespec="seconds")
