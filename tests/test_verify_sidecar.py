from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.verify_sidecar import main


def test_verify_sidecar_rejects_missing_binary(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["verify_sidecar.py", "--sidecar", "/tmp/not-exists-redactor-sidecar"])

    try:
        main()
    except FileNotFoundError as exc:
        assert "sidecar not found" in str(exc)
    else:
        raise AssertionError("expected missing sidecar to fail")
