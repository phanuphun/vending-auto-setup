from typing import Any
from unittest.mock import patch

from vending_auto_setup.status import (
    XORG_TOUCHSCREEN_SIGNATURE,
    collect_display_session_status,
    collect_xorg_touchscreen_config_status,
    main,
)


def test_vending_status_returns_zero_when_all_tools_exist(capsys: Any) -> None:
    with patch("vending_auto_setup.status.shutil.which", return_value="/usr/bin/tool"):
        with patch("vending_auto_setup.status._read_version", return_value="tool 1.0.0"):
            exit_code = main()

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "OK" in output
    assert "Git" in output
    assert "Docker" in output


def test_vending_status_returns_one_when_a_tool_is_missing(capsys: Any) -> None:
    def fake_which(command: str) -> str | None:
        return None if command == "docker" else f"/usr/bin/{command}"

    with patch("vending_auto_setup.status.shutil.which", side_effect=fake_which):
        with patch("vending_auto_setup.status._read_version", return_value="tool 1.0.0"):
            exit_code = main()

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "MISSING Docker" in output


def test_display_session_status_is_ok_for_x11() -> None:
    with patch.dict("vending_auto_setup.status.os.environ", {"XDG_SESSION_TYPE": "x11"}, clear=True):
        status = collect_display_session_status()

    assert status.is_x11 is True
    assert status.session_type == "x11"


def test_display_session_status_warns_for_wayland() -> None:
    with patch.dict("vending_auto_setup.status.os.environ", {"XDG_SESSION_TYPE": "wayland"}, clear=True):
        status = collect_display_session_status()

    assert status.is_x11 is False
    assert status.session_type == "wayland"


def test_xorg_touchscreen_config_status_warns_when_file_is_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    status = collect_xorg_touchscreen_config_status(tmp_path / "99-vending-touchscreen.conf")

    assert status.exists is False
    assert status.has_signature is False


def test_xorg_touchscreen_config_status_warns_when_signature_is_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "99-vending-touchscreen.conf"
    config_path.write_text('Section "InputClass"\nEndSection\n', encoding="utf-8")

    status = collect_xorg_touchscreen_config_status(config_path)

    assert status.exists is True
    assert status.has_signature is False


def test_xorg_touchscreen_config_status_is_ok_when_signature_exists(tmp_path) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "99-vending-touchscreen.conf"
    config_path.write_text(f"{XORG_TOUCHSCREEN_SIGNATURE}\n", encoding="utf-8")

    status = collect_xorg_touchscreen_config_status(config_path)

    assert status.exists is True
    assert status.has_signature is True
