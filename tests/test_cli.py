from typing import Any

from vending_auto_setup.cli import main


def test_check_command_runs_in_dry_run_mode(capsys: Any) -> None:
    exit_code = main(["--dry-run", "check"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Vending Auto Setup Status" in output
    assert "Node.js" in output
    assert "Docker" in output


def test_install_dry_run_uses_requested_versions(capsys: Any) -> None:
    exit_code = main(
        [
            "--dry-run",
            "install",
            "--node-major",
            "22",
            "--docker-version",
            "5:28.5.1-1~ubuntu.22.04~jammy",
            "--git-version",
            "1:2.34.1-1ubuntu1.17",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "https://deb.nodesource.com/node_22.x" in output
    assert "docker-ce=5:28.5.1-1~ubuntu.22.04~jammy" in output
    assert "git=1:2.34.1-1ubuntu1.17" in output


def test_about_os_command_prints_poc_header(capsys: Any) -> None:
    exit_code = main(["about-os"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Vending Auto Setup POC" in output
    assert "Python:" in output


def test_display_apply_dry_run_prints_rotation_and_mapping(capsys: Any) -> None:
    exit_code = main(
        [
            "--dry-run",
            "display",
            "apply",
            "--display",
            ":0",
            "--output",
            "Virtual1",
            "--touch",
            "Vending Virtual Touchscreen",
            "--rotate",
            "left",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "xrandr --output Virtual1 --rotate left" in output
    assert "Coordinate Transformation Matrix" in output
    assert "0 -1 1 1 0 0 0 0 1" in output


def test_display_persist_xorg_dry_run_prints_config(capsys: Any) -> None:
    exit_code = main(
        [
            "--dry-run",
            "display",
            "persist-xorg",
            "--touch",
            "Vending Virtual Touchscreen",
            "--rotate",
            "normal",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "write /etc/X11/xorg.conf.d/99-vending-touchscreen.conf" in output
    assert "# vending-auto-config: touchscreen-xorg" in output
    assert 'MatchProduct "Vending Virtual Touchscreen"' in output


def test_display_persist_session_dry_run_prints_xprofile_block(capsys: Any) -> None:
    exit_code = main(
        [
            "--dry-run",
            "display",
            "persist-session",
            "--display",
            ":0",
            "--output",
            "Virtual1",
            "--touch",
            "Vending Virtual Touchscreen",
            "--rotate",
            "left",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "write " in output
    assert "display-session.sh" in output
    assert "# vending-auto-config: display-session-script" in output
    assert "# vending-auto-config: display-session BEGIN" in output
    assert 'xrandr --output "$OUTPUT" --rotate "$ROTATE"' in output
    assert 'xinput set-prop "$TOUCH_DEVICE"' in output
