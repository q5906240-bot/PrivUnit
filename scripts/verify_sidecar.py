from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sidecar", required=True)
    args = parser.parse_args()

    sidecar = Path(args.sidecar)
    if not sidecar.is_file():
        raise FileNotFoundError(f"sidecar not found: {sidecar}")

    with tempfile.TemporaryDirectory(prefix="redactor-sidecar-verify-") as tmp:
        image_path = Path(tmp) / "identity.png"
        image = Image.new("RGB", (760, 160), "white")
        draw = ImageDraw.Draw(image)
        draw.text((24, 56), "ID 110105199001011234", fill="black")
        image.save(image_path)

        completed = subprocess.run(
            [str(sidecar), "analyze", "--file", str(image_path), "--file-id", "sidecar-smoke"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )

    payload = json.loads(completed.stdout)
    categories = {candidate["category"] for candidate in payload.get("candidates", [])}
    if "identity_number" not in categories:
        raise AssertionError("sidecar did not produce identity_number candidate")

    print(json.dumps({"ok": True, "sidecar": str(sidecar), "candidateCount": len(payload.get("candidates", []))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
