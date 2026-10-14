"""Cross-platform Global Hotkey Manager for Ctrl + 1 and Ctrl + 2."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys
import threading
import time
from typing import Callable, Optional, Set

from pynput import keyboard


class GlobalHotkeyManager:
    """Listens globally for Ctrl+1, PrtSc (instant clipboard capture) and Ctrl+2 (capture & draw)."""

    WM_TOGGLE_PRTSC = 0x8001  # WM_APP + 1

    def __init__(
        self,
        on_ctrl_1: Callable[[], None],
        on_ctrl_2: Callable[[], None],
        prtsc_enabled: bool = True,
    ) -> None:
        self.on_ctrl_1 = on_ctrl_1
        self.on_ctrl_2 = on_ctrl_2
        self.prtsc_enabled = prtsc_enabled

        self._running = False
        self._last_trigger_time = 0.0
        self._debounce_seconds = 0.30

        self._win32_thread: Optional[threading.Thread] = None
        self._win32_thread_id: Optional[int] = None
        self._win32_ctrl1_ok = False
        self._win32_ctrl2_ok = False
        self._win32_prtsc_ok = False

        self._listener: Optional[keyboard.Listener] = None
        self._ctrl_pressed = False
        self._alt_pressed = False
        self._shift_pressed = False
        self._active_digits: Set[int] = set()

    def set_prtsc_enabled(self, enabled: bool) -> None:
        """Dynamically enable or disable the PrtSc hotkey at runtime."""
        self.prtsc_enabled = bool(enabled)
        if sys.platform == "win32" and self._win32_thread_id is not None:
            try:
                ctypes.windll.user32.PostThreadMessageW(
                    self._win32_thread_id,
                    self.WM_TOGGLE_PRTSC,
                    1 if self.prtsc_enabled else 0,
                    0,
                )
            except Exception:
                pass

    def _trigger(self, mode: int) -> None:
        now = time.monotonic()
        if now - self._last_trigger_time < self._debounce_seconds:
            return
        self._last_trigger_time = now
        if mode == 1:
            self.on_ctrl_1()
        elif mode == 2:
            self.on_ctrl_2()

    def start(self) -> None:
        """Start listening for global hotkeys."""
        if self._running:
            return
        self._running = True

        if sys.platform == "win32":
            ready_event = threading.Event()
            self._win32_thread = threading.Thread(
                target=self._run_win32_hotkey_loop,
                args=(ready_event,),
                name="Win32HotkeyThread",
                daemon=True,
            )
            self._win32_thread.start()
            ready_event.wait(timeout=1.5)

            if not (self._win32_ctrl1_ok and self._win32_ctrl2_ok and (self._win32_prtsc_ok or not self.prtsc_enabled)):
                self._start_pynput_listener()
        else:
            self._start_pynput_listener()

    def stop(self) -> None:
        """Stop listening and release global hotkeys."""
        self._running = False

        if sys.platform == "win32" and self._win32_thread_id is not None:
            try:
                WM_QUIT = 0x0012
                ctypes.windll.user32.PostThreadMessageW(
                    self._win32_thread_id, WM_QUIT, 0, 0
                )
            except Exception:
                pass

        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _run_win32_hotkey_loop(self, ready_event: threading.Event) -> None:
        """Register Ctrl+1, Ctrl+2, and PrtSc via Win32 API and pump WM_HOTKEY messages."""
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._win32_thread_id = kernel32.GetCurrentThreadId()

        MOD_CONTROL = 0x0002
        MOD_NOREPEAT = 0x4000
        WM_HOTKEY = 0x0312
        VK_SNAPSHOT = 0x2C

        self._win32_ctrl1_ok = bool(
            user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_NOREPEAT, 0x31)
        )
        self._win32_ctrl2_ok = bool(
            user32.RegisterHotKey(None, 2, MOD_CONTROL | MOD_NOREPEAT, 0x32)
        )
        user32.RegisterHotKey(None, 3, MOD_CONTROL | MOD_NOREPEAT, 0x61)
        user32.RegisterHotKey(None, 4, MOD_CONTROL | MOD_NOREPEAT, 0x62)

        if self.prtsc_enabled:
            self._win32_prtsc_ok = bool(
                user32.RegisterHotKey(None, 5, MOD_NOREPEAT, VK_SNAPSHOT)
            )
        else:
            self._win32_prtsc_ok = False

        ready_event.set()

        msg = wintypes.MSG()
        try:
            while self._running:
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0:
                    break
                if msg.message == WM_HOTKEY:
                    hotkey_id = int(msg.wParam)
                    if hotkey_id in (1, 3):
                        self._trigger(1)
                    elif hotkey_id == 5 and self.prtsc_enabled:
                        self._trigger(1)
                    elif hotkey_id in (2, 4):
                        self._trigger(2)
                elif msg.message == self.WM_TOGGLE_PRTSC:
                    want_enable = bool(msg.wParam)
                    if want_enable and not self._win32_prtsc_ok:
                        self._win32_prtsc_ok = bool(
                            user32.RegisterHotKey(None, 5, MOD_NOREPEAT, VK_SNAPSHOT)
                        )
                    elif not want_enable and self._win32_prtsc_ok:
                        try:
                            user32.UnregisterHotKey(None, 5)
                        except Exception:
                            pass
                        self._win32_prtsc_ok = False
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            for hk_id in (1, 2, 3, 4, 5):
                try:
                    user32.UnregisterHotKey(None, hk_id)
                except Exception:
                    pass

    def _start_pynput_listener(self) -> None:
        if self._listener is not None:
            return
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_pynput_press,
                on_release=self._on_pynput_release,
            )
            self._listener.daemon = True
            self._listener.start()
        except Exception as exc:
            print(f"[Warning] Không thể khởi tạo pynput keyboard listener: {exc}")

    @staticmethod
    def _is_ctrl_key(key) -> bool:
        return key in (
            keyboard.Key.ctrl,
            getattr(keyboard.Key, "ctrl_l", None),
            getattr(keyboard.Key, "ctrl_r", None),
        )

    @staticmethod
    def _is_alt_key(key) -> bool:
        return key in (
            keyboard.Key.alt,
            getattr(keyboard.Key, "alt_l", None),
            getattr(keyboard.Key, "alt_r", None),
            getattr(keyboard.Key, "alt_gr", None),
        )

    @staticmethod
    def _is_shift_key(key) -> bool:
        return key in (
            keyboard.Key.shift,
            getattr(keyboard.Key, "shift_l", None),
            getattr(keyboard.Key, "shift_r", None),
        )

    @staticmethod
    def _is_prtsc_key(key) -> bool:
        if key == getattr(keyboard.Key, "print_screen", None):
            return True
        vk = getattr(key, "vk", None)
        return vk == 0x2C

    @staticmethod
    def _detect_digit_1_or_2(key) -> Optional[int]:
        char = getattr(key, "char", None)
        vk = getattr(key, "vk", None)

        if char == "1":
            return 1
        if char == "2":
            return 2

        if sys.platform == "darwin":
            if vk in (18, 83):
                return 1
            if vk in (19, 84):
                return 2
        else:
            if vk in (0x31, 0x61):
                return 1
            if vk in (0x32, 0x62):
                return 2
            if char == "\x00" and vk in (0x32, None):
                return 2

        return None

    def _on_pynput_press(self, key) -> None:
        if self._is_ctrl_key(key):
            self._ctrl_pressed = True
            return
        if self._is_alt_key(key):
            self._alt_pressed = True
            return
        if self._is_shift_key(key):
            self._shift_pressed = True
            return

        if self.prtsc_enabled and self._is_prtsc_key(key) and not self._win32_prtsc_ok:
            self._trigger(1)
            return

        digit = self._detect_digit_1_or_2(key)
        if digit is not None and self._ctrl_pressed and not self._alt_pressed and not self._shift_pressed:
            if digit in self._active_digits:
                return
            self._active_digits.add(digit)
            if digit == 1 and not self._win32_ctrl1_ok:
                self._trigger(1)
            elif digit == 2 and not self._win32_ctrl2_ok:
                self._trigger(2)

    def _on_pynput_release(self, key) -> None:
        if self._is_ctrl_key(key):
            self._ctrl_pressed = False
            self._active_digits.clear()
            return
        if self._is_alt_key(key):
            self._alt_pressed = False
            return
        if self._is_shift_key(key):
            self._shift_pressed = False
            return

        digit = self._detect_digit_1_or_2(key)
        if digit is not None:
            self._active_digits.discard(digit)
