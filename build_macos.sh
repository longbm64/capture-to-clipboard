#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "========================================================"
echo "  Đang đóng gói CHỤP MÀN HÌNH cho macOS (.app & .dmg)   "
echo "========================================================"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "[!] Lưu ý: PyInstaller yêu cầu chạy trên môi trường macOS (hoặc GitHub Actions macos-latest)"
    echo "    để biên dịch nhân Mach-O của ChupManHinh.app."
    exit 1
fi

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller
python3 -c "from app.tray import ensure_logo_assets; ensure_logo_assets()"

python3 -m PyInstaller --noconfirm --clean ChupManHinh_macOS.spec

if [[ -d "dist/ChupManHinh.app" ]]; then
    echo "-> Đang ký số ad-hoc (codesign) cho Apple Silicon / Gatekeeper..."
    codesign --force --deep --sign - "dist/ChupManHinh.app" || true

    echo "-> Đang nén dist/ChupManHinh-macOS-App.zip..."
    ditto -c -k --sequesterRsrc --keepParent "dist/ChupManHinh.app" "dist/ChupManHinh-macOS-App.zip"

    echo "-> Đang đóng gói bộ cài đặt dist/ChupManHinh-macOS.dmg..."
    rm -rf dist/dmg_staging dist/ChupManHinh-macOS.dmg
    mkdir -p dist/dmg_staging
    cp -R "dist/ChupManHinh.app" dist/dmg_staging/
    ln -s /Applications dist/dmg_staging/Applications

    hdiutil create \
        -volname "CHUP MAN HINH" \
        -srcfolder dist/dmg_staging \
        -ov -format UDZO \
        "dist/ChupManHinh-macOS.dmg"

    rm -rf dist/dmg_staging
    echo ""
    echo "[OK] Đóng gói thành công cho macOS:"
    echo "  • App Bundle : $(pwd)/dist/ChupManHinh.app"
    echo "  • App ZIP    : $(pwd)/dist/ChupManHinh-macOS-App.zip"
    echo "  • Bộ cài DMG : $(pwd)/dist/ChupManHinh-macOS.dmg"
else
    echo "[ERROR] Không tìm thấy dist/ChupManHinh.app sau khi build!"
    exit 1
fi
