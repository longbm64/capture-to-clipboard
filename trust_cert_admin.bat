@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo =================================================================
echo   Cai dat chung chi Capture To Clipboard vao he thong (Root Trust)
echo =================================================================

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Yeu cau quyen Administrator de cai chung chi vao he thong...
    powershell -Command "Start-Process cmd -ArgumentList '/c `\"%~f0`\" admin' -Verb RunAs"
    exit /b 0
)

if not exist "build\CaptureToClipboard.cer" (
    powershell -ExecutionPolicy Bypass -File "%~dp0sign_and_trust.ps1"
)

if exist "build\CaptureToClipboard.cer" (
    echo Dang cai dat chung chi vao LocalMachine\Root va LocalMachine\TrustedPublisher...
    certutil -addstore -f "Root" "build\CaptureToClipboard.cer"
    certutil -addstore -f "TrustedPublisher" "build\CaptureToClipboard.cer"
    echo.
    echo [OK] Da cai dat va tin cay chung chi Capture To Clipboard thanh cong!
    echo.
    powershell -ExecutionPolicy Bypass -File "%~dp0sign_and_trust.ps1"
) else (
    echo [ERROR] Khong tim thay file build\CaptureToClipboard.cer!
)

if "%1"=="admin" (
    echo Nhan phim bat ky de thoat...
    pause >nul
)
