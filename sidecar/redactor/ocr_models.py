from __future__ import annotations

import os
import sys
import hashlib
import json
from pathlib import Path

REQUIRED_MODEL_FILES = [
    "models/ch_PP-OCRv3_det_infer.onnx",
    "models/ch_ppocr_mobile_v2.0_cls_infer.onnx",
    "models/ch_PP-OCRv3_rec_infer.onnx",
]


def find_bundled_model_dir() -> Path:
    candidates = _candidate_model_dirs()
    for candidate in candidates:
        if _has_required_models(candidate):
            return candidate.resolve()
    searched = "\n".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"未找到随客户端打包的 OCR 模型。已搜索:\n{searched}")


def verify_model_dir(model_dir: str | Path) -> None:
    root = Path(model_dir)
    for relative_path in REQUIRED_MODEL_FILES:
        path = root / relative_path
        if not path.exists() or path.stat().st_size == 0:
            raise FileNotFoundError(f"缺少 OCR 模型文件: {relative_path}")
    _verify_manifest(root)


def model_kwargs(model_dir: str | Path) -> dict[str, str]:
    root = Path(model_dir)
    verify_model_dir(root)
    return {
        "det_model_path": str(root / "models/ch_PP-OCRv3_det_infer.onnx"),
        "det_module_name": "rapidocr_onnxruntime.ch_ppocr_v3_det",
        "cls_model_path": str(root / "models/ch_ppocr_mobile_v2.0_cls_infer.onnx"),
        "cls_module_name": "rapidocr_onnxruntime.ch_ppocr_v2_cls",
        "rec_model_path": str(root / "models/ch_PP-OCRv3_rec_infer.onnx"),
        "rec_module_name": "rapidocr_onnxruntime.ch_ppocr_v3_rec",
    }


def _candidate_model_dirs() -> list[Path]:
    roots: list[Path] = []
    env_resource_dir = os.environ.get("LOCAL_REDACTOR_RESOURCE_DIR")
    if env_resource_dir:
        roots.append(Path(env_resource_dir))

    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        roots.extend(_frozen_resource_roots(executable_dir))
    else:
        roots.extend([Path.cwd(), Path(__file__).resolve().parents[2]])

    candidates: list[Path] = []
    for root in roots:
        candidates.extend(
            [
                root / "resources" / "ocr" / "rapidocr",
                root / "ocr" / "rapidocr",
                root / "rapidocr",
            ]
        )
    return candidates


def _frozen_resource_roots(executable_dir: Path) -> list[Path]:
    contents_dir = executable_dir.parent
    app_names = ("privunit", "local-redactor")
    linux_roots = [
        root / app_name / suffix
        for app_name in app_names
        for root in (Path("/usr/lib"), Path("/opt"))
        for suffix in ("", "_up_")
    ]
    return [
        Path(getattr(sys, "_MEIPASS", executable_dir)),
        contents_dir / "Resources" / "_up_",
        contents_dir / "Resources",
        executable_dir.parent / "_up_",
        executable_dir.parent / "resources",
        *(executable_dir / ".." / "lib" / app_name / suffix for app_name in app_names for suffix in ("", "_up_")),
        *linux_roots,
        executable_dir,
        contents_dir,
        Path.cwd(),
    ]


def _has_required_models(model_dir: Path) -> bool:
    return all((model_dir / relative_path).is_file() for relative_path in REQUIRED_MODEL_FILES)


def _verify_manifest(model_dir: Path) -> None:
    manifest_path = model_dir / "manifest.json"
    if not manifest_path.exists():
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest.get("files", []):
        relative_path = item["path"]
        expected_size = int(item["size"])
        expected_sha256 = item["sha256"]
        file_path = model_dir / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"缺少 OCR 模型文件: {relative_path}")
        data = file_path.read_bytes()
        actual_sha256 = hashlib.sha256(data).hexdigest()
        if len(data) != expected_size or actual_sha256 != expected_sha256:
            raise ValueError(f"OCR 模型校验失败: {relative_path}")
