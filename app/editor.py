"""Annotation & Drawing Editor Window for Ctrl + 2 mode.

Features:
- Object-based Vector Annotation System: Every drawn Arrow, Line, Text, Rectangle,
  Ellipse, Pen stroke, Highlighter, and Pixelate box is an interactive object!
- Click-and-hold on any drawn object to move/reposition it smoothly in real time,
  or drag its endpoints/corners to adjust direction and size.
- Double-click any Text object to edit its content; click Color or Size while an
  object is selected to change its color/thickness; press Delete/Backspace to remove it.
- Brighter, high-contrast toolbar menu with mathematically centered [icon + text] pill buttons
  and uniform Vietnamese typographic baseline across all buttons.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import math
from pathlib import Path
import tkinter as tk
from tkinter import colorchooser, filedialog
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageTk


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    r, g, b = _hex_to_rgb(hex_color)
    return (r, g, b, alpha)


def _get_dpi_scale(widget: tk.Widget) -> float:
    """Return physical-to-logical DPI scale factor (e.g. 1.5 on 150% 2K display, 1.0 on 100%)."""
    try:
        tk_scaling = float(widget.tk.call("tk", "scaling"))
        return max(1.0, min(3.0, tk_scaling / (96.0 / 72.0)))
    except Exception:
        return 1.25


def _load_ui_font(size_px: int, bold: bool = True):
    from app.platform_utils import get_bundled_assets_dir

    fonts_dir = get_bundled_assets_dir() / "fonts"
    candidates = (
        [
            str(fonts_dir / "Roboto-Bold.ttf"),
            "Roboto-Bold.ttf",
            "segoeuib.ttf",
            "arialbd.ttf",
            "calibrib.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        if bold
        else [
            str(fonts_dir / "Roboto-Regular.ttf"),
            "Roboto-Regular.ttf",
            "segoeui.ttf",
            "arial.ttf",
            "calibri.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    for c in candidates:
        try:
            return ImageFont.truetype(c, max(8, int(size_px)))
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=max(8, int(size_px)))
    except TypeError:
        return ImageFont.load_default()


def _point_to_segment_dist(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    """Return minimum Euclidean distance from point (px, py) to segment (x1, y1)-(x2, y2)."""
    dx = x2 - x1
    dy = y2 - y1
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-6:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


@dataclass
class AnnotationItem:
    """Represents a single movable/editable annotation object on the canvas."""

    tool: str
    color: str
    size: int
    stroke_px: int
    points: List[Tuple[int, int]] = field(default_factory=list)
    text: str = ""
    font_px: int = 24

    def clone(self) -> "AnnotationItem":
        return AnnotationItem(
            tool=self.tool,
            color=self.color,
            size=self.size,
            stroke_px=self.stroke_px,
            points=list(self.points),
            text=self.text,
            font_px=self.font_px,
        )

    def translate(self, dx: int, dy: int, max_w: int, max_h: int) -> None:
        if not self.points:
            return
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        if min_x + dx < 0:
            dx = -min_x
        if max_x + dx >= max_w:
            dx = (max_w - 1) - max_x
        if min_y + dy < 0:
            dy = -min_y
        if max_y + dy >= max_h:
            dy = (max_h - 1) - max_y

        self.points = [(px + dx, py + dy) for px, py in self.points]

    def get_bbox(self) -> Tuple[int, int, int, int]:
        """Return bounding box (x1, y1, x2, y2) in image coordinates."""
        if not self.points:
            return (0, 0, 0, 0)

        if self.tool == "text":
            ix, iy = self.points[0]
            font = _load_ui_font(self.font_px, bold=True)
            dummy = Image.new("RGB", (10, 10))
            draw = ImageDraw.Draw(dummy)
            stroke_w = max(2, self.font_px // 11)
            bbox = draw.textbbox(
                (ix, iy), self.text or " ", font=font, stroke_width=stroke_w
            )
            pad = max(6, self.font_px // 6)
            return (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)

        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        pad = max(6, self.stroke_px)
        return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

    def get_handles(self) -> List[Tuple[int, int]]:
        """Return interactive control point handles in image coordinates."""
        if not self.points:
            return []
        if self.tool in ("arrow", "line") and len(self.points) >= 2:
            return [self.points[0], self.points[-1]]
        if self.tool in ("rect", "ellipse", "pixelate") and len(self.points) >= 2:
            x1, y1 = self.points[0]
            x2, y2 = self.points[-1]
            return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        return []

    def move_handle(self, handle_idx: int, new_x: int, new_y: int) -> None:
        """Update endpoint or corner handle position."""
        if self.tool in ("arrow", "line") and len(self.points) >= 2:
            if handle_idx == 0:
                self.points[0] = (new_x, new_y)
            elif handle_idx == 1:
                self.points[-1] = (new_x, new_y)
        elif self.tool in ("rect", "ellipse", "pixelate") and len(self.points) >= 2:
            x1, y1 = self.points[0]
            x2, y2 = self.points[-1]
            if handle_idx == 0:
                self.points[0] = (new_x, new_y)
            elif handle_idx == 1:
                self.points[0] = (x1, new_y)
                self.points[-1] = (new_x, y2)
            elif handle_idx == 2:
                self.points[-1] = (new_x, new_y)
            elif handle_idx == 3:
                self.points[0] = (new_x, y1)
                self.points[-1] = (x2, new_y)

    def hit_test(self, ix: int, iy: int, base_tol: int = 14) -> bool:
        """Return True if point (ix, iy) in image coordinates hits this annotation item."""
        if not self.points:
            return False

        tol = max(base_tol, self.stroke_px + 10)

        if self.tool == "text":
            bx1, by1, bx2, by2 = self.get_bbox()
            return (bx1 - 6 <= ix <= bx2 + 6) and (by1 - 6 <= iy <= by2 + 6)

        if self.tool in ("arrow", "line"):
            x1, y1 = self.points[0]
            x2, y2 = self.points[-1]
            if _point_to_segment_dist(ix, iy, x1, y1, x2, y2) <= tol * 1.3:
                return True
            if self.tool == "arrow":
                head_r = max(tol * 2.0, self.stroke_px * 4.5)
                dx = x2 - x1
                dy = y2 - y1
                length = math.hypot(dx, dy)
                if length > 1:
                    hx = x2 - (dx / length) * (head_r * 0.45)
                    hy = y2 - (dy / length) * (head_r * 0.45)
                    if math.hypot(ix - hx, iy - hy) <= head_r * 0.65:
                        return True
            return False

        if self.tool == "rect":
            x1, y1 = self.points[0]
            x2, y2 = self.points[-1]
            rx1, rx2 = min(x1, x2), max(x1, x2)
            ry1, ry2 = min(y1, y2), max(y1, y2)
            if (rx2 - rx1 < 80 and ry2 - ry1 < 80) and (
                rx1 - tol <= ix <= rx2 + tol and ry1 - tol <= iy <= ry2 + tol
            ):
                return True
            near_top = _point_to_segment_dist(ix, iy, rx1, ry1, rx2, ry1) <= tol
            near_bot = _point_to_segment_dist(ix, iy, rx1, ry2, rx2, ry2) <= tol
            near_left = _point_to_segment_dist(ix, iy, rx1, ry1, rx1, ry2) <= tol
            near_right = _point_to_segment_dist(ix, iy, rx2, ry1, rx2, ry2) <= tol
            return near_top or near_bot or near_left or near_right

        if self.tool == "ellipse":
            x1, y1 = self.points[0]
            x2, y2 = self.points[-1]
            rx1, rx2 = min(x1, x2), max(x1, x2)
            ry1, ry2 = min(y1, y2), max(y1, y2)
            cx = (rx1 + rx2) / 2.0
            cy = (ry1 + ry2) / 2.0
            a = max(1.0, (rx2 - rx1) / 2.0)
            b = max(1.0, (ry2 - ry1) / 2.0)
            if a < 40 and b < 40:
                return ((ix - cx) / (a + tol)) ** 2 + ((iy - cy) / (b + tol)) ** 2 <= 1.0
            norm_r = math.hypot((ix - cx) / a, (iy - cy) / b)
            avg_rad = (a + b) / 2.0
            rel_tol = tol / max(10.0, avg_rad)
            return abs(norm_r - 1.0) <= max(0.18, rel_tol)

        if self.tool == "pixelate":
            x1, y1 = self.points[0]
            x2, y2 = self.points[-1]
            rx1, rx2 = min(x1, x2), max(x1, x2)
            ry1, ry2 = min(y1, y2), max(y1, y2)
            return (rx1 - 6 <= ix <= rx2 + 6) and (ry1 - 6 <= iy <= ry2 + 6)

        if self.tool in ("pen", "highlighter"):
            hit_r = tol * (1.6 if self.tool == "highlighter" else 1.15)
            if len(self.points) == 1:
                px, py = self.points[0]
                return math.hypot(ix - px, iy - py) <= hit_r
            for i in range(len(self.points) - 1):
                p1x, p1y = self.points[i]
                p2x, p2y = self.points[i + 1]
                if _point_to_segment_dist(ix, iy, p1x, p1y, p2x, p2y) <= hit_r:
                    return True
            return False

        return False


def _draw_tool_vector_icon(
    draw: ImageDraw.ImageDraw,
    icon_name: str,
    cx: int,
    cy: int,
    size: int,
    color: Tuple[int, int, int, int],
) -> None:
    """Draw crisp vector icons centered around (cx, cy) at supersampled resolution."""
    half = size // 2
    x1, y1 = cx - half, cy - half
    x2, y2 = cx + half, cy + half
    w = max(4, int(round(size * 0.135)))

    if icon_name == "arrow":
        sx, sy = x1 + int(size * 0.14), y2 - int(size * 0.14)
        ex, ey = x2 - int(size * 0.10), y1 + int(size * 0.10)
        draw.line(
            [(sx, sy), (ex - int(size * 0.14), ey + int(size * 0.14))],
            fill=color,
            width=w + 2,
        )
        draw.polygon(
            [
                (ex, ey),
                (ex - int(size * 0.54), ey + int(size * 0.08)),
                (ex - int(size * 0.25), ey + int(size * 0.25)),
                (ex - int(size * 0.08), ey + int(size * 0.54)),
            ],
            fill=color,
        )
        r = (w + 2) // 2
        draw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=color)

    elif icon_name == "pen":
        pts = [
            (x1 + int(size * 0.12), y2 - int(size * 0.12)),
            (x1 + int(size * 0.28), y2 - int(size * 0.44)),
            (x2 - int(size * 0.24), y1 + int(size * 0.12)),
            (x2 - int(size * 0.12), y1 + int(size * 0.24)),
            (x1 + int(size * 0.44), y2 - int(size * 0.28)),
        ]
        draw.polygon(pts, outline=color, width=w)
        draw.line(
            [
                (x1 + int(size * 0.12), y2 - int(size * 0.12)),
                (x1 + int(size * 0.30), y2 - int(size * 0.30)),
            ],
            fill=color,
            width=w,
        )

    elif icon_name == "highlighter":
        draw.polygon(
            [
                (x1 + int(size * 0.20), y2 - int(size * 0.36)),
                (x2 - int(size * 0.22), y1 + int(size * 0.10)),
                (x2 - int(size * 0.08), y1 + int(size * 0.26)),
                (x1 + int(size * 0.38), y2 - int(size * 0.18)),
            ],
            outline=color,
            width=w,
        )
        bar_color = (color[0], color[1], color[2], 195)
        draw.rounded_rectangle(
            (x1 + int(size * 0.10), y2 - int(size * 0.16), x2 - int(size * 0.10), y2),
            radius=max(3, size // 10),
            fill=bar_color,
        )

    elif icon_name == "rect":
        draw.rounded_rectangle(
            (
                x1 + int(size * 0.10),
                y1 + int(size * 0.16),
                x2 - int(size * 0.10),
                y2 - int(size * 0.16),
            ),
            radius=max(4, size // 9),
            outline=color,
            width=w,
        )

    elif icon_name == "ellipse":
        draw.ellipse(
            (
                x1 + int(size * 0.10),
                y1 + int(size * 0.14),
                x2 - int(size * 0.10),
                y2 - int(size * 0.14),
            ),
            outline=color,
            width=w,
        )

    elif icon_name == "line":
        p1x, p1y = x1 + int(size * 0.15), y2 - int(size * 0.16)
        p2x, p2y = x2 - int(size * 0.15), y1 + int(size * 0.16)
        draw.line([(p1x, p1y), (p2x, p2y)], fill=color, width=w)
        r = max(4, int(w * 1.15))
        draw.ellipse((p1x - r, p1y - r, p1x + r, p1y + r), fill=color)
        draw.ellipse((p2x - r, p2y - r, p2x + r, p2y + r), fill=color)

    elif icon_name == "text":
        top_y = y1 + int(size * 0.14)
        bot_y = y2 - int(size * 0.14)
        lx = x1 + int(size * 0.16)
        rx = x2 - int(size * 0.16)
        serif = int(size * 0.18)
        draw.line([(lx, top_y), (rx, top_y)], fill=color, width=w + 1)
        draw.line([(lx, top_y), (lx, top_y + serif)], fill=color, width=w)
        draw.line([(rx, top_y), (rx, top_y + serif)], fill=color, width=w)
        draw.line([(cx, top_y), (cx, bot_y)], fill=color, width=w + 2)
        draw.line(
            [(cx - int(size * 0.20), bot_y), (cx + int(size * 0.20), bot_y)],
            fill=color,
            width=w,
        )

    elif icon_name == "pixelate":
        grid = 3
        cell = int(size * 0.81) // grid
        start_x = cx - (cell * grid) // 2
        start_y = cy - (cell * grid) // 2
        for r_idx in range(grid):
            for c_idx in range(grid):
                alpha = 245 if (r_idx + c_idx) % 2 == 0 else 110
                c_fill = (color[0], color[1], color[2], alpha)
                gx1 = start_x + c_idx * cell
                gy1 = start_y + r_idx * cell
                draw.rectangle(
                    (gx1 + 1, gy1 + 1, gx1 + cell - 1, gy1 + cell - 1),
                    fill=c_fill,
                )

    elif icon_name == "undo":
        draw.arc(
            (
                x1 + int(size * 0.12),
                y1 + int(size * 0.20),
                x2 - int(size * 0.10),
                y2 - int(size * 0.08),
            ),
            start=200,
            end=45,
            fill=color,
            width=w,
        )
        ax, ay = x1 + int(size * 0.18), cy - int(size * 0.04)
        d = int(size * 0.25)
        draw.polygon(
            [(ax - d // 3, ay + d // 3), (ax + d, ay - d // 2), (ax + d, ay + d)],
            fill=color,
        )

    elif icon_name == "redo":
        draw.arc(
            (
                x1 + int(size * 0.10),
                y1 + int(size * 0.20),
                x2 - int(size * 0.12),
                y2 - int(size * 0.08),
            ),
            start=135,
            end=340,
            fill=color,
            width=w,
        )
        ax, ay = x2 - int(size * 0.18), cy - int(size * 0.04)
        d = int(size * 0.25)
        draw.polygon(
            [(ax + d // 3, ay + d // 3), (ax - d, ay - d // 2), (ax - d, ay + d)],
            fill=color,
        )

    elif icon_name == "clear":
        top_lid = y1 + int(size * 0.24)
        draw.line(
            [(x1 + int(size * 0.14), top_lid), (x2 - int(size * 0.14), top_lid)],
            fill=color,
            width=w,
        )
        draw.rectangle(
            (
                x1 + int(size * 0.22),
                top_lid,
                x2 - int(size * 0.22),
                y2 - int(size * 0.10),
            ),
            outline=color,
            width=w,
        )
        draw.line(
            [
                (cx - int(size * 0.12), y1 + int(size * 0.13)),
                (cx + int(size * 0.12), y1 + int(size * 0.13)),
            ],
            fill=color,
            width=w,
        )

    elif icon_name == "copy":
        draw.rounded_rectangle(
            (
                x1 + int(size * 0.12),
                y1 + int(size * 0.12),
                x2 - int(size * 0.12),
                y2 - int(size * 0.12),
            ),
            radius=max(6, size // 7),
            outline=color,
            width=w,
        )
        draw.line(
            [
                (x1 + int(size * 0.28), cy + int(size * 0.04)),
                (cx - int(size * 0.04), y2 - int(size * 0.26)),
                (x2 - int(size * 0.24), y1 + int(size * 0.30)),
            ],
            fill=color,
            width=w + 1,
            joint="curve",
        )

    elif icon_name == "save":
        draw.line(
            [(cx, y1 + int(size * 0.12)), (cx, cy + int(size * 0.16))],
            fill=color,
            width=w + 1,
        )
        aw = int(size * 0.24)
        draw.line(
            [
                (cx - aw, cy - int(size * 0.04)),
                (cx, cy + int(size * 0.20)),
                (cx + aw, cy - int(size * 0.04)),
            ],
            fill=color,
            width=w + 1,
            joint="curve",
        )
        tray_y = y2 - int(size * 0.12)
        tray_top = y2 - int(size * 0.28)
        lx = x1 + int(size * 0.16)
        rx = x2 - int(size * 0.16)
        draw.line(
            [(lx, tray_top), (lx, tray_y), (rx, tray_y), (rx, tray_top)],
            fill=color,
            width=w,
            joint="curve",
        )

    elif icon_name == "palette":
        r = int(size * 0.38)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=w)
        dot = max(3, size // 10)
        for dx, dy in [(-r // 2, -r // 3), (r // 3, -r // 2), (-r // 3, r // 3)]:
            draw.ellipse(
                (cx + dx - dot, cy + dy - dot, cx + dx + dot, cy + dy + dot),
                fill=color,
            )

    elif icon_name == "capture":
        # Sleek viewfinder corner brackets + center lens circle
        m = int(size * 0.14)
        blen = int(size * 0.22)
        sw = max(3, int(round(size * 0.115)))
        # Top-left
        draw.line([(x1 + m, y1 + m), (x1 + m + blen, y1 + m)], fill=color, width=sw)
        draw.line([(x1 + m, y1 + m), (x1 + m, y1 + m + blen)], fill=color, width=sw)
        # Top-right
        draw.line([(x2 - m, y1 + m), (x2 - m - blen, y1 + m)], fill=color, width=sw)
        draw.line([(x2 - m, y1 + m), (x2 - m, y1 + m + blen)], fill=color, width=sw)
        # Bottom-left
        draw.line([(x1 + m, y2 - m), (x1 + m + blen, y2 - m)], fill=color, width=sw)
        draw.line([(x1 + m, y2 - m), (x1 + m, y2 - m - blen)], fill=color, width=sw)
        # Bottom-right
        draw.line([(x2 - m, y2 - m), (x2 - m - blen, y2 - m)], fill=color, width=sw)
        draw.line([(x2 - m, y2 - m), (x2 - m, y2 - m - blen)], fill=color, width=sw)
        # Center lens dot
        lr = max(4, int(round(size * 0.15)))
        draw.ellipse((cx - lr, cy - lr, cx + lr, cy + lr), fill=color)

    elif icon_name == "close":
        m = int(size * 0.25)
        sw = max(3, int(round(size * 0.105)))
        p1, p2 = (x1 + m, y1 + m), (x2 - m, y2 - m)
        p3, p4 = (x2 - m, y1 + m), (x1 + m, y2 - m)
        draw.line([p1, p2], fill=color, width=sw)
        draw.line([p3, p4], fill=color, width=sw)
        r = sw // 2
        for px, py in (p1, p2, p3, p4):
            draw.ellipse((px - r, py - r, px + r, py + r), fill=color)


class ModernPillButton(tk.Label):
    """High-DPI flat button with 4 rounded corners, centered [icon + text], and uniform baseline."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        icon_name: Optional[str],
        command: Callable[[], None],
        parent_bg: str = "#e8eef5",
        bg_normal: str = "#ffffff",
        bg_hover: str = "#f1f5f9",
        bg_active: str = "#0284c7",
        fg_normal: str = "#1e293b",
        fg_hover: Optional[str] = None,
        fg_active: str = "#ffffff",
        border_active: Optional[str] = None,
        border_normal: Optional[str] = "#cbd5e1",
        border_hover: Optional[str] = "#94a3b8",
        font_pt: int = 12,
        height_pt: int = 31,
        pad_x_pt: float = 14.0,
        corner_radius_pt: float = 5.5,
    ) -> None:
        super().__init__(parent, bg=parent_bg, bd=0, highlightthickness=0, cursor="hand2")
        self.text_label = text
        self.icon_name = icon_name
        self.command = command
        self.parent_bg = parent_bg
        self.bg_normal = bg_normal
        self.bg_hover = bg_hover
        self.bg_active = bg_active
        self.fg_normal = fg_normal
        self.fg_hover = fg_hover if fg_hover is not None else (
            "#0f172a" if fg_normal == "#1e293b" else fg_normal
        )
        self.fg_active = fg_active
        self.border_active = border_active
        self.border_normal = border_normal
        self.border_hover = border_hover
        self.corner_radius_pt = corner_radius_pt

        self.dpi_scale = _get_dpi_scale(parent)
        self.font_px = max(12, int(round(font_pt * self.dpi_scale)))
        self.icon_px = (
            max(16, int(round((font_pt + 2) * self.dpi_scale)))
            if self.icon_name
            else 0
        )
        self.btn_h = max(28, int(round(height_pt * self.dpi_scale)))
        self.pad_x = max(10, int(round(pad_x_pt * self.dpi_scale)))
        self.gap_px = (
            max(8, int(round(7.5 * self.dpi_scale))) if self.icon_name else 0
        )

        ss = 3
        ss_font = _load_ui_font(self.font_px * ss, bold=True)
        dummy_img = Image.new("RGBA", (10, 10))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), self.text_label, font=ss_font)
        text_w_1x = int(math.ceil((bbox[2] - bbox[0]) / ss))

        self.btn_w = self.pad_x * 2 + self.icon_px + self.gap_px + text_w_1x

        self._is_active = False
        self._is_hovered = False

        self._img_normal = self._render_state(bg_normal, fg_normal, border_normal)
        self._img_hover = self._render_state(bg_hover, self.fg_hover, self.border_hover)
        self._img_active = self._render_state(bg_active, fg_active, border_active)
        self._img_active_hover = self._render_state("#0369a1", "#ffffff", None)

        self.configure(image=self._img_normal)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_click)

    def _render_state(
        self, bg_hex: str, fg_hex: str, border_hex: Optional[str]
    ) -> ImageTk.PhotoImage:
        ss = 3
        W, H = self.btn_w * ss, self.btn_h * ss
        img = Image.new("RGBA", (W, H), _hex_to_rgba(self.parent_bg, 255))
        draw = ImageDraw.Draw(img)

        pad = max(2, int(round(1.2 * self.dpi_scale * ss)))
        radius = int(round(self.corner_radius_pt * self.dpi_scale * ss))

        has_border = bool(border_hex and border_hex.lower() != bg_hex.lower())
        if has_border and border_hex is not None:
            draw.rounded_rectangle(
                (pad, pad, W - pad, H - pad),
                radius=radius,
                fill=_hex_to_rgba(bg_hex, 255),
                outline=_hex_to_rgba(border_hex, 255),
                width=max(2, int(round(0.95 * self.dpi_scale * ss))),
            )
        else:
            draw.rounded_rectangle(
                (pad, pad, W - pad, H - pad),
                radius=radius,
                fill=_hex_to_rgba(bg_hex, 255),
            )

        fg_rgba = _hex_to_rgba(fg_hex, 255)
        icon_size = self.icon_px * ss
        gap = self.gap_px * ss
        font = _load_ui_font(self.font_px * ss, bold=True)

        bbox = draw.textbbox((0, 0), self.text_label, font=font)
        text_w = bbox[2] - bbox[0]

        total_content_w = icon_size + gap + text_w
        start_x = (W - total_content_w) // 2

        if self.icon_name:
            icon_cx = start_x + (icon_size // 2)
            icon_cy = H // 2
            _draw_tool_vector_icon(draw, self.icon_name, icon_cx, icon_cy, icon_size, fg_rgba)

        ref_bbox = draw.textbbox((0, 0), "ÁgĐy", font=font)
        ref_h = ref_bbox[3] - ref_bbox[1]
        text_x = start_x + icon_size + gap - bbox[0]
        text_y = (H - ref_h) // 2 - ref_bbox[1]

        draw.text((text_x, text_y), self.text_label, fill=fg_rgba, font=font)

        smooth = img.resize((self.btn_w, self.btn_h), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(smooth)

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self._update_image()

    def _on_enter(self, _event=None) -> None:
        self._is_hovered = True
        self._update_image()

    def _on_leave(self, _event=None) -> None:
        self._is_hovered = False
        self._update_image()

    def _on_click(self, _event=None) -> None:
        self.command()

    def _update_image(self) -> None:
        if self._is_active:
            self.configure(
                image=self._img_active_hover if self._is_hovered else self._img_active
            )
        else:
            self.configure(image=self._img_hover if self._is_hovered else self._img_normal)


class ColorSwatchButton(tk.Label):
    """High-DPI anti-aliased circular color swatch button with active ring."""

    def __init__(
        self,
        parent: tk.Widget,
        hex_color: str,
        command: Callable[[], None],
        base_size: int = 24,
        parent_bg: str = "#f1f5f9",
    ) -> None:
        super().__init__(parent, bg=parent_bg, bd=0, highlightthickness=0, cursor="hand2")
        self.hex_color = hex_color
        self.command = command
        self.dpi_scale = _get_dpi_scale(parent)
        self.swatch_size = max(28, int(round(base_size * self.dpi_scale)))
        self.parent_bg = parent_bg
        self._active = False
        self._hovered = False

        self._img_normal = self._render(active=False, hovered=False)
        self._img_hover = self._render(active=False, hovered=True)
        self._img_active = self._render(active=True, hovered=False)

        self.configure(image=self._img_normal)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", lambda _e: self.command())

    def _render(self, active: bool, hovered: bool) -> ImageTk.PhotoImage:
        ss = 3
        S = self.swatch_size * ss
        img = Image.new("RGBA", (S, S), _hex_to_rgba(self.parent_bg, 255))
        draw = ImageDraw.Draw(img)

        ring_pad = int(round(2 * self.dpi_scale * ss))
        if active:
            draw.ellipse(
                (ring_pad, ring_pad, S - ring_pad, S - ring_pad),
                outline=(2, 132, 199, 255),
                width=max(3, int(round(2.4 * self.dpi_scale * ss))),
            )
            pad = int(round(6 * self.dpi_scale * ss))
        elif hovered:
            draw.ellipse(
                (ring_pad, ring_pad, S - ring_pad, S - ring_pad),
                outline=(100, 116, 139, 220),
                width=max(2, int(round(1.6 * self.dpi_scale * ss))),
            )
            pad = int(round(5 * self.dpi_scale * ss))
        else:
            pad = int(round(5.5 * self.dpi_scale * ss))

        draw.ellipse(
            (pad, pad, S - pad, S - pad),
            fill=_hex_to_rgba(self.hex_color, 255),
            outline=(100, 116, 139, 185),
            width=max(2, int(round(1.2 * self.dpi_scale * ss))),
        )
        smooth = img.resize(
            (self.swatch_size, self.swatch_size), Image.Resampling.LANCZOS
        )
        return ImageTk.PhotoImage(smooth)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.configure(image=self._img_active if active else self._img_normal)

    def _on_enter(self, _e=None) -> None:
        self._hovered = True
        if not self._active:
            self.configure(image=self._img_hover)

    def _on_leave(self, _e=None) -> None:
        self._hovered = False
        if not self._active:
            self.configure(image=self._img_normal)


class SizeDotButton(tk.Label):
    """High-DPI flat stroke thickness button with 4 rounded corners and centered [dot + text]."""

    def __init__(
        self,
        parent: tk.Widget,
        size_val: int,
        label_text: str,
        dot_radius_pt: int,
        command: Callable[[], None],
        parent_bg: str = "#f1f5f9",
    ) -> None:
        super().__init__(parent, bg=parent_bg, bd=0, highlightthickness=0, cursor="hand2")
        self.size_val = size_val
        self.label_text = label_text
        self.dpi_scale = _get_dpi_scale(parent)
        self.dot_r = max(3, int(round(dot_radius_pt * self.dpi_scale)))
        self.font_px = max(14, int(round(12 * self.dpi_scale)))
        self.btn_h = max(36, int(round(30 * self.dpi_scale)))
        self.pad_x = max(13, int(round(12 * self.dpi_scale)))
        self.gap_px = max(7, int(round(7 * self.dpi_scale)))
        self.command = command
        self.parent_bg = parent_bg

        ss = 3
        ss_font = _load_ui_font(self.font_px * ss, bold=True)
        dummy_img = Image.new("RGBA", (10, 10))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), self.label_text, font=ss_font)
        text_w_1x = int(math.ceil((bbox[2] - bbox[0]) / ss))
        dot_d_1x = self.dot_r * 2

        self.btn_w = self.pad_x * 2 + dot_d_1x + self.gap_px + text_w_1x
        self._active = False

        self._img_normal = self._render(active=False, hovered=False)
        self._img_hover = self._render(active=False, hovered=True)
        self._img_active = self._render(active=True, hovered=False)

        self.configure(image=self._img_normal)
        self.bind("<Enter>", lambda _e: not self._active and self.configure(image=self._img_hover))
        self.bind("<Leave>", lambda _e: not self._active and self.configure(image=self._img_normal))
        self.bind("<ButtonPress-1>", lambda _e: self.command())

    def _render(self, active: bool, hovered: bool) -> ImageTk.PhotoImage:
        ss = 3
        W, H = self.btn_w * ss, self.btn_h * ss
        img = Image.new("RGBA", (W, H), _hex_to_rgba(self.parent_bg, 255))
        draw = ImageDraw.Draw(img)

        bg = "#0284c7" if active else ("#e0f2fe" if hovered else "#ffffff")
        fg = "#ffffff" if active else ("#0369a1" if hovered else "#1e293b")

        pad = max(2, int(round(1.2 * self.dpi_scale * ss)))
        radius = int(round(5.5 * self.dpi_scale * ss))
        if active:
            draw.rounded_rectangle(
                (pad, pad, W - pad, H - pad),
                radius=radius,
                fill=_hex_to_rgba(bg, 255),
            )
        else:
            border = "#7dd3fc" if hovered else "#cbd5e1"
            draw.rounded_rectangle(
                (pad, pad, W - pad, H - pad),
                radius=radius,
                fill=_hex_to_rgba(bg, 255),
                outline=_hex_to_rgba(border, 255),
                width=max(2, int(round(0.95 * self.dpi_scale * ss))),
            )

        r = self.dot_r * ss
        dot_d = r * 2
        gap = self.gap_px * ss
        font = _load_ui_font(self.font_px * ss, bold=True)

        bbox = draw.textbbox((0, 0), self.label_text, font=font)
        text_w = bbox[2] - bbox[0]

        total_content_w = dot_d + gap + text_w
        start_x = (W - total_content_w) // 2

        cx = start_x + r
        cy = H // 2
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=_hex_to_rgba(fg, 255))

        ref_bbox = draw.textbbox((0, 0), "ÁgĐy", font=font)
        ref_h = ref_bbox[3] - ref_bbox[1]
        tx = start_x + dot_d + gap - bbox[0]
        ty = (H - ref_h) // 2 - ref_bbox[1]
        draw.text((tx, ty), self.label_text, fill=_hex_to_rgba(fg, 255), font=font)

        smooth = img.resize((self.btn_w, self.btn_h), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(smooth)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.configure(image=self._img_active if active else self._img_normal)


class ResponsiveFlowBar(tk.Frame):
    """Responsive toolbar frame that centers items and wraps groups/buttons onto new rows when resized."""

    def __init__(
        self,
        parent: tk.Widget,
        bg: str,
        pad_x: int = 14,
        pad_y: int = 8,
        row_gap: int = 6,
    ) -> None:
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0)
        self.bg_color = bg
        self.pad_x = pad_x
        self.pad_y = pad_y
        self.row_gap = row_gap
        self._entries: List[dict] = []
        self._last_width: int = -1
        self.pack_propagate(False)
        self.bind("<Configure>", self._on_configure)

    def add_widget(
        self,
        widget: tk.Widget,
        gap_x: int = 8,
        keep_with_next: bool = False,
        glue_next: bool = False,
    ) -> None:
        self._entries.append(
            {
                "type": "widget",
                "widget": widget,
                "gap_x": gap_x,
                "keep_with_next": keep_with_next,
                "glue_next": glue_next,
            }
        )

    def add_divider(
        self,
        bg: str = "#cbd5e1",
        height: int = 28,
        gap_x: int = 20,
    ) -> tk.Frame:
        div = tk.Frame(self, bg=bg, width=1, height=height)
        self._entries.append(
            {
                "type": "divider",
                "widget": div,
                "gap_x": gap_x,
                "keep_with_next": False,
                "glue_next": False,
            }
        )
        return div

    def _measure_entries(self) -> None:
        for entry in self._entries:
            w_obj = entry["widget"]
            if entry["type"] == "divider":
                entry["w"] = 1
                entry["h"] = int(w_obj.cget("height") or 28)
            else:
                req_w = w_obj.winfo_reqwidth()
                req_h = w_obj.winfo_reqheight()
                if req_w <= 1 or req_h <= 1:
                    w_obj.update_idletasks()
                    req_w = w_obj.winfo_reqwidth()
                    req_h = w_obj.winfo_reqheight()
                entry["w"] = req_w
                entry["h"] = req_h

    def get_single_row_width(self) -> int:
        self._measure_entries()
        if not self._entries:
            return self.pad_x * 2
        total = self.pad_x * 2
        for i, entry in enumerate(self._entries):
            total += entry["w"]
            if i < len(self._entries) - 1:
                total += entry["gap_x"]
        return total

    def _build_units(self, avail_w: int) -> List[dict]:
        raw_groups: List[List[dict]] = []
        cur: List[dict] = []
        for entry in self._entries:
            if entry["type"] == "divider":
                if cur:
                    raw_groups.append(cur)
                    cur = []
                raw_groups.append([entry])
            else:
                cur.append(entry)
                if not entry.get("keep_with_next", False):
                    raw_groups.append(cur)
                    cur = []
        if cur:
            raw_groups.append(cur)

        final_units: List[dict] = []
        for grp in raw_groups:
            if len(grp) == 1 and grp[0]["type"] == "divider":
                final_units.append(
                    {
                        "type": "divider",
                        "items": grp,
                        "w": grp[0]["w"],
                        "gap_x": grp[0]["gap_x"],
                    }
                )
                continue

            grp_w = sum(it["w"] for it in grp) + sum(it["gap_x"] for it in grp[:-1])
            if grp_w <= avail_w or len(grp) == 1:
                final_units.append(
                    {
                        "type": "unit",
                        "items": grp,
                        "w": grp_w,
                        "gap_x": grp[-1]["gap_x"],
                    }
                )
            else:
                sub: List[dict] = []
                for it in grp:
                    sub.append(it)
                    if not it.get("glue_next", False):
                        sub_w = sum(x["w"] for x in sub) + sum(
                            x["gap_x"] for x in sub[:-1]
                        )
                        final_units.append(
                            {
                                "type": "unit",
                                "items": sub,
                                "w": sub_w,
                                "gap_x": sub[-1]["gap_x"],
                            }
                        )
                        sub = []
                if sub:
                    sub_w = sum(x["w"] for x in sub) + sum(
                        x["gap_x"] for x in sub[:-1]
                    )
                    final_units.append(
                        {
                            "type": "unit",
                            "items": sub,
                            "w": sub_w,
                            "gap_x": sub[-1]["gap_x"],
                        }
                    )
        return final_units

    def _compute_lines(self, avail_w: int) -> Tuple[List[List[dict]], List[tk.Widget]]:
        units = self._build_units(avail_w)
        lines: List[List[dict]] = []
        cur_line: List[dict] = []
        cur_w = 0
        hidden_dividers: List[tk.Widget] = []

        for u in units:
            if u["type"] == "divider":
                if not cur_line or cur_line[-1]["type"] == "divider":
                    hidden_dividers.append(u["items"][0]["widget"])
                else:
                    cur_line.append(u)
                    cur_w += cur_line[-2]["gap_x"] + u["w"]
                continue

            if not cur_line:
                cur_line.append(u)
                cur_w = u["w"]
            else:
                prev_gap = cur_line[-1]["gap_x"]
                if cur_w + prev_gap + u["w"] <= avail_w:
                    cur_line.append(u)
                    cur_w += prev_gap + u["w"]
                else:
                    if cur_line[-1]["type"] == "divider":
                        div_u = cur_line.pop()
                        hidden_dividers.append(div_u["items"][0]["widget"])
                    if cur_line:
                        lines.append(cur_line)
                    cur_line = [u]
                    cur_w = u["w"]

        if cur_line and cur_line[-1]["type"] == "divider":
            div_u = cur_line.pop()
            hidden_dividers.append(div_u["items"][0]["widget"])
        if cur_line:
            lines.append(cur_line)

        return lines, hidden_dividers

    def compute_height_for_width(self, total_width: int) -> int:
        self._measure_entries()
        avail_w = max(200, total_width - self.pad_x * 2)
        lines, _ = self._compute_lines(avail_w)
        cur_y = self.pad_y
        for line in lines:
            flat_items = [it for u in line for it in u["items"]]
            if flat_items:
                line_h = max(it["h"] for it in flat_items)
                cur_y += line_h + self.row_gap
        return max(36, cur_y - (self.row_gap if lines else 0) + self.pad_y)

    def relayout(self, total_width: int) -> int:
        self._measure_entries()
        avail_w = max(200, total_width - self.pad_x * 2)
        lines, hidden_dividers = self._compute_lines(avail_w)

        for div_w in hidden_dividers:
            div_w.place_forget()

        cur_y = self.pad_y
        for line in lines:
            flat_items: List[dict] = []
            for u in line:
                flat_items.extend(u["items"])
            if not flat_items:
                continue
            line_w = sum(it["w"] for it in flat_items) + sum(
                it["gap_x"] for it in flat_items[:-1]
            )
            line_h = max(it["h"] for it in flat_items)
            cur_x = self.pad_x + max(0, (avail_w - line_w) // 2)
            for idx, it in enumerate(flat_items):
                w_obj = it["widget"]
                iy = cur_y + (line_h - it["h"]) // 2
                w_obj.place(x=cur_x, y=iy, width=it["w"], height=it["h"])
                cur_x += it["w"] + (it["gap_x"] if idx < len(flat_items) - 1 else 0)
            cur_y += line_h + self.row_gap

        total_h = max(36, cur_y - (self.row_gap if lines else 0) + self.pad_y)
        if int(self.cget("height") or 0) != total_h:
            self.configure(height=total_h)
        self._last_width = total_width
        return total_h

    def _on_configure(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        if event.width > 1 and abs(event.width - self._last_width) >= 2:
            self.relayout(event.width)


class AnnotationEditor:
    """Interactive window for drawing, selecting, and moving annotations on a screenshot."""

    # Soft Daylight Palette (fresh, bright, gentle on eyes, zero glare)
    TOOLBAR_ROW1_BG = "#e8eef5"
    TOOLBAR_ROW2_BG = "#f1f5f9"
    TOOLBAR_BORDER = "#94a3b8"
    CANVAS_AREA_BG = "#d5dfec"

    COLORS = [
        ("#ef4444", "Đỏ"),
        ("#f97316", "Cam"),
        ("#eab308", "Vàng"),
        ("#22c55e", "Xanh lá"),
        ("#06b6d4", "Xanh ngọc"),
        ("#3b82f6", "Xanh dương"),
        ("#a855f7", "Tím"),
        ("#ffffff", "Trắng"),
        ("#111827", "Đen"),
    ]

    TOOLS = [
        ("arrow", "Mũi tên"),
        ("pen", "Bút vẽ"),
        ("highlighter", "Dạ quang"),
        ("rect", "Khung"),
        ("ellipse", "Elip"),
        ("line", "Đường thẳng"),
        ("text", "Chèn chữ"),
        ("pixelate", "Làm mờ"),
    ]

    SIZES = [
        (3, "Nhỏ", 3),
        (5, "Vừa", 5),
        (9, "Lớn", 7),
        (14, "Rất lớn", 9),
    ]

    def __init__(
        self,
        root: tk.Tk,
        image: Image.Image,
        on_copy_clipboard: Callable[[Image.Image], None],
        on_close: Optional[Callable[[], None]] = None,
        logical_size: Optional[Tuple[int, int]] = None,
    ) -> None:
        self.root = root
        self.base_image = image.convert("RGB")
        self.on_copy_clipboard = on_copy_clipboard
        self.on_close = on_close

        self.items: List[AnnotationItem] = []
        self._undo_stack: List[List[AnnotationItem]] = []
        self._redo_stack: List[List[AnnotationItem]] = []

        self.selected_item: Optional[AnnotationItem] = None

        self.current_tool = "arrow"
        self.current_color = "#ef4444"
        self.current_size = 5

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        max_canvas_w = max(560, int(screen_w * 0.86))
        max_canvas_h = max(380, int(screen_h * 0.72))

        self.target_w, self.target_h = (
            logical_size
            if logical_size is not None
            else (self.base_image.width, self.base_image.height)
        )
        fit_scale = min(
            1.0,
            max_canvas_w / max(1, self.target_w),
            max_canvas_h / max(1, self.target_h),
        )
        self.canvas_w = max(1, int(round(self.target_w * fit_scale)))
        self.canvas_h = max(1, int(round(self.target_h * fit_scale)))
        self._initial_canvas_w = self.canvas_w
        self._initial_canvas_h = self.canvas_h
        self._resize_hq_after_id: Optional[str] = None
        self._window_ready = False

        self.display_scale_x = self.canvas_w / max(1, self.base_image.width)
        self.display_scale_y = self.canvas_h / max(1, self.base_image.height)

        self._interaction_mode = "none"
        self._active_handle_idx: int = -1
        self._drag_last_img_pos: Tuple[int, int] = (0, 0)
        self._drawing_item: Optional[AnnotationItem] = None
        self._drag_bg_image: Optional[Image.Image] = None

        self._cached_composite: Image.Image = self.base_image.copy()
        self._tk_image: Optional[ImageTk.PhotoImage] = None
        self._selection_canvas_ids: List[int] = []

        self._active_text_entry: Optional[tk.Entry] = None
        self._editing_text_item: Optional[AnnotationItem] = None
        self._text_img_pos: Tuple[int, int] = (0, 0)

        self._tool_buttons: Dict[str, ModernPillButton] = {}
        self._color_buttons: Dict[str, ColorSwatchButton] = {}
        self._size_buttons: Dict[int, SizeDotButton] = {}

        self._build_window()

    @property
    def working_image(self) -> Image.Image:
        """Return full-resolution composite image with all annotations rendered (no selection handles)."""
        return self._render_items_onto(self.base_image, self.items, smooth_aa=True)

    def _canvas_to_image_coords(self, cx: int, cy: int) -> Tuple[int, int]:
        ix = int(round(cx / self.display_scale_x))
        iy = int(round(cy / self.display_scale_y))
        ix = max(0, min(self.base_image.width - 1, ix))
        iy = max(0, min(self.base_image.height - 1, iy))
        return ix, iy

    def _image_to_canvas_coords(self, ix: float, iy: float) -> Tuple[int, int]:
        cx = int(round(ix * self.display_scale_x))
        cy = int(round(iy * self.display_scale_y))
        return cx, cy

    def _save_undo_snapshot(self) -> None:
        snapshot = [item.clone() for item in self.items]
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _build_window(self) -> None:
        from app.i18n import APP_NAME, get_editor_sizes, get_editor_tools, tr
        from app.tray import apply_window_icon

        self.win = tk.Toplevel(self.root)
        self.win.withdraw()
        try:
            self.win.attributes("-alpha", 0.0)
        except Exception:
            pass
        self.win.title(APP_NAME)
        self.win.configure(bg=self.CANVAS_AREA_BG)
        self.win.resizable(True, True)

        # ==================== TOP TOOLBAR ROW 1 (RESPONSIVE FLOW): DRAWING TOOLS & HISTORY ====================
        self.top_bar_flow = ResponsiveFlowBar(
            self.win, bg=self.TOOLBAR_ROW1_BG, pad_x=16, pad_y=8, row_gap=6
        )
        self.top_bar_flow.pack(side=tk.TOP, fill=tk.X)

        for tool_id, label in get_editor_tools():
            btn = ModernPillButton(
                self.top_bar_flow,
                text=label,
                icon_name=tool_id,
                parent_bg=self.TOOLBAR_ROW1_BG,
                bg_normal="#ffffff",
                bg_hover="#e0f2fe",
                bg_active="#0284c7",
                fg_normal="#1e293b",
                fg_hover="#0369a1",
                fg_active="#ffffff",
                border_active=None,
                border_normal="#cbd5e1",
                border_hover="#7dd3fc",
                font_pt=12,
                height_pt=32,
                command=lambda t=tool_id: self._select_tool(t),
            )
            self.top_bar_flow.add_widget(btn, gap_x=8)
            self._tool_buttons[tool_id] = btn

        self.top_bar_flow.add_divider(bg="#cbd5e1", height=28, gap_x=14)

        self.btn_undo = ModernPillButton(
            self.top_bar_flow,
            text=tr("editor_undo"),
            icon_name="undo",
            parent_bg=self.TOOLBAR_ROW1_BG,
            bg_normal="#ffffff",
            bg_hover="#e0f2fe",
            fg_normal="#1e293b",
            fg_hover="#0369a1",
            border_normal="#cbd5e1",
            border_hover="#7dd3fc",
            font_pt=12,
            height_pt=32,
            command=self.undo,
        )
        self.top_bar_flow.add_widget(self.btn_undo, gap_x=6)

        self.btn_redo = ModernPillButton(
            self.top_bar_flow,
            text=tr("editor_redo"),
            icon_name="redo",
            parent_bg=self.TOOLBAR_ROW1_BG,
            bg_normal="#ffffff",
            bg_hover="#e0f2fe",
            fg_normal="#1e293b",
            fg_hover="#0369a1",
            border_normal="#cbd5e1",
            border_hover="#7dd3fc",
            font_pt=12,
            height_pt=32,
            command=self.redo,
        )
        self.top_bar_flow.add_widget(self.btn_redo, gap_x=6)

        self.btn_clear = ModernPillButton(
            self.top_bar_flow,
            text=tr("editor_clear"),
            icon_name="clear",
            parent_bg=self.TOOLBAR_ROW1_BG,
            bg_normal="#fff1f2",
            bg_hover="#ffe4e6",
            fg_normal="#be123c",
            fg_hover="#9f1239",
            border_normal="#fecdd3",
            border_hover="#fda4af",
            font_pt=12,
            height_pt=32,
            command=self.clear_all,
        )
        self.top_bar_flow.add_widget(self.btn_clear, gap_x=6)

        # Subtle divider line between Row 1 and Row 2
        tk.Frame(self.win, bg="#cbd5e1", height=1).pack(side=tk.TOP, fill=tk.X)

        # ==================== TOP TOOLBAR ROW 2 (RESPONSIVE FLOW): COLORS, STROKE SIZE & EXPORT ====================
        self.sub_bar_flow = ResponsiveFlowBar(
            self.win, bg=self.TOOLBAR_ROW2_BG, pad_x=14, pad_y=8, row_gap=6
        )
        self.sub_bar_flow.pack(side=tk.TOP, fill=tk.X)

        color_label = tk.Label(
            self.sub_bar_flow,
            text=tr("editor_color_label"),
            font=("Roboto", 10, "bold"),
            fg="#1e293b",
            bg=self.TOOLBAR_ROW2_BG,
        )
        self.sub_bar_flow.add_widget(
            color_label, gap_x=6, keep_with_next=True, glue_next=True
        )

        for hex_code, _name in self.COLORS:
            c_btn = ColorSwatchButton(
                self.sub_bar_flow,
                hex_color=hex_code,
                base_size=24,
                parent_bg=self.TOOLBAR_ROW2_BG,
                command=lambda c=hex_code: self._select_color(c),
            )
            self.sub_bar_flow.add_widget(c_btn, gap_x=5)
            self._color_buttons[hex_code] = c_btn

        custom_color_btn = ModernPillButton(
            self.sub_bar_flow,
            text=tr("editor_custom_color"),
            icon_name="palette",
            parent_bg=self.TOOLBAR_ROW2_BG,
            bg_normal="#ffffff",
            bg_hover="#e0f2fe",
            fg_normal="#1e293b",
            fg_hover="#0369a1",
            border_normal="#cbd5e1",
            border_hover="#7dd3fc",
            font_pt=11,
            height_pt=30,
            command=self._pick_custom_color,
        )
        self.sub_bar_flow.add_widget(custom_color_btn, gap_x=12)

        self.sub_bar_flow.add_divider(bg="#cbd5e1", height=26, gap_x=12)

        size_label = tk.Label(
            self.sub_bar_flow,
            text=tr("editor_size_label"),
            font=("Roboto", 10, "bold"),
            fg="#1e293b",
            bg=self.TOOLBAR_ROW2_BG,
        )
        self.sub_bar_flow.add_widget(
            size_label, gap_x=6, keep_with_next=True, glue_next=True
        )

        editor_sizes = get_editor_sizes()
        for idx_sz, (sz_val, sz_name, dot_r) in enumerate(editor_sizes):
            s_btn = SizeDotButton(
                self.sub_bar_flow,
                size_val=sz_val,
                label_text=sz_name,
                dot_radius_pt=dot_r,
                parent_bg=self.TOOLBAR_ROW2_BG,
                command=lambda s=sz_val: self._select_size(s),
            )
            is_last_sz = idx_sz == len(editor_sizes) - 1
            self.sub_bar_flow.add_widget(
                s_btn,
                gap_x=12 if is_last_sz else 5,
            )
            self._size_buttons[sz_val] = s_btn

        self.sub_bar_flow.add_divider(bg="#cbd5e1", height=26, gap_x=12)

        btn_copy = ModernPillButton(
            self.sub_bar_flow,
            text=tr("editor_copy_btn"),
            icon_name="copy",
            parent_bg=self.TOOLBAR_ROW2_BG,
            bg_normal="#059669",
            bg_hover="#047857",
            fg_normal="#ffffff",
            fg_hover="#ffffff",
            border_normal=None,
            border_hover=None,
            font_pt=11,
            height_pt=30,
            command=self.copy_and_finish,
        )
        self.sub_bar_flow.add_widget(btn_copy, gap_x=6)

        btn_save = ModernPillButton(
            self.sub_bar_flow,
            text=tr("editor_save_btn"),
            icon_name="save",
            parent_bg=self.TOOLBAR_ROW2_BG,
            bg_normal="#0284c7",
            bg_hover="#0369a1",
            fg_normal="#ffffff",
            fg_hover="#ffffff",
            border_normal=None,
            border_hover=None,
            font_pt=11,
            height_pt=30,
            command=self.save_to_file,
        )
        self.sub_bar_flow.add_widget(btn_save, gap_x=6)

        btn_close = ModernPillButton(
            self.sub_bar_flow,
            text=tr("editor_close_btn"),
            icon_name="close",
            parent_bg=self.TOOLBAR_ROW2_BG,
            bg_normal="#e2e8f0",
            bg_hover="#fee2e2",
            fg_normal="#334155",
            fg_hover="#b91c1c",
            border_normal=None,
            border_hover=None,
            font_pt=11,
            height_pt=30,
            command=self.close_editor,
        )
        self.sub_bar_flow.add_widget(btn_close, gap_x=6)

        # Soft slate divider separating menu bar from canvas area
        tk.Frame(self.win, bg=self.TOOLBAR_BORDER, height=1).pack(
            side=tk.TOP, fill=tk.X
        )

        # ==================== BOTTOM STATUS BAR (PACKED BEFORE CANVAS SO IT NEVER CLIPS) ====================
        status_text = tr(
            "editor_status_bar",
            w=self.base_image.width,
            h=self.base_image.height,
        )
        status_bar = tk.Label(
            self.win,
            text=status_text,
            font=("Roboto", 9, "bold"),
            fg="#334155",
            bg=self.TOOLBAR_ROW1_BG,
            anchor=tk.CENTER,
            padx=14,
            pady=6,
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # ==================== IMAGE CANVAS AREA ====================
        self.canvas_container = tk.Frame(
            self.win,
            bg=self.CANVAS_AREA_BG,
            width=self.canvas_w + 36,
            height=self.canvas_h + 28,
        )
        self.canvas_container.pack_propagate(False)
        self.canvas_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        canvas_border = tk.Frame(self.canvas_container, bg="#64748b", padx=1, pady=1)
        canvas_border.pack(expand=True)

        self.canvas = tk.Canvas(
            canvas_border,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#f8fafc",
            highlightthickness=0,
            bd=0,
            cursor="crosshair",
        )
        self.canvas.pack()
        self._canvas_img_id = self.canvas.create_image(0, 0, anchor=tk.NW)

        self._select_tool("arrow")
        self._select_color("#ef4444")
        self._select_size(5)

        # Bind canvas & keyboard events
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas_container.bind("<Configure>", self._on_canvas_container_configure)

        self.win.bind("<Control-z>", lambda _e: self.undo())
        self.win.bind("<Control-Z>", lambda _e: self.undo())
        self.win.bind("<Control-y>", lambda _e: self.redo())
        self.win.bind("<Control-Y>", lambda _e: self.redo())
        self.win.bind("<Control-s>", lambda _e: self.save_to_file())
        self.win.bind("<Control-S>", lambda _e: self.save_to_file())
        self.win.bind("<Control-c>", self._on_ctrl_c)
        self.win.bind("<Control-C>", self._on_ctrl_c)
        self.win.bind("<Delete>", self._on_delete_key)
        self.win.bind("<BackSpace>", self._on_delete_key)
        self.win.bind("<Return>", self._on_enter_key)
        self.win.bind("<Escape>", self._on_escape_key)
        self.win.protocol("WM_DELETE_WINDOW", self.close_editor)

        self._rebuild_composite_and_refresh(high_quality=True)

        self.win.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        dpi_scale = _get_dpi_scale(self.win)

        min_w = min(screen_w - 40, max(720, int(round(700 * dpi_scale))))
        top_min_h = self.top_bar_flow.compute_height_for_width(min_w)
        sub_min_h = self.sub_bar_flow.compute_height_for_width(min_w)
        status_h = max(28, status_bar.winfo_reqheight())
        min_canvas_h = max(160, min(220, self.canvas_h + 28))
        min_h = min(
            screen_h - 60,
            top_min_h + sub_min_h + min_canvas_h + status_h + 4,
        )
        self.win.minsize(min_w, min_h)

        single_row_w = max(
            self.top_bar_flow.get_single_row_width(),
            self.sub_bar_flow.get_single_row_width(),
        )
        max_win_w = max(min_w, int(screen_w * 0.92))
        win_w = min(max_win_w, max(min_w, single_row_w, self.canvas_w + 36))
        top_h = self.top_bar_flow.relayout(win_w)
        sub_h = self.sub_bar_flow.relayout(win_w)
        win_h = min(
            max(min_h, int(screen_h * 0.90)),
            max(min_h, top_h + sub_h + self.canvas_h + 28 + status_h + 4),
        )

        pos_x = max(10, (screen_w - win_w) // 2)
        pos_y = max(10, (screen_h - win_h) // 2 - 20)
        self.win.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.win.update_idletasks()
        apply_window_icon(self.win)
        try:
            self.win.attributes("-topmost", True)
        except Exception:
            pass
        self.win.deiconify()
        self.win.lift()
        self.win.update_idletasks()
        try:
            self.win.attributes("-alpha", 1.0)
            self.win.focus_force()
        except Exception:
            pass
        self._window_ready = True
        self.win.bind("<Unmap>", self._on_window_unmap)

    def _on_canvas_container_configure(self, event: tk.Event) -> None:
        if not self._window_ready or event.widget is not self.canvas_container:
            return
        if self._interaction_mode != "none":
            return
        avail_w = max(80, event.width - 36)
        avail_h = max(80, event.height - 28)

        # Allow scaling down when window is shrunk, or scaling up up to 1.0 (or larger if window expanded beyond 1:1)
        max_scale = 1.0
        if avail_w > self.target_w and avail_h > self.target_h and (
            avail_w > self._initial_canvas_w + 60 and avail_h > self._initial_canvas_h + 60
        ):
            max_scale = min(2.0, avail_w / max(1, self.target_w), avail_h / max(1, self.target_h))

        fit_scale = min(
            max_scale,
            avail_w / max(1, self.target_w),
            avail_h / max(1, self.target_h),
        )
        new_cw = max(1, int(round(self.target_w * fit_scale)))
        new_ch = max(1, int(round(self.target_h * fit_scale)))

        if abs(new_cw - self.canvas_w) < 2 and abs(new_ch - self.canvas_h) < 2:
            return

        self.canvas_w = new_cw
        self.canvas_h = new_ch
        self.display_scale_x = self.canvas_w / max(1, self.base_image.width)
        self.display_scale_y = self.canvas_h / max(1, self.base_image.height)
        self.canvas.configure(width=self.canvas_w, height=self.canvas_h)

        if self._active_text_entry is not None:
            try:
                tx, ty = self._image_to_canvas_coords(*self._text_img_pos)
                self._active_text_entry.place(x=tx, y=ty)
            except Exception:
                pass

        self._refresh_canvas(high_quality=False)
        self._draw_selection_overlay()

        if self._resize_hq_after_id is not None:
            try:
                self.win.after_cancel(self._resize_hq_after_id)
            except Exception:
                pass
        self._resize_hq_after_id = self.win.after(70, self._finish_high_quality_resize)

    def _finish_high_quality_resize(self) -> None:
        self._resize_hq_after_id = None
        if not self._window_ready:
            return
        try:
            if self.win.winfo_exists():
                self._refresh_canvas(high_quality=True)
                self._draw_selection_overlay()
        except Exception:
            pass

    def _on_window_unmap(self, event: tk.Event) -> None:
        if event.widget is not self.win:
            return
        try:
            if self.win.winfo_exists() and self.win.state() == "iconic":
                self.close_editor()
        except Exception:
            pass

    def _select_tool(self, tool_id: str) -> None:
        self._commit_active_text()
        self.current_tool = tool_id
        for t_id, btn in self._tool_buttons.items():
            btn.set_active(t_id == tool_id)

    def _select_color(self, hex_color: str) -> None:
        self.current_color = hex_color
        for c_hex, btn in self._color_buttons.items():
            btn.set_active(c_hex.lower() == hex_color.lower())

        if self.selected_item is not None and self.selected_item in self.items:
            if self.selected_item.color.lower() != hex_color.lower():
                self._save_undo_snapshot()
                self.selected_item.color = hex_color
                self._rebuild_composite_and_refresh(high_quality=True)

    def _pick_custom_color(self) -> None:
        from app.i18n import tr

        result = colorchooser.askcolor(
            color=self.current_color,
            title=tr("editor_custom_color_title"),
            parent=self.win,
        )
        if result and result[1]:
            self._select_color(result[1])

    def _select_size(self, size_val: int) -> None:
        self.current_size = size_val
        for s_val, btn in self._size_buttons.items():
            btn.set_active(s_val == size_val)

        if self.selected_item is not None and self.selected_item in self.items:
            if self.selected_item.size != size_val:
                self._save_undo_snapshot()
                self.selected_item.size = size_val
                self.selected_item.stroke_px = self._scaled_stroke_width(size_val)
                self.selected_item.font_px = self._scaled_font_px(size_val)
                self._rebuild_composite_and_refresh(high_quality=True)

    def _scaled_stroke_width(self, size_override: Optional[int] = None) -> int:
        sz = size_override if size_override is not None else self.current_size
        inv = 1.0 / max(0.25, min(self.display_scale_x, self.display_scale_y))
        return max(2, int(round(sz * inv)))

    def _scaled_font_px(self, size_override: Optional[int] = None) -> int:
        sz = size_override if size_override is not None else self.current_size
        inv = 1.0 / max(0.25, min(self.display_scale_x, self.display_scale_y))
        return max(18, int(round(sz * 4.5 * inv)))

    def _push_history(self, new_img: Image.Image) -> None:
        self.base_image = new_img.convert("RGB")
        self._rebuild_composite_and_refresh(high_quality=True)

    def undo(self) -> None:
        self._commit_active_text()
        if self._undo_stack:
            self._redo_stack.append([item.clone() for item in self.items])
            self.items = self._undo_stack.pop()
            self.selected_item = self.items[-1] if self.items else None
            self._rebuild_composite_and_refresh(high_quality=True)

    def redo(self) -> None:
        self._commit_active_text()
        if self._redo_stack:
            self._undo_stack.append([item.clone() for item in self.items])
            self.items = self._redo_stack.pop()
            self.selected_item = self.items[-1] if self.items else None
            self._rebuild_composite_and_refresh(high_quality=True)

    def clear_all(self) -> None:
        self._commit_active_text()
        if self.items:
            self._save_undo_snapshot()
            self.items.clear()
            self.selected_item = None
            self._rebuild_composite_and_refresh(high_quality=True)

    def _on_delete_key(self, _event=None) -> None:
        if self._active_text_entry is not None:
            return
        if self.selected_item is not None and self.selected_item in self.items:
            self._save_undo_snapshot()
            self.items.remove(self.selected_item)
            self.selected_item = self.items[-1] if self.items else None
            self._rebuild_composite_and_refresh(high_quality=True)

    # ==================== HIT TESTING & MOUSE INTERACTION ====================

    def _find_handle_at(self, ix: int, iy: int) -> int:
        if self.selected_item is None or self.selected_item not in self.items:
            return -1
        inv = 1.0 / max(0.25, min(self.display_scale_x, self.display_scale_y))
        handle_tol = max(14, int(round(12 * inv)))
        for idx, (hx, hy) in enumerate(self.selected_item.get_handles()):
            if math.hypot(ix - hx, iy - hy) <= handle_tol:
                return idx
        return -1

    def _find_item_at(self, ix: int, iy: int) -> Optional[AnnotationItem]:
        inv = 1.0 / max(0.25, min(self.display_scale_x, self.display_scale_y))
        base_tol = max(12, int(round(10 * inv)))
        if self.selected_item in self.items and self.selected_item.hit_test(
            ix, iy, base_tol
        ):
            return self.selected_item
        for item in reversed(self.items):
            if item.hit_test(ix, iy, base_tol):
                return item
        return None

    def _on_mouse_move(self, event: tk.Event) -> None:
        if self._interaction_mode != "none" or self._active_text_entry is not None:
            return
        ix, iy = self._canvas_to_image_coords(event.x, event.y)
        if self._find_handle_at(ix, iy) >= 0:
            self.canvas.configure(cursor="hand2")
        elif self._find_item_at(ix, iy) is not None:
            self.canvas.configure(cursor="fleur")
        else:
            self.canvas.configure(cursor="crosshair")

    def _on_double_click(self, event: tk.Event) -> None:
        ix, iy = self._canvas_to_image_coords(event.x, event.y)
        hit = self._find_item_at(ix, iy)
        if hit is not None and hit.tool == "text":
            self._commit_active_text()
            self.selected_item = hit
            self._editing_text_item = hit
            cx, cy = self._image_to_canvas_coords(hit.points[0][0], hit.points[0][1])
            self._spawn_text_entry(cx, cy, initial_text=hit.text)

    def _on_mouse_down(self, event: tk.Event) -> None:
        if self._active_text_entry is not None:
            self._commit_active_text()
            return

        ix, iy = self._canvas_to_image_coords(event.x, event.y)

        h_idx = self._find_handle_at(ix, iy)
        if h_idx >= 0 and self.selected_item is not None:
            self._save_undo_snapshot()
            self._interaction_mode = "handle"
            self._active_handle_idx = h_idx
            self._drag_last_img_pos = (ix, iy)
            other_items = [it for it in self.items if it is not self.selected_item]
            self._drag_bg_image = self._render_items_onto(
                self.base_image, other_items, smooth_aa=False
            )
            self.canvas.configure(cursor="hand2")
            return

        hit_item = self._find_item_at(ix, iy)
        if hit_item is not None:
            self._save_undo_snapshot()
            self.selected_item = hit_item
            self._interaction_mode = "moving"
            self._drag_last_img_pos = (ix, iy)
            other_items = [it for it in self.items if it is not hit_item]
            self._drag_bg_image = self._render_items_onto(
                self.base_image, other_items, smooth_aa=False
            )
            self.canvas.configure(cursor="fleur")
            self._draw_selection_overlay()
            return

        self.selected_item = None
        self._clear_selection_overlay()

        if self.current_tool == "text":
            self._editing_text_item = None
            self._spawn_text_entry(event.x, event.y)
            return

        self._interaction_mode = "drawing"
        self._drag_bg_image = self._cached_composite.copy()
        self._drawing_item = AnnotationItem(
            tool=self.current_tool,
            color=self.current_color,
            size=self.current_size,
            stroke_px=self._scaled_stroke_width(),
            points=[(ix, iy)],
            font_px=self._scaled_font_px(),
        )

    def _on_mouse_drag(self, event: tk.Event) -> None:
        if self._interaction_mode == "none":
            return

        ix, iy = self._canvas_to_image_coords(event.x, event.y)

        if self._interaction_mode == "moving" and self.selected_item is not None:
            dx = ix - self._drag_last_img_pos[0]
            dy = iy - self._drag_last_img_pos[1]
            if dx == 0 and dy == 0:
                return
            self.selected_item.translate(
                dx, dy, self.base_image.width, self.base_image.height
            )
            self._drag_last_img_pos = (ix, iy)

            bg = self._drag_bg_image if self._drag_bg_image is not None else self.base_image
            preview = self._render_items_onto(bg, [self.selected_item], smooth_aa=False)
            self._refresh_canvas(preview, high_quality=False)
            self._draw_selection_overlay()
            return

        if self._interaction_mode == "handle" and self.selected_item is not None:
            self.selected_item.move_handle(self._active_handle_idx, ix, iy)
            self._drag_last_img_pos = (ix, iy)

            bg = self._drag_bg_image if self._drag_bg_image is not None else self.base_image
            preview = self._render_items_onto(bg, [self.selected_item], smooth_aa=False)
            self._refresh_canvas(preview, high_quality=False)
            self._draw_selection_overlay()
            return

        if self._interaction_mode == "drawing" and self._drawing_item is not None:
            if self._drawing_item.tool in ("pen", "highlighter"):
                self._drawing_item.points.append((ix, iy))
            else:
                if len(self._drawing_item.points) == 1:
                    self._drawing_item.points.append((ix, iy))
                else:
                    self._drawing_item.points[-1] = (ix, iy)

            bg = self._drag_bg_image if self._drag_bg_image is not None else self._cached_composite
            preview = self._render_items_onto(bg, [self._drawing_item], smooth_aa=False)
            self._refresh_canvas(preview, high_quality=False)

    def _on_mouse_up(self, event: tk.Event) -> None:
        if self._interaction_mode == "none":
            return

        ix, iy = self._canvas_to_image_coords(event.x, event.y)
        mode = self._interaction_mode
        self._interaction_mode = "none"
        self._active_handle_idx = -1
        self._drag_bg_image = None

        if mode in ("moving", "handle"):
            self._rebuild_composite_and_refresh(high_quality=True)
            return

        if mode == "drawing" and self._drawing_item is not None:
            item = self._drawing_item
            self._drawing_item = None

            if item.tool in ("pen", "highlighter"):
                item.points.append((ix, iy))
            else:
                if len(item.points) == 1:
                    item.points.append((ix, iy))
                else:
                    item.points[-1] = (ix, iy)

                p0, p1 = item.points[0], item.points[-1]
                if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 4:
                    self._rebuild_composite_and_refresh(high_quality=True)
                    return

            self._save_undo_snapshot()
            self.items.append(item)
            self.selected_item = item
            self._rebuild_composite_and_refresh(high_quality=True)

    # ==================== RENDERING & SELECTION OVERLAY ====================

    def _rebuild_composite_and_refresh(self, high_quality: bool = True) -> None:
        self._cached_composite = self._render_items_onto(
            self.base_image, self.items, smooth_aa=high_quality
        )
        self._refresh_canvas(self._cached_composite, high_quality=high_quality)
        self._draw_selection_overlay()

    def _refresh_canvas(
        self,
        img_override: Optional[Image.Image] = None,
        high_quality: bool = True,
    ) -> None:
        src = img_override if img_override is not None else self._cached_composite
        if (src.width, src.height) != (self.canvas_w, self.canvas_h):
            resample = (
                Image.Resampling.LANCZOS
                if high_quality
                else Image.Resampling.BILINEAR
            )
            disp = src.resize((self.canvas_w, self.canvas_h), resample)
        else:
            disp = src
        self._tk_image = ImageTk.PhotoImage(disp)
        self.canvas.itemconfigure(self._canvas_img_id, image=self._tk_image)

    def _clear_selection_overlay(self) -> None:
        for cid in self._selection_canvas_ids:
            try:
                self.canvas.delete(cid)
            except Exception:
                pass
        self._selection_canvas_ids.clear()

    def _draw_selection_overlay(self) -> None:
        self._clear_selection_overlay()
        item = self.selected_item
        if item is None or item not in self.items:
            return

        if item.tool not in ("arrow", "line"):
            bx1, by1, bx2, by2 = item.get_bbox()
            cx1, cy1 = self._image_to_canvas_coords(bx1, by1)
            cx2, cy2 = self._image_to_canvas_coords(bx2, by2)
            rect_id = self.canvas.create_rectangle(
                cx1,
                cy1,
                cx2,
                cy2,
                outline="#38bdf8",
                dash=(4, 4),
                width=1,
            )
            self._selection_canvas_ids.append(rect_id)

        r = 5
        for hx, hy in item.get_handles():
            chx, chy = self._image_to_canvas_coords(hx, hy)
            hid = self.canvas.create_oval(
                chx - r,
                chy - r,
                chx + r,
                chy + r,
                fill="#ffffff",
                outline="#0284c7",
                width=2,
            )
            self._selection_canvas_ids.append(hid)

    def _render_stroke(
        self,
        base: Image.Image,
        points: List[Tuple[int, int]],
        smooth_aa: bool = True,
    ) -> Image.Image:
        temp_item = AnnotationItem(
            tool=self.current_tool,
            color=self.current_color,
            size=self.current_size,
            stroke_px=self._scaled_stroke_width(),
            points=points,
            font_px=self._scaled_font_px(),
        )
        return self._render_items_onto(base, [temp_item], smooth_aa=smooth_aa)

    def _render_items_onto(
        self,
        base: Image.Image,
        items_to_draw: List[AnnotationItem],
        smooth_aa: bool = True,
    ) -> Image.Image:
        if not items_to_draw:
            return base.copy()

        out = base.copy()

        for item in items_to_draw:
            if item.tool == "pixelate" and len(item.points) >= 2:
                x1, y1 = item.points[0]
                x2, y2 = item.points[-1]
                rx1, rx2 = max(0, min(x1, x2)), min(out.width, max(x1, x2))
                ry1, ry2 = max(0, min(y1, y2)), min(out.height, max(y1, y2))
                if rx2 - rx1 >= 4 and ry2 - ry1 >= 4:
                    region = out.crop((rx1, ry1, rx2, ry2))
                    block_size = max(10, item.stroke_px * 2)
                    small_w = max(1, (rx2 - rx1) // block_size)
                    small_h = max(1, (ry2 - ry1) // block_size)
                    mosaic = region.resize(
                        (small_w, small_h), Image.Resampling.BILINEAR
                    ).resize(region.size, Image.Resampling.NEAREST)
                    out.paste(mosaic, (rx1, ry1))

        vector_items = [it for it in items_to_draw if it.tool != "pixelate"]
        if not vector_items:
            return out

        ss = 2 if (smooth_aa and max(out.width, out.height) <= 3200) else 1
        W, H = out.width * ss, out.height * ss
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        for item in vector_items:
            if not item.points:
                continue
            tool = item.tool
            rgb = _hex_to_rgb(item.color)
            sw = max(2, item.stroke_px * ss)
            x1, y1 = item.points[0]
            x2, y2 = item.points[-1]

            if tool == "pen":
                rgba = (rgb[0], rgb[1], rgb[2], 255)
                r = max(1, sw // 2)
                scaled_pts = [(px * ss, py * ss) for px, py in item.points]
                if len(scaled_pts) == 1:
                    px, py = scaled_pts[0]
                    draw.ellipse((px - r, py - r, px + r, py + r), fill=rgba)
                else:
                    draw.line(scaled_pts, fill=rgba, width=sw, joint="curve")
                    for px, py in scaled_pts:
                        draw.ellipse((px - r, py - r, px + r, py + r), fill=rgba)

            elif tool == "highlighter":
                hl_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                hl_draw = ImageDraw.Draw(hl_layer)
                rgba = (rgb[0], rgb[1], rgb[2], 96)
                hl_w = max(14 * ss, sw * 3)
                r = hl_w // 2
                scaled_pts = [(px * ss, py * ss) for px, py in item.points]
                if len(scaled_pts) == 1:
                    px, py = scaled_pts[0]
                    hl_draw.ellipse((px - r, py - r, px + r, py + r), fill=rgba)
                else:
                    hl_draw.line(scaled_pts, fill=rgba, width=hl_w, joint="curve")
                    for px, py in scaled_pts[::2]:
                        hl_draw.ellipse((px - r, py - r, px + r, py + r), fill=rgba)
                overlay = Image.alpha_composite(overlay, hl_layer)
                draw = ImageDraw.Draw(overlay)

            elif tool == "line":
                rgba = (rgb[0], rgb[1], rgb[2], 255)
                sx1, sy1, sx2, sy2 = x1 * ss, y1 * ss, x2 * ss, y2 * ss
                r = max(1, sw // 2)
                draw.line([(sx1, sy1), (sx2, sy2)], fill=rgba, width=sw)
                draw.ellipse((sx1 - r, sy1 - r, sx1 + r, sy1 + r), fill=rgba)
                draw.ellipse((sx2 - r, sy2 - r, sx2 + r, sy2 + r), fill=rgba)

            elif tool == "arrow":
                self._draw_pro_arrow(
                    draw,
                    x1 * ss,
                    y1 * ss,
                    x2 * ss,
                    y2 * ss,
                    rgb,
                    sw,
                )

            elif tool == "rect":
                rgba = (rgb[0], rgb[1], rgb[2], 255)
                rx1, rx2 = min(x1, x2) * ss, max(x1, x2) * ss
                ry1, ry2 = min(y1, y2) * ss, max(y1, y2) * ss
                draw.rectangle([rx1, ry1, rx2, ry2], outline=rgba, width=sw)

            elif tool == "ellipse":
                rgba = (rgb[0], rgb[1], rgb[2], 255)
                rx1, rx2 = min(x1, x2) * ss, max(x1, x2) * ss
                ry1, ry2 = min(y1, y2) * ss, max(y1, y2) * ss
                draw.ellipse([rx1, ry1, rx2, ry2], outline=rgba, width=sw)

            elif tool == "text" and item.text:
                rgba = (rgb[0], rgb[1], rgb[2], 255)
                f_px = item.font_px * ss
                font = _load_ui_font(f_px, bold=True)
                lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
                stroke_fill = (15, 23, 42, 245) if lum > 110 else (255, 255, 255, 245)
                stroke_w = max(2, f_px // 11)
                try:
                    draw.text(
                        (x1 * ss, y1 * ss),
                        item.text,
                        fill=rgba,
                        font=font,
                        stroke_width=stroke_w,
                        stroke_fill=stroke_fill,
                    )
                except TypeError:
                    draw.text((x1 * ss, y1 * ss), item.text, fill=rgba, font=font)

        if ss > 1:
            overlay = overlay.resize(out.size, Image.Resampling.LANCZOS)

        composited = Image.alpha_composite(out.convert("RGBA"), overlay)
        return composited.convert("RGB")

    @staticmethod
    def _draw_pro_arrow(
        draw: ImageDraw.ImageDraw,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        rgb: Tuple[int, int, int],
        width: int,
    ) -> None:
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 4:
            return

        ux = dx / length
        uy = dy / length
        px = -uy
        py = ux

        head_len = min(max(width * 4.5, 22.0), max(24.0, length * 0.55))
        head_half_w = head_len * 0.52
        neck_indent = head_len * 0.78

        tail_half_w = max(1.5, width * 0.28)
        neck_half_w = max(2.5, width * 0.58)

        nx = x2 - ux * neck_indent
        ny = y2 - uy * neck_indent

        bx = x2 - ux * head_len
        by = y2 - uy * head_len

        poly = [
            (x1 + px * tail_half_w, y1 + py * tail_half_w),
            (nx + px * neck_half_w, ny + py * neck_half_w),
            (bx + px * head_half_w, by + py * head_half_w),
            (x2, y2),
            (bx - px * head_half_w, by - py * head_half_w),
            (nx - px * neck_half_w, ny - py * neck_half_w),
            (x1 - px * tail_half_w, y1 - py * tail_half_w),
        ]

        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        outline_rgba = (15, 23, 42, 180) if lum > 90 else (255, 255, 255, 190)
        fill_rgba = (rgb[0], rgb[1], rgb[2], 255)

        draw.polygon(
            poly,
            fill=fill_rgba,
            outline=outline_rgba,
            width=max(2, width // 5),
        )
        tr = int(round(tail_half_w))
        draw.ellipse((x1 - tr, y1 - tr, x1 + tr, y1 + tr), fill=fill_rgba)

    # ==================== INLINE TEXT ENTRY ====================

    def _spawn_text_entry(
        self, canvas_x: int, canvas_y: int, initial_text: str = ""
    ) -> None:
        self._text_img_pos = self._canvas_to_image_coords(canvas_x, canvas_y)
        font_pt = max(12, self.current_size * 3)

        entry = tk.Entry(
            self.canvas,
            font=("Roboto", font_pt, "bold"),
            fg=self.current_color,
            bg="#0f172a",
            insertbackground="#ffffff",
            relief=tk.SOLID,
            bd=1,
            width=24,
        )
        if initial_text:
            entry.insert(0, initial_text)
            entry.select_range(0, tk.END)
        entry.place(x=canvas_x, y=canvas_y)
        entry.focus_set()
        entry.bind("<Return>", lambda _e: self._commit_active_text())
        entry.bind("<Escape>", lambda _e: self._cancel_active_text())
        self._active_text_entry = entry

    def _cancel_active_text(self) -> None:
        self._editing_text_item = None
        if self._active_text_entry is not None:
            try:
                self._active_text_entry.destroy()
            except Exception:
                pass
            self._active_text_entry = None

    def _commit_active_text(self) -> None:
        if self._active_text_entry is None:
            return
        entry = self._active_text_entry
        editing_item = self._editing_text_item
        self._active_text_entry = None
        self._editing_text_item = None
        try:
            text_val = entry.get().strip()
            entry.destroy()
        except Exception:
            return

        if editing_item is not None and editing_item in self.items:
            self._save_undo_snapshot()
            if not text_val:
                self.items.remove(editing_item)
                self.selected_item = None
            else:
                editing_item.text = text_val
                self.selected_item = editing_item
            self._rebuild_composite_and_refresh(high_quality=True)
            return

        if not text_val:
            return

        self._save_undo_snapshot()
        new_text_item = AnnotationItem(
            tool="text",
            color=self.current_color,
            size=self.current_size,
            stroke_px=self._scaled_stroke_width(),
            points=[self._text_img_pos],
            text=text_val,
            font_px=self._scaled_font_px(),
        )
        self.items.append(new_text_item)
        self.selected_item = new_text_item
        self._rebuild_composite_and_refresh(high_quality=True)

    # ==================== SHORTCUTS & EXPORT ====================

    def _on_ctrl_c(self, _event=None) -> None:
        if self._active_text_entry is not None:
            return
        self.copy_and_finish()

    def _on_enter_key(self, _event=None) -> None:
        if self._active_text_entry is not None:
            self._commit_active_text()
            return
        self.copy_and_finish()

    def _on_escape_key(self, _event=None) -> None:
        if self._active_text_entry is not None:
            self._cancel_active_text()
            return
        if self.selected_item is not None:
            self.selected_item = None
            self._clear_selection_overlay()
            return
        self.close_editor()

    def save_to_file(self) -> None:
        from app.i18n import tr

        self._commit_active_text()
        default_name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        file_path = filedialog.asksaveasfilename(
            parent=self.win,
            title=tr("editor_save_dialog_title"),
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[
                ("PNG Lossless (*.png)", "*.png"),
                ("JPEG High Quality (*.jpg)", "*.jpg;*.jpeg"),
                ("WebP Lossless (*.webp)", "*.webp"),
                ("Bitmap (*.bmp)", "*.bmp"),
            ],
        )
        if not file_path:
            return
        export_img = self.working_image
        lower = file_path.lower()
        if lower.endswith((".jpg", ".jpeg")):
            export_img.convert("RGB").save(file_path, quality=100, subsampling=0)
        elif lower.endswith(".webp"):
            export_img.save(file_path, lossless=True, quality=100)
        elif lower.endswith(".bmp"):
            export_img.convert("RGB").save(file_path)
        else:
            from app.platform_utils import _encode_lossless_png_bytes

            Path(file_path).write_bytes(_encode_lossless_png_bytes(export_img))

    def copy_and_finish(self) -> None:
        self._commit_active_text()
        final_img = self.working_image
        self.close_editor()
        self.on_copy_clipboard(final_img)

    def close_editor(self) -> None:
        self._cancel_active_text()
        try:
            self.win.destroy()
        except Exception:
            pass
        if self.on_close is not None:
            self.on_close()
