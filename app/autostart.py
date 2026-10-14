"""Cross-platform Auto-Start (Start on OS Boot) Manager.

- Windows: Uses HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
  (no Administrator privileges required, launches silently via pythonw.exe).
- macOS: Uses ~/Library/LaunchAgents/com.capturetoclipboard.app.plist
- Linux: Uses ~/.config/autostart/capture-to-clipboard.desktop
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Tuple

APP_RUN_NAME = "CaptureToClipboard"


def _get_main_script_path() -> Path:
    return Path(__file__).resolve().parent.parent / "main.py"


def _get_windows_launch_command() -> str:
    """Build the command string stored in HKCU Run registry key."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'

    exe_path = Path(sys.executable)
    pythonw_path = exe_path.with_name("pythonw.exe")
    runner = pythonw_path if pythonw_path.exists() else exe_path
    main_script = _get_main_script_path()
    return f'"{runner}" "{main_script}" --minimized'


def is_autostart_enabled() -> bool:
    """Return True if the application is configured to start automatically on OS login."""
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ,
            ) as key:
                val, _ = winreg.QueryValueEx(key, APP_RUN_NAME)
                return bool(val and str(val).strip())
        except FileNotFoundError:
            return False
        except OSError:
            return False

    if sys.platform == "darwin":
        plist_path = (
            Path.home()
            / "Library"
            / "LaunchAgents"
            / "com.capturetoclipboard.app.plist"
        )
        return plist_path.exists()

    desktop_path = (
        Path.home() / ".config" / "autostart" / "capture-to-clipboard.desktop"
    )
    return desktop_path.exists()


def set_autostart_enabled(enabled: bool) -> Tuple[bool, str]:
    """Enable or disable auto-start on OS login. Returns (success, status_message)."""
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                if enabled:
                    cmd = _get_windows_launch_command()
                    winreg.SetValueEx(key, APP_RUN_NAME, 0, winreg.REG_SZ, cmd)
                    return True, "Đã bật khởi động cùng máy tính."
                else:
                    try:
                        winreg.DeleteValue(key, APP_RUN_NAME)
                    except FileNotFoundError:
                        pass
                    return True, "Đã tắt khởi động cùng máy tính."
        except Exception as exc:
            return False, f"Không thể cập nhật cài đặt khởi động: {exc}"

    if sys.platform == "darwin":
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_path = plist_dir / "com.capturetoclipboard.app.plist"
        try:
            if enabled:
                plist_dir.mkdir(parents=True, exist_ok=True)
                if getattr(sys, "frozen", False):
                    prog_args = f"""        <string>{sys.executable}</string>
        <string>--minimized</string>"""
                else:
                    main_script = _get_main_script_path()
                    prog_args = f"""        <string>{sys.executable}</string>
        <string>{main_script}</string>
        <string>--minimized</string>"""
                plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.capturetoclipboard.app</string>
    <key>ProgramArguments</key>
    <array>
{prog_args}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
                plist_path.write_text(plist_content, encoding="utf-8")
                return True, "Đã bật khởi động cùng macOS!"
            else:
                if plist_path.exists():
                    plist_path.unlink()
                return True, "Đã tắt khởi động cùng macOS."
        except Exception as exc:
            return False, f"Lỗi cấu hình LaunchAgent trên macOS: {exc}"

    # Linux XDG Autostart
    autostart_dir = Path.home() / ".config" / "autostart"
    desktop_path = autostart_dir / "capture-to-clipboard.desktop"
    try:
        if enabled:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            if getattr(sys, "frozen", False):
                exec_cmd = f'"{sys.executable}" --minimized'
            else:
                main_script = _get_main_script_path()
                exec_cmd = f'"{sys.executable}" "{main_script}" --minimized'
            desktop_content = f"""[Desktop Entry]
Type=Application
Name=Chup Man Hinh
Comment=Screenshot region to clipboard and annotation tool
Exec={exec_cmd}
Terminal=false
X-GNOME-Autostart-enabled=true
"""
            desktop_path.write_text(desktop_content, encoding="utf-8")
            return True, "Đã bật khởi động cùng Linux!"
        else:
            if desktop_path.exists():
                desktop_path.unlink()
            return True, "Đã tắt khởi động cùng Linux."
    except Exception as exc:
        return False, f"Lỗi cấu hình Autostart trên Linux: {exc}"


def _get_settings_file_path() -> Path:
    from app.platform_utils import get_writable_data_dir

    return get_writable_data_dir() / "settings.json"


def is_prtsc_enabled() -> bool:
    """Return True if pressing PrtSc should trigger instant capture (same as Ctrl + 1)."""
    import json

    cfg_path = _get_settings_file_path()
    if not cfg_path.exists():
        return True
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return bool(data.get("prtsc_enabled", True))
    except Exception:
        return True


def set_prtsc_enabled(enabled: bool) -> Tuple[bool, str]:
    """Persist the PrtSc hotkey preference to assets/settings.json."""
    import json

    cfg_path = _get_settings_file_path()
    try:
        data = {}
        if cfg_path.exists():
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data["prtsc_enabled"] = bool(enabled)
        cfg_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        msg = (
            "Đã bật chụp nhanh bằng phím PrtSc."
            if enabled
            else "Đã tắt chụp nhanh bằng phím PrtSc."
        )
        return True, msg
    except Exception as exc:
        return False, f"Không thể lưu cài đặt phím PrtSc: {exc}"

