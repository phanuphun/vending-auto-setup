from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from audit_log import log_runner_command


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    def __init__(self, dry_run: bool = False, audit_source: str | None = None, audit_dir: Path | None = None) -> None:
        self.dry_run = dry_run
        self.audit_source = audit_source
        self.audit_dir = audit_dir
        self._progress_total: int | None = None
        self._progress_current = 0

    def start_progress(self, total: int) -> None:
        self._progress_total = max(total, 1)
        self._progress_current = 0

    def stop_progress(self) -> None:
        self._progress_total = None
        self._progress_current = 0

    def print_operation(self, operation: str) -> None:
        print(self._format_operation(operation))

    def run(self, args: Sequence[str], check: bool = True) -> CommandResult:
        normalized_args = tuple(args)
        self.print_operation(format_command(normalized_args))
        if self.dry_run:
            self._log_command(normalized_args, returncode=0, status="dry-run")
            return CommandResult(normalized_args, 0, "", "")

        try:
            completed = subprocess.run(
                normalized_args,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError:
            self._log_command(normalized_args, returncode=-1, status="error")
            raise
        result = CommandResult(
            normalized_args,
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )
        self._log_command(
            normalized_args,
            returncode=completed.returncode,
            status="ok" if completed.returncode == 0 else "error",
        )
        if check and completed.returncode != 0:
            raise CommandExecutionError(result)
        return result

    def _format_operation(self, operation: str) -> str:
        if self._progress_total is None:
            return operation

        if self._progress_total == 1:
            percent = 100
        else:
            percent = round((self._progress_current / (self._progress_total - 1)) * 100)
        self._progress_current = min(self._progress_current + 1, self._progress_total - 1)
        return f"[vending-auto-setup ({percent}%)] - {operation}"

    def _log_command(self, args: tuple[str, ...], *, returncode: int, status: str) -> None:
        if self.audit_source != "cli":
            return
        log_runner_command(
            args=args,
            dry_run=self.dry_run,
            returncode=returncode,
            status=status,
            log_dir=self.audit_dir,
        )


class CommandExecutionError(RuntimeError):
    def __init__(self, result: CommandResult) -> None:
        super().__init__(
            f"Command failed with exit code {result.returncode}: "
            f"{format_command(result.args)}\n{result.stderr.strip()}"
        )
        self.result = result


def format_command(args: Sequence[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)
