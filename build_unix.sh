#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "========================================================"
echo "  Building ChupManHinh standalone app (macOS / Linux)"
echo "========================================================"

if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
python -c "from app.tray import ensure_logo_assets; ensure_logo_assets()"

python -m PyInstaller --noconfirm --clean --windowed --onefile \
    --name "ChupManHinh" \
    --icon "assets/logo.png" \
    --add-data "assets:assets" \
    main.py

echo "[OK] Build completed: $(pwd)/dist/ChupManHinh"
