#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

python -m pip install -r requirements.txt --quiet
nohup python main.py >/dev/null 2>&1 &
echo "Đã khởi chạy CHỤP MÀN HÌNH!"
