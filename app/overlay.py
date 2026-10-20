from __future__ import annotations

import sys
import tkinter as tk
from typing import Callable, Dict, Optional

from PIL import Image, ImageTk


class ToastNotification:
    """Non-intrusive floating toast notification that auto-dismisses."""

    _active_toast: Optional[tk.Toplevel] = None

    @classmethod
    def show(
        cls,
        root: tk.Tk,
        message: str,
        success: bool = True,
        duration_ms: int = 2000,
    ) -> None:
        if cls._active_toast is not None:
            try:
                cls._active_toast.destroy()
            except Exception:
                pass
            cls._active_toast = None

        toast = tk.Toplevel(root)
        cls._active_toast = toast
        toast.withdraw()
        toast.overrideredirect(True)
        try:
            toast.attributes("-topmost", True)
        except Exception:
            pass

        bg_color = "#ffffff"
        accent_color = "#10b981" if success else "#ef4444"
        fg_color = "#1e293b"
        border_color = "#94a3b8"

        outer = tk.Frame(toast, bg=border_color, padx=1, pady=1)
        outer.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(outer, bg=bg_color)
        inner.pack(fill=tk.BOTH, expand=True)

        stripe = tk.Frame(inner, bg=accent_color, width=6)
        stripe.pack(side=tk.LEFT, fill=tk.Y)

        icon_text = "✓" if success else "!"
        icon_lbl = tk.Label(
            inner,
            text=icon_text,
            font=("Roboto", 12, "bold"),
            fg=accent_color,
            bg=bg_color,
            padx=10,
            pady=10,
        )
        icon_lbl.pack(side=tk.LEFT)

        msg_lbl = tk.Label(
            inner,
            text=message,
            font=("Roboto", 10, "bold"),
            fg=fg_color,
            bg=bg_color,
            padx=4,
            pady=10,
        )
        msg_lbl.pack(side=tk.LEFT)

        pad_right = tk.Frame(inner, bg=bg_color, width=14)
        pad_right.pack(side=tk.LEFT)

        toast.update_idletasks()
        w = toast.winfo_reqwidth()
        h = toast.winfo_reqheight()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()

        x = max(16, screen_w - w - 28)
        y = max(16, screen_h - h - 68)
        toast.geometry(f"{w}x{h}+{x}+{y}")
        toast.deiconify()
        toast.lift()

        def _dismiss(_event=None) -> None:
            if cls._active_toast is toast:
                cls._active_toast = None
            try:
                toast.destroy()
            except Exception:
                pass

        toast.bind("<Button-1>", _dismiss)
        inner.bind("<Button-1>", _dismiss)
        msg_lbl.bind("<Button-1>", _dismiss)
        toast.after(duration_ms, _dismiss)


def _enable_mac_borderless_key_window() -> None:
    """Allow Tkinter borderless overrideredirect window to become Key Window on macOS Aqua/Cocoa."""
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication
        import objc

        for w in NSApplication.sharedApplication().windows():
            cls = w.__class__
            while cls and cls.__name__ != "NSWindow":
                def canBecomeKeyWindow(self):
                    return True

                def canBecomeMainWindow(self):
                    return True

                try:
                    objc.classAddMethods(
                        cls,
                        [
                            objc.selector(canBecomeKeyWindow, selector=b"canBecomeKeyWindow", signature=b"Z@:"),
                            objc.selector(canBecomeMainWindow, selector=b"canBecomeMainWindow", signature=b"Z@:"),
                        ],
                    )
                except Exception:
                    pass
                cls = getattr(cls, "__base__", None)
    except Exception:
        pass


class RegionSelectorOverlay:
    """Fullscreen interactive overlay to drag-and-select a screen region."""

    def __init__(
        self,
        root: tk.Tk,
        screenshot: Image.Image,
        geometry: Dict[str, int],
        mode_title: str,
        accent_color: str,
        on_selected: Callable[[Image.Image], None],
        on_cancel: Optional[Callable[[], None]] = None,
    ) -> None:
        self.root = root
        self.original_screenshot = screenshot
        self.geometry = geometry
        self.mode_title = mode_title
        self.accent_color = accent_color
        self.on_selected = on_selected
        self.on_cancel = on_cancel

        self._closed = False
        self._dragging = False
        self._start_x = 0
        self._start_y = 0
        self._cur_x = 0
        self._cur_y = 0

        self.win_left = int(geometry.get("left", 0))
        self.win_top = int(geometry.get("top", 0))
        self.win_width = int(geometry.get("width", screenshot.width))
        self.win_height = int(geometry.get("height", screenshot.height))

        self.scale_x = screenshot.width / max(1, self.win_width)
        self.scale_y = screenshot.height / max(1, self.win_height)

        if (screenshot.width, screenshot.height) != (self.win_width, self.win_height):
            resized = screenshot.resize(
                (self.win_width, self.win_height), Image.Resampling.LANCZOS
            )
            # If macOS has native ICC profile (Display P3), convert display preview to calibrated sRGB for Tkinter
            icc = screenshot.info.get("icc_profile")
            if icc:
                try:
                    from PIL import ImageCms
                    import io

                    p_in = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                    p_out = ImageCms.createProfile("sRGB")
                    resized = ImageCms.profileToProfile(resized, p_in, p_out, outputMode="RGB")
                except Exception:
                    pass

            try:
                from PIL import ImageFilter

                self.display_image = resized.filter(
                    ImageFilter.UnsharpMask(radius=1.0, percent=130, threshold=1)
                )
            except Exception:
                self.display_image = resized
        else:
            self.display_image = screenshot

        self.display_bright = self.display_image
        lut_rgb = [int(i * 0.78) for i in range(256)]
        lut = (
            lut_rgb * 3 + list(range(256))
            if self.display_bright.mode == "RGBA"
            else lut_rgb * 3
        )
        self.display_dimmed = self.display_bright.point(lut)

        self.top = tk.Toplevel(self.root)
        if sys.platform != "darwin":
            self.top.withdraw()
        self.top.overrideredirect(True)
        try:
            self.top.attributes("-topmost", True)
        except Exception:
            pass

        self.top.geometry(
            f"{self.win_width}x{self.win_height}+{self.win_left}+{self.win_top}"
        )
        self.top.configure(bg="#000000", cursor="none")

        self.canvas = tk.Canvas(
            self.top,
            width=self.win_width,
            height=self.win_height,
            highlightthickness=0,
            bd=0,
            bg="#000000",
            cursor="none",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._tk_dimmed = ImageTk.PhotoImage(self.display_dimmed)
        self._tk_crop_patch: Optional[ImageTk.PhotoImage] = None
        self._patch_after_id: Optional[str] = None
        self._patch_pending: bool = False

        self._bg_image_id = self.canvas.create_image(
            0, 0, anchor=tk.NW, image=self._tk_dimmed
        )
        self._crop_image_id = self.canvas.create_image(
            0, 0, anchor=tk.NW, state="hidden"
        )

        self._rect_id = self.canvas.create_rectangle(
            0, 0, 0, 0, outline=self.accent_color, width=2, state="hidden"
        )
        self._size_bg_id = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#ffffff", outline=self.accent_color, width=1.5, state="hidden"
        )
        self._size_text_id = self.canvas.create_text(
            0,
            0,
            text="",
            fill="#1e293b",
            font=("Roboto", 9, "bold"),
            anchor=tk.NW,
            state="hidden",
        )
        self._handle_ids = [
            self.canvas.create_rectangle(
                0, 0, 0, 0, fill="#ffffff", outline=self.accent_color, width=2, state="hidden"
            )
            for _ in range(4)
        ]

        # Crosshair guide lines — solid for max render speed, initially off-screen
        self._crosshair_h = self.canvas.create_line(
            0, -10, self.win_width, -10,
            fill=self.accent_color, width=1
        )
        self._crosshair_v = self.canvas.create_line(
            -10, 0, -10, self.win_height,
            fill=self.accent_color, width=1
        )

        # Coordinate label near cursor (canvas items with dark pill background & crisp text)
        self._coord_bg_id = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#0f172a", outline=self.accent_color, width=1, state="hidden"
        )
        self._coord_text_id = self.canvas.create_text(
            0, 0, text="", fill="#f8fafc",
            font=("Helvetica Neue", 9, "bold"), anchor=tk.NW, state="hidden"
        )

        # Ensure guide lines and coordinate badge are always on top
        self.canvas.tag_raise(self._crosshair_h)
        self.canvas.tag_raise(self._crosshair_v)
        self.canvas.tag_raise(self._coord_bg_id)
        self.canvas.tag_raise(self._coord_text_id)

        self._draw_top_banner()
        self._bind_events()

        self._mac_esc_monitor = None
        if sys.platform == "darwin":
            try:
                from AppKit import NSEvent, NSEventMaskKeyDown

                def _mac_key_filter(event):
                    k = event.keyCode()
                    if k == 53:  # ESC key on macOS
                        try:
                            self._cancel()
                        except Exception:
                            pass
                        return None
                    elif k in (36, 49) and not self._dragging:  # Return (36) or Space (49)
                        try:
                            self._confirm_or_select_fullscreen()
                        except Exception:
                            pass
                        return None
                    return event

                self._mac_esc_monitor = (
                    NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
                        NSEventMaskKeyDown, _mac_key_filter
                    )
                )
            except Exception:
                pass

        self.top.deiconify()
        self.top.lift()
        self._activate_and_refresh_overlay()

    def _activate_and_refresh_overlay(self) -> None:
        """Ensure macOS Aqua & Windows immediately paint the canvas without waiting for a mouse click."""
        try:
            self.top.update_idletasks()
        except Exception:
            pass

        if sys.platform == "darwin":
            try:
                from AppKit import NSApplication

                app = NSApplication.sharedApplication()
                app.activateIgnoringOtherApps_(True)
                _enable_mac_borderless_key_window()
                for w in app.windows():
                    if w.isVisible():
                        w.makeKeyAndOrderFront_(None)
            except Exception:
                pass

        try:
            self.top.focus_force()
            self.canvas.focus_set()
            self.top.grab_set()
        except Exception:
            pass

    def _draw_top_banner(self) -> None:
        """Top banner disabled to keep the entire screen clean and unobstructed."""
        pass

    def _select_fullscreen(self) -> None:
        """Immediately capture the entire virtual screen at native pixel resolution."""
        if self._closed:
            return
        self._close_window()
        self.on_selected(self.original_screenshot)

    def _confirm_or_select_fullscreen(self) -> None:
        """If a region has been dragged, confirm it; otherwise capture the whole screen."""
        if self._closed:
            return
        x1 = min(self._start_x, self._cur_x)
        y1 = min(self._start_y, self._cur_y)
        x2 = max(self._start_x, self._cur_x)
        y2 = max(self._start_y, self._cur_y)
        if (x2 - x1) >= 5 and (y2 - y1) >= 5:
            px1 = max(0, min(self.original_screenshot.width, int(round(x1 * self.scale_x))))
            py1 = max(0, min(self.original_screenshot.height, int(round(y1 * self.scale_y))))
            px2 = max(0, min(self.original_screenshot.width, int(round(x2 * self.scale_x))))
            py2 = max(0, min(self.original_screenshot.height, int(round(y2 * self.scale_y))))
            if px2 - px1 >= 2 and py2 - py1 >= 2:
                cropped = self.original_screenshot.crop((px1, py1, px2, py2))
                cg_orig = getattr(self.original_screenshot, "cg_image", None)
                if cg_orig is not None:
                    try:
                        import Quartz

                        crop_rect = Quartz.CGRectMake(px1, py1, px2 - px1, py2 - py1)
                        cropped.cg_image = Quartz.CGImageCreateWithImageInRect(cg_orig, crop_rect)
                    except Exception:
                        pass
                self._close_window()
                self.on_selected(cropped)
                return
        self._select_fullscreen()

    def _bind_events(self) -> None:
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Enter>", self._on_mouse_move)
        self.canvas.bind("<Leave>", self._on_mouse_leave)
        self.canvas.bind("<Double-Button-1>", lambda _e: self._select_fullscreen())
        self.canvas.bind("<ButtonPress-2>", self._cancel)
        self.canvas.bind("<ButtonPress-3>", self._cancel)
        self.top.bind("<ButtonPress-2>", self._cancel)
        self.top.bind("<ButtonPress-3>", self._cancel)

        def _on_key_any(event: tk.Event) -> None:
            if (
                event.keysym in ("Escape", "Esc")
                or getattr(event, "keycode", 0) in (53, 27)
                or getattr(event, "char", "") == "\x1b"
            ):
                self._cancel()
            elif event.keysym in ("space", "Return", "KP_Enter") and not self._dragging:
                self._confirm_or_select_fullscreen()

        self.top.bind("<Escape>", self._cancel)
        self.canvas.bind("<Escape>", self._cancel)
        self.top.bind("<Key>", _on_key_any)
        self.canvas.bind("<Key>", _on_key_any)
        try:
            self.root.bind("<Escape>", self._cancel)
            self.root.bind("<Key>", _on_key_any)
        except Exception:
            pass

    def _on_mouse_down(self, event: tk.Event) -> None:
        if self._closed:
            return
        self._dragging = True
        self._start_x = max(0, min(self.win_width, event.x))
        self._start_y = max(0, min(self.win_height, event.y))
        self._cur_x = self._start_x
        self._cur_y = self._start_y
        self.canvas.itemconfigure(self._crop_image_id, state="hidden")
        if self._patch_after_id is not None:
            try:
                self.top.after_cancel(self._patch_after_id)
            except Exception:
                pass
            self._patch_after_id = None
        self._patch_pending = False

        self.canvas.coords(self._crosshair_h, 0, self._start_y, self.win_width, self._start_y)
        self.canvas.coords(self._crosshair_v, self._start_x, 0, self._start_x, self.win_height)
        self._update_coord_label(self._start_x, self._start_y)

    def _on_mouse_move(self, event: tk.Event) -> None:
        """Update crosshair position and coordinate label immediately (0ms latency)."""
        if self._closed or self._dragging:
            return
        x = max(0, min(self.win_width, event.x))
        y = max(0, min(self.win_height, event.y))
        self.canvas.coords(self._crosshair_h, 0, y, self.win_width, y)
        self.canvas.coords(self._crosshair_v, x, 0, x, self.win_height)
        self._update_coord_label(x, y)

    def _on_mouse_leave(self, _event: tk.Event) -> None:
        """Hide crosshair and coordinates when mouse leaves canvas."""
        if self._closed or self._dragging:
            return
        self.canvas.coords(self._crosshair_h, 0, -10, self.win_width, -10)
        self.canvas.coords(self._crosshair_v, -10, 0, -10, self.win_height)
        self.canvas.itemconfigure(self._coord_bg_id, state="hidden")
        self.canvas.itemconfigure(self._coord_text_id, state="hidden")

    def _on_mouse_drag(self, event: tk.Event) -> None:
        """Update selection region and crosshair immediately (0ms latency)."""
        if not self._dragging or self._closed:
            return
        self._cur_x = max(0, min(self.win_width, event.x))
        self._cur_y = max(0, min(self.win_height, event.y))
        x, y = self._cur_x, self._cur_y

        # Update crosshair and coordinate label immediately (0ms latency)
        self.canvas.coords(self._crosshair_h, 0, y, self.win_width, y)
        self.canvas.coords(self._crosshair_v, x, 0, x, self.win_height)
        self._update_coord_label(x, y)

        # Update selection geometry on canvas immediately (0ms latency)
        self._update_selection_geometry()

        # Schedule throttled bright patch update without blocking mouse movement
        if not self._patch_pending:
            self._patch_pending = True
            self._patch_after_id = self.top.after(20, self._render_bright_patch)

    def _update_coord_label(self, x: int, y: int) -> None:
        """Update coordinate text near the cursor on the canvas."""
        phys_x = int(round(x * self.scale_x))
        phys_y = int(round(y * self.scale_y))
        coord_str = f" {phys_x}, {phys_y} "
        # Position: bottom-right of cursor, flip if near edge
        lx = x + 16
        ly = y + 16
        cw = len(coord_str) * 7 + 8
        ch = 20
        if lx + cw > self.win_width - 8:
            lx = x - cw - 12
        if ly + ch > self.win_height - 8:
            ly = y - ch - 12
        self.canvas.coords(self._coord_bg_id, lx, ly, lx + cw, ly + ch)
        self.canvas.itemconfigure(self._coord_bg_id, state="normal")
        self.canvas.coords(self._coord_text_id, lx + 4, ly + 2)
        self.canvas.itemconfigure(self._coord_text_id, text=coord_str, state="normal")

    def _update_selection_geometry(self) -> None:
        """Update selection border, handles, and resolution badge with zero latency (120 FPS)."""
        x1 = min(self._start_x, self._cur_x)
        y1 = min(self._start_y, self._cur_y)
        x2 = max(self._start_x, self._cur_x)
        y2 = max(self._start_y, self._cur_y)

        if x2 - x1 < 3 or y2 - y1 < 3:
            self.canvas.itemconfigure(self._crop_image_id, state="hidden")
            self.canvas.itemconfigure(self._rect_id, state="hidden")
            self.canvas.itemconfigure(self._size_bg_id, state="hidden")
            self.canvas.itemconfigure(self._size_text_id, state="hidden")
            for h_id in self._handle_ids:
                self.canvas.itemconfigure(h_id, state="hidden")
            return

        self.canvas.coords(self._rect_id, x1, y1, x2, y2)
        self.canvas.itemconfigure(self._rect_id, state="normal")

        r = 4
        corners = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
        for h_id, (cx, cy) in zip(self._handle_ids, corners):
            self.canvas.coords(h_id, cx - r, cy - r, cx + r, cy + r)
            self.canvas.itemconfigure(h_id, state="normal")

        phys_w = max(1, int(round((x2 - x1) * self.scale_x)))
        phys_h = max(1, int(round((y2 - y1) * self.scale_y)))
        label_str = f" {phys_w} × {phys_h} px "

        badge_x = x1
        badge_y = y1 - 26 if y1 >= 30 else y2 + 8
        self.canvas.coords(self._size_text_id, badge_x + 8, badge_y + 3)
        self.canvas.itemconfigure(self._size_text_id, text=label_str, state="normal")

        # Fast direct coordinate calculation for badge background without slow canvas.bbox()
        badge_w = len(label_str) * 7 + 16
        badge_h = 20
        self.canvas.coords(
            self._size_bg_id,
            badge_x,
            badge_y,
            badge_x + badge_w,
            badge_y + badge_h,
        )
        self.canvas.itemconfigure(self._size_bg_id, state="normal")

    def _render_bright_patch(self) -> None:
        """Render the bright un-dimmed region patch at a paced refresh rate (~50 FPS)."""
        self._patch_pending = False
        self._patch_after_id = None
        if not self._dragging or self._closed:
            return

        x1 = min(self._start_x, self._cur_x)
        y1 = min(self._start_y, self._cur_y)
        x2 = max(self._start_x, self._cur_x)
        y2 = max(self._start_y, self._cur_y)

        if x2 - x1 < 5 or y2 - y1 < 5:
            self.canvas.itemconfigure(self._crop_image_id, state="hidden")
            return

        try:
            patch = self.display_bright.crop((x1, y1, x2, y2))
            self._tk_crop_patch = ImageTk.PhotoImage(patch)
            self.canvas.coords(self._crop_image_id, x1, y1)
            self.canvas.itemconfigure(self._crop_image_id, image=self._tk_crop_patch, state="normal")
            self.canvas.tag_lower(self._crop_image_id, self._rect_id)
        except Exception:
            pass

    def _on_mouse_up(self, event: tk.Event) -> None:
        if not self._dragging or self._closed:
            return
        self._dragging = False
        if self._patch_after_id is not None:
            try:
                self.top.after_cancel(self._patch_after_id)
            except Exception:
                pass
            self._patch_after_id = None
        self._patch_pending = False
        self._cur_x = max(0, min(self.win_width, event.x))
        self._cur_y = max(0, min(self.win_height, event.y))

        x1 = min(self._start_x, self._cur_x)
        y1 = min(self._start_y, self._cur_y)
        x2 = max(self._start_x, self._cur_x)
        y2 = max(self._start_y, self._cur_y)

        if (x2 - x1) < 5 or (y2 - y1) < 5:
            self.canvas.itemconfigure("banner", state="normal")
            return

        px1 = max(0, min(self.original_screenshot.width, int(round(x1 * self.scale_x))))
        py1 = max(0, min(self.original_screenshot.height, int(round(y1 * self.scale_y))))
        px2 = max(0, min(self.original_screenshot.width, int(round(x2 * self.scale_x))))
        py2 = max(0, min(self.original_screenshot.height, int(round(y2 * self.scale_y))))

        if px2 - px1 < 2 or py2 - py1 < 2:
            self._cancel()
            return

        cropped = self.original_screenshot.crop((px1, py1, px2, py2))
        cg_orig = getattr(self.original_screenshot, "cg_image", None)
        if cg_orig is not None:
            try:
                import Quartz

                crop_rect = Quartz.CGRectMake(px1, py1, px2 - px1, py2 - py1)
                cropped.cg_image = Quartz.CGImageCreateWithImageInRect(cg_orig, crop_rect)
            except Exception:
                pass
        self._close_window()
        self.on_selected(cropped)

    def _cancel(self, _event=None) -> None:
        if self._closed:
            return
        self._close_window()
        if self.on_cancel is not None:
            self.on_cancel()

    def _close_window(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._patch_after_id is not None:
            try:
                self.top.after_cancel(self._patch_after_id)
            except Exception:
                pass
            self._patch_after_id = None
        self._patch_pending = False
        if self._mac_esc_monitor is not None:
            try:
                from AppKit import NSEvent

                NSEvent.removeMonitor_(self._mac_esc_monitor)
            except Exception:
                pass
            self._mac_esc_monitor = None
        try:
            self.top.grab_release()
        except Exception:
            pass
        try:
            self.top.destroy()
            self.root.update_idletasks()
        except Exception:
            pass
