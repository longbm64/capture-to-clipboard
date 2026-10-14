@echo off
cd /d "%~dp0"
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%' AND CommandLine LIKE '%main.py%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
start "" pythonw main.py
if errorlevel 1 (
    python main.py
)
