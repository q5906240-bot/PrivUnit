from __future__ import annotations

import shutil
import subprocess
import sys
import platform
from pathlib import Path

EXCLUDED_MODULES = [
    "av",
    "boto3",
    "botocore",
    "datasets",
    "fastapi",
    "jupyter",
    "matplotlib",
    "openpyxl",
    "pandas",
    "pyarrow",
    "pytest",
    "scipy",
    "sklearn",
    "sqlalchemy",
    "tensorflow",
    "timm",
    "torch",
    "torchvision",
    "transformers",
    "uvicorn",
]

HIDDEN_IMPORTS = [
    "rapidocr_onnxruntime.ch_ppocr_v3_det",
    "rapidocr_onnxruntime.ch_ppocr_v2_cls",
    "rapidocr_onnxruntime.ch_ppocr_v3_rec",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    target_dir = root / "src-tauri" / "binaries"
    target_dir.mkdir(parents=True, exist_ok=True)
    entrypoint = root / "build" / "redactor_sidecar_entry.py"
    entrypoint.parent.mkdir(parents=True, exist_ok=True)
    entrypoint.write_text(
        "from redactor.cli import main\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n",
        encoding="utf-8",
    )

    if shutil.which("pyinstaller") is None:
        print("pyinstaller is not installed. Install it with: python3 -m pip install pyinstaller", file=sys.stderr)
        return 1

    subprocess.run(
        build_pyinstaller_command(
            sys.executable,
            str(root),
            str(entrypoint),
            ";" if sys.platform.startswith("win") else ":",
            "redactor-sidecar",
        ),
        cwd=root,
        check=True,
    )

    binary_name = "redactor-sidecar.exe" if sys.platform.startswith("win") else "redactor-sidecar"
    built = root / "dist" / binary_name
    target = target_dir / tauri_sidecar_name("redactor-sidecar", sys.platform, platform.machine())
    shutil.copy2(built, target)
    print(target)
    return 0


def build_pyinstaller_command(
    python_executable: str,
    root: str,
    entrypoint: str,
    data_separator: str,
    name: str,
) -> list[str]:
    root_path = Path(root)
    command = [
        python_executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--onefile",
        "--name",
        name,
        "--paths",
        str(root_path / "sidecar"),
        "--add-data",
        f"{root_path / 'resources'}{data_separator}resources",
    ]
    for source, target in rapidocr_config_data_files(data_separator):
        command.extend(["--add-data", f"{source}{data_separator}{target}"])
    for module in HIDDEN_IMPORTS:
        command.extend(["--hidden-import", module])
    for module in EXCLUDED_MODULES:
        command.extend(["--exclude-module", module])
    command.append(entrypoint)
    return command


def rapidocr_config_data_files(data_separator: str) -> list[tuple[str, str]]:
    try:
        import rapidocr_onnxruntime
    except Exception as exc:
        raise RuntimeError("打包 sidecar 前需要安装 rapidocr-onnxruntime") from exc

    root = Path(rapidocr_onnxruntime.__file__).resolve().parent
    return [
        (str(root / "config.yaml"), "rapidocr_onnxruntime"),
        (str(root / "ch_ppocr_v3_det/config.yaml"), "rapidocr_onnxruntime/ch_ppocr_v3_det"),
        (str(root / "ch_ppocr_v2_cls/config.yaml"), "rapidocr_onnxruntime/ch_ppocr_v2_cls"),
        (str(root / "ch_ppocr_v3_rec/config.yaml"), "rapidocr_onnxruntime/ch_ppocr_v3_rec"),
    ]


def tauri_sidecar_name(name: str, system_platform: str, machine_name: str) -> str:
    machine = machine_name.lower()
    if system_platform == "darwin":
        triple = "aarch64-apple-darwin" if machine in {"arm64", "aarch64"} else "x86_64-apple-darwin"
        return f"{name}-{triple}"
    if system_platform.startswith("win"):
        triple = "x86_64-pc-windows-msvc" if machine in {"amd64", "x86_64"} else "aarch64-pc-windows-msvc"
        return f"{name}-{triple}.exe"
    triple = "x86_64-unknown-linux-gnu" if machine in {"amd64", "x86_64"} else "aarch64-unknown-linux-gnu"
    return f"{name}-{triple}"


if __name__ == "__main__":
    raise SystemExit(main())
