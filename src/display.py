from __future__ import annotations

import os
import re
import shlex
import stat
from dataclasses import dataclass
from pathlib import Path

from runner import CommandRunner
from status import (
    DISPLAY_SESSION_SCRIPT_SIGNATURE,
    DISPLAY_SESSION_SIGNATURE,
    XORG_TOUCHSCREEN_CONFIG_PATH,
    XORG_TOUCHSCREEN_SIGNATURE,
    _effective_home_config_path,
    _effective_home_script_path,
)


@dataclass(frozen=True)
class TouchDevice:
    """Touchscreen device พร้อม xinput ID สำหรับสั่งงาน"""

    name: str
    xinput_id: "int | None"


ROTATION_MATRICES: "dict[str, tuple[str, ...]]" = {
    "normal": ("1", "0", "0", "0", "1", "0", "0", "0", "1"),
    "right": ("0", "1", "0", "-1", "0", "1", "0", "0", "1"),
    "left": ("0", "-1", "1", "1", "0", "0", "0", "0", "1"),
    "inverted": ("-1", "0", "1", "0", "-1", "1", "0", "0", "1"),
}

COORDINATE_TRANSFORMATION_MATRIX = "Coordinate Transformation Matrix"
DISPLAY_SESSION_BEGIN = f"{DISPLAY_SESSION_SIGNATURE} BEGIN"
DISPLAY_SESSION_END = f"{DISPLAY_SESSION_SIGNATURE} END"

__all__ = [
    "DISPLAY_SESSION_SIGNATURE",
    "ROTATION_MATRICES",
    "XORG_TOUCHSCREEN_SIGNATURE",
    "DisplayConfigurator",
    "TouchDevice",
    "build_display_session_block",
    "build_display_session_script",
    "build_xorg_touchscreen_config",
    "get_udevadm_touchscreen_names",
    "list_touch_devices",
    "matrix_for_rotation",
    "parse_xinput_device_map",
    "remove_managed_block",
    "upsert_managed_block",
]


class DisplayConfigurator:
    def __init__(self, runner: CommandRunner) -> None:
        self.runner = runner

    def print_status(self, x_display: "str | None" = None, xauthority: "str | None" = None) -> None:
        print("[Xrandr]")
        self.runner.run(self._with_x_env(["xrandr", "--query"], x_display, xauthority), check=False)
        print()
        print("[Xinput]")
        self.runner.run(self._with_x_env(["xinput", "list"], x_display, xauthority), check=False)

    def print_touch_devices(self, x_display: "str | None" = None, xauthority: "str | None" = None) -> None:
        """แสดงรายการ touchscreen devices พร้อม xinput ID"""
        devices = list_touch_devices(self.runner, x_display=x_display, xauthority=xauthority)
        if not devices:
            print("No touchscreen devices found.")
            return
        print(f"{'ID':>4}  Name")
        print("-" * 48)
        for d in devices:
            id_str = str(d.xinput_id) if d.xinput_id is not None else "?"
            print(f"{id_str:>4}  {d.name}")

    def apply_runtime(
        self,
        output: str,
        touch: str,
        rotate: str,
        x_display: "str | None" = None,
        xauthority: "str | None" = None,
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

    def persist_session(
        self,
        output: str,
        touch: str,
        rotate: str,
        x_display: "str | None" = None,
        path: "Path | None" = None,
        script_path: "Path | None" = None,
        delay_seconds: int = 5,
        retries: int = 30,
    ) -> None:
        if path is None:
            path = _effective_home_config_path()
        if script_path is None:
            script_path = _effective_home_script_path()
        matrix = " ".join(matrix_for_rotation(rotate))
        script_content = build_display_session_script(
            output=output,
            touch=touch,
            rotate=rotate,
            matrix=matrix,
            x_display=x_display,
            delay_seconds=delay_seconds,
            retries=retries,
        )
        content = build_display_session_block(script_path=script_path)
        print(f"write {script_path.as_posix()}")
        print(f"write {path.as_posix()}")
        if self.runner.dry_run:
            print(script_content.rstrip())
            print(content.rstrip())
            return

        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script_content, encoding="utf-8")
        # 755: executable โดย owner และ others (จำเป็นเมื่อ server root เขียนไฟล์ใน home user)
        script_path.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        _chown_to_effective_user(script_path)

        existing_content = path.read_text(encoding="utf-8") if path.exists() else ""
        path.write_text(upsert_managed_block(existing_content, content), encoding="utf-8")
        _chown_to_effective_user(path)

    def _with_x_env(
        self,
        args: list,
        x_display: "str | None",
        xauthority: "str | None",
    ) -> list:
        env_args = []
        resolved_display = x_display or os.environ.get("DISPLAY")
        if resolved_display:
            env_args.append(f"DISPLAY={resolved_display}")
        if xauthority:
            env_args.append(f"XAUTHORITY={xauthority}")
        if not env_args:
            return args
        return ["env", *env_args, *args]


# ---------------------------------------------------------------------------
# Touchscreen detection helpers
# ---------------------------------------------------------------------------

def parse_xinput_device_map(output: str) -> "dict[str, int]":
    """Parse output ของ `xinput list` -> dict ของ name: xinput_id

    รองรับ format:
      <tree>  Virtual core pointer                  id=2    [master pointer  (3)]
      <tree>  Vending Virtual Touchscreen           id=13   [slave  pointer  (2)]
    """
    result: "dict[str, int]" = {}
    for line in output.splitlines():
        m = re.search(r"\bid=(\d+)\b", line)
        if not m:
            continue
        xinput_id = int(m.group(1))
        name_part = line[: m.start()]
        name_part = re.sub(r"^[^a-zA-Z0-9]+", "", name_part).rstrip()
        if name_part:
            result[name_part] = xinput_id
    return result


def get_udevadm_touchscreen_names(runner: CommandRunner) -> "frozenset[str]":
    """อ่านชื่อ touchscreen จาก udevadm (kernel-level ไม่ต้องพึ่ง X session)

    เทียบเท่า:
      udevadm info --export-db | awk '/ID_INPUT_TOUCHSCREEN=1/' RS= | grep 'E: NAME=' | cut -d'"' -f2
    """
    result = runner.run(["udevadm", "info", "--export-db"], check=False)
    if result.returncode != 0:
        return frozenset()

    names: "set[str]" = set()
    block: "list[str]" = []

    def _process_block(lines: "list[str]") -> None:
        if any(l == "E: ID_INPUT_TOUCHSCREEN=1" for l in lines):
            for l in lines:
                if l.startswith("E: NAME="):
                    name = l[8:].strip().strip('"')
                    if name:
                        names.add(name)

    for raw in result.stdout.splitlines():
        line = raw.strip()
        if line:
            block.append(line)
        elif block:
            _process_block(block)
            block = []
    if block:
        _process_block(block)

    return frozenset(names)


def list_touch_devices(
    runner: CommandRunner,
    x_display: "str | None" = None,
    xauthority: "str | None" = None,
) -> "tuple[TouchDevice, ...]":
    """คืน touchscreen devices ที่ detect ได้พร้อม xinput ID

    ลำดับการ detect:
    1. ใช้ udevadm เป็นแหล่งชื่อหลัก (kernel-level, ไม่ต้องพึ่ง session)
    2. Cross-ref กับ xinput list เพื่อให้ได้ xinput ID
    3. ถ้า udevadm ไม่มี touchscreen -> fallback กรอง xinput ด้วย "touch" ใน name
    """
    configurator = DisplayConfigurator(runner)
    xinput_result = runner.run(
        configurator._with_x_env(["xinput", "list"], x_display, xauthority),
        check=False,
    )
    xinput_map = parse_xinput_device_map(xinput_result.stdout)
    udev_names = get_udevadm_touchscreen_names(runner)

    if udev_names:
        return tuple(
            TouchDevice(name=name, xinput_id=xinput_map.get(name))
            for name in sorted(udev_names)
        )
    return tuple(
        TouchDevice(name=name, xinput_id=id_)
        for name, id_ in sorted(xinput_map.items())
        if "touch" in name.lower()
    )


# ---------------------------------------------------------------------------
# Ownership helper
# ---------------------------------------------------------------------------

def _chown_to_effective_user(path: Path) -> None:
    """chown ไฟล์ไปให้ SUDO_USER เมื่อ process รันเป็น root"""
    if not (hasattr(os, "geteuid") and os.geteuid() == 0):
        return
    sudo_user = os.environ.get("SUDO_USER", "").strip()
    if not sudo_user or sudo_user == "root":
        return
    try:
        import pwd
        pw = pwd.getpwnam(sudo_user)
        os.chown(path, pw.pw_uid, pw.pw_gid)
    except (ImportError, KeyError, OSError):
        pass


# ---------------------------------------------------------------------------
# Pure builders
# ---------------------------------------------------------------------------

def matrix_for_rotation(rotate: str) -> "tuple[str, ...]":
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


def build_display_session_script(
    output: str,
    touch: str,
    rotate: str,
    matrix: str,
    x_display: "str | None",
    delay_seconds: int,
    retries: int,
) -> str:
    display_line = f"export DISPLAY={shlex.quote(x_display)}\n" if x_display else ""
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"{DISPLAY_SESSION_SCRIPT_SIGNATURE}\n"
        "# Managed by vending-auto-setup. Manual edits may be overwritten.\n"
        f"sleep {delay_seconds}\n"
        f"{display_line}"
        f"OUTPUT={shlex.quote(output)}\n"
        f"TOUCH_DEVICE={shlex.quote(touch)}\n"
        f"ROTATE={shlex.quote(rotate)}\n"
        f"MATRIX={shlex.quote(matrix)}\n"
        f"RETRIES={retries}\n"
        "\n"
        "display_found=0\n"
        'for attempt in $(seq 1 "$RETRIES"); do\n'
        '  if xrandr --query | grep -q "^${OUTPUT} connected"; then\n'
        '    xrandr --output "$OUTPUT" --rotate "$ROTATE"\n'
        "    display_found=1\n"
        "    break\n"
        "  fi\n"
        '  echo "Waiting for display output ${OUTPUT} (${attempt}/${RETRIES})"\n'
        "  sleep 1\n"
        "done\n"
        'if [ "$display_found" -ne 1 ]; then\n'
        '  echo "Display output ${OUTPUT} was not found after ${RETRIES} seconds" >&2\n'
        "  exit 1\n"
        "fi\n"
        "\n"
        'for attempt in $(seq 1 "$RETRIES"); do\n'
        '  if xinput list --name-only | grep -Fxq "$TOUCH_DEVICE"; then\n'
        f'    xinput set-prop "$TOUCH_DEVICE" "{COORDINATE_TRANSFORMATION_MATRIX}" $MATRIX\n'
        "    exit 0\n"
        "  fi\n"
        '  echo "Waiting for touchscreen ${TOUCH_DEVICE} (${attempt}/${RETRIES})"\n'
        "  sleep 1\n"
        "done\n"
        "\n"
        'echo "Touchscreen ${TOUCH_DEVICE} was not found after ${RETRIES} seconds" >&2\n'
        "exit 1\n"
    )


def build_display_session_block(script_path: Path) -> str:
    return (
        f"{DISPLAY_SESSION_BEGIN}\n"
        "# Managed by vending-auto-setup. Manual edits inside this block may be overwritten.\n"
        f"{shlex.quote(script_path.as_posix())} &\n"
        f"{DISPLAY_SESSION_END}\n"
    )


def upsert_managed_block(existing_content: str, managed_block: str) -> str:
    if DISPLAY_SESSION_BEGIN not in existing_content:
        separator = "\n" if existing_content and not existing_content.endswith("\n") else ""
        return f"{existing_content}{separator}{managed_block}"

    start = existing_content.index(DISPLAY_SESSION_BEGIN)
    end = existing_content.find(DISPLAY_SESSION_END, start)
    if end == -1:
        return f"{existing_content.rstrip()}\n{managed_block}"

    end += len(DISPLAY_SESSION_END)
    if end < len(existing_content) and existing_content[end : end + 1] == "\n":
        end += 1
    return f"{existing_content[:start]}{managed_block}{existing_content[end:]}"


def remove_managed_block(existing_content: str) -> str:
    if DISPLAY_SESSION_BEGIN not in existing_content:
        return existing_content

    start = existing_content.index(DISPLAY_SESSION_BEGIN)
    end = existing_content.find(DISPLAY_SESSION_END, start)
    if end == -1:
        return existing_content

    end += len(DISPLAY_SESSION_END)
    if end < len(existing_content) and existing_content[end : end + 1] == "\n":
        end += 1
    return f"{existing_content[:start]}{existing_content[end:]}"
