@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo ================================================================
echo   Building CaptureToClipboard.exe (Native C++17 Win32 / GDI+)
echo ================================================================

cd /d "%~dp0"

taskkill /F /IM CaptureToClipboard.exe >nul 2>&1
taskkill /F /IM ChupManHinh.exe >nul 2>&1
if exist "build\app.res" del /F /Q "build\app.res" >nul 2>&1
if exist "dist\CaptureToClipboard.exe" del /F /Q "dist\CaptureToClipboard.exe" >nul 2>&1

:: Locate Visual Studio vcvars64.bat via vswhere or standard paths
set "VCVARS="
if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" (
    for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
        if exist "%%i\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=%%i\VC\Auxiliary\Build\vcvars64.bat"
    )
)
if not defined VCVARS (
    if exist "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
        set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
    )
)

if defined VCVARS (
    call "!VCVARS!" >nul
)

if not exist "build" mkdir "build"
if not exist "dist" mkdir "dist"
if not exist "dist\assets" mkdir "dist\assets"
if exist "assets\settings.json" copy /Y "assets\settings.json" "dist\assets\settings.json" >nul
if exist "assets\logo.ico" copy /Y "assets\logo.ico" "dist\assets\logo.ico" >nul
if exist "assets\logo.png" copy /Y "assets\logo.png" "dist\assets\logo.png" >nul

echo [1/2] Compiling Win32 Resources (Icon + Roboto Fonts)...
pushd src
rc.exe /nologo /fo "..\build\app.res" app.rc
if errorlevel 1 (
    popd
    echo [ERROR] Resource compilation failed!
    exit /b 1
)
popd

echo [2/2] Compiling and Linking C++17 Sources (/O2 /GL /MT)...
cl.exe /nologo /std:c++17 /O2 /Oi /GL /MT /EHsc /utf-8 /DNDEBUG /DUNICODE /D_UNICODE ^
    /I"src" ^
    src\main.cpp ^
    src\i18n.cpp ^
    src\autostart.cpp ^
    src\platform_utils.cpp ^
    src\toast.cpp ^
    src\hotkeys.cpp ^
    src\tray.cpp ^
    src\overlay.cpp ^
    src\settings_window.cpp ^
    src\editor.cpp ^
    build\app.res ^
    /Fo"build\\" ^
    /Fe"dist\CaptureToClipboard.exe" ^
    /link /LTCG /OPT:REF /OPT:ICF /SUBSYSTEM:WINDOWS ^
    user32.lib gdi32.lib gdiplus.lib shell32.lib advapi32.lib comdlg32.lib ole32.lib shlwapi.lib

if errorlevel 1 (
    echo [ERROR] C++ Compilation failed!
    exit /b 1
)

echo.
echo [3/3] Dang ky so ung dung (Authenticode Code Signing)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sign_and_trust.ps1"

echo.
echo [OK] Build va ky so thanh cong: "%~dp0dist\CaptureToClipboard.exe"
exit /b 0
