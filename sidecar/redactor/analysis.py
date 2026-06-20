from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .detection import detect_sensitive_text
from .models import Candidate
from .ocr import run_ocr
from .serde import candidate_to_dict
from .validation import normalize_allowed_extension, validate_upload
from .vision import detect_visual_candidates


@dataclass(frozen=True)
class PageAnalysis:
    index: int
    width: int
    height: int
    image_path: str | None = None


@dataclass(frozen=True)
class FileAnalysis:
    file_id: str
    source_path: str
    file_type: str
    pages: list[PageAnalysis]
    candidates: list[Candidate]

    def to_dict(self) -> dict[str, object]:
        return {
            "fileId": self.file_id,
            "sourcePath": self.source_path,
            "fileType": self.file_type,
            "pages": [
                {"index": page.index, "width": page.width, "height": page.height, "imagePath": page.image_path}
                for page in self.pages
            ],
            "candidates": [candidate_to_dict(candidate) for candidate in self.candidates],
        }


def analyze_file(
    path: str | Path,
    *,
    file_id: str,
    person_name: str,
    employer_terms: list[str],
    material_type: str = "social",
) -> FileAnalysis:
    source = Path(path)
    validation = validate_upload(source, material_type)
    extension = validation.extension

    if extension in {"jpg", "jpeg", "png"}:
        return _analyze_image(source, file_id=file_id, person_name=person_name, employer_terms=employer_terms)
    if extension == "pdf":
        return _analyze_pdf(source, file_id=file_id, person_name=person_name, employer_terms=employer_terms)
    raise ValueError("仅支持 PDF、JPG、JPEG、PNG")


def _analyze_image(source: Path, *, file_id: str, person_name: str, employer_terms: list[str]) -> FileAnalysis:
    image = Image.open(source)
    words = run_ocr(source)
    candidates = detect_sensitive_text(words, person_name=person_name, employer_terms=employer_terms, file_id=file_id)
    candidates.extend(detect_visual_candidates(source, file_id=file_id, page_index=0))
    return FileAnalysis(
        file_id=file_id,
        source_path=str(source),
        file_type="image",
        pages=[PageAnalysis(index=0, width=image.width, height=image.height, image_path=str(source))],
        candidates=candidates,
    )


def _analyze_pdf(source: Path, *, file_id: str, person_name: str, employer_terms: list[str]) -> FileAnalysis:
    try:
        import fitz  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - depends on optional runtime dependency.
        raise RuntimeError("PDF 分析需要安装 PyMuPDF") from exc

    document = fitz.open(source)
    temp_dir = Path(tempfile.mkdtemp(prefix="redactor-preview-"))
    pages: list[PageAnalysis] = []
    candidates: list[Candidate] = []
    try:
        for page_index, page in enumerate(document):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            preview_path = temp_dir / f"{source.stem}-page-{page_index + 1}.png"
            pixmap.save(preview_path)
            pages.append(PageAnalysis(index=page_index, width=pixmap.width, height=pixmap.height, image_path=str(preview_path)))

            words = _extract_pdf_words(page)
            if not words:
                words = run_ocr(preview_path)
            candidates.extend(
                detect_sensitive_text(
                    words,
                    person_name=person_name,
                    employer_terms=employer_terms,
                    file_id=file_id,
                    page_index=page_index,
                )
            )
            candidates.extend(detect_visual_candidates(preview_path, file_id=file_id, page_index=page_index))
    finally:
        document.close()

    return FileAnalysis(file_id=file_id, source_path=str(source), file_type="pdf", pages=pages, candidates=candidates)


def _extract_pdf_words(page: object) -> list[dict[str, object]]:
    rect = page.rect
    words: list[dict[str, object]] = []
    for item in page.get_text("words"):
        left, top, right, bottom, text = item[:5]
        words.append(
            {
                "text": text,
                "box": (left, top, right, bottom),
                "page_width": rect.width,
                "page_height": rect.height,
            }
        )
    return words
