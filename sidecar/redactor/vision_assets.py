from __future__ import annotations

import os
import sys
from pathlib import Path

FACE_CASCADE_RELATIVE_PATH = "vision/haarcascades/haarcascade_frontalface_default.xml"


def find_face_cascade_path() -> Path:
    candidates = _candidate_resource_files(FACE_CASCADE_RELATIVE_PATH)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    searched = "\n".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"未找到随客户端打包的人脸检测模型。已搜索:\n{searched}")


def _candidate_resource_files(relative_path: str) -> list[Path]:
    roots: list[Path] = []
    env_resource_dir = os.environ.get("LOCAL_REDACTOR_RESOURCE_DIR")
    if env_resource_dir:
        roots.append(Path(env_resource_dir))

    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        roots.extend(_frozen_resource_roots(executable_dir))
    else:
        roots.extend([Path.cwd(), Path(__file__).resolve().parents[2]])

    candidates: list[Path] = []
    for root in roots:
        candidates.extend([root / "resources" / relative_path, root / relative_path])
    return candidates


def _frozen_resource_roots(executable_dir: Path) -> list[Path]:
    contents_dir = executable_dir.parent
    app_names = ("privunit", "local-redactor")
    linux_roots = [
        root / app_name / suffix
        for app_name in app_names
        for root in (Path("/usr/lib"), Path("/opt"))
        for suffix in ("", "_up_")
    ]
    return [
        Path(getattr(sys, "_MEIPASS", executable_dir)),
        contents_dir / "Resources" / "_up_",
        contents_dir / "Resources",
        executable_dir.parent / "_up_",
        executable_dir.parent / "resources",
        *(executable_dir / ".." / "lib" / app_name / suffix for app_name in app_names for suffix in ("", "_up_")),
        *linux_roots,
        executable_dir,
        contents_dir,
        Path.cwd(),
    ]
