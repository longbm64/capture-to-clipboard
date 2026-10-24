"""Internationalization (i18n) Manager for Capture To Clipboard.

Supports two languages:
- 'vi' : Tiếng Việt (Default)
- 'en' : English

Persists the user's language choice in `settings.json` so the app launches
in the previously selected language on startup.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

from app import APP_VERSION

APP_NAME = "Capture To Clipboard"
APP_NAME_WITH_VERSION = f"{APP_NAME} v{APP_VERSION}"
MOD_KEY = "Cmd" if sys.platform == "darwin" else "Ctrl"
CAPTURE_HOTKEY_FAST = "Ctrl + 1"
CAPTURE_HOTKEY_DRAW = "Ctrl + 2"

_CURRENT_LANG: Optional[str] = None


def _get_settings_path() -> Path:
    from app.platform_utils import get_writable_data_dir

    return get_writable_data_dir() / "settings.json"


def _read_settings_dict() -> Dict[str, Any]:
    cfg_path = _get_settings_path()
    if not cfg_path.exists():
        return {}
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_settings_dict(data: Dict[str, Any]) -> bool:
    cfg_path = _get_settings_path()
    try:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except Exception:
        return False


def get_language() -> str:
    """Return current language code ('vi' or 'en'). Defaults to 'vi'."""
    global _CURRENT_LANG
    if _CURRENT_LANG in ("vi", "en"):
        return _CURRENT_LANG
    data = _read_settings_dict()
    lang = str(data.get("language", "vi")).strip().lower()
    _CURRENT_LANG = "en" if lang == "en" else "vi"
    return _CURRENT_LANG


def set_language(lang: str) -> Tuple[bool, str]:
    """Set and persist language ('vi' or 'en') to settings.json."""
    global _CURRENT_LANG
    normalized = "en" if str(lang).strip().lower() == "en" else "vi"
    _CURRENT_LANG = normalized
    data = _read_settings_dict()
    data["language"] = normalized
    ok = _write_settings_dict(data)
    msg = (
        "Switched language to English."
        if normalized == "en"
        else "Đã chuyển ngôn ngữ sang Tiếng Việt."
    )
    return ok, msg


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "vi": {
        # App & Tray
        "app_title": f"Capture To Clipboard v{APP_VERSION}",
        "tray_tooltip": f"Capture To Clipboard v{APP_VERSION} — Nhấn để mở Cài đặt & Hướng dẫn",
        "tray_open_settings": "Bảng hướng dẫn & Cài đặt",
        "tray_autostart": "Khởi động cùng máy tính",
        "tray_capture_fast": f"Chụp nhanh ({CAPTURE_HOTKEY_FAST})",
        "tray_capture_draw": f"Chụp & Ghi chú ({CAPTURE_HOTKEY_DRAW})",
        "tray_exit": "Đóng ứng dụng",
        # Toasts
        "toast_ready": (
            f"Capture To Clipboard đã sẵn sàng  •  {CAPTURE_HOTKEY_FAST} / PrtSc: Chụp nhanh  |  {CAPTURE_HOTKEY_DRAW}: Chụp & Ghi chú"
        ),
        "toast_minimized_tray": "Capture To Clipboard đã thu xuống khay hệ thống (System Tray).",
        "toast_autostart_on": "Đã bật khởi động cùng máy tính.",
        "toast_autostart_off": "Đã tắt khởi động cùng máy tính.",
        "toast_prtsc_on": "Đã bật chụp nhanh bằng phím PrtSc.",
        "toast_prtsc_off": "Đã tắt chụp nhanh bằng phím PrtSc.",
        "toast_capture_err": "Không thể chụp màn hình: {err}",
        "toast_copied_fast": "Đã sao chép ảnh sắc nét ({w}×{h} px) vào bộ nhớ tạm!",
        "toast_copied_draw": "Đã sao chép ảnh ghi chú ({w}×{h} px) vào bộ nhớ tạm!",
        # Settings Window
        "settings_autostart_title": "Khởi động cùng máy tính",
        "settings_prtsc_title": "Bấm phím PrtSc để chụp nhanh (tương tự Ctrl + 1)",
        "settings_lang_title": "Ngôn ngữ hiển thị (Language)",
        "status_enabled": "✓ Đang bật",
        "status_disabled": "Đang tắt",
        "header_tagline": "Chụp vùng màn hình sắc nét & Lưu nhanh vào bộ nhớ tạm",
        "header_badge": f"v{APP_VERSION} • Retina HD",
        "guide_section_title": "PHÍM TẮT & HƯỚNG DẪN NHANH",
        "footer_version": f"Phiên bản: v{APP_VERSION}",
        "footer_developer": "Được phát triển bởi KAHUB PLATFORM",
        "table_col_shortcut": "PHÍM TẮT",
        "table_col_function": "CHỨC NĂNG",
        "table_col_desc": "MÔ TẢ THAO TÁC",
        # Overlay
        "overlay_ctrl1_title": f"⚡ {CAPTURE_HOTKEY_FAST} : Kéo chọn vùng để sao chép ảnh ngay",
        "overlay_ctrl2_title": f"🎨 {CAPTURE_HOTKEY_DRAW} : Kéo chọn vùng để thêm ghi chú",
        "overlay_banner_hint": "Kéo chọn vùng   •   Nhấp đúp hoặc Space: Chụp toàn màn hình   •   ESC để hủy",
        # Editor
        "editor_undo": "Hoàn tác",
        "editor_redo": "Làm lại",
        "editor_clear": "Xóa hết",
        "editor_color_label": "Màu sắc:",
        "editor_custom_color": "Màu khác",
        "editor_custom_color_title": "Chọn màu nét vẽ",
        "editor_copy_btn": f"Sao chép ({MOD_KEY}+C)",
        "editor_save_btn": f"Lưu ảnh ({MOD_KEY}+S)",
        "editor_close_btn": "Đóng (ESC)",
        "editor_save_dialog_title": "Lưu ảnh chụp màn hình chất lượng cao",
        "editor_status_bar": (
            "Kích thước: {w}×{h} px   •   "
            "Kéo giữ chuột vào nét đã vẽ để di chuyển vị trí   •   "
            f"Delete: Xóa nét chọn   |   {MOD_KEY}+C: Sao chép ảnh"
        ),
    },
    "en": {
        # App & Tray
        "app_title": f"Capture To Clipboard v{APP_VERSION}",
        "tray_tooltip": f"Capture To Clipboard v{APP_VERSION} — Click to open Settings & Guide",
        "tray_open_settings": "Settings & Shortcut Guide",
        "tray_autostart": "Launch at system startup",
        "tray_capture_fast": f"Quick Capture ({CAPTURE_HOTKEY_FAST})",
        "tray_capture_draw": f"Capture & Annotate ({CAPTURE_HOTKEY_DRAW})",
        "tray_exit": "Quit Application",
        # Toasts
        "toast_ready": (
            f"Capture To Clipboard is ready  •  {CAPTURE_HOTKEY_FAST} / PrtSc: Quick Capture  |  {CAPTURE_HOTKEY_DRAW}: Capture & Annotate"
        ),
        "toast_minimized_tray": "Capture To Clipboard minimized to the System Tray.",
        "toast_autostart_on": "Enabled launch at system startup.",
        "toast_autostart_off": "Disabled launch at system startup.",
        "toast_prtsc_on": "Enabled instant capture with PrtSc key.",
        "toast_prtsc_off": "Disabled instant capture with PrtSc key.",
        "toast_capture_err": "Failed to capture screen: {err}",
        "toast_copied_fast": "Copied HD screenshot ({w}×{h} px) to Clipboard!",
        "toast_copied_draw": "Copied annotated image ({w}×{h} px) to Clipboard!",
        # Settings Window
        "settings_autostart_title": "Launch at system startup",
        "settings_prtsc_title": "Press PrtSc for instant capture (same as Ctrl + 1)",
        "settings_lang_title": "Display Language (Ngôn ngữ)",
        "status_enabled": "✓ Enabled",
        "status_disabled": "Disabled",
        "header_tagline": "Ultra-sharp screen capture & instant clipboard sharing",
        "header_badge": f"v{APP_VERSION} • Retina HD",
        "guide_section_title": "KEYBOARD SHORTCUTS & QUICK GUIDE",
        "footer_version": f"Version: v{APP_VERSION}",
        "footer_developer": "Developed by KAHUB PLATFORM",
        "table_col_shortcut": "SHORTCUT",
        "table_col_function": "FUNCTION",
        "table_col_desc": "ACTION DESCRIPTION",
        # Overlay
        "overlay_ctrl1_title": f"⚡ {CAPTURE_HOTKEY_FAST} : Drag to select region & copy immediately",
        "overlay_ctrl2_title": f"🎨 {CAPTURE_HOTKEY_DRAW} : Drag to select region & annotate",
        "overlay_banner_hint": "Drag to select region   •   Double-click or Space: Full Screen   •   ESC to cancel",
        # Editor
        "editor_undo": "Undo",
        "editor_redo": "Redo",
        "editor_clear": "Clear All",
        "editor_color_label": "Color:",
        "editor_custom_color": "Custom",
        "editor_custom_color_title": "Choose stroke color",
        "editor_copy_btn": f"Copy ({MOD_KEY}+C)",
        "editor_save_btn": f"Save ({MOD_KEY}+S)",
        "editor_close_btn": "Close (ESC)",
        "editor_save_dialog_title": "Save High-Quality Screenshot",
        "editor_status_bar": (
            "Resolution: {w}×{h} px   •   "
            "Drag any drawn shape to move or resize   •   "
            f"Delete: Remove selected   |   {MOD_KEY}+C: Copy to Clipboard"
        ),
    },
}


SHORTCUTS_GUIDE_I18N: Dict[str, List[Tuple[str, str, str, str, str]]] = {
    "vi": [
        (
            f"{CAPTURE_HOTKEY_FAST} / PrtSc",
            "#0284c7",
            "#e0f2fe",
            "Chụp & Sao chép ngay",
            f"Kéo chọn vùng màn hình để lưu ngay ảnh nét cao vào bộ nhớ tạm (nhấn {MOD_KEY} + V để dán).",
        ),
        (
            CAPTURE_HOTKEY_DRAW,
            "#7c3aed",
            "#f3e8ff",
            "Chụp & Ghi chú trên ảnh",
            "Kéo chọn vùng màn hình và mở bảng vẽ Mũi tên, Khung, Chữ, Bút dạ quang, Làm mờ...",
        ),
        (
            "Kéo giữ chuột",
            "#d97706",
            "#fef3c7",
            "Di chuyển nét đã vẽ",
            "Nhấn giữ vào mũi tên, chữ hoặc khung đã vẽ để dời vị trí hoặc chỉnh lại hướng.",
        ),
        (
            "Nhấp đúp chuột",
            "#db2777",
            "#fce7f3",
            "Sửa nội dung chữ",
            "Nhấp đúp chuột trái vào chữ đã thêm trên ảnh để chỉnh sửa lại nội dung.",
        ),
        (
            f"{MOD_KEY} + C",
            "#059669",
            "#d1fae5",
            "Hoàn tất & Sao chép",
            "Sao chép ảnh đã ghi chú vào bộ nhớ tạm và đóng cửa sổ vẽ.",
        ),
        (
            f"{MOD_KEY} + S",
            "#0369a1",
            "#e0f2fe",
            "Lưu thành file ảnh",
            "Lưu ảnh về máy tính với định dạng PNG, JPG hoặc WebP chất lượng cao.",
        ),
        (
            f"{MOD_KEY} + Z / Delete",
            "#475569",
            "#e2e8f0",
            "Hoàn tác / Xóa nét vẽ",
            f"Nhấn {MOD_KEY} + Z để quay lại bước trước, hoặc nhấn Delete để xóa nét đang chọn.",
        ),
        (
            "ESC / Chuột phải",
            "#dc2626",
            "#fee2e2",
            "Hủy thao tác",
            "Thoát nhanh màn hình chọn vùng chụp hoặc đóng cửa sổ hiện tại.",
        ),
    ],
    "en": [
        (
            f"{CAPTURE_HOTKEY_FAST} / PrtSc",
            "#0284c7",
            "#e0f2fe",
            "Instant Capture & Copy",
            f"Drag to select a screen region and immediately copy HD image to Clipboard ({MOD_KEY} + V to paste).",
        ),
        (
            CAPTURE_HOTKEY_DRAW,
            "#7c3aed",
            "#f3e8ff",
            "Capture & Annotate",
            "Drag to select a region and open the editor with Arrow, Rectangle, Text, Highlighter, Blur...",
        ),
        (
            "Click & Drag",
            "#d97706",
            "#fef3c7",
            "Move / Resize Shapes",
            "Click and drag any drawn arrow, text, or box to reposition or adjust its control handles.",
        ),
        (
            "Double-Click",
            "#db2777",
            "#fce7f3",
            "Edit Text Content",
            "Double-click on any added text annotation on the canvas to edit its content.",
        ),
        (
            f"{MOD_KEY} + C",
            "#059669",
            "#d1fae5",
            "Finish & Copy Image",
            "Copy the annotated image to the Clipboard and close the editor window.",
        ),
        (
            f"{MOD_KEY} + S",
            "#0369a1",
            "#e0f2fe",
            "Save Image to File",
            "Export the annotated screenshot as high-resolution PNG, JPG, or WebP.",
        ),
        (
            f"{MOD_KEY} + Z / Delete",
            "#475569",
            "#e2e8f0",
            "Undo / Delete Shape",
            f"Press {MOD_KEY} + Z to undo the previous step, or press Delete to remove the selected shape.",
        ),
        (
            "ESC / Right-Click",
            "#dc2626",
            "#fee2e2",
            "Cancel Action",
            "Quickly exit the region selection overlay or close the current window.",
        ),
    ],
}


EDITOR_TOOLS_I18N: Dict[str, List[Tuple[str, str]]] = {
    "vi": [
        ("arrow", "Mũi tên"),
        ("pen", "Bút vẽ"),
        ("highlighter", "Dạ quang"),
        ("rect", "Khung"),
        ("ellipse", "Elip"),
        ("line", "Đường thẳng"),
        ("text", "Chèn chữ"),
        ("pixelate", "Làm mờ"),
    ],
    "en": [
        ("arrow", "Arrow"),
        ("pen", "Pen"),
        ("highlighter", "Highlight"),
        ("rect", "Box"),
        ("ellipse", "Ellipse"),
        ("line", "Line"),
        ("text", "Text"),
        ("pixelate", "Blur"),
    ],
}


EDITOR_SIZES_I18N: Dict[str, List[Tuple[int, str, int]]] = {
    "vi": [
        (3, "Nhỏ", 3),
        (5, "Vừa", 5),
        (9, "Lớn", 7),
        (14, "Rất lớn", 9),
    ],
    "en": [
        (3, "Small", 3),
        (5, "Medium", 5),
        (9, "Large", 7),
        (14, "X-Large", 9),
    ],
}


def tr(key: str, **kwargs: Any) -> str:
    """Translate a UI key using the currently active language ('vi' or 'en')."""
    lang = get_language()
    lang_map = TRANSLATIONS.get(lang, TRANSLATIONS["vi"])
    text = lang_map.get(key) or TRANSLATIONS["vi"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def get_shortcuts_guide() -> List[Tuple[str, str, str, str, str]]:
    """Return the shortcut guide table rows for the active language."""
    return SHORTCUTS_GUIDE_I18N.get(get_language(), SHORTCUTS_GUIDE_I18N["vi"])


def get_editor_tools() -> List[Tuple[str, str]]:
    """Return the editor tool definitions for the active language."""
    return EDITOR_TOOLS_I18N.get(get_language(), EDITOR_TOOLS_I18N["vi"])


def get_editor_sizes() -> List[Tuple[int, str, int]]:
    """Return the editor stroke size definitions for the active language."""
    return EDITOR_SIZES_I18N.get(get_language(), EDITOR_SIZES_I18N["vi"])
