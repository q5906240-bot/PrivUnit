$ErrorActionPreference = "Stop"

python scripts/build_sidecar.py
npm run tauri -- build --bundles nsis
