"""Main Entry Point for Capture-to-Clipboard Cross-Platform App (Windows, macOS, Linux).

Hotkeys:
  - Ctrl + 1 : Select screen region -> Enhance HD quality & immediately copy to Clipboard
  - Ctrl + 2 : Select screen region -> Open polished HD annotation/drawing editor window
Tray Icon:
  - Click Tray Icon -> Open Settings (Auto-start on boot checkbox) & Shortcut Guide window
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import queue
import signal
import sys
import tkinter as tk
from typing import Optional, Tuple

from PIL import Image, ImageTk

from app.autostart import (
    is_autostart_enabled,
    is_prtsc_enabled,
    set_autostart_enabled,
    sync_autostart_on_startup,
)
from app.editor import AnnotationEditor
from app.hotkeys import GlobalHotkeyManager
from app.overlay import RegionSelectorOverlay, ToastNotification
from app.platform_utils import (
    capture_virtual_screen,
    copy_image_to_clipboard,
    enable_dpi_awareness,
    enhance_image_quality,
)
from app.settings_window import SettingsAndGuideWindow
from app.tray import (
    SystemTrayController,
    apply_window_icon,
)

_SINGLE_INSTANCE_MUTEX: Optional[int] = None
_SHOW_SETTINGS_EVENT: Optional[int] = None


class CaptureApp:
    """Coordinates the hidden Tkinter main loop, System Tray, Settings Window, and Global Hotkeys."""

    def __init__(self) -> None:
        enable_dpi_awareness()
        sync_autostart_on_startup()
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "CaptureToClipboard.HD.App"
                )
            except Exception:
                pass

        from app.i18n import APP_NAME

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_NAME)
        apply_window_icon(self.root)

        self.event_queue: "queue.Queue[Tuple[str, bool]]" = queue.Queue()
        self._overlay_active = False
        self._active_editor: Optional[AnnotationEditor] = None
        self._shutting_down = False

        self.settings_window = SettingsAndGuideWindow(
            root=self.root,
            on_trigger_ctrl1=lambda: self.event_queue.put(("capture_clipboard", True)),
            on_trigger_ctrl2=lambda: self.event_queue.put(("capture_draw", True)),
            on_autostart_changed=self._on_autostart_changed_from_ui,
            on_prtsc_changed=self._on_prtsc_changed_from_ui,
            on_language_changed=self._on_language_changed_from_ui,
            on_minimized_to_tray=self._on_window_minimized_to_tray,
        )

        self.hotkeys = GlobalHotkeyManager(
            on_ctrl_1=lambda: self.event_queue.put(("capture_clipboard", False)),
            on_ctrl_2=lambda: self.event_queue.put(("capture_draw", False)),
            prtsc_enabled=is_prtsc_enabled(),
        )
        self.tray = SystemTrayController(
            on_open_settings=lambda: self.event_queue.put(("open_settings", False)),
            on_toggle_autostart=lambda: self.event_queue.put(("toggle_autostart", False)),
            on_capture_clipboard=lambda: self.event_queue.put(("capture_clipboard", True)),
            on_capture_draw=lambda: self.event_queue.put(("capture_draw", True)),
            on_exit=lambda: self.event_queue.put(("exit", False)),
        )

    def start(self, minimized: bool = False) -> None:
        """Start background services and enter the main GUI event loop."""
        from app.i18n import tr

        self.hotkeys.start()
        self.tray.start()

        for delay_ms in (1500, 4000, 8000):
            self.root.after(delay_ms, self.tray.ensure_visible)

        try:
            signal.signal(signal.SIGINT, lambda *_: self.event_queue.put(("exit", False)))
        except Exception:
            pass

        toast_delay = 1200 if minimized else 200
        self.root.after(
            toast_delay,
            lambda: ToastNotification.show(
                self.root,
                tr("toast_ready"),
                success=True,
                duration_ms=2800,
            ),
        )

        self.root.after(30, self._poll_events)
        self.root.mainloop()

    def _poll_events(self) -> None:
        if self._shutting_down:
            return

        if sys.platform == "win32" and _SHOW_SETTINGS_EVENT:
            try:
                import ctypes

                if ctypes.windll.kernel32.WaitForSingleObject(_SHOW_SETTINGS_EVENT, 0) == 0:
                    ctypes.windll.kernel32.ResetEvent(_SHOW_SETTINGS_EVENT)
                    self.event_queue.put(("open_settings", False))
            except Exception:
                pass

        try:
            while True:
                action, from_tray = self.event_queue.get_nowait()
                try:
                    if action == "exit":
                        self.shutdown()
                        return
                    elif action == "open_settings":
                        self.settings_window.show()
                    elif action == "toggle_autostart":
                        new_state = not is_autostart_enabled()
                        ok, msg = set_autostart_enabled(new_state)
                        self.tray.refresh_menu()
                        ToastNotification.show(
                            self.root,
                            msg,
                            success=ok,
                            duration_ms=2000,
                        )
                    elif action == "capture_clipboard":
                        delay = 180 if from_tray else 10
                        self.root.after(delay, lambda: self._begin_capture(mode=1))
                    elif action == "capture_draw":
                        delay = 180 if from_tray else 10
                        self.root.after(delay, lambda: self._begin_capture(mode=2))
                except Exception as exc:
                    print(f"[Error] Event '{action}' failed: {exc}")
        except queue.Empty:
            pass

        if not self._shutting_down:
            self.root.after(30, self._poll_events)

    def _on_autostart_changed_from_ui(self, enabled: bool) -> None:
        from app.i18n import tr

        self.tray.refresh_menu()
        msg = tr("toast_autostart_on") if enabled else tr("toast_autostart_off")
        ToastNotification.show(self.root, msg, success=True, duration_ms=1800)

    def _on_prtsc_changed_from_ui(self, enabled: bool) -> None:
        from app.i18n import tr

        self.hotkeys.set_prtsc_enabled(enabled)
        msg = tr("toast_prtsc_on") if enabled else tr("toast_prtsc_off")
        ToastNotification.show(self.root, msg, success=True, duration_ms=1800)

    def _on_language_changed_from_ui(self, _lang: str) -> None:
        self.tray.refresh_menu()

    def _on_window_minimized_to_tray(self) -> None:
        from app.i18n import tr

        ToastNotification.show(
            self.root,
            tr("toast_minimized_tray"),
            success=True,
            duration_ms=1800,
        )

    def _begin_capture(self, mode: int) -> None:
        if self._overlay_active or self._shutting_down:
            return

        was_settings_visible = self.settings_window.is_visible()
        self.settings_window.close()
        self._overlay_active = True
        if was_settings_visible:
            try:
                self.root.update_idletasks()
            except Exception:
                pass
            self.root.after(65, lambda: self._execute_capture(mode))
        else:
            self._execute_capture(mode)

    def _execute_capture(self, mode: int) -> None:
        from app.i18n import tr

        if self._shutting_down:
            self._overlay_active = False
            return

        try:
            screenshot, geom = capture_virtual_screen(self.root)
        except Exception as exc:
            self._overlay_active = False
            ToastNotification.show(
                self.root,
                tr("toast_capture_err", err=exc),
                success=False,
                duration_ms=3000,
            )
            return

        if mode == 1:
            mode_title = tr("overlay_ctrl1_title")
            accent = "#0284c7"
            on_done = self._handle_instant_clipboard
        else:
            mode_title = tr("overlay_ctrl2_title")
            accent = "#7c3aed"
            on_done = self._handle_open_editor

        RegionSelectorOverlay(
            root=self.root,
            screenshot=screenshot,
            geometry=geom,
            mode_title=mode_title,
            accent_color=accent,
            on_selected=on_done,
            on_cancel=self._on_overlay_cancelled,
        )

    def _on_overlay_cancelled(self) -> None:
        self._overlay_active = False

    def _handle_instant_clipboard(self, cropped_img: Image.Image) -> None:
        from app.i18n import tr

        self._overlay_active = False
        hd_img = enhance_image_quality(cropped_img, upscale_hd=True)
        ok, msg = copy_image_to_clipboard(hd_img)
        if ok:
            ToastNotification.show(
                self.root,
                tr("toast_copied_fast", w=hd_img.width, h=hd_img.height),
                success=True,
                duration_ms=2000,
            )
        else:
            ToastNotification.show(
                self.root,
                msg,
                success=False,
                duration_ms=3200,
            )

    def _handle_open_editor(self, cropped_img: Image.Image) -> None:
        self._overlay_active = False
        if self._active_editor is not None:
            try:
                self._active_editor.close_editor()
            except Exception:
                pass
            self._active_editor = None

        logical_size = cropped_img.size
        hd_img = enhance_image_quality(cropped_img, upscale_hd=True)

        self._active_editor = AnnotationEditor(
            root=self.root,
            image=hd_img,
            logical_size=logical_size,
            on_copy_clipboard=self._handle_editor_copy,
            on_close=self._on_editor_closed,
        )

    def _handle_editor_copy(self, edited_img: Image.Image) -> None:
        from app.i18n import tr

        self._active_editor = None
        ok, msg = copy_image_to_clipboard(edited_img)
        if ok:
            ToastNotification.show(
                self.root,
                tr("toast_copied_draw", w=edited_img.width, h=edited_img.height),
                success=True,
                duration_ms=2200,
            )
        else:
            ToastNotification.show(
                self.root,
                msg,
                success=False,
                duration_ms=3200,
            )

    def _on_editor_closed(self) -> None:
        self._active_editor = None

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        try:
            self.settings_window.close(destroy=True)
        except Exception:
            pass
        try:
            self.hotkeys.stop()
        except Exception:
            pass
        try:
            self.tray.stop()
        except Exception:
            pass
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass


def run_self_test() -> int:
    print("[Self-Test] 1. Kiểm tra tạo icon System Tray...")
    from app.tray import create_tray_icon_image

    icon_img = create_tray_icon_image(64)
    assert icon_img.size == (64, 64), "Icon size mismatch"
    print("  -> OK")

    print("[Self-Test] 2. Kiểm tra giữ nguyên chất lượng ảnh gốc Lossless 1:1 & copy vào Clipboard...")
    test_img = Image.new("RGB", (240, 120), (37, 99, 235))
    hd_img = enhance_image_quality(test_img, upscale_hd=True)
    assert hd_img.size == (240, 120), f"Expected (240, 120), got {hd_img.size}"
    ok, msg = copy_image_to_clipboard(hd_img)
    print(f"  -> {ok}: {msg} (Size: {hd_img.size})")

    print("[Self-Test] 3. Kiểm tra đăng ký phím tắt Ctrl+1 và Ctrl+2...")
    hk = GlobalHotkeyManager(on_ctrl_1=lambda: None, on_ctrl_2=lambda: None)
    hk.start()
    hk.stop()
    print("  -> OK")

    print("[Self-Test] 4. Kiểm tra trạng thái Autostart & cửa sổ Cài đặt...")
    auto_state = is_autostart_enabled()
    print(f"  -> Autostart hiện tại: {auto_state}")
    print("[Self-Test] Hoàn tất thành công!")
    return 0


def _ensure_single_instance(minimized: bool) -> bool:
    """Ensure only one instance runs. If already running and not --minimized, signal it to open settings."""
    global _SINGLE_INSTANCE_MUTEX, _SHOW_SETTINGS_EVENT
    if sys.platform != "win32":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        _SHOW_SETTINGS_EVENT = kernel32.CreateEventW(
            None, True, False, "Local\\CaptureToClipboard_ShowSettings_Event"
        )
        _SINGLE_INSTANCE_MUTEX = kernel32.CreateMutexW(
            None, False, "Local\\CaptureToClipboard_SingleInstance_Mutex"
        )
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            if not minimized and _SHOW_SETTINGS_EVENT:
                kernel32.SetEvent(_SHOW_SETTINGS_EVENT)
            return False
    except Exception:
        pass
    return True


def main() -> int:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    try:
        app_dir = (
            Path(sys.executable).resolve().parent
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent
        )
        os.chdir(app_dir)
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Capture to Clipboard - Ứng dụng chụp màn hình HD đa nền tảng (Windows, macOS, Linux)"
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Chạy kiểm tra tự động các thành phần của ứng dụng rồi thoát",
    )
    parser.add_argument(
        "--show-settings",
        action="store_true",
        help="Mở ngay cửa sổ Cài đặt & Hướng dẫn khi khởi động",
    )
    parser.add_argument(
        "--minimized",
        action="store_true",
        help="Khởi động thu gọn trên khay hệ thống (dùng khi khởi động cùng máy tính)",
    )
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    if not _ensure_single_instance(minimized=args.minimized):
        return 0

    app = CaptureApp()
    if args.show_settings or not args.minimized:
        app.event_queue.put(("open_settings", False))
    app.start(minimized=args.minimized)
    return 0


if __name__ == "__main__":
    sys.exit(main())
