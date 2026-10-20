"""Cross-platform Global Hotkey Manager for Ctrl + 1 and Ctrl + 2."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys
import threading
import time
from typing import Any, Callable, Optional, Set

from pynput import keyboard


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


_LRESULT = ctypes.c_ssize_t
_WIN_FUNCTYPE = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
_HOOKPROC = _WIN_FUNCTYPE(
    _LRESULT,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


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
        self._win32_ll_hook_ok = False
        self._ll_hook_proc_ref: Optional[Any] = None

        self._listener: Optional[keyboard.Listener] = None
        self._ctrl_pressed = False
        self._cmd_pressed = False
        self._alt_pressed = False
        self._shift_pressed = False
        self._active_digits: Set[int] = set()
        self._overlay_cancel_handler: Optional[Callable[[], None]] = None

    def set_overlay_cancel_handler(self, handler: Optional[Callable[[], None]]) -> None:
        """Register a callback to cancel an active fullscreen overlay when ESC is pressed."""
        self._overlay_cancel_handler = handler

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

            if not (
                self._win32_ctrl1_ok
                and self._win32_ctrl2_ok
                and (self._win32_ll_hook_ok or self._win32_prtsc_ok)
            ):
                self._start_pynput_listener()
        else:
            if sys.platform == "darwin":
                self._check_macos_accessibility()
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
        """Register Ctrl+1, Ctrl+2, PrtSc, and WH_KEYBOARD_LL hook via Win32 API."""
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._win32_thread_id = kernel32.GetCurrentThreadId()

        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            _HOOKPROC,
            wintypes.HINSTANCE,
            wintypes.DWORD,
        ]
        user32.SetWindowsHookExW.restype = wintypes.HHOOK
        user32.CallNextHookEx.argtypes = [
            wintypes.HHOOK,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.CallNextHookEx.restype = _LRESULT
        user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        user32.GetAsyncKeyState.restype = wintypes.SHORT
        user32.SetTimer.argtypes = [
            wintypes.HWND,
            ctypes.c_size_t,
            wintypes.UINT,
            ctypes.c_void_p,
        ]
        user32.SetTimer.restype = ctypes.c_size_t
        user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
        user32.KillTimer.restype = wintypes.BOOL

        MOD_CONTROL = 0x0002
        MOD_NOREPEAT = 0x4000
        WM_HOTKEY = 0x0312
        WM_TIMER = 0x0113
        VK_SNAPSHOT = 0x2C
        WH_KEYBOARD_LL = 13
        WM_KEYDOWN = 0x0100
        WM_KEYUP = 0x0101
        WM_SYSKEYDOWN = 0x0104
        WM_SYSKEYUP = 0x0105

        self._win32_ctrl1_ok = bool(
            user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_NOREPEAT, 0x31)
        )
        self._win32_ctrl2_ok = bool(
            user32.RegisterHotKey(None, 2, MOD_CONTROL | MOD_NOREPEAT, 0x32)
        )
        user32.RegisterHotKey(None, 3, MOD_CONTROL | MOD_NOREPEAT, 0x61)
        user32.RegisterHotKey(None, 4, MOD_CONTROL | MOD_NOREPEAT, 0x62)

        def _register_prtsc_hotkeys() -> bool:
            ok_norepeat = bool(
                user32.RegisterHotKey(None, 5, MOD_NOREPEAT, VK_SNAPSHOT)
            )
            ok_plain = bool(
                user32.RegisterHotKey(None, 6, 0, VK_SNAPSHOT)
            )
            return ok_norepeat or ok_plain

        def _unregister_prtsc_hotkeys() -> None:
            for hk_id in (5, 6):
                try:
                    user32.UnregisterHotKey(None, hk_id)
                except Exception:
                    pass

        if self.prtsc_enabled:
            self._win32_prtsc_ok = _register_prtsc_hotkeys()
        else:
            self._win32_prtsc_ok = False

        hook_handle: Optional[int] = None

        def _ll_keyboard_callback(
            n_code: int, w_param: int, l_param: int
        ) -> int:
            if n_code >= 0 and l_param:
                try:
                    kb = _KBDLLHOOKSTRUCT.from_address(l_param)
                    vk = kb.vkCode
                    scan = kb.scanCode
                    flags = kb.flags
                    is_prtsc = (vk == VK_SNAPSHOT) or (
                        scan == 0x37 and bool(flags & 0x01)
                    )
                    if is_prtsc and self.prtsc_enabled:
                        win_down = bool(
                            (user32.GetAsyncKeyState(0x5B) & 0x8000)
                            or (user32.GetAsyncKeyState(0x5C) & 0x8000)
                        )
                        alt_down = bool(user32.GetAsyncKeyState(0x12) & 0x8000)
                        if not win_down and not alt_down:
                            if w_param in (
                                WM_KEYDOWN,
                                WM_SYSKEYDOWN,
                                WM_KEYUP,
                                WM_SYSKEYUP,
                            ):
                                self._trigger(1)
                                return 1
                except Exception:
                    pass
            return user32.CallNextHookEx(hook_handle, n_code, w_param, l_param)

        self._ll_hook_proc_ref = _HOOKPROC(_ll_keyboard_callback)
        hmod = kernel32.GetModuleHandleW(None)
        hook_handle = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._ll_hook_proc_ref,
            hmod,
            0,
        )
        self._win32_ll_hook_ok = bool(hook_handle)

        # Clear any stale async state bit for VK_SNAPSHOT and start a 25ms fallback timer
        user32.GetAsyncKeyState(VK_SNAPSHOT)
        prev_prtsc_down = False
        timer_id = user32.SetTimer(None, 0, 25, None)

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
                    elif hotkey_id in (5, 6) and self.prtsc_enabled:
                        self._trigger(1)
                    elif hotkey_id in (2, 4):
                        self._trigger(2)
                elif msg.message == WM_TIMER:
                    if self.prtsc_enabled:
                        state = user32.GetAsyncKeyState(VK_SNAPSHOT)
                        is_down = bool(state & 0x8000)
                        was_pressed = bool(state & 0x0001)
                        if (is_down or was_pressed) and not prev_prtsc_down:
                            win_down = bool(
                                (user32.GetAsyncKeyState(0x5B) & 0x8000)
                                or (user32.GetAsyncKeyState(0x5C) & 0x8000)
                            )
                            alt_down = bool(user32.GetAsyncKeyState(0x12) & 0x8000)
                            if not win_down and not alt_down:
                                self._trigger(1)
                        prev_prtsc_down = is_down
                    else:
                        prev_prtsc_down = False
                elif msg.message == self.WM_TOGGLE_PRTSC:
                    want_enable = bool(msg.wParam)
                    user32.GetAsyncKeyState(VK_SNAPSHOT)
                    prev_prtsc_down = False
                    if want_enable and not self._win32_prtsc_ok:
                        self._win32_prtsc_ok = _register_prtsc_hotkeys()
                    elif not want_enable and self._win32_prtsc_ok:
                        _unregister_prtsc_hotkeys()
                        self._win32_prtsc_ok = False
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            if timer_id:
                try:
                    user32.KillTimer(None, timer_id)
                except Exception:
                    pass
            if hook_handle:
                try:
                    user32.UnhookWindowsHookEx(hook_handle)
                except Exception:
                    pass
            self._win32_ll_hook_ok = False
            for hk_id in (1, 2, 3, 4, 5, 6):
                try:
                    user32.UnregisterHotKey(None, hk_id)
                except Exception:
                    pass

    @staticmethod
    def _check_macos_accessibility() -> None:
        try:
            import ApplicationServices

            if not ApplicationServices.AXIsProcessTrusted():
                ApplicationServices.AXIsProcessTrustedWithOptions(
                    {ApplicationServices.kAXTrustedCheckOptionPrompt: True}
                )
        except Exception:
            pass

    def _darwin_event_intercept(self, event_type, event):
        """Intercept Ctrl + 1 and Ctrl + 2 at Quartz level on macOS.

        Consumes the event (returns None) so active apps do not receive
        or conflict with the shortcut, giving priority to Capture To Clipboard.
        Cmd + 1 and Cmd + 2 are preserved untouched for web browsers (tab switching)
        and native macOS applications.
        """
        try:
            import Quartz

            if event_type == Quartz.kCGEventKeyDown:
                keycode = Quartz.CGEventGetIntegerValueField(
                    event, Quartz.kCGKeyboardEventKeycode
                )
                # 53: Escape key on macOS
                if keycode == 53 and self._overlay_cancel_handler is not None:
                    try:
                        self._overlay_cancel_handler()
                    except Exception:
                        pass
                    return None

            flags = Quartz.CGEventGetFlags(event)
            is_cmd = bool(flags & Quartz.kCGEventFlagMaskCommand)
            is_alt = bool(flags & Quartz.kCGEventFlagMaskAlternate)
            is_shift = bool(flags & Quartz.kCGEventFlagMaskShift)
            is_ctrl = bool(flags & Quartz.kCGEventFlagMaskControl)

            # Only intercept Control + 1 / Control + 2 (never touch Command to avoid browser tab conflicts)
            if is_ctrl and not is_cmd and not is_alt and not is_shift:
                keycode = Quartz.CGEventGetIntegerValueField(
                    event, Quartz.kCGKeyboardEventKeycode
                )
                # 18: '1', 83: Numpad 1
                if keycode in (18, 83):
                    if event_type == Quartz.kCGEventKeyDown:
                        self._trigger(1)
                    return None
                # 19: '2', 84: Numpad 2
                elif keycode in (19, 84):
                    if event_type == Quartz.kCGEventKeyDown:
                        self._trigger(2)
                    return None
        except Exception:
            pass
        return event

    def _start_pynput_listener(self) -> None:
        if self._listener is not None:
            return
        try:
            kwargs = {
                "on_press": self._on_pynput_press,
                "on_release": self._on_pynput_release,
            }
            if sys.platform == "darwin":
                kwargs["intercept"] = self._darwin_event_intercept

            self._listener = keyboard.Listener(**kwargs)
            self._listener.daemon = True
            self._listener.start()
        except Exception as exc:
            print(f"[Warning] Không thể khởi tạo pynput keyboard listener: {exc}")

    @staticmethod
    def _is_cmd_key(key) -> bool:
        return key in (
            keyboard.Key.cmd,
            getattr(keyboard.Key, "cmd_l", None),
            getattr(keyboard.Key, "cmd_r", None),
        )

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
        if key == keyboard.Key.esc and self._overlay_cancel_handler is not None:
            try:
                self._overlay_cancel_handler()
            except Exception:
                pass
            return

        if self._is_cmd_key(key):
            self._cmd_pressed = True
            return
        if self._is_ctrl_key(key):
            self._ctrl_pressed = True
            return
        if self._is_alt_key(key):
            self._alt_pressed = True
            return
        if self._is_shift_key(key):
            self._shift_pressed = True
            return

        if (
            self.prtsc_enabled
            and self._is_prtsc_key(key)
            and not (self._win32_ll_hook_ok or self._win32_prtsc_ok)
        ):
            self._trigger(1)
            return

        digit = self._detect_digit_1_or_2(key)
        if digit is not None:
            # Globally across macOS, Windows, Linux: Ctrl + 1 / Ctrl + 2
            if self._ctrl_pressed and not self._cmd_pressed and not self._alt_pressed and not self._shift_pressed:
                if digit in self._active_digits:
                    return
                self._active_digits.add(digit)
                if digit == 1 and not self._win32_ctrl1_ok:
                    self._trigger(1)
                elif digit == 2 and not self._win32_ctrl2_ok:
                    self._trigger(2)

    def _on_pynput_release(self, key) -> None:
        if self._is_cmd_key(key):
            self._cmd_pressed = False
            self._active_digits.clear()
            return
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

        if (
            self.prtsc_enabled
            and self._is_prtsc_key(key)
            and not (self._win32_ll_hook_ok or self._win32_prtsc_ok)
        ):
            self._trigger(1)
            return

        digit = self._detect_digit_1_or_2(key)
        if digit is not None:
            self._active_digits.discard(digit)
