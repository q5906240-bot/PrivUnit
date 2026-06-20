from __future__ import annotations

from scripts.build_sidecar import EXCLUDED_MODULES, HIDDEN_IMPORTS, build_pyinstaller_command, tauri_sidecar_name


def test_tauri_sidecar_name_uses_platform_triple() -> None:
    assert tauri_sidecar_name("redactor-sidecar", "darwin", "arm64") == "redactor-sidecar-aarch64-apple-darwin"
    assert tauri_sidecar_name("redactor-sidecar", "darwin", "x86_64") == "redactor-sidecar-x86_64-apple-darwin"
    assert tauri_sidecar_name("redactor-sidecar", "win32", "AMD64") == "redactor-sidecar-x86_64-pc-windows-msvc.exe"
    assert tauri_sidecar_name("redactor-sidecar", "linux", "x86_64") == "redactor-sidecar-x86_64-unknown-linux-gnu"
    assert tauri_sidecar_name("redactor-sidecar", "linux", "aarch64") == "redactor-sidecar-aarch64-unknown-linux-gnu"


def test_pyinstaller_command_excludes_unrelated_ml_stacks() -> None:
    command = build_pyinstaller_command("/python", "/repo", "/repo/build/entry.py", ":", "redactor-sidecar")
    joined = " ".join(command)

    assert "torch" in EXCLUDED_MODULES
    assert "transformers" in EXCLUDED_MODULES
    assert "--exclude-module torch" in joined
    assert "--exclude-module transformers" in joined
    assert "rapidocr_onnxruntime" in joined
    assert "rapidocr_onnxruntime.ch_ppocr_v3_det" in HIDDEN_IMPORTS
    assert "--hidden-import rapidocr_onnxruntime.ch_ppocr_v3_det" in joined
