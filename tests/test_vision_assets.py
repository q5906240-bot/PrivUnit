from __future__ import annotations

from pathlib import Path

from redactor.vision_assets import find_face_cascade_path


def test_repository_contains_face_cascade_asset() -> None:
    path = find_face_cascade_path()

    assert path.name == "haarcascade_frontalface_default.xml"
    assert path.exists()
