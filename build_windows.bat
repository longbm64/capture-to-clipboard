@echo off
chcp 65001 >nul
echo ========================================================
echo   Dang dong goi ung dung CaptureToClipboard.exe (Windows)
echo ========================================================

cd /d "%~dp0"

python -m pip install -r requirements.txt pyinstaller
python -c "from app.tray import ensure_logo_assets; ensure_logo_assets()"

python -m PyInstaller --noconfirm --clean --noconsole --onefile ^
    --name "CaptureToClipboard" ^
    --icon "assets/logo.ico" ^
    --add-data "assets;assets" ^
    --hidden-import "pystray._win32" ^
    --hidden-import "pynput.keyboard._win32" ^
    --hidden-import "pynput.mouse._win32" ^
    main.py

echo.
if exist "dist\CaptureToClipboard.exe" (
    echo [OK] Build thanh cong: "%~dp0dist\CaptureToClipboard.exe"
) else (
    echo [ERROR] Build that bai!
)
pause
