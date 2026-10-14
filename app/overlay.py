"""Fullscreen Region Selection Overlay and Toast Notification UI."""

from __future__ import annotations

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
            self.display_bright = screenshot.resize(
                (self.win_width, self.win_height), Image.Resampling.LANCZOS
            )
        else:
            self.display_bright = screenshot

        self.display_dimmed = self.display_bright.point(lambda p: int(p * 0.52))

        self.top = tk.Toplevel(self.root)
        self.top.withdraw()
        self.top.overrideredirect(True)
        try:
            self.top.attributes("-topmost", True)
        except Exception:
            pass

        self.top.geometry(
            f"{self.win_width}x{self.win_height}+{self.win_left}+{self.win_top}"
        )
        self.top.configure(bg="#000000", cursor="crosshair")

        self.canvas = tk.Canvas(
            self.top,
            width=self.win_width,
            height=self.win_height,
            highlightthickness=0,
            bd=0,
            bg="#000000",
            cursor="crosshair",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._tk_dimmed = ImageTk.PhotoImage(self.display_dimmed)
        self._tk_crop_patch: Optional[ImageTk.PhotoImage] = None

        self.canvas.create_image(0, 0, anchor=tk.NW, image=self._tk_dimmed)

        self._crop_image_id = self.canvas.create_image(0, 0, anchor=tk.NW, state="hidden")
        self._guide_h_id = self.canvas.create_line(
            0, 0, 0, 0, fill="#cbd5e1", dash=(3, 3), width=1
        )
        self._guide_v_id = self.canvas.create_line(
            0, 0, 0, 0, fill="#cbd5e1", dash=(3, 3), width=1
        )
        self._rect_id = self.canvas.create_rectangle(
            0, 0, 0, 0, outline=self.accent_color, width=2, state="hidden"
        )
        self._size_bg_id = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#ffffff", outline=self.accent_color, width=1, state="hidden"
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

        self._draw_top_banner()
        self._bind_events()

        self.top.deiconify()
        self.top.lift()
        try:
            self.top.focus_force()
            self.canvas.focus_set()
            self.top.grab_set()
        except Exception:
            pass

    def _draw_top_banner(self) -> None:
        from app.i18n import tr

        cx = self.win_width // 2
        y = 30
        banner_text = f"  {self.mode_title}   •   {tr('overlay_banner_hint')}  "
        text_id = self.canvas.create_text(
            cx,
            y,
            text=banner_text,
            fill="#1e293b",
            font=("Roboto", 10, "bold"),
            tags=("banner",),
        )
        bbox = self.canvas.bbox(text_id)
        if bbox:
            pad_x, pad_y = 14, 8
            bg_id = self.canvas.create_rectangle(
                bbox[0] - pad_x,
                bbox[1] - pad_y,
                bbox[2] + pad_x,
                bbox[3] + pad_y,
                fill="#f8fafc",
                outline=self.accent_color,
                width=2,
                tags=("banner",),
            )
            self.canvas.tag_lower(bg_id, text_id)

    def _bind_events(self) -> None:
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<ButtonPress-2>", self._cancel)
        self.canvas.bind("<ButtonPress-3>", self._cancel)
        self.top.bind("<Escape>", self._cancel)
        self.canvas.bind("<Escape>", self._cancel)

    def _on_mouse_move(self, event: tk.Event) -> None:
        if self._dragging or self._closed:
            return
        x, y = event.x, event.y
        self.canvas.coords(self._guide_h_id, 0, y, self.win_width, y)
        self.canvas.coords(self._guide_v_id, x, 0, x, self.win_height)

    def _on_mouse_down(self, event: tk.Event) -> None:
        if self._closed:
            return
        self._dragging = True
        self._start_x = max(0, min(self.win_width, event.x))
        self._start_y = max(0, min(self.win_height, event.y))
        self._cur_x = self._start_x
        self._cur_y = self._start_y

        self.canvas.itemconfigure(self._guide_h_id, state="hidden")
        self.canvas.itemconfigure(self._guide_v_id, state="hidden")
        self.canvas.itemconfigure("banner", state="hidden")

    def _on_mouse_drag(self, event: tk.Event) -> None:
        if not self._dragging or self._closed:
            return
        self._cur_x = max(0, min(self.win_width, event.x))
        self._cur_y = max(0, min(self.win_height, event.y))
        self._update_selection_visuals()

    def _update_selection_visuals(self) -> None:
        x1 = min(self._start_x, self._cur_x)
        y1 = min(self._start_y, self._cur_y)
        x2 = max(self._start_x, self._cur_x)
        y2 = max(self._start_y, self._cur_y)

        if x2 - x1 < 2 or y2 - y1 < 2:
            self.canvas.itemconfigure(self._crop_image_id, state="hidden")
            self.canvas.itemconfigure(self._rect_id, state="hidden")
            self.canvas.itemconfigure(self._size_bg_id, state="hidden")
            self.canvas.itemconfigure(self._size_text_id, state="hidden")
            for h_id in self._handle_ids:
                self.canvas.itemconfigure(h_id, state="hidden")
            return

        patch = self.display_bright.crop((x1, y1, x2, y2))
        self._tk_crop_patch = ImageTk.PhotoImage(patch)
        self.canvas.itemconfigure(self._crop_image_id, image=self._tk_crop_patch, state="normal")
        self.canvas.coords(self._crop_image_id, x1, y1)

        self.canvas.coords(self._rect_id, x1, y1, x2, y2)
        self.canvas.itemconfigure(self._rect_id, state="normal")

        r = 4
        corners = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
        for h_id, (cx, cy) in zip(self._handle_ids, corners):
            self.canvas.coords(h_id, cx - r, cy - r, cx + r, cy + r)
            self.canvas.itemconfigure(h_id, state="normal")

        phys_w = max(1, int(round((x2 - x1) * self.scale_x)))
        phys_h = max(1, int(round((y2 - y1) * self.scale_y)))
        label_str = f"{phys_w} × {phys_h} px"

        badge_x = x1
        badge_y = y1 - 28 if y1 >= 32 else y2 + 8
        self.canvas.coords(self._size_text_id, badge_x + 8, badge_y + 4)
        self.canvas.itemconfigure(self._size_text_id, text=label_str, state="normal")
        bbox = self.canvas.bbox(self._size_text_id)
        if bbox:
            self.canvas.coords(
                self._size_bg_id,
                bbox[0] - 8,
                bbox[1] - 4,
                bbox[2] + 8,
                bbox[3] + 4,
            )
            self.canvas.itemconfigure(self._size_bg_id, state="normal")
            self.canvas.tag_lower(self._size_bg_id, self._size_text_id)

    def _on_mouse_up(self, event: tk.Event) -> None:
        if not self._dragging or self._closed:
            return
        self._dragging = False
        self._cur_x = max(0, min(self.win_width, event.x))
        self._cur_y = max(0, min(self.win_height, event.y))

        x1 = min(self._start_x, self._cur_x)
        y1 = min(self._start_y, self._cur_y)
        x2 = max(self._start_x, self._cur_x)
        y2 = max(self._start_y, self._cur_y)

        if (x2 - x1) < 5 or (y2 - y1) < 5:
            self.canvas.itemconfigure(self._guide_h_id, state="normal")
            self.canvas.itemconfigure(self._guide_v_id, state="normal")
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
        try:
            self.top.grab_release()
        except Exception:
            pass
        try:
            self.top.destroy()
            self.root.update_idletasks()
        except Exception:
            pass
