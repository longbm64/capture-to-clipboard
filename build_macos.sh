#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "========================================================"
echo "  Building Capture To Clipboard for macOS (.app & .dmg) "
echo "========================================================"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "[!] Lưu ý: PyInstaller yêu cầu chạy trên môi trường macOS"
    echo "    để biên dịch nhân Mach-O của Capture To Clipboard.app."
    exit 1
fi

export PATH="/opt/homebrew/opt/python@3.14/libexec/bin:/opt/homebrew/opt/python@3.13/libexec/bin:/opt/homebrew/opt/python@3.12/libexec/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
hash -r 2>/dev/null || true

find_python_bin() {
    for candidate in \
        "/opt/homebrew/bin/python3.14" \
        "/opt/homebrew/opt/python@3.14/libexec/bin/python3" \
        "/opt/homebrew/bin/python3.13" \
        "/opt/homebrew/opt/python@3.13/libexec/bin/python3" \
        "/opt/homebrew/bin/python3.12" \
        "/opt/homebrew/opt/python@3.12/libexec/bin/python3" \
        "/opt/homebrew/bin/python3" \
        "$(command -v python3 2>/dev/null || true)" \
        "/usr/local/bin/python3" \
        "/usr/bin/python3"; do
        if [[ -n "$candidate" && -x "$candidate" ]]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

PYTHON_BIN="$(find_python_bin)"
if [[ -z "$PYTHON_BIN" ]]; then
    echo "[ERROR] Không tìm thấy Python 3 trên máy. Hãy cài bằng: brew install python"
    exit 1
fi
echo "-> Sử dụng Python: $PYTHON_BIN ($("$PYTHON_BIN" --version))"

# 1. Kiểm tra module tkinter trên macOS (Homebrew tách riêng gói python-tk)
if ! "$PYTHON_BIN" -c "import tkinter" >/dev/null 2>&1; then
    echo "-> Phát hiện thiếu module tkinter, đang tự động cài đặt python-tk qua Homebrew..."
    PY_MM=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if command -v brew >/dev/null 2>&1; then
        brew install "python-tk@${PY_MM}" || brew install python-tk
        hash -r 2>/dev/null || true
        PYTHON_BIN="$(find_python_bin)"
        echo "-> Đã cập nhật đường dẫn Python: $PYTHON_BIN"
    else
        echo "[ERROR] Python hiện tại chưa có tkinter. Hãy chạy: brew install python-tk@${PY_MM}"
        exit 1
    fi
fi

# 2. Tạo và kích hoạt môi trường ảo (.venv)
echo "-> Đang chuẩn bị môi trường ảo (.venv)..."
if [[ -d ".venv" ]]; then
    if [[ ! -x ".venv/bin/python" ]] || ! .venv/bin/python -c "import tkinter" >/dev/null 2>&1; then
        echo "-> Làm mới lại .venv để đồng bộ với $PYTHON_BIN..."
        rm -rf .venv
    fi
fi

if [[ ! -d ".venv" ]]; then
    "$PYTHON_BIN" -m venv .venv
fi
source .venv/bin/activate

echo "-> Đang cài đặt các thư viện cần thiết vào .venv..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
python -c "from app.tray import ensure_logo_assets; ensure_logo_assets()"

echo "-> Đang biên dịch Capture To Clipboard.app..."
python -m PyInstaller --noconfirm --clean ChupManHinh_macOS.spec

APP_BUNDLE="dist/Capture To Clipboard.app"
DMG_FILE="dist/CaptureToClipboard-macOS.dmg"
ZIP_FILE="dist/CaptureToClipboard-macOS-App.zip"

if [[ -d "$APP_BUNDLE" ]]; then
    echo "-> Đang ký số ad-hoc (codesign) cho Apple Silicon / Gatekeeper..."
    codesign --force --deep --sign - "$APP_BUNDLE" || true

    echo "-> Đang nén $ZIP_FILE..."
    rm -f "$ZIP_FILE"
    ditto -c -k --sequesterRsrc --keepParent "$APP_BUNDLE" "$ZIP_FILE"

    echo "-> Đang đóng gói bộ cài đặt $DMG_FILE..."
    rm -rf dist/dmg_staging "$DMG_FILE"
    mkdir -p dist/dmg_staging
    cp -R "$APP_BUNDLE" dist/dmg_staging/
    ln -s /Applications dist/dmg_staging/Applications

    hdiutil create \
        -volname "Capture To Clipboard" \
        -srcfolder dist/dmg_staging \
        -fs HFS+ \
        -ov -format UDZO \
        "$DMG_FILE" || (
        sleep 2
        hdiutil create \
            -volname "Capture To Clipboard" \
            -srcfolder dist/dmg_staging \
            -ov -format UDZO \
            "$DMG_FILE"
    )

    rm -rf dist/dmg_staging
    echo ""
    echo "========================================================"
    echo "[OK] Đóng gói thành công cho macOS:"
    echo "  • App Bundle : $(pwd)/$APP_BUNDLE"
    echo "  • App ZIP    : $(pwd)/$ZIP_FILE"
    echo "  • Bộ cài DMG : $(pwd)/$DMG_FILE"
    echo "========================================================"
else
    echo "[ERROR] Không tìm thấy $APP_BUNDLE sau khi build!"
    exit 1
fi
