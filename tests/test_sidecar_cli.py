from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from redactor.analysis import analyze_file
from redactor.models import Candidate, ExportRequest, Rect, ReviewStatus


def test_social_material_requires_at_least_one_file() -> None:
    from redactor.validation import validate_material_submission

    with pytest.raises(ValueError, match="社会化类型需要上传脱敏材料"):
        validate_material_submission("social", [])

    validate_material_submission("other", [])


def test_analyze_image_returns_red_seal_candidate(tmp_path: Path) -> None:
    source = tmp_path / "seal.png"
    image = Image.new("RGB", (160, 120), "white")
    for x in range(95, 145):
        for y in range(35, 85):
            image.putpixel((x, y), (220, 20, 20))
    image.save(source)

    result = analyze_file(
        source,
        file_id="file-1",
        person_name="",
        employer_terms=[],
    )

    assert any(candidate.category == "seal" for candidate in result.candidates)


def test_analyze_image_uses_bundled_ocr_models_for_text_candidates(tmp_path: Path) -> None:
    source = tmp_path / "identity.png"
    image = Image.new("RGB", (760, 160), "white")
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    draw.text((24, 56), "ID 110105199001011234", fill="black")
    image.save(source)

    result = analyze_file(
        source,
        file_id="file-1",
        person_name="",
        employer_terms=[],
    )

    assert any(candidate.category == "identity_number" for candidate in result.candidates)


def test_cli_analyze_outputs_json(tmp_path: Path) -> None:
    source = tmp_path / "sample.png"
    Image.new("RGB", (80, 60), "white").save(source)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "redactor.cli",
            "analyze",
            "--file",
            str(source),
            "--file-id",
            "file-1",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        env={"PYTHONPATH": str(Path.cwd() / "sidecar")},
    )

    payload = json.loads(completed.stdout)
    assert payload["fileId"] == "file-1"
    assert payload["pages"][0]["index"] == 0


def test_cli_export_redacts_image_from_json_request(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "out.png"
    request_path = tmp_path / "request.json"
    Image.new("RGB", (100, 100), "white").save(source)

    request = {
        "sourcePath": str(source),
        "outputPath": str(output),
        "candidates": [
            {
                "fileId": "file-1",
                "pageIndex": 0,
                "rectNormalized": {"x": 0.2, "y": 0.2, "width": 0.2, "height": 0.2},
                "category": "manual",
                "source": "manual",
                "confidence": 1,
                "status": "approved",
                "color": "#059669",
            }
        ],
    }
    request_path.write_text(json.dumps(request), encoding="utf-8")

    subprocess.run(
        [sys.executable, "-m", "redactor.cli", "export", "--request", str(request_path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        env={"PYTHONPATH": str(Path.cwd() / "sidecar")},
    )

    assert Image.open(output).convert("RGB").getpixel((25, 25)) == (5, 150, 105)


def test_pdf_export_removes_approved_text_when_pymupdf_is_available(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    source = tmp_path / "source.pdf"
    output = tmp_path / "out.pdf"

    document = fitz.open()
    page = document.new_page(width=300, height=160)
    page.insert_text((40, 80), "Name ZhangSan ID 110105199001011234", fontsize=14)
    document.save(source)
    document.close()

    request = ExportRequest(
        source_path=str(source),
        output_path=str(output),
        candidates=[
            Candidate(
                file_id="file-1",
                page_index=0,
                rect_normalized=Rect(0.12, 0.35, 0.78, 0.3),
                category="identity_number",
                source="manual",
                confidence=1,
                status=ReviewStatus.APPROVED,
                color="#2563eb",
            )
        ],
    )

    from redactor.exporter import export_redacted_file

    export_redacted_file(request)

    redacted = fitz.open(output)
    try:
        assert "110105199001011234" not in redacted[0].get_text()
    finally:
        redacted.close()


def test_analyze_landscape_image_pdf_preserves_page_ratio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fitz = pytest.importorskip("fitz")
    source = tmp_path / "landscape_scan.pdf"
    scan = tmp_path / "landscape_scan.png"

    image = Image.new("RGB", (800, 420), "white")
    for x in range(610, 730):
        for y in range(130, 250):
            image.putpixel((x, y), (220, 20, 20))
    image.save(scan)

    document = fitz.open()
    page = document.new_page(width=800, height=420)
    page.insert_image(page.rect, filename=str(scan))
    document.save(source)
    document.close()

    monkeypatch.setattr("redactor.analysis.run_ocr", lambda _: [])

    result = analyze_file(source, file_id="file-1", person_name="", employer_terms=[])

    assert result.pages[0].width > result.pages[0].height
    assert any(candidate.category == "seal" for candidate in result.candidates)


def test_export_redacts_landscape_image_pdf_region(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    source = tmp_path / "landscape_scan.pdf"
    scan = tmp_path / "landscape_scan.png"
    output = tmp_path / "landscape_out.pdf"

    Image.new("RGB", (800, 420), "white").save(scan)
    document = fitz.open()
    page = document.new_page(width=800, height=420)
    page.insert_image(page.rect, filename=str(scan))
    document.save(source)
    document.close()

    from redactor.exporter import export_redacted_file

    export_redacted_file(
        ExportRequest(
            source_path=str(source),
            output_path=str(output),
            candidates=[
                Candidate(
                    file_id="file-1",
                    page_index=0,
                    rect_normalized=Rect(0.72, 0.2, 0.18, 0.3),
                    category="manual",
                    source="manual",
                    confidence=1,
                    status=ReviewStatus.APPROVED,
                    color="#059669",
                )
            ],
        )
    )

    redacted = fitz.open(output)
    try:
        assert redacted[0].rect.width > redacted[0].rect.height
        pixmap = redacted[0].get_pixmap(alpha=False)
        rendered = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        assert rendered.getpixel((round(pixmap.width * 0.8), round(pixmap.height * 0.3))) == (5, 150, 105)
    finally:
        redacted.close()
