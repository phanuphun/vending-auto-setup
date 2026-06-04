from vending_auto_setup.display import (
    XORG_TOUCHSCREEN_SIGNATURE,
    build_xorg_touchscreen_config,
    matrix_for_rotation,
)


def test_matrix_for_left_rotation() -> None:
    assert matrix_for_rotation("left") == ("0", "-1", "1", "1", "0", "0", "0", "0", "1")


def test_xorg_config_includes_signature_and_touch_name() -> None:
    config = build_xorg_touchscreen_config("Vending Virtual Touchscreen", "1 0 0 0 1 0 0 0 1")

    assert XORG_TOUCHSCREEN_SIGNATURE in config
    assert 'MatchProduct "Vending Virtual Touchscreen"' in config
    assert 'Option "CalibrationMatrix" "1 0 0 0 1 0 0 0 1"' in config
