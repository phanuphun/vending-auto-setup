from typing import Any
from unittest.mock import patch

from vending_auto_setup.status import main


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
