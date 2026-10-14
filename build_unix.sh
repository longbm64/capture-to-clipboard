#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "========================================================"
echo "  Building ChupManHinh standalone app (macOS / Linux)"
echo "========================================================"

python3 -m pip install -r requirements.txt pyinstaller
python3 -c "from app.tray import ensure_logo_assets; ensure_logo_assets()"

python3 -m PyInstaller --noconfirm --clean --windowed --onefile \
    --name "ChupManHinh" \
    --icon "assets/logo.png" \
    --add-data "assets:assets" \
    main.py

echo "[OK] Build completed: $(pwd)/dist/ChupManHinh"
