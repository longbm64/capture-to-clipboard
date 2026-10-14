"""Cross-platform screen capture, DPI scaling, HD image enhancement, and clipboard utilities.

Supports Windows, macOS, and Linux (both X11 and Wayland).
"""

from __future__ import annotations

import ctypes
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Dict, Tuple

import mss
from PIL import Image, ImageFilter, ImageGrab


def get_bundled_assets_dir():
    """Return path to bundled read-only assets (works both in normal Python and PyInstaller --onefile)."""
    from pathlib import Path

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / "assets"
    return Path(__file__).resolve().parent.parent / "assets"


def get_writable_data_dir():
    """Return a writable directory for settings.json and generated icons."""
    from pathlib import Path

    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            mac_dir = Path.home() / "Library" / "Application Support" / "CaptureToClipboard"
            mac_dir.mkdir(parents=True, exist_ok=True)
            return mac_dir
        exe_assets = Path(sys.executable).resolve().parent / "assets"
        try:
            exe_assets.mkdir(parents=True, exist_ok=True)
            return exe_assets
        except Exception:
            fallback = Path.home() / ".capture-to-clipboard"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    dev_assets = Path(__file__).resolve().parent.parent / "assets"
    dev_assets.mkdir(parents=True, exist_ok=True)
    return dev_assets


def register_roboto_fonts() -> None:
    """Register bundled Roboto TTF fonts with the OS font subsystem so Tkinter and Pillow can use 'Roboto'."""
    fonts_dir = get_bundled_assets_dir() / "fonts"
    if not fonts_dir.exists():
        return

    if sys.platform == "win32":
        try:
            FR_PRIVATE = 0x10
            gdi32 = ctypes.windll.gdi32
            for ttf in fonts_dir.glob("*.ttf"):
                gdi32.AddFontResourceExW(str(ttf), FR_PRIVATE, 0)
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            from pathlib import Path

            mac_fonts = Path.home() / "Library" / "Fonts"
            mac_fonts.mkdir(parents=True, exist_ok=True)
            for ttf in fonts_dir.glob("*.ttf"):
                dest = mac_fonts / ttf.name
                if not dest.exists():
                    shutil.copy2(ttf, dest)
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            from pathlib import Path

            user_fonts = Path.home() / ".local" / "share" / "fonts"
            user_fonts.mkdir(parents=True, exist_ok=True)
            for ttf in fonts_dir.glob("*.ttf"):
                dest = user_fonts / ttf.name
                if not dest.exists():
                    shutil.copy2(ttf, dest)
        except Exception:
            pass


def enable_dpi_awareness() -> None:
    """Enable Per-Monitor v2 High-DPI awareness so screen coordinates match physical pixels 1:1."""
    register_roboto_fonts()
    if sys.platform == "win32":
        try:
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
            user32 = ctypes.windll.user32
            user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
            user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
            if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
                return
        except Exception:
            pass
        try:
            # PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return
        except Exception:
            pass
        try:
            # PROCESS_SYSTEM_DPI_AWARE = 1
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            return
        except Exception:
            pass
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def enhance_image_quality(
    image: Image.Image,
    upscale_hd: bool = True,
) -> Image.Image:
    """Enhance screenshot clarity and sharpness (Retina-style Lanczos upscale + UnsharpMask)."""
    img = image.convert("RGB")
    w, h = img.size
    max_dim = max(w, h)

    if upscale_hd:
        if max_dim <= 1400:
            scale = 2.0
        elif max_dim <= 2200:
            scale = 1.5
        else:
            scale = 1.0

        if scale > 1.0:
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            img = img.filter(
                ImageFilter.UnsharpMask(radius=1.15, percent=80, threshold=2)
            )
        else:
            img = img.filter(
                ImageFilter.UnsharpMask(radius=0.9, percent=55, threshold=2)
            )
    else:
        img = img.filter(
            ImageFilter.UnsharpMask(radius=0.75, percent=40, threshold=3)
        )

    return img


def get_virtual_screen_geometry(root=None) -> Dict[str, int]:
    """Return the bounding box of the virtual desktop across all monitors."""
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            SM_XVIRTUALSCREEN = 76
            SM_YVIRTUALSCREEN = 77
            SM_CXVIRTUALSCREEN = 78
            SM_CYVIRTUALSCREEN = 79
            left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
            top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            if width > 0 and height > 0:
                return {"left": left, "top": top, "width": width, "height": height}
        except Exception:
            pass

    try:
        sct_cls = getattr(mss, "MSS", mss.mss)
        with sct_cls() as sct:
            mon = sct.monitors[0]
            return {
                "left": int(mon["left"]),
                "top": int(mon["top"]),
                "width": int(mon["width"]),
                "height": int(mon["height"]),
            }
    except Exception:
        pass

    if root is not None:
        try:
            root.update_idletasks()
            return {
                "left": 0,
                "top": 0,
                "width": int(root.winfo_screenwidth()),
                "height": int(root.winfo_screenheight()),
            }
        except Exception:
            pass

    return {"left": 0, "top": 0, "width": 1920, "height": 1080}


def capture_virtual_screen(root=None) -> Tuple[Image.Image, Dict[str, int]]:
    """Capture the entire screen (including multi-monitor setups) at native pixel resolution."""
    try:
        sct_cls = getattr(mss, "MSS", mss.mss)
        with sct_cls() as sct:
            mon = sct.monitors[0]
            raw = sct.grab(mon)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            geom = {
                "left": int(mon["left"]),
                "top": int(mon["top"]),
                "width": int(mon["width"]),
                "height": int(mon["height"]),
            }
            return img, geom
    except Exception:
        pass

    try:
        if sys.platform in ("win32", "darwin"):
            img = ImageGrab.grab(all_screens=True)
        else:
            img = ImageGrab.grab()
        img = img.convert("RGB")
        geom = get_virtual_screen_geometry(root)
        return img, geom
    except Exception:
        pass

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png", prefix="capture_")
    os.close(tmp_fd)
    try:
        commands = []
        if sys.platform == "darwin":
            commands.append(["screencapture", "-x", tmp_path])
        elif sys.platform.startswith("linux"):
            commands.extend(
                [
                    ["grim", tmp_path],
                    ["gnome-screenshot", "-f", tmp_path],
                    ["spectacle", "-b", "-n", "-o", tmp_path],
                    ["maim", tmp_path],
                    ["scrot", "-o", tmp_path],
                    ["import", "-window", "root", tmp_path],
                ]
            )

        for cmd in commands:
            if shutil.which(cmd[0]) is None:
                continue
            res = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            if res.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                with Image.open(tmp_path) as captured:
                    img = captured.convert("RGB")
                geom = get_virtual_screen_geometry(root)
                geom["width"] = img.width
                geom["height"] = img.height
                return img, geom
    except Exception:
        pass
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass

    raise RuntimeError(
        "Không thể chụp màn hình. Trên Linux Wayland hãy cài 'grim' hoặc 'gnome-screenshot'; "
        "trên macOS hãy cấp quyền Screen Recording cho Terminal/Python."
    )


def _copy_image_windows(image: Image.Image) -> Tuple[bool, str]:
    """Copy a PIL Image to the Windows clipboard in lossless PNG and high-DPI CF_DIB formats."""
    CF_DIB = 8
    GMEM_MOVEABLE = 0x0002

    rgb_img = image.convert("RGB")

    bmp_io = io.BytesIO()
    rgb_img.save(bmp_io, format="BMP", dpi=(144, 144))
    dib_bytes = bmp_io.getvalue()[14:]

    png_io = io.BytesIO()
    rgb_img.save(png_io, format="PNG", compress_level=1, dpi=(144, 144))
    png_bytes = png_io.getvalue()

    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_bool
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p

    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_bool
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.c_bool
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_bool
    user32.RegisterClipboardFormatW.argtypes = [ctypes.c_wchar_p]
    user32.RegisterClipboardFormatW.restype = ctypes.c_uint

    def _alloc_and_copy(payload: bytes) -> int:
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(payload))
        if not h_mem:
            raise MemoryError("GlobalAlloc failed for clipboard buffer")
        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            kernel32.GlobalFree(h_mem)
            raise MemoryError("GlobalLock failed for clipboard buffer")
        try:
            ctypes.memmove(ptr, payload, len(payload))
        finally:
            kernel32.GlobalUnlock(h_mem)
        return h_mem

    opened = False
    for _ in range(8):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.025)

    if not opened:
        return False, "Không thể mở Clipboard trên Windows (đang bị ứng dụng khác khóa)."

    try:
        user32.EmptyClipboard()

        for fmt_name in ("PNG", "image/png"):
            cf_fmt = user32.RegisterClipboardFormatW(fmt_name)
            if cf_fmt:
                try:
                    h_png = _alloc_and_copy(png_bytes)
                    if not user32.SetClipboardData(cf_fmt, h_png):
                        kernel32.GlobalFree(h_png)
                except Exception:
                    pass

        h_dib = _alloc_and_copy(dib_bytes)
        if not user32.SetClipboardData(CF_DIB, h_dib):
            kernel32.GlobalFree(h_dib)
            return False, "SetClipboardData(CF_DIB) thất bại."

        return True, "Đã copy ảnh chất lượng cao vào Clipboard!"
    finally:
        user32.CloseClipboard()


def _copy_image_macos(image: Image.Image) -> Tuple[bool, str]:
    """Copy a PIL Image to the macOS clipboard via osascript (AppleScript)."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png", prefix="clip_")
    os.close(tmp_fd)
    try:
        image.save(tmp_path, format="PNG", compress_level=1, dpi=(144, 144))
        escaped_path = tmp_path.replace('"', '\\"')
        script = f'set the clipboard to (read (POSIX file "{escaped_path}") as «class PNGf»)'
        res = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode == 0:
            return True, "Đã copy ảnh chất lượng cao vào Clipboard!"

        script_tiff = f'set the clipboard to (read (POSIX file "{escaped_path}") as TIFF picture)'
        res2 = subprocess.run(
            ["osascript", "-e", script_tiff],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res2.returncode == 0:
            return True, "Đã copy ảnh vào Clipboard!"
        return False, f"Lỗi osascript trên macOS: {res.stderr.strip()}"
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass


def _copy_image_linux(image: Image.Image) -> Tuple[bool, str]:
    """Copy a PIL Image to the Linux clipboard (supports both Wayland wl-copy and X11 xclip)."""
    png_io = io.BytesIO()
    image.save(png_io, format="PNG", compress_level=1, dpi=(144, 144))
    png_bytes = png_io.getvalue()

    is_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))

    if is_wayland and shutil.which("wl-copy"):
        res = subprocess.run(
            ["wl-copy", "--type", "image/png"],
            input=png_bytes,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )
        if res.returncode == 0:
            return True, "Đã copy ảnh vào Clipboard (wl-copy)!"

    if shutil.which("xclip"):
        proc = subprocess.Popen(
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-i"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert proc.stdin is not None
        proc.stdin.write(png_bytes)
        proc.stdin.close()
        proc.wait(timeout=3)
        if proc.returncode == 0:
            return True, "Đã copy ảnh vào Clipboard (xclip)!"

    if shutil.which("wl-copy"):
        res = subprocess.run(
            ["wl-copy", "--type", "image/png"],
            input=png_bytes,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )
        if res.returncode == 0:
            return True, "Đã copy ảnh vào Clipboard (wl-copy)!"

    return (
        False,
        "Chưa cài công cụ clipboard cho Linux. Hãy chạy: sudo apt install xclip (X11) hoặc wl-clipboard (Wayland).",
    )


def copy_image_to_clipboard(image: Image.Image) -> Tuple[bool, str]:
    """Copy a PIL Image to the system clipboard on Windows, macOS, or Linux."""
    try:
        if sys.platform == "win32":
            return _copy_image_windows(image)
        if sys.platform == "darwin":
            return _copy_image_macos(image)
        return _copy_image_linux(image)
    except Exception as exc:
        return False, f"Lỗi khi copy vào Clipboard: {exc}"
