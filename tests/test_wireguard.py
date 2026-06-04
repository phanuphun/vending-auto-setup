from __future__ import annotations

from pathlib import Path
from typing import Any

from cli import main
from wireguard import mask_secrets, validate_config_content


VALID_CONFIG = """\
[Interface]
PrivateKey = interface-secret
Address = 10.8.0.13/24

[Peer]
PublicKey = peer-public
PresharedKey = peer-secret
AllowedIPs = 10.8.0.0/24
Endpoint = vpn.example.com:51820
PersistentKeepalive = 25
"""


def test_wireguard_init_config_writes_template(tmp_path: Path) -> None:
    output = tmp_path / "wg0.conf"

    exit_code = main(["wireguard", "init-config", "--output", str(output)])

    assert exit_code == 0
    content = output.read_text(encoding="utf-8")
    assert "# vending-auto-config: wireguard" in content
    assert "[Interface]" in content
    assert "[Peer]" in content
    assert "PrivateKey = <interface-private-key>" in content


def test_wireguard_validate_reports_missing_peer(capsys: Any, tmp_path: Path) -> None:
    config = tmp_path / "wg0.conf"
    config.write_text("[Interface]\nPrivateKey = secret\nAddress = 10.8.0.2/24\n", encoding="utf-8")

    exit_code = main(["wireguard", "validate", "--config", str(config)])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "missing [Peer] section" in output
    assert "secret" not in output


def test_wireguard_save_stores_config_without_printing_secrets(capsys: Any, tmp_path: Path) -> None:
    config = tmp_path / "source.conf"
    store_dir = tmp_path / "store"
    config.write_text(VALID_CONFIG, encoding="utf-8")

    exit_code = main(
        [
            "wireguard",
            "--store-dir",
            str(store_dir),
            "save",
            "--name",
            "wg0",
            "--config",
            str(config),
        ]
    )

    assert exit_code == 0
    assert (store_dir / "configs" / "wg0.conf").read_text(encoding="utf-8") == VALID_CONFIG
    output = capsys.readouterr().out
    assert "interface-secret" not in output
    assert "peer-secret" not in output


def test_wireguard_sync_dry_run_uses_saved_config(capsys: Any, tmp_path: Path) -> None:
    store_dir = tmp_path / "store"
    wireguard_dir = tmp_path / "etc-wireguard"
    saved = store_dir / "configs" / "wg0.conf"
    saved.parent.mkdir(parents=True)
    saved.write_text(VALID_CONFIG, encoding="utf-8")

    exit_code = main(
        [
            "--dry-run",
            "wireguard",
            "--store-dir",
            str(store_dir),
            "--wireguard-dir",
            str(wireguard_dir),
            "sync",
            "--name",
            "wg0",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert f"write {wireguard_dir / 'wg0.conf'}" in output
    assert "systemctl enable wg-quick@wg0" in output
    assert "systemctl restart wg-quick@wg0" in output
    assert "interface-secret" not in output
    assert "peer-secret" not in output


def test_wireguard_history_show_masks_secrets(capsys: Any, tmp_path: Path) -> None:
    store_dir = tmp_path / "store"
    history = store_dir / "history" / "wg0" / "20260604T120000Z-sync.conf"
    history.parent.mkdir(parents=True)
    history.write_text(VALID_CONFIG, encoding="utf-8")

    exit_code = main(
        [
            "wireguard",
            "--store-dir",
            str(store_dir),
            "show",
            "--name",
            "wg0",
            "--id",
            "20260604T120000Z-sync",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "PrivateKey = <hidden>" in output
    assert "PresharedKey = <hidden>" in output
    assert "interface-secret" not in output
    assert "peer-secret" not in output


def test_wireguard_unsync_dry_run_disables_service(capsys: Any, tmp_path: Path) -> None:
    store_dir = tmp_path / "store"
    wireguard_dir = tmp_path / "etc-wireguard"

    exit_code = main(
        [
            "--dry-run",
            "wireguard",
            "--store-dir",
            str(store_dir),
            "--wireguard-dir",
            str(wireguard_dir),
            "unsync",
            "--name",
            "wg0",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "systemctl disable --now wg-quick@wg0" in output
    assert f"skip {wireguard_dir / 'wg0.conf'}" in output


def test_mask_secrets_hides_private_and_preshared_keys() -> None:
    assert "interface-secret" not in mask_secrets(VALID_CONFIG)
    assert "peer-secret" not in mask_secrets(VALID_CONFIG)


def test_validate_config_accepts_required_wireguard_keys() -> None:
    result = validate_config_content(VALID_CONFIG)

    assert result.valid
    assert result.errors == ()
