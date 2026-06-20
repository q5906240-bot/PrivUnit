from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence

MAX_UPLOAD_BYTES = 4 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "ipg"}


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class UploadValidationResult:
    path: str
    extension: str
    size_bytes: int
    material_type: str


def normalize_allowed_extension(path_or_name: str) -> str:
    extension = Path(path_or_name).suffix.lower().lstrip(".")
    if extension == "ipg":
        return "jpg"
    return extension


def validate_upload(path: str | Path, material_type: str) -> UploadValidationResult:
    file_path = Path(path)
    extension = file_path.suffix.lower().lstrip(".")
    normalized = normalize_allowed_extension(file_path.name)

    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError("仅允许上传 PDF、JPG、JPEG、PNG 格式文件")

    size = file_path.stat().st_size
    if size > MAX_UPLOAD_BYTES:
        raise ValidationError("单个文件不超过 4MiB")

    if material_type == "social" and size == 0:
        raise ValidationError("社会化类型需要上传脱敏材料")

    return UploadValidationResult(
        path=str(file_path),
        extension=normalized,
        size_bytes=size,
        material_type=material_type,
    )


def validate_material_submission(material_type: str, files: Sequence[str | Path]) -> None:
    if material_type == "social" and not files:
        raise ValidationError("社会化类型需要上传脱敏材料")
