from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .colors import hex_to_rgb, normalize_hex_color
from .models import Candidate, ExportRequest, ReviewStatus

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".ipg"}


def approved_candidates(candidates: list[Candidate], page_index: int | None = None) -> list[Candidate]:
    result = [
        candidate
        for candidate in candidates
        if candidate.status == ReviewStatus.APPROVED and (page_index is None or candidate.page_index == page_index)
    ]
    for candidate in result:
        normalize_hex_color(candidate.color)
    return result


def export_redacted_file(request: ExportRequest) -> str:
    source = Path(request.source_path)
    output = Path(request.output_path)
    extension = source.suffix.lower()

    if extension in IMAGE_EXTENSIONS:
        _export_image(source, output, approved_candidates(request.candidates, page_index=0))
        return str(output)

    if extension == ".pdf":
        _export_pdf(source, output, request)
        return str(output)

    raise ValueError("仅支持导出 PDF、JPG、JPEG、PNG 文件")


def _export_image(source: Path, output: Path, candidates: list[Candidate]) -> None:
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    for candidate in candidates:
        draw.rectangle(candidate.rect_normalized.to_pixels(*image.size), fill=hex_to_rgb(candidate.color))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def _export_pdf(source: Path, output: Path, request: ExportRequest) -> None:
    try:
        import fitz  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - depends on optional runtime dependency.
        raise RuntimeError("PDF 导出需要安装 PyMuPDF，或改用图片导出流程") from exc

    document = fitz.open(str(source))
    try:
        if request.rasterize_pdf_pages:
            _export_rasterized_pdf(document, output, request.candidates)
        else:
            _export_structured_pdf(document, output, request.candidates)
    finally:
        document.close()


def _export_structured_pdf(document: object, output: Path, candidates: list[Candidate]) -> None:
    import fitz  # type: ignore[import-not-found]

    for page_index in range(len(document)):  # type: ignore[arg-type]
        page = document[page_index]  # type: ignore[index]
        for candidate in approved_candidates(candidates, page_index=page_index):
            rect = candidate.rect_normalized.clamped()
            page_rect = page.rect
            pdf_rect = fitz.Rect(
                page_rect.x0 + rect.x * page_rect.width,
                page_rect.y0 + rect.y * page_rect.height,
                page_rect.x0 + (rect.x + rect.width) * page_rect.width,
                page_rect.y0 + (rect.y + rect.height) * page_rect.height,
            )
            color = tuple(channel / 255 for channel in hex_to_rgb(candidate.color))
            page.add_redact_annot(pdf_rect, fill=color)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)

    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output), garbage=4, deflate=True, clean=True)


def _export_rasterized_pdf(document: object, output: Path, candidates: list[Candidate]) -> None:
    import fitz  # type: ignore[import-not-found]

    output_document = fitz.open()
    for page_index in range(len(document)):  # type: ignore[arg-type]
        page = document[page_index]  # type: ignore[index]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        draw = ImageDraw.Draw(image)
        for candidate in approved_candidates(candidates, page_index=page_index):
            draw.rectangle(candidate.rect_normalized.to_pixels(*image.size), fill=hex_to_rgb(candidate.color))

        pdf_page = output_document.new_page(width=page.rect.width, height=page.rect.height)
        png_bytes = _image_to_png_bytes(image)
        pdf_page.insert_image(pdf_page.rect, stream=png_bytes)

    output.parent.mkdir(parents=True, exist_ok=True)
    output_document.save(str(output), garbage=4, deflate=True)
    output_document.close()


def _image_to_png_bytes(image: Image.Image) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
