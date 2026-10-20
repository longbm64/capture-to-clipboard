#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

export PATH="/opt/homebrew/opt/python@3.14/libexec/bin:/opt/homebrew/opt/python@3.13/libexec/bin:/opt/homebrew/opt/python@3.12/libexec/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
hash -r 2>/dev/null || true

PYTHON_BIN="$(command -v python3.14 || command -v python3.13 || command -v python3.12 || command -v python3)"

if [[ -d ".venv" ]] && [[ ! -x ".venv/bin/python" ]]; then
    rm -rf .venv
fi
if [[ ! -d ".venv" ]]; then
    "$PYTHON_BIN" -m venv .venv
fi
source .venv/bin/activate

python -m pip install -r requirements.txt --quiet
if [[ "$1" == "--foreground" || "$1" == "-f" ]]; then
    echo "Đang chạy CHỤP MÀN HÌNH ở chế độ foreground (bấm Ctrl+C để dừng)..."
    exec python main.py "${@:2}"
fi

LOG_FILE=".app.log"
nohup python main.py "$@" > "$LOG_FILE" 2>&1 &
PID=$!
sleep 0.5
if kill -0 "$PID" 2>/dev/null; then
    echo "Đã khởi chạy CHỤP MÀN HÌNH (PID: $PID)! Biểu tượng khay hệ thống đã sẵn sàng."
else
    echo "[LỖI] Ứng dụng không thể khởi động. Chi tiết lỗi:"
    cat "$LOG_FILE"
    exit 1
fi
