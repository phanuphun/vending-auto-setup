from __future__ import annotations

import os
from pathlib import Path

from vending_auto_setup.runner import CommandRunner
from vending_auto_setup.status import XORG_TOUCHSCREEN_CONFIG_PATH, XORG_TOUCHSCREEN_SIGNATURE

ROTATION_MATRICES: dict[str, tuple[str, ...]] = {
    "normal": ("1", "0", "0", "0", "1", "0", "0", "0", "1"),
    "right": ("0", "1", "0", "-1", "0", "1", "0", "0", "1"),
    "left": ("0", "-1", "1", "1", "0", "0", "0", "0", "1"),
    "inverted": ("-1", "0", "1", "0", "-1", "1", "0", "0", "1"),
}

COORDINATE_TRANSFORMATION_MATRIX = "Coordinate Transformation Matrix"


class DisplayConfigurator:
    def __init__(self, runner: CommandRunner) -> None:
        self.runner = runner

    def print_status(self, x_display: str | None = None, xauthority: str | None = None) -> None:
        print("[Xrandr]")
        self.runner.run(self._with_x_env(["xrandr", "--query"], x_display, xauthority), check=False)
        print()
        print("[Xinput]")
        self.runner.run(self._with_x_env(["xinput", "list"], x_display, xauthority), check=False)

    def apply_runtime(
        self,
        output: str,
        touch: str,
        rotate: str,
        x_display: str | None = None,
        xauthority: str | None = None,
    ) -> None:
        matrix = matrix_for_rotation(rotate)
        self.runner.run(self._with_x_env(["xrandr", "--output", output, "--rotate", rotate], x_display, xauthority))
        self.runner.run(
            self._with_x_env(
                ["xinput", "set-prop", touch, COORDINATE_TRANSFORMATION_MATRIX, *matrix],
                x_display,
                xauthority,
            )
        )

    def persist_xorg(
        self,
        touch: str,
        rotate: str,
        path: Path = XORG_TOUCHSCREEN_CONFIG_PATH,
    ) -> None:
        matrix = " ".join(matrix_for_rotation(rotate))
        content = build_xorg_touchscreen_config(touch, matrix)
        print(f"write {path.as_posix()}")
        if self.runner.dry_run:
            print(content.rstrip())
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _with_x_env(
        self,
        args: list[str],
        x_display: str | None,
        xauthority: str | None,
    ) -> list[str]:
        env_args = []
        resolved_display = x_display or os.environ.get("DISPLAY")
        if resolved_display:
            env_args.append(f"DISPLAY={resolved_display}")
        if xauthority:
            env_args.append(f"XAUTHORITY={xauthority}")
        if not env_args:
            return args
        return ["env", *env_args, *args]


def matrix_for_rotation(rotate: str) -> tuple[str, ...]:
    try:
        return ROTATION_MATRICES[rotate]
    except KeyError as error:
        choices = ", ".join(sorted(ROTATION_MATRICES))
        raise ValueError(f"Unsupported rotation: {rotate}. Expected one of: {choices}") from error


def build_xorg_touchscreen_config(touch: str, matrix: str) -> str:
    return (
        f"{XORG_TOUCHSCREEN_SIGNATURE}\n"
        "# Managed by vending-auto-setup. Manual edits may be overwritten.\n"
        'Section "InputClass"\n'
        '    Identifier "vending-touchscreen-calibration"\n'
        f'    MatchProduct "{touch}"\n'
        f'    Option "CalibrationMatrix" "{matrix}"\n'
        "EndSection\n"
    )
