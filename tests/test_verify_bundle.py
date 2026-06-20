from __future__ import annotations

from scripts.verify_bundle import REQUIRED_RESOURCE_FILES


def test_bundle_verifier_requires_ocr_and_vision_models() -> None:
    assert "resources/ocr/rapidocr/models/ch_PP-OCRv3_det_infer.onnx" in REQUIRED_RESOURCE_FILES
    assert "resources/ocr/rapidocr/models/ch_PP-OCRv3_rec_infer.onnx" in REQUIRED_RESOURCE_FILES
    assert "resources/vision/haarcascades/haarcascade_frontalface_default.xml" in REQUIRED_RESOURCE_FILES
