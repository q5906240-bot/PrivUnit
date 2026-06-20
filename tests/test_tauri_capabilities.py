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
