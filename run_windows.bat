@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "dist\CaptureToClipboard.exe" (
    call build_windows.bat
    if errorlevel 1 exit /b 1
)

start "" "dist\CaptureToClipboard.exe" --show-settings
