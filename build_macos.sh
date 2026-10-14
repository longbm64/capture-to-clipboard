#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "========================================================"
echo "  Đang đóng gói CHỤP MÀN HÌNH cho macOS (.app & .dmg)   "
echo "========================================================"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "[!] Lưu ý: PyInstaller yêu cầu chạy trên môi trường macOS"
    echo "    để biên dịch nhân Mach-O của ChupManHinh.app."
    exit 1
fi

# 1. Kiểm tra module tkinter trên macOS (Homebrew tách riêng gói python-tk)
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "-> Phát hiện thiếu module tkinter, đang tự động cài đặt python-tk qua Homebrew..."
    PY_MM=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if command -v brew >/dev/null 2>&1; then
        brew install "python-tk@${PY_MM}" || brew install python-tk
    else
        echo "[ERROR] Python hiện tại chưa có tkinter. Hãy chạy: brew install python-tk@${PY_MM}"
        exit 1
    fi
fi

# 2. Tạo và kích hoạt môi trường ảo (.venv) để tránh lỗi PEP 668 externally-managed-environment
echo "-> Đang chuẩn bị môi trường ảo (.venv)..."
if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "-> Đang cài đặt các thư viện cần thiết vào .venv..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
python -c "from app.tray import ensure_logo_assets; ensure_logo_assets()"

echo "-> Đang biên dịch ChupManHinh.app..."
python -m PyInstaller --noconfirm --clean ChupManHinh_macOS.spec

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
        -fs HFS+ \
        -ov -format UDZO \
        "dist/ChupManHinh-macOS.dmg" || (
        sleep 2
        hdiutil create \
            -volname "CHUP MAN HINH" \
            -srcfolder dist/dmg_staging \
            -ov -format UDZO \
            "dist/ChupManHinh-macOS.dmg"
    )

    rm -rf dist/dmg_staging
    echo ""
    echo "========================================================"
    echo "[OK] Đóng gói thành công cho macOS:"
    echo "  • App Bundle : $(pwd)/dist/ChupManHinh.app"
    echo "  • App ZIP    : $(pwd)/dist/ChupManHinh-macOS-App.zip"
    echo "  • Bộ cài DMG : $(pwd)/dist/ChupManHinh-macOS.dmg"
    echo "========================================================"
else
    echo "[ERROR] Không tìm thấy dist/ChupManHinh.app sau khi build!"
    exit 1
fi
