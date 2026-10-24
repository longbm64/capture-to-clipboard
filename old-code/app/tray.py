"""Vibrant App Logo Generator & System Tray Controller."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Dict, Optional

from PIL import Image, ImageDraw, ImageFilter
import pystray

from app.autostart import is_autostart_enabled

_ICON_CACHE: Dict[int, Image.Image] = {}


def _create_master_logo(master_size: int = 512) -> Image.Image:
    """Render a creative multi-layered app logo: Aurora squircle + tilted Polaroid landscape card + Lightning badge."""
    S = master_size
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # 1. Rich Aurora Mesh Gradient Squircle (Deep Royal Indigo -> Electric Cyan -> Sunset Magenta -> Emerald Aqua)
    grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    px = grad.load()
    for y in range(S):
        fy = y / (S - 1)
        for x in range(S):
            fx = x / (S - 1)
            t = fx * 0.42 + (1.0 - fy) * 0.58
            r = int(30 * (1 - t) + 14 * t)
            g = int(41 * (1 - t) + 185 * t)
            b = int(139 * (1 - t) + 235 * t)

            # Top-right vibrant violet-coral aurora glow
            d1 = math.hypot(fx - 0.84, fy - 0.18)
            if d1 < 0.78:
                w1 = (1.0 - d1 / 0.78) ** 2 * 0.78
                r = min(255, int(r * (1 - w1) + 236 * w1))
                g = min(255, int(g * (1 - w1) + 72 * w1))
                b = min(255, int(b * (1 - w1) + 153 * w1))

            # Bottom-left emerald-aqua glow
            d2 = math.hypot(fx - 0.16, fy - 0.84)
            if d2 < 0.68:
                w2 = (1.0 - d2 / 0.68) ** 2 * 0.60
                r = min(255, int(r * (1 - w2) + 6 * w2))
                g = min(255, int(g * (1 - w2) + 214 * w2))
                b = min(255, int(b * (1 - w2) + 160 * w2))

            px[x, y] = (r, g, b, 255)

    pad = int(S * 0.035)
    rad = int(S * 0.23)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (pad, pad, S - pad, S - pad), radius=rad, fill=255
    )
    img.paste(grad, (0, 0), mask)

    # 2. Back tilted frosted-glass screen layer (+11 deg)
    card_back = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cb_draw = ImageDraw.Draw(card_back)
    cb_draw.rounded_rectangle(
        (int(S * 0.20), int(S * 0.18), int(S * 0.76), int(S * 0.70)),
        radius=int(S * 0.075),
        fill=(255, 255, 255, 78),
        outline=(255, 255, 255, 160),
        width=int(S * 0.015),
    )
    card_back = card_back.rotate(
        11, resample=Image.Resampling.BICUBIC, center=(int(S * 0.48), int(S * 0.44))
    )
    img = Image.alpha_composite(img, card_back)

    # 3. Front crisp Polaroid/Snapshot card (-5 deg) with vivid mountain & sun artwork inside
    card_front = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cx1, cy1, cx2, cy2 = int(S * 0.15), int(S * 0.19), int(S * 0.77), int(S * 0.75)
    cf_sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(cf_sh).rounded_rectangle(
        (cx1 + 6, cy1 + 12, cx2 + 6, cy2 + 12),
        radius=int(S * 0.075),
        fill=(15, 23, 42, 130),
    )
    cf_sh = cf_sh.filter(ImageFilter.GaussianBlur(radius=9))
    card_front = Image.alpha_composite(card_front, cf_sh)

    cf_draw = ImageDraw.Draw(card_front)
    cf_draw.rounded_rectangle(
        (cx1, cy1, cx2, cy2), radius=int(S * 0.075), fill=(255, 255, 255, 255)
    )

    ix1, iy1 = cx1 + int(S * 0.045), cy1 + int(S * 0.045)
    ix2, iy2 = cx2 - int(S * 0.045), cy2 - int(S * 0.075)
    pic_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(pic_mask).rounded_rectangle(
        (ix1, iy1, ix2, iy2), radius=int(S * 0.045), fill=255
    )

    pic = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(pic)
    pdraw.rectangle((ix1, iy1, ix2, iy2), fill=(224, 242, 254, 255))

    # Warm golden sun
    sun_x = ix1 + int((ix2 - ix1) * 0.73)
    sun_y = iy1 + int((iy2 - iy1) * 0.29)
    sun_r = int(S * 0.068)
    pdraw.ellipse(
        (sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r),
        fill=(249, 115, 22, 255),
    )
    in_sr = int(sun_r * 0.72)
    pdraw.ellipse(
        (sun_x - in_sr, sun_y - in_sr, sun_x + in_sr, sun_y + in_sr),
        fill=(250, 204, 21, 255),
    )

    # Back mountain peak (Vibrant Cyan)
    pdraw.polygon(
        [
            (ix1 + int((ix2 - ix1) * 0.24), iy2 + 12),
            (ix1 + int((ix2 - ix1) * 0.69), iy1 + int((iy2 - iy1) * 0.36)),
            (ix2 + 24, iy2 + 12),
        ],
        fill=(6, 182, 212, 255),
    )
    # Front mountain peak (Royal Blue)
    pdraw.polygon(
        [
            (ix1 - 15, iy2 + 12),
            (ix1 + int((ix2 - ix1) * 0.36), iy1 + int((iy2 - iy1) * 0.22)),
            (ix1 + int((ix2 - ix1) * 0.82), iy2 + 12),
        ],
        fill=(37, 99, 235, 255),
    )

    card_front.paste(pic, (0, 0), pic_mask)
    card_front = card_front.rotate(
        -5, resample=Image.Resampling.BICUBIC, center=(int(S * 0.46), int(S * 0.47))
    )
    img = Image.alpha_composite(img, card_front)

    # 4. Creative Action Badge (Bottom-Right): Warm Amber-Orange Gradient Circle + Crisp White Lightning Bolt
    bx_c, by_c = int(S * 0.72), int(S * 0.72)
    br = int(S * 0.185)
    b_sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(b_sh).ellipse(
        (bx_c - br + 2, by_c - br + 7, bx_c + br + 2, by_c + br + 7),
        fill=(15, 23, 42, 135),
    )
    b_sh = b_sh.filter(ImageFilter.GaussianBlur(radius=8))
    img = Image.alpha_composite(img, b_sh)

    badge_grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bpx = badge_grad.load()
    for y in range(max(0, by_c - br), min(S, by_c + br + 1)):
        for x in range(max(0, bx_c - br), min(S, bx_c + br + 1)):
            u = ((x - (bx_c - br)) + (y - (by_c - br))) / max(1, 4 * br)
            bpx[x, y] = (
                int(251 * (1 - u) + 234 * u),
                int(191 * (1 - u) + 88 * u),
                int(36 * (1 - u) + 12 * u),
                255,
            )
    b_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(b_mask).ellipse((bx_c - br, by_c - br, bx_c + br, by_c + br), fill=255)
    img.paste(badge_grad, (0, 0), b_mask)

    draw = ImageDraw.Draw(img)
    draw.ellipse(
        (bx_c - br, by_c - br, bx_c + br, by_c + br),
        outline=(255, 255, 255, 255),
        width=int(S * 0.026),
    )
    bolt = [
        (bx_c + int(br * 0.12), by_c - int(br * 0.60)),
        (bx_c - int(br * 0.44), by_c + int(br * 0.06)),
        (bx_c - int(br * 0.03), by_c + int(br * 0.06)),
        (bx_c - int(br * 0.14), by_c + int(br * 0.60)),
        (bx_c + int(br * 0.44), by_c - int(br * 0.06)),
        (bx_c + int(br * 0.03), by_c - int(br * 0.06)),
    ]
    draw.polygon(bolt, fill=(255, 255, 255, 255))
    return img


def create_tray_icon_image(size: int = 64) -> Image.Image:
    """Return a high-resolution anti-aliased app logo at the requested pixel size."""
    if size in _ICON_CACHE:
        return _ICON_CACHE[size].copy()

    if 1024 not in _ICON_CACHE:
        from app.platform_utils import get_bundled_assets_dir

        master_img = None
        for cand in (
            get_bundled_assets_dir() / "logo.png",
            Path(__file__).resolve().parent.parent / "assets" / "logo.png",
        ):
            if cand.exists():
                try:
                    master_img = Image.open(cand).convert("RGBA")
                    break
                except Exception:
                    pass
        if master_img is None:
            master_img = _create_master_logo(1024)
        _ICON_CACHE[1024] = master_img

    master = _ICON_CACHE[1024]
    resized = (
        master.copy()
        if size == master.width and size == master.height
        else master.resize((size, size), Image.Resampling.LANCZOS)
    )
    _ICON_CACHE[size] = resized
    return resized.copy()


_CACHED_ICO_PATH: Optional[Path] = None


def ensure_logo_assets() -> Path:
    """Save or locate `assets/logo.png` and `assets/logo.ico` for window icons and shortcuts."""
    global _CACHED_ICO_PATH
    if _CACHED_ICO_PATH is not None and _CACHED_ICO_PATH.exists():
        return _CACHED_ICO_PATH

    from app.platform_utils import get_bundled_assets_dir, get_writable_data_dir

    bundled_ico = get_bundled_assets_dir() / "logo.ico"
    if bundled_ico.exists() and getattr(__import__("sys"), "frozen", False):
        _CACHED_ICO_PATH = bundled_ico
        return bundled_ico

    assets_dir = get_writable_data_dir()
    png_path = assets_dir / "logo.png"
    ico_path = assets_dir / "logo.ico"
    icns_path = assets_dir / "logo.icns"

    if not ico_path.exists() or not png_path.exists():
        logo_256 = create_tray_icon_image(256)
        if not png_path.exists():
            logo_256.save(png_path, format="PNG")
        if not ico_path.exists():
            logo_256.save(
                ico_path,
                format="ICO",
                bitmap_format="bmp",
                sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
            )
        if not icns_path.exists():
            try:
                logo_512 = create_tray_icon_image(512)
                logo_512.save(icns_path, format="ICNS")
            except Exception:
                pass
    _CACHED_ICO_PATH = ico_path
    return ico_path


_WIN32_HICON_SM: int = 0
_WIN32_HICON_LG: int = 0


def apply_window_icon(win) -> None:
    """Apply the bright app logo to a Tkinter Tk or Toplevel window titlebar & taskbar."""
    import sys
    from PIL import ImageTk

    if sys.platform == "darwin":
        try:
            from AppKit import NSApplication, NSImage
            from app.platform_utils import get_bundled_assets_dir

            app = NSApplication.sharedApplication()
            for cand in (
                get_bundled_assets_dir() / "logo.icns",
                get_bundled_assets_dir() / "logo.png",
                Path(__file__).resolve().parent.parent / "assets" / "logo.icns",
                Path(__file__).resolve().parent.parent / "assets" / "logo.png",
            ):
                if cand.exists():
                    ns_img = NSImage.alloc().initWithContentsOfFile_(str(cand.resolve()))
                    if ns_img:
                        app.setApplicationIconImage_(ns_img)
                        break
        except Exception:
            pass
        return

    try:
        ico_path = ensure_logo_assets()
        root_widget = getattr(win, "master", None) or win
        tk_icons = getattr(root_widget, "_cached_app_tk_icons", None)
        if not tk_icons:
            tk_icons = [
                ImageTk.PhotoImage(create_tray_icon_image(sz))
                for sz in (16, 24, 32, 48, 64, 128)
            ]
            root_widget._cached_app_tk_icons = tk_icons
        win._app_tk_icons = tk_icons  # keep reference alive
        win.iconphoto(True, *tk_icons)
    except Exception:
        ico_path = None

    if sys.platform == "win32" and ico_path is not None and ico_path.exists():
        def _set_win32_hwnd_icon() -> None:
            global _WIN32_HICON_SM, _WIN32_HICON_LG
            try:
                import ctypes

                user32 = ctypes.windll.user32
                LR_LOADFROMFILE = 0x0010
                IMAGE_ICON = 1
                WM_SETICON = 0x0080
                GCLP_HICON = -14
                GCLP_HICONSM = -34

                if not _WIN32_HICON_SM:
                    sm_w = max(16, user32.GetSystemMetrics(49))  # SM_CXSMICON
                    sm_h = max(16, user32.GetSystemMetrics(50))  # SM_CYSMICON
                    _WIN32_HICON_SM = user32.LoadImageW(
                        None, str(ico_path), IMAGE_ICON, sm_w, sm_h, LR_LOADFROMFILE
                    )
                if not _WIN32_HICON_LG:
                    lg_w = max(32, user32.GetSystemMetrics(11))  # SM_CXICON
                    lg_h = max(32, user32.GetSystemMetrics(12))  # SM_CYICON
                    _WIN32_HICON_LG = user32.LoadImageW(
                        None, str(ico_path), IMAGE_ICON, lg_w, lg_h, LR_LOADFROMFILE
                    )

                hwnd = user32.GetParent(win.winfo_id()) or win.winfo_id()
                if hwnd:
                    if _WIN32_HICON_SM:
                        user32.SendMessageW(hwnd, WM_SETICON, 0, _WIN32_HICON_SM)
                        user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, _WIN32_HICON_SM)
                    if _WIN32_HICON_LG:
                        user32.SendMessageW(hwnd, WM_SETICON, 1, _WIN32_HICON_LG)
                        user32.SetClassLongPtrW(hwnd, GCLP_HICON, _WIN32_HICON_LG)
            except Exception:
                pass

        _set_win32_hwnd_icon()
        try:
            win.after(30, _set_win32_hwnd_icon)
        except Exception:
            pass


class SystemTrayController:
    """Manages the background system tray icon and context menu."""

    def __init__(
        self,
        on_open_settings: Callable[[], None],
        on_toggle_autostart: Callable[[], None],
        on_capture_clipboard: Callable[[], None],
        on_capture_draw: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        self.on_open_settings = on_open_settings
        self.on_toggle_autostart = on_toggle_autostart
        self.on_capture_clipboard = on_capture_clipboard
        self.on_capture_draw = on_capture_draw
        self.on_exit = on_exit
        self.icon: Optional[pystray.Icon] = None

    def start(self) -> None:
        from app.i18n import tr

        image = create_tray_icon_image(64)
        menu = pystray.Menu(
            pystray.MenuItem(
                lambda _item: tr("tray_open_settings"),
                lambda _icon, _item: self.on_open_settings(),
                default=True,
            ),
            pystray.MenuItem(
                lambda _item: tr("tray_autostart"),
                lambda _icon, _item: self.on_toggle_autostart(),
                checked=lambda _item: is_autostart_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _item: tr("tray_capture_fast"),
                lambda _icon, _item: self.on_capture_clipboard(),
            ),
            pystray.MenuItem(
                lambda _item: tr("tray_capture_draw"),
                lambda _icon, _item: self.on_capture_draw(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _item: tr("tray_exit"),
                lambda _icon, _item: self.on_exit(),
            ),
        )
        self.icon = pystray.Icon(
            name="CaptureToClipboard",
            icon=image,
            title=tr("tray_tooltip"),
            menu=menu,
        )
        self.icon.run_detached()

    def refresh_menu(self) -> None:
        from app.i18n import tr

        if self.icon is not None:
            try:
                self.icon.title = tr("tray_tooltip")
                self.icon.update_menu()
            except Exception:
                pass

    def ensure_visible(self) -> None:
        """Verify tray icon is registered with Windows Explorer (retries NIM_ADD if early boot NIM_ADD failed)."""
        import sys

        if sys.platform != "win32" or self.icon is None:
            return
        try:
            hwnd = getattr(self.icon, "_hwnd", None)
            icon_handle = getattr(self.icon, "_icon_handle", None)
            if not hwnd or not icon_handle:
                return
            from pystray._util import win32

            nid = win32.NOTIFYICONDATAW(
                cbSize=__import__("ctypes").sizeof(win32.NOTIFYICONDATAW),
                hWnd=hwnd,
                hID=id(self.icon),
                uFlags=win32.NIF_TIP,
                szTip=self.icon.title,
            )
            if not win32.Shell_NotifyIcon(win32.NIM_MODIFY, nid):
                self.icon._show()
        except Exception:
            pass

    def stop(self) -> None:
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None
