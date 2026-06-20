from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from .ocr_models import find_bundled_model_dir, model_kwargs


def run_ocr(image_path: str | Path) -> list[dict[str, Any]]:
    """Return OCR words in the normalized internal shape."""

    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-not-found]
    except Exception as exc:
        raise RuntimeError("OCR 引擎未打包，请确认 rapidocr-onnxruntime 已包含在 sidecar 中") from exc

    image = Image.open(image_path)
    page_width, page_height = image.size
    engine = RapidOCR(**model_kwargs(find_bundled_model_dir()))
    result, _ = engine(str(image_path))
    words: list[dict[str, Any]] = []
    for item in result or []:
        points, text, score = item
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        words.append(
            {
                "text": text,
                "score": score,
                "box": (min(xs), min(ys), max(xs), max(ys)),
                "page_width": page_width,
                "page_height": page_height,
            }
        )
    return words
