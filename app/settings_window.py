"""Settings & Shortcut Guide Window with a Soft Daylight Theme.

Provides:
- Reassuring, concise, easy-to-understand Vietnamese text
- Soft, eye-friendly daylight color palette (bright and fresh without glare)
- High-DPI checkbox for "Khởi động cùng máy tính"
- Clear visual guide for Ctrl + 1, Ctrl + 2, and editing actions
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageTk

from app.autostart import (
    is_autostart_enabled,
    is_prtsc_enabled,
    set_autostart_enabled,
    set_prtsc_enabled,
)
from app.editor import ModernPillButton, _get_dpi_scale, _hex_to_rgba
from app.tray import create_tray_icon_image


class ModernCheckbox(tk.Frame):
    """High-DPI anti-aliased custom checkbox on a soft daylight surface."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        initial_checked: bool,
        on_toggle: Callable[[bool], None],
        subtitle: str = "",
        bg: str = "#ffffff",
    ) -> None:
        super().__init__(parent, bg=bg, cursor="hand2")
        self.checked = initial_checked
        self.on_toggle = on_toggle
        self.bg = bg
        self.dpi_scale = _get_dpi_scale(parent)
        self.box_size = max(26, int(round(22 * self.dpi_scale)))

        self._img_unchecked = self._render_box(checked=False, hovered=False)
        self._img_unchecked_hover = self._render_box(checked=False, hovered=True)
        self._img_checked = self._render_box(checked=True, hovered=False)
        self._img_checked_hover = self._render_box(checked=True, hovered=True)
        self._hovered = False

        self.box_lbl = tk.Label(
            self,
            bg=bg,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            image=self._img_checked if self.checked else self._img_unchecked,
        )
        self.box_lbl.pack(side=tk.LEFT, padx=(0, 12), pady=2)

        text_frame = tk.Frame(self, bg=bg, cursor="hand2")
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.title_lbl = tk.Label(
            text_frame,
            text=title,
            font=("Roboto", 11, "bold"),
            fg="#1e293b",
            bg=bg,
            anchor=tk.W,
            cursor="hand2",
        )
        self.title_lbl.pack(side=tk.TOP, anchor=tk.W)

        clickable_widgets = [self, self.box_lbl, text_frame, self.title_lbl]
        if subtitle:
            self.sub_lbl = tk.Label(
                text_frame,
                text=subtitle,
                font=("Roboto", 9),
                fg="#475569",
                bg=bg,
                anchor=tk.W,
                cursor="hand2",
            )
            self.sub_lbl.pack(side=tk.TOP, anchor=tk.W, pady=(2, 0))
            clickable_widgets.append(self.sub_lbl)

        for w in clickable_widgets:
            w.bind("<ButtonPress-1>", self._handle_click)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _render_box(self, checked: bool, hovered: bool) -> ImageTk.PhotoImage:
        ss = 3
        S = self.box_size * ss
        img = Image.new("RGBA", (S, S), _hex_to_rgba(self.bg, 255))
        draw = ImageDraw.Draw(img)

        pad = int(round(2 * self.dpi_scale * ss))
        radius = int(round(6 * self.dpi_scale * ss))

        if checked:
            fill_c = "#059669" if hovered else "#10b981"
            border_c = "#047857"
        else:
            fill_c = "#e0f2fe" if hovered else "#f1f5f9"
            border_c = "#0284c7" if hovered else "#94a3b8"

        draw.rounded_rectangle(
            (pad, pad, S - pad, S - pad),
            radius=radius,
            fill=_hex_to_rgba(fill_c, 255),
            outline=_hex_to_rgba(border_c, 255),
            width=max(2, int(round(1.5 * self.dpi_scale * ss))),
        )

        if checked:
            w = max(4, int(round(2.4 * self.dpi_scale * ss)))
            p1 = (int(S * 0.26), int(S * 0.52))
            p2 = (int(S * 0.44), int(S * 0.70))
            p3 = (int(S * 0.76), int(S * 0.30))
            draw.line([p1, p2, p3], fill=(255, 255, 255, 255), width=w, joint="curve")

        smooth = img.resize((self.box_size, self.box_size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(smooth)

    def set_checked(self, checked: bool) -> None:
        self.checked = checked
        self._refresh_visual()

    def _handle_click(self, _event=None) -> None:
        self.checked = not self.checked
        self._refresh_visual()
        self.on_toggle(self.checked)

    def _on_enter(self, _event=None) -> None:
        self._hovered = True
        self._refresh_visual()

    def _on_leave(self, _event=None) -> None:
        self._hovered = False
        self._refresh_visual()

    def _refresh_visual(self) -> None:
        if self.checked:
            img = self._img_checked_hover if self._hovered else self._img_checked
        else:
            img = self._img_unchecked_hover if self._hovered else self._img_unchecked
        self.box_lbl.configure(image=img)


class SettingsAndGuideWindow:
    """Soft Daylight window displaying auto-start, PrtSc, language settings, and shortcut instructions."""

    # Soft Daylight Palette (fresh, bright, zero glare)
    BG_MAIN = "#edf2f7"
    BG_HEADER = "#ffffff"
    BG_CARD = "#ffffff"
    BG_ROW_ALT = "#f8fafc"
    BORDER_SOFT = "#cbd5e1"
    TEXT_PRIMARY = "#1e293b"
    TEXT_SECONDARY = "#475569"

    def __init__(
        self,
        root: tk.Tk,
        on_trigger_ctrl1: Callable[[], None],
        on_trigger_ctrl2: Callable[[], None],
        on_autostart_changed: Optional[Callable[[bool], None]] = None,
        on_prtsc_changed: Optional[Callable[[bool], None]] = None,
        on_language_changed: Optional[Callable[[str], None]] = None,
        on_minimized_to_tray: Optional[Callable[[], None]] = None,
    ) -> None:
        self.root = root
        self.on_trigger_ctrl1 = on_trigger_ctrl1
        self.on_trigger_ctrl2 = on_trigger_ctrl2
        self.on_autostart_changed = on_autostart_changed
        self.on_prtsc_changed = on_prtsc_changed
        self.on_language_changed = on_language_changed
        self.on_minimized_to_tray = on_minimized_to_tray
        self.win: Optional[tk.Toplevel] = None
        self._body_frame: Optional[tk.Frame] = None
        self._closing = False
        self._checkbox: Optional[ModernCheckbox] = None
        self._status_lbl: Optional[tk.Label] = None
        self._prtsc_checkbox: Optional[ModernCheckbox] = None
        self._prtsc_status_lbl: Optional[tk.Label] = None
        self._lang_btn_vi: Optional[ModernPillButton] = None
        self._lang_btn_en: Optional[ModernPillButton] = None

    def show(self) -> None:
        """Open or bring the Settings & Guide window to the front."""
        if self.win is not None:
            try:
                if self.win.winfo_exists():
                    auto_val = is_autostart_enabled()
                    prtsc_val = is_prtsc_enabled()
                    if self._checkbox is not None:
                        self._checkbox.set_checked(auto_val)
                    self._update_status_label(self._status_lbl, auto_val)
                    if self._prtsc_checkbox is not None:
                        self._prtsc_checkbox.set_checked(prtsc_val)
                    self._update_status_label(self._prtsc_status_lbl, prtsc_val)
                    self.win.deiconify()
                    self.win.state("normal")
                    self.win.lift()
                    self.win.focus_force()
                    return
            except Exception:
                pass
            self.win = None

        self._build_window()

    def _build_window(self, preserve_pos: Optional[ tuple[int, int] ] = None) -> None:
        from app.i18n import APP_NAME
        from app.tray import apply_window_icon

        self._closing = False
        win = tk.Toplevel(self.root)
        self.win = win
        win.title(APP_NAME)
        win.configure(bg=self.BG_MAIN)
        win.resizable(False, False)
        apply_window_icon(win)
        try:
            win.attributes("-topmost", True)
        except Exception:
            pass

        self._populate_window_content(win)

        win.bind("<Escape>", lambda _e: self.minimize_to_tray())
        win.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        win.bind("<Unmap>", self._on_window_unmap)

        win.update_idletasks()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        if preserve_pos is not None:
            x, y = preserve_pos
        else:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(16, (sw - w) // 2)
            y = max(16, (sh - h) // 2 - 20)
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.lift()
        try:
            win.focus_force()
        except Exception:
            pass

    def _populate_window_content(self, win: tk.Toplevel) -> None:
        from app.i18n import get_language, get_shortcuts_guide, tr

        if self._body_frame is not None:
            try:
                self._body_frame.destroy()
            except Exception:
                pass

        # ==================== MAIN BODY ====================
        body = tk.Frame(win, bg=self.BG_MAIN, padx=22, pady=18)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._body_frame = body

        # --- Card 1: Settings (Auto-start, PrtSc key & Language) ---
        card_setting_border = tk.Frame(body, bg=self.BORDER_SOFT, padx=1, pady=1)
        card_setting_border.pack(side=tk.TOP, fill=tk.X, pady=(0, 14))

        card_setting = tk.Frame(card_setting_border, bg=self.BG_CARD, padx=16, pady=10)
        card_setting.pack(fill=tk.X)

        # Row 1: Auto-start checkbox (compact, no subtitle)
        row_auto = tk.Frame(card_setting, bg=self.BG_CARD, pady=4)
        row_auto.pack(side=tk.TOP, fill=tk.X)

        current_auto = is_autostart_enabled()
        self._checkbox = ModernCheckbox(
            row_auto,
            title=tr("settings_autostart_title"),
            initial_checked=current_auto,
            on_toggle=self._on_toggle_autostart,
            bg=self.BG_CARD,
        )
        self._checkbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._status_lbl = tk.Label(
            row_auto,
            text="",
            font=("Roboto", 9, "bold"),
            bg=self.BG_CARD,
            padx=10,
            pady=4,
        )
        self._status_lbl.pack(side=tk.RIGHT)
        self._update_status_label(self._status_lbl, current_auto)

        # Subtle divider
        tk.Frame(card_setting, bg="#e2e8f0", height=1).pack(
            side=tk.TOP, fill=tk.X, pady=6
        )

        # Row 2: PrtSc key checkbox (same as Ctrl + 1)
        row_prtsc = tk.Frame(card_setting, bg=self.BG_CARD, pady=4)
        row_prtsc.pack(side=tk.TOP, fill=tk.X)

        current_prtsc = is_prtsc_enabled()
        self._prtsc_checkbox = ModernCheckbox(
            row_prtsc,
            title=tr("settings_prtsc_title"),
            initial_checked=current_prtsc,
            on_toggle=self._on_toggle_prtsc,
            bg=self.BG_CARD,
        )
        self._prtsc_checkbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._prtsc_status_lbl = tk.Label(
            row_prtsc,
            text="",
            font=("Roboto", 9, "bold"),
            bg=self.BG_CARD,
            padx=10,
            pady=4,
        )
        self._prtsc_status_lbl.pack(side=tk.RIGHT)
        self._update_status_label(self._prtsc_status_lbl, current_prtsc)

        # Subtle divider
        tk.Frame(card_setting, bg="#e2e8f0", height=1).pack(
            side=tk.TOP, fill=tk.X, pady=6
        )

        # Row 3: Language Selector (Tiếng Việt / English)
        row_lang = tk.Frame(card_setting, bg=self.BG_CARD, pady=4)
        row_lang.pack(side=tk.TOP, fill=tk.X)

        lang_lbl = tk.Label(
            row_lang,
            text=tr("settings_lang_title"),
            font=("Roboto", 11, "bold"),
            fg=self.TEXT_PRIMARY,
            bg=self.BG_CARD,
            anchor=tk.W,
        )
        lang_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        lang_btn_frame = tk.Frame(row_lang, bg=self.BG_CARD)
        lang_btn_frame.pack(side=tk.RIGHT)

        cur_lang = get_language()
        self._lang_btn_vi = ModernPillButton(
            lang_btn_frame,
            text="Tiếng Việt",
            icon_name=None,
            parent_bg=self.BG_CARD,
            bg_normal="#f1f5f9",
            bg_hover="#e0f2fe",
            bg_active="#0284c7",
            fg_normal="#334155",
            fg_hover="#0369a1",
            fg_active="#ffffff",
            border_normal="#cbd5e1",
            border_hover="#7dd3fc",
            border_active=None,
            font_pt=10,
            height_pt=28,
            pad_x_pt=12,
            command=lambda: self._on_select_language("vi"),
        )
        self._lang_btn_vi.pack(side=tk.LEFT, padx=(0, 6))
        self._lang_btn_vi.set_active(cur_lang == "vi")

        self._lang_btn_en = ModernPillButton(
            lang_btn_frame,
            text="English",
            icon_name=None,
            parent_bg=self.BG_CARD,
            bg_normal="#f1f5f9",
            bg_hover="#e0f2fe",
            bg_active="#0284c7",
            fg_normal="#334155",
            fg_hover="#0369a1",
            fg_active="#ffffff",
            border_normal="#cbd5e1",
            border_hover="#7dd3fc",
            border_active=None,
            font_pt=10,
            height_pt=28,
            pad_x_pt=12,
            command=lambda: self._on_select_language("en"),
        )
        self._lang_btn_en.pack(side=tk.LEFT)
        self._lang_btn_en.set_active(cur_lang == "en")

        # --- Card 2: Shortcuts & Usage Guide Table ---
        guide_title = tk.Label(
            body,
            text=tr("guide_section_title"),
            font=("Roboto", 10, "bold"),
            fg="#0369a1",
            bg=self.BG_MAIN,
            anchor=tk.W,
        )
        guide_title.pack(side=tk.TOP, anchor=tk.W, pady=(2, 8))

        # Unified table grid: bg=BORDER_SOFT with 1px cell spacing creates crisp table gridlines
        table_grid = tk.Frame(body, bg=self.BORDER_SOFT)
        table_grid.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        table_grid.grid_columnconfigure(0, weight=0)
        table_grid.grid_columnconfigure(1, weight=0)
        table_grid.grid_columnconfigure(2, weight=1)

        # Table Header Row
        hdr_bg = "#e2e8f0"
        headers = [
            (tr("table_col_shortcut"), tk.CENTER),
            (tr("table_col_function"), tk.W),
            (tr("table_col_desc"), tk.W),
        ]
        for col_idx, (hdr_text, hdr_anchor) in enumerate(headers):
            hdr_cell = tk.Frame(table_grid, bg=hdr_bg, padx=14, pady=8)
            hdr_cell.grid(
                row=0,
                column=col_idx,
                sticky="nsew",
                padx=(1 if col_idx == 0 else 0, 1),
                pady=(1, 1),
            )
            tk.Label(
                hdr_cell,
                text=hdr_text,
                font=("Roboto", 9, "bold"),
                fg="#334155",
                bg=hdr_bg,
                anchor=hdr_anchor,
            ).pack(fill=tk.X, expand=True)

        # Table Data Rows (all sharing the exact same column grid)
        for row_idx, (
            key_text,
            key_fg,
            key_bg,
            action_title,
            desc_text,
        ) in enumerate(get_shortcuts_guide(), start=1):
            row_bg = self.BG_CARD if row_idx % 2 == 1 else self.BG_ROW_ALT

            # Column 0: Key badge cell (centered)
            c0 = tk.Frame(table_grid, bg=row_bg, padx=12, pady=8)
            c0.grid(row=row_idx, column=0, sticky="nsew", padx=(1, 1), pady=(0, 1))

            badge_outer = tk.Frame(c0, bg=key_fg, padx=1, pady=1)
            badge_outer.pack(expand=True)

            key_lbl = tk.Label(
                badge_outer,
                text=key_text,
                font=("Roboto", 9, "bold"),
                fg=key_fg,
                bg=key_bg,
                width=16,
                pady=3,
                anchor=tk.CENTER,
            )
            key_lbl.pack()

            # Column 1: Feature name cell (left-aligned, vertically centered)
            c1 = tk.Frame(table_grid, bg=row_bg, padx=14, pady=8)
            c1.grid(row=row_idx, column=1, sticky="nsew", padx=(0, 1), pady=(0, 1))

            act_lbl = tk.Label(
                c1,
                text=action_title,
                font=("Roboto", 9, "bold"),
                fg=self.TEXT_PRIMARY,
                bg=row_bg,
                anchor=tk.W,
                justify=tk.LEFT,
            )
            act_lbl.pack(fill=tk.X, expand=True)

            # Column 2: Description cell (left-aligned, vertically centered)
            c2 = tk.Frame(table_grid, bg=row_bg, padx=14, pady=8)
            c2.grid(row=row_idx, column=2, sticky="nsew", padx=(0, 1), pady=(0, 1))

            desc_lbl = tk.Label(
                c2,
                text=desc_text,
                font=("Roboto", 9),
                fg=self.TEXT_SECONDARY,
                bg=row_bg,
                anchor=tk.W,
                justify=tk.LEFT,
                wraplength=430,
            )
            desc_lbl.pack(fill=tk.X, expand=True)

    @staticmethod
    def _update_status_label(lbl: Optional[tk.Label], enabled: bool) -> None:
        from app.i18n import tr

        if lbl is None:
            return
        if enabled:
            lbl.configure(
                text=tr("status_enabled"),
                fg="#047857",
                bg="#d1fae5",
            )
        else:
            lbl.configure(
                text=tr("status_disabled"),
                fg="#64748b",
                bg="#f1f5f9",
            )

    def _on_select_language(self, lang: str) -> None:
        from app.i18n import get_language, set_language

        if lang == get_language():
            return
        set_language(lang)
        if self.win is not None and self.win.winfo_exists():
            cur_x = self.win.winfo_x()
            cur_y = self.win.winfo_y()
            self._populate_window_content(self.win)
            self.win.update_idletasks()
            w = self.win.winfo_reqwidth()
            h = self.win.winfo_reqheight()
            self.win.geometry(f"{w}x{h}+{cur_x}+{cur_y}")
        if self.on_language_changed is not None:
            self.on_language_changed(lang)

    def _on_toggle_autostart(self, enabled: bool) -> None:
        ok, _msg = set_autostart_enabled(enabled)
        actual = is_autostart_enabled() if not ok else enabled
        if self._checkbox is not None and actual != enabled:
            self._checkbox.set_checked(actual)
        self._update_status_label(self._status_lbl, actual)
        if self.on_autostart_changed is not None:
            self.on_autostart_changed(actual)

    def _on_toggle_prtsc(self, enabled: bool) -> None:
        ok, _msg = set_prtsc_enabled(enabled)
        actual = is_prtsc_enabled() if not ok else enabled
        if self._prtsc_checkbox is not None and actual != enabled:
            self._prtsc_checkbox.set_checked(actual)
        self._update_status_label(self._prtsc_status_lbl, actual)
        if self.on_prtsc_changed is not None:
            self.on_prtsc_changed(actual)

    def _on_window_unmap(self, event: tk.Event) -> None:
        """Detect when user clicks the '-' (Minimize) button and hide window to System Tray."""
        if event.widget is not self.win or self._closing:
            return
        self.root.after(15, self._check_minimized_state)

    def _check_minimized_state(self) -> None:
        if self.win is None or self._closing:
            return
        try:
            if self.win.winfo_exists() and self.win.state() == "iconic":
                self.minimize_to_tray()
        except Exception:
            pass

    def minimize_to_tray(self) -> None:
        """Close/hide the window to the System Tray when clicking X or -."""
        was_open = self.win is not None
        self.close()
        if was_open and self.on_minimized_to_tray is not None:
            self.on_minimized_to_tray()

    def _trigger_1_from_window(self) -> None:
        self.close()
        self.on_trigger_ctrl1()

    def _trigger_2_from_window(self) -> None:
        self.close()
        self.on_trigger_ctrl2()

    def close(self) -> None:
        self._closing = True
        if self.win is not None:
            try:
                self.win.destroy()
            except Exception:
                pass
            self.win = None
            self._body_frame = None
