"""Cross-platform Auto-Start (Start on OS Boot) Manager.

- Windows: Uses HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
  (no Administrator privileges required, launches silently via pythonw.exe).
- macOS: Uses ~/Library/LaunchAgents/com.capturetoclipboard.app.plist
- Linux: Uses ~/.config/autostart/capture-to-clipboard.desktop
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import plistlib
import sys
from typing import Any, Dict, Optional, Tuple

APP_RUN_NAME = "CaptureToClipboard"
LEGACY_RUN_NAMES = ("ChupManHinh",)


def _get_main_script_path() -> Path:
    return Path(__file__).resolve().parent.parent / "main.py"


def _get_settings_file_path() -> Path:
    from app.platform_utils import get_writable_data_dir

    return get_writable_data_dir() / "settings.json"


def _read_settings_dict() -> Dict[str, Any]:
    cfg_path = _get_settings_file_path()
    if not cfg_path.exists():
        return {}
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_settings_dict(data: Dict[str, Any]) -> bool:
    cfg_path = _get_settings_file_path()
    try:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except Exception:
        return False


def _get_windows_launch_command() -> str:
    """Build the command string stored in HKCU Run registry key."""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --minimized'

    dist_exe = _get_main_script_path().parent / "dist" / "CaptureToClipboard.exe"
    if dist_exe.exists():
        return f'"{dist_exe.resolve()}" --minimized'

    exe_path = Path(sys.executable).resolve()
    pythonw_path = exe_path.with_name("pythonw.exe")
    runner = pythonw_path if pythonw_path.exists() else exe_path
    main_script = _get_main_script_path()
    return f'"{runner}" "{main_script}" --minimized'


def _extract_exe_from_command(cmd: str) -> Optional[Path]:
    """Extract the target executable path from a Windows registry command string."""
    s = cmd.strip()
    if not s:
        return None
    if s.startswith('"'):
        end_quote = s.find('"', 1)
        if end_quote > 1:
            return Path(s[1:end_quote])
    parts = s.split()
    return Path(parts[0]) if parts else None


def _is_windows_startup_approved() -> bool:
    """Return False only if Windows Task Manager explicitly disabled this startup entry."""
    if sys.platform != "win32":
        return True
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
            0,
            winreg.KEY_READ,
        ) as key:
            val, _ = winreg.QueryValueEx(key, APP_RUN_NAME)
            if isinstance(val, (bytes, bytearray)) and len(val) > 0:
                # Odd first byte (1, 3, etc.) means disabled by Task Manager
                if val[0] in (1, 3):
                    return False
    except OSError:
        pass
    return True


def _set_windows_startup_approved(enabled: bool) -> None:
    """Ensure Windows Task Manager marks CaptureToClipboard as enabled in StartupApproved\\Run."""
    if sys.platform != "win32":
        return
    try:
        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            for legacy_name in LEGACY_RUN_NAMES:
                try:
                    winreg.DeleteValue(key, legacy_name)
                except OSError:
                    pass
            if enabled:
                enabled_bytes = b"\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                winreg.SetValueEx(
                    key, APP_RUN_NAME, 0, winreg.REG_BINARY, enabled_bytes
                )
            else:
                try:
                    winreg.DeleteValue(key, APP_RUN_NAME)
                except OSError:
                    pass
    except OSError:
        pass


def is_autostart_enabled() -> bool:
    """Return True if the application is configured to start automatically on OS login."""
    if sys.platform == "win32":
        try:
            import winreg

            if not _is_windows_startup_approved():
                return False

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ,
            ) as key:
                val, _ = winreg.QueryValueEx(key, APP_RUN_NAME)
                if not (val and str(val).strip()):
                    return False
                exe_path = _extract_exe_from_command(str(val))
                return bool(exe_path and exe_path.exists())
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
    from app.i18n import tr

    data = _read_settings_dict()
    data["autostart_enabled"] = bool(enabled)
    _write_settings_dict(data)

    if sys.platform == "win32":
        try:
            import winreg

            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                for legacy_name in LEGACY_RUN_NAMES:
                    try:
                        winreg.DeleteValue(key, legacy_name)
                    except OSError:
                        pass

                if enabled:
                    cmd = _get_windows_launch_command()
                    winreg.SetValueEx(key, APP_RUN_NAME, 0, winreg.REG_SZ, cmd)
                    _set_windows_startup_approved(True)
                    return True, tr("toast_autostart_on")
                else:
                    try:
                        winreg.DeleteValue(key, APP_RUN_NAME)
                    except FileNotFoundError:
                        pass
                    _set_windows_startup_approved(False)
                    return True, tr("toast_autostart_off")
        except Exception as exc:
            return False, f"Autostart error: {exc}"

    if sys.platform == "darwin":
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_path = plist_dir / "com.capturetoclipboard.app.plist"
        try:
            if enabled:
                plist_dir.mkdir(parents=True, exist_ok=True)
                if getattr(sys, "frozen", False):
                    exe_str = str(Path(sys.executable).resolve())
                    app_in_applications = Path(
                        "/Applications/Capture To Clipboard.app/Contents/MacOS/CaptureToClipboard"
                    )
                    if (
                        "/Volumes/" in exe_str or "/AppTranslocation/" in exe_str
                    ) and app_in_applications.exists():
                        exe_str = str(app_in_applications)
                    prog_args = [exe_str, "--minimized"]
                else:
                    main_script = str(_get_main_script_path())
                    prog_args = [str(Path(sys.executable).resolve()), main_script, "--minimized"]

                plist_data = {
                    "Label": "com.capturetoclipboard.app",
                    "ProgramArguments": prog_args,
                    "RunAtLoad": True,
                    "ProcessType": "Interactive",
                    "LimitLoadToSessionType": "Aqua",
                }
                plist_path.write_bytes(plistlib.dumps(plist_data))
                return True, tr("toast_autostart_on")
            else:
                if plist_path.exists():
                    plist_path.unlink()
                return True, tr("toast_autostart_off")
        except Exception as exc:
            return False, f"LaunchAgent error: {exc}"

    # Linux XDG Autostart
    autostart_dir = Path.home() / ".config" / "autostart"
    desktop_path = autostart_dir / "capture-to-clipboard.desktop"
    try:
        if enabled:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            if getattr(sys, "frozen", False):
                exec_cmd = f'"{Path(sys.executable).resolve()}" --minimized'
            else:
                main_script = _get_main_script_path()
                exec_cmd = f'"{Path(sys.executable).resolve()}" "{main_script}" --minimized'
            desktop_content = f"""[Desktop Entry]
Type=Application
Name=Capture To Clipboard
Comment=Screenshot region to clipboard and annotation tool
Exec={exec_cmd}
Terminal=false
X-GNOME-Autostart-enabled=true
"""
            desktop_path.write_text(desktop_content, encoding="utf-8")
            return True, tr("toast_autostart_on")
        else:
            if desktop_path.exists():
                desktop_path.unlink()
            return True, tr("toast_autostart_off")
    except Exception as exc:
        return False, f"Autostart error: {exc}"


def sync_autostart_on_startup() -> None:
    """Ensure OS autostart registration points to the current executable path when enabled."""
    data = _read_settings_dict()
    if "autostart_enabled" in data:
        want_enabled = bool(data.get("autostart_enabled", True))
    else:
        # Default to enabled on first run (or if a registry/plist entry already existed)
        want_enabled = True

    if want_enabled:
        set_autostart_enabled(True)


def is_prtsc_enabled() -> bool:
    """Return True if pressing PrtSc should trigger instant capture (same as Ctrl + 1)."""
    data = _read_settings_dict()
    return bool(data.get("prtsc_enabled", True))


def set_prtsc_enabled(enabled: bool) -> Tuple[bool, str]:
    """Persist the PrtSc hotkey preference to settings.json."""
    from app.i18n import tr

    data = _read_settings_dict()
    data["prtsc_enabled"] = bool(enabled)
    if _write_settings_dict(data):
        msg = tr("toast_prtsc_on") if enabled else tr("toast_prtsc_off")
        return True, msg
    return False, "Failed to save PrtSc setting"

