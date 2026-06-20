from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from redactor.detection import detect_sensitive_text
from redactor.exporter import export_redacted_file
from redactor.models import Candidate, ExportRequest, Rect, ReviewStatus
from redactor.validation import ValidationError, normalize_allowed_extension, validate_upload


def test_upload_validation_allows_pdf_jpg_jpeg_png_and_rejects_large_files(tmp_path: Path) -> None:
    allowed = tmp_path / "paper.JPG"
    allowed.write_bytes(b"x" * 16)

    result = validate_upload(allowed, material_type="social")

    assert result.extension == "jpg"

    too_large = tmp_path / "large.pdf"
    too_large.write_bytes(b"x" * (4 * 1024 * 1024 + 1))

    with pytest.raises(ValidationError, match="不超过 4MiB"):
        validate_upload(too_large, material_type="social")


def test_ipg_is_normalized_as_jpg() -> None:
    assert normalize_allowed_extension("scan.ipg") == "jpg"


def test_text_detection_only_matches_declared_person_name() -> None:
    words = [
        {"text": "张三", "box": (10, 10, 50, 30), "page_width": 200, "page_height": 100},
        {"text": "李四", "box": (60, 10, 100, 30), "page_width": 200, "page_height": 100},
        {"text": "身份证号 110105199001011234", "box": (10, 40, 190, 60), "page_width": 200, "page_height": 100},
    ]

    candidates = detect_sensitive_text(words, person_name="张三", employer_terms=[])

    assert [candidate.category for candidate in candidates] == ["person_name", "identity_number"]
    assert candidates[0].rect_normalized == Rect(0.05, 0.1, 0.2, 0.2)


def test_person_name_detection_trims_ocr_line_to_matched_name() -> None:
    words = [
        {
            "text": "孙恺，女，中国国籍，1991年10月25日生于内蒙古",
            "box": (10, 20, 410, 44),
            "page_width": 500,
            "page_height": 100,
        }
    ]

    candidates = detect_sensitive_text(words, person_name="孙恺", employer_terms=[])

    assert len(candidates) == 1
    assert candidates[0].category == "person_name"
    assert candidates[0].text == "孙恺"
    assert candidates[0].rect_normalized.x <= 0.02
    assert candidates[0].rect_normalized.width < 0.12


def test_export_rejects_white_redaction_color(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 100), "white").save(source)

    request = ExportRequest(
        source_path=str(source),
        output_path=str(tmp_path / "out.png"),
        candidates=[
            Candidate(
                file_id="file-1",
                page_index=0,
                rect_normalized=Rect(0.1, 0.1, 0.2, 0.2),
                category="manual",
                source="manual",
                confidence=1.0,
                status=ReviewStatus.APPROVED,
                color="#ffffff",
            )
        ],
    )

    with pytest.raises(ValueError, match="不能使用白色"):
        export_redacted_file(request)


def test_export_redacts_approved_image_regions_and_ignores_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 100), "white").save(source)
    output = tmp_path / "out.png"

    request = ExportRequest(
        source_path=str(source),
        output_path=str(output),
        candidates=[
            Candidate(
                file_id="file-1",
                page_index=0,
                rect_normalized=Rect(0.1, 0.1, 0.2, 0.2),
                category="manual",
                source="manual",
                confidence=1.0,
                status=ReviewStatus.APPROVED,
                color="#2563eb",
            ),
            Candidate(
                file_id="file-1",
                page_index=0,
                rect_normalized=Rect(0.5, 0.5, 0.2, 0.2),
                category="manual",
                source="manual",
                confidence=1.0,
                status=ReviewStatus.REJECTED,
                color="#dc2626",
            ),
        ],
    )

    export_redacted_file(request)

    redacted = Image.open(output).convert("RGB")
    assert redacted.getpixel((15, 15)) == (37, 99, 235)
    assert redacted.getpixel((55, 55)) == (255, 255, 255)
