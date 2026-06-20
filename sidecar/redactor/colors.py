from __future__ import annotations

import re


WHITE_HEX_VALUES = {"#fff", "#ffffff", "#ffffffff"}


def normalize_hex_color(color: str) -> str:
    value = color.strip().lower()
    if not re.fullmatch(r"#[0-9a-f]{3}([0-9a-f]{3})?([0-9a-f]{2})?", value):
        raise ValueError("脱敏颜色必须是 HEX 格式")
    if value in WHITE_HEX_VALUES:
        raise ValueError("脱敏选择框颜色不能使用白色")
    if len(value) == 4:
        value = "#" + "".join(char * 2 for char in value[1:])
    if len(value) == 9:
        value = value[:7]
    return value


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    value = normalize_hex_color(color)
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)
