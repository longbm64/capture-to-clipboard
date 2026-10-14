#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
nohup python3 main.py >/dev/null 2>&1 &
echo "Capture to Clipboard da san sang (PID: $!). Nhan Ctrl+1 hoac Ctrl+2 de chup man hinh."
