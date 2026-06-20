from __future__ import annotations

from pathlib import Path

import sys

import pytest

from redactor.ocr_models import REQUIRED_MODEL_FILES, find_bundled_model_dir, model_kwargs, verify_model_dir


def test_verify_model_dir_requires_all_onnx_files(tmp_path: Path) -> None:
    model_dir = tmp_path / "rapidocr"
    model_dir.mkdir()
    for relative_path in REQUIRED_MODEL_FILES[:-1]:
        target = model_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake")

    with pytest.raises(FileNotFoundError, match=REQUIRED_MODEL_FILES[-1]):
        verify_model_dir(model_dir)


def test_model_kwargs_points_to_bundled_files(tmp_path: Path) -> None:
    model_dir = tmp_path / "rapidocr"
    for relative_path in REQUIRED_MODEL_FILES:
        target = model_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake")

    kwargs = model_kwargs(model_dir)

    assert kwargs["det_model_path"].endswith("ch_PP-OCRv3_det_infer.onnx")
    assert kwargs["cls_model_path"].endswith("ch_ppocr_mobile_v2.0_cls_infer.onnx")
    assert kwargs["rec_model_path"].endswith("ch_PP-OCRv3_rec_infer.onnx")
    assert kwargs["det_module_name"] == "rapidocr_onnxruntime.ch_ppocr_v3_det"


def test_find_bundled_model_dir_supports_tauri_resource_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    resource_dir = tmp_path / "resources"
    model_dir = resource_dir / "resources" / "ocr" / "rapidocr"
    for relative_path in REQUIRED_MODEL_FILES:
        target = model_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake")

    monkeypatch.setenv("LOCAL_REDACTOR_RESOURCE_DIR", str(resource_dir))

    assert find_bundled_model_dir() == model_dir


def test_find_bundled_model_dir_supports_macos_app_resources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = tmp_path / "私元处理.app" / "Contents" / "MacOS" / "redactor-sidecar"
    model_dir = tmp_path / "私元处理.app" / "Contents" / "Resources" / "_up_" / "resources" / "ocr" / "rapidocr"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"fake")
    for relative_path in REQUIRED_MODEL_FILES:
        target = model_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    unrelated_cwd = tmp_path / "unrelated"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)

    assert find_bundled_model_dir() == model_dir


def test_find_bundled_model_dir_supports_linux_deb_resources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = tmp_path / "usr" / "bin" / "redactor-sidecar"
    model_dir = tmp_path / "usr" / "lib" / "privunit" / "resources" / "ocr" / "rapidocr"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"fake")
    for relative_path in REQUIRED_MODEL_FILES:
        target = model_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    unrelated_cwd = tmp_path / "unrelated"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)

    assert find_bundled_model_dir() == model_dir


def test_repository_contains_bundled_rapidocr_models() -> None:
    model_dir = Path.cwd() / "resources" / "ocr" / "rapidocr"

    verify_model_dir(model_dir)
