#!/usr/bin/env bash
set -euo pipefail

export LC_ALL="${LC_ALL:-en_US.UTF-8}"
export LANG="${LANG:-en_US.UTF-8}"

python3 scripts/build_sidecar.py
if npm run tauri -- build; then
  exit 0
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  exit 1
fi

echo "Tauri build failed. Trying macOS DMG fallback without Finder AppleScript..."
python3 - <<'PY'
import json
import platform
import subprocess
from pathlib import Path

root = Path.cwd()
bundle_root = root / "src-tauri" / "target" / "release" / "bundle"
macos_dir = bundle_root / "macos"
dmg_dir = bundle_root / "dmg"
config = json.loads((root / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
product_name = config["productName"]
version = config["version"]
machine = platform.machine().lower()
arch = "aarch64" if machine in {"arm64", "aarch64"} else "x64" if machine in {"x86_64", "amd64"} else machine
app_path = macos_dir / f"{product_name}.app"
dmg_script = dmg_dir / "bundle_dmg.sh"
output = dmg_dir / f"{product_name}_{version}_{arch}.dmg"

if not app_path.is_dir():
    raise SystemExit(f"fallback unavailable: missing app bundle {app_path}")
if not dmg_script.is_file():
    raise SystemExit(f"fallback unavailable: missing DMG script {dmg_script}")

info = subprocess.run(["hdiutil", "info"], text=True, stdout=subprocess.PIPE, check=True).stdout.splitlines()
project_prefix = str(bundle_root)
devices: list[str] = []
matching_image = False
for line in info:
    stripped = line.strip()
    if stripped.startswith("================================================"):
        matching_image = False
        continue
    if stripped.startswith("image-path"):
        matching_image = project_prefix in stripped
        continue
    if matching_image and stripped.startswith("/dev/disk"):
        devices.append(stripped.split()[0])

for device in devices:
    subprocess.run(["hdiutil", "detach", device], check=False)

for temp in list(macos_dir.glob("rw.*.dmg")) + list(dmg_dir.glob("rw.*.dmg")):
    temp.unlink(missing_ok=True)
output.unlink(missing_ok=True)

subprocess.run(["bash", str(dmg_script), "--skip-jenkins", str(output), str(macos_dir)], check=True)
subprocess.run(["hdiutil", "verify", str(output)], check=True)
print(f"Fallback DMG created: {output}")
PY
