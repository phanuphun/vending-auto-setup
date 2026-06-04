from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def run(self, args: Sequence[str], check: bool = True) -> CommandResult:
        normalized_args = tuple(args)
        print(format_command(normalized_args))
        if self.dry_run:
            return CommandResult(normalized_args, 0, "", "")

        completed = subprocess.run(
            normalized_args,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        result = CommandResult(
            normalized_args,
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )
        if check and completed.returncode != 0:
            raise CommandExecutionError(result)
        return result


class CommandExecutionError(RuntimeError):
    def __init__(self, result: CommandResult) -> None:
        super().__init__(
            f"Command failed with exit code {result.returncode}: "
            f"{format_command(result.args)}\n{result.stderr.strip()}"
        )
        self.result = result


def format_command(args: Sequence[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)
