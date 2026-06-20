from __future__ import annotations

import sys
import types

from scripts.build_sidecar import (
    EXCLUDED_MODULES,
    HIDDEN_IMPORTS,
    build_pyinstaller_command,
    rapidocr_config_data_files,
    tauri_sidecar_name,
)


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


def test_rapidocr_config_data_files_only_includes_existing_configs(tmp_path, monkeypatch) -> None:
    package_root = tmp_path / "rapidocr_onnxruntime"
    (package_root / "ch_ppocr_v3_det").mkdir(parents=True)
    (package_root / "ch_ppocr_v2_cls").mkdir()
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    (package_root / "config.yaml").write_text("root: true\n", encoding="utf-8")
    (package_root / "ch_ppocr_v3_det" / "config.yaml").write_text("det: true\n", encoding="utf-8")

    fake_module = types.ModuleType("rapidocr_onnxruntime")
    fake_module.__file__ = str(package_root / "__init__.py")
    monkeypatch.setitem(sys.modules, "rapidocr_onnxruntime", fake_module)

    assert rapidocr_config_data_files(":") == [
        (str(package_root / "config.yaml"), "rapidocr_onnxruntime"),
        (str(package_root / "ch_ppocr_v3_det" / "config.yaml"), "rapidocr_onnxruntime/ch_ppocr_v3_det"),
    ]
