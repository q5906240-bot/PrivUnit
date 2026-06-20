#!/usr/bin/env bash
set -euo pipefail

export LC_ALL="${LC_ALL:-C.UTF-8}"
export LANG="${LANG:-C.UTF-8}"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "build_desktop_linux.sh must run on Linux" >&2
  exit 1
fi

python3 scripts/build_sidecar.py
npm run tauri -- build --bundles deb,appimage
