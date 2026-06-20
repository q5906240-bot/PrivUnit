from __future__ import annotations

import json
from pathlib import Path


def test_shell_permission_allows_redactor_sidecar() -> None:
    capability = json.loads(Path("src-tauri/capabilities/default.json").read_text(encoding="utf-8"))
    shell_permissions = [
        permission
        for permission in capability["permissions"]
        if isinstance(permission, dict) and permission.get("identifier") == "shell:allow-execute"
    ]

    assert shell_permissions
    allowed = shell_permissions[0]["allow"]
    assert {
        "name": "binaries/redactor-sidecar",
        "sidecar": True,
        "args": True,
    } in allowed


def test_tauri_bundle_declares_square_png_icons_for_linux_appimage() -> None:
    config = json.loads(Path("src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    icons = config["bundle"]["icon"]

    assert "icons/32x32.png" in icons
    assert "icons/128x128.png" in icons
    assert "icons/128x128@2x.png" in icons
    assert "icons/icon.png" in icons
    assert "icons/icon.ico" in icons
    for icon in icons:
        assert Path("src-tauri", icon).is_file()
