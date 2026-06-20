from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED_RESOURCE_FILES = [
    "resources/ocr/rapidocr/models/ch_PP-OCRv3_det_infer.onnx",
    "resources/ocr/rapidocr/models/ch_ppocr_mobile_v2.0_cls_infer.onnx",
    "resources/ocr/rapidocr/models/ch_PP-OCRv3_rec_infer.onnx",
    "resources/ocr/rapidocr/manifest.json",
    "resources/vision/haarcascades/haarcascade_frontalface_default.xml",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True, help="Path to the macOS .app bundle")
    parser.add_argument("--smoke-image", required=True, help="Image containing a known identity number")
    args = parser.parse_args()

    app_path = Path(args.app).resolve()
    smoke_image = Path(args.smoke_image).resolve()
    contents = app_path / "Contents"
    resources_root = contents / "Resources" / "_up_"
    sidecar = contents / "MacOS" / "redactor-sidecar"

    missing = [path for path in REQUIRED_RESOURCE_FILES if not (resources_root / path).is_file()]
    if missing:
        raise FileNotFoundError("Missing bundled resource files: " + ", ".join(missing))

    if not sidecar.is_file():
        raise FileNotFoundError(f"Missing bundled sidecar: {sidecar}")

    completed = subprocess.run(
        [str(sidecar), "analyze", "--file", str(smoke_image), "--file-id", "bundle-smoke"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        cwd=tempfile.gettempdir(),
    )
    payload = json.loads(completed.stdout)
    categories = {candidate["category"] for candidate in payload.get("candidates", [])}
    if "identity_number" not in categories:
        raise AssertionError("Bundled sidecar did not produce identity_number candidate")

    print(
        json.dumps(
            {
                "ok": True,
                "app": str(app_path),
                "sidecar": str(sidecar),
                "resourceCount": len(REQUIRED_RESOURCE_FILES),
                "candidateCount": len(payload.get("candidates", [])),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
