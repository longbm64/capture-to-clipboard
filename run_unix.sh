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
nohup python main.py >/dev/null 2>&1 &
echo "Đã khởi chạy CHỤP MÀN HÌNH!"
