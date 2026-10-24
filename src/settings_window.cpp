#include "settings_window.h"
#include "autostart.h"
#include "i18n.h"
#include "platform_utils.h"

namespace app {

namespace {
constexpr const wchar_t* kSettingsClassName = L"CaptureToClipboard_SettingsWnd";

void DrawCustomCheckbox(
    Gdiplus::Graphics& g,
    float x,
    float y,
    float size,
    bool checked,
    bool hovered,
    float dpi) {

    Gdiplus::Color fill_c;
    Gdiplus::Color border_c;
    if (checked) {
        fill_c = hovered ? HexToColor(L"#059669") : HexToColor(L"#10b981");
        border_c = HexToColor(L"#047857");
    } else {
        fill_c = hovered ? HexToColor(L"#e0f2fe") : HexToColor(L"#f1f5f9");
        border_c = hovered ? HexToColor(L"#0284c7") : HexToColor(L"#94a3b8");
    }

    float pad = std::round(1.5f * dpi);
    Gdiplus::RectF box(x + pad, y + pad, size - pad * 2.0f, size - pad * 2.0f);
    DrawRoundedRect(g, box, std::round(5.5f * dpi), fill_c, border_c, std::max(1.5f, 1.4f * dpi));

    if (checked) {
        Gdiplus::Pen check_pen(Gdiplus::Color(255, 255, 255, 255), std::max(2.2f, 2.2f * dpi));
        check_pen.SetStartCap(Gdiplus::LineCapRound);
        check_pen.SetEndCap(Gdiplus::LineCapRound);
        check_pen.SetLineJoin(Gdiplus::LineJoinRound);
        Gdiplus::PointF pts[3] = {
            {x + size * 0.27f, y + size * 0.52f},
            {x + size * 0.44f, y + size * 0.70f},
            {x + size * 0.75f, y + size * 0.31f}
        };
        g.DrawLines(&check_pen, pts, 3);
    }
}

void DrawStatusBadge(
    Gdiplus::Graphics& g,
    float right_x,
    float center_y,
    bool enabled,
    float dpi,
    Gdiplus::Font* font) {

    std::wstring txt = enabled ? Tr(L"status_enabled") : Tr(L"status_disabled");
    Gdiplus::Color fg = enabled ? HexToColor(L"#047857") : HexToColor(L"#64748b");
    Gdiplus::Color bg = enabled ? HexToColor(L"#d1fae5") : HexToColor(L"#f1f5f9");

    Gdiplus::RectF box;
    g.MeasureString(txt.c_str(), -1, font, Gdiplus::PointF(0, 0), &box);
    float bw = std::ceil(box.Width) + std::round(18.0f * dpi);
    float bh = std::round(24.0f * dpi);
    Gdiplus::RectF rc(right_x - bw, center_y - bh * 0.5f, bw, bh);

    FillRoundedRect(g, rc, std::round(5.0f * dpi), bg);
    Gdiplus::SolidBrush tb(fg);
    Gdiplus::StringFormat sf;
    sf.SetAlignment(Gdiplus::StringAlignmentCenter);
    sf.SetLineAlignment(Gdiplus::StringAlignmentCenter);
    g.DrawString(txt.c_str(), -1, font, rc, &sf, &tb);
}

} // namespace

SettingsAndGuideWindow::SettingsAndGuideWindow(
    OnAutostartChanged on_autostart_changed,
    OnPrtScChanged on_prtsc_changed,
    OnLanguageChanged on_language_changed,
    OnMinimizedToTray on_minimized_to_tray)
    : on_autostart_changed_(std::move(on_autostart_changed)),
      on_prtsc_changed_(std::move(on_prtsc_changed)),
      on_language_changed_(std::move(on_language_changed)),
      on_minimized_to_tray_(std::move(on_minimized_to_tray)) {}

SettingsAndGuideWindow::~SettingsAndGuideWindow() {
    Close(true);
}

bool SettingsAndGuideWindow::IsVisible() const {
    return hwnd_ != nullptr && IsWindow(hwnd_) && IsWindowVisible(hwnd_) && !IsIconic(hwnd_);
}

void SettingsAndGuideWindow::RefreshState() {
    autostart_checked_ = IsAutostartEnabled();
    prtsc_checked_ = IsPrtScEnabled();
    if (hwnd_ && IsWindow(hwnd_)) {
        InvalidateRect(hwnd_, nullptr, FALSE);
    }
}

void SettingsAndGuideWindow::Show() {
    autostart_checked_ = IsAutostartEnabled();
    prtsc_checked_ = IsPrtScEnabled();

    if (hwnd_ && IsWindow(hwnd_)) {
        ShowWindow(hwnd_, SW_RESTORE);
        ShowWindow(hwnd_, SW_SHOW);
        SetForegroundWindow(hwnd_);
        SetFocus(hwnd_);
        InvalidateRect(hwnd_, nullptr, FALSE);
        UpdateWindow(hwnd_);
        return;
    }

    static bool class_registered = false;
    if (!class_registered) {
        WNDCLASSEXW wc{};
        wc.cbSize = sizeof(wc);
        wc.style = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc = SettingsAndGuideWindow::WndProc;
        wc.hInstance = GetModuleHandleW(nullptr);
        wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
        wc.hIcon = GetAppIcon(std::max(32, GetSystemMetrics(SM_CXICON)));
        wc.hIconSm = GetAppIcon(std::max(16, GetSystemMetrics(SM_CXSMICON)));
        wc.lpszClassName = kSettingsClassName;
        RegisterClassExW(&wc);
        class_registered = true;
    }

    DWORD style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX;
    hwnd_ = CreateWindowExW(
        WS_EX_TOPMOST,
        kSettingsClassName,
        APP_TITLE_WITH_VERSION_W,
        style,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        820,
        630,
        nullptr,
        nullptr,
        GetModuleHandleW(nullptr),
        this);

    if (!hwnd_) return;

    ApplyWindowIcon(hwnd_);
    ComputeLayoutAndResize(true);
    ShowWindow(hwnd_, SW_SHOW);
    SetForegroundWindow(hwnd_);
    SetFocus(hwnd_);
    UpdateWindow(hwnd_);
}

void SettingsAndGuideWindow::ComputeLayoutAndResize(bool center_on_screen) {
    if (!hwnd_) return;
    float dpi = GetWindowDpiScale(hwnd_);

    int client_w = static_cast<int>(std::round(820.0f * dpi));
    int pad_x = static_cast<int>(std::round(20.0f * dpi));
    int pad_y = static_cast<int>(std::round(14.0f * dpi));
    int card1_h = static_cast<int>(std::round(138.0f * dpi));
    int section_hdr_h = static_cast<int>(std::round(28.0f * dpi));

    // Measure table height based on 8 rows
    int table_hdr_h = static_cast<int>(std::round(34.0f * dpi));
    int row_h = static_cast<int>(std::round(44.0f * dpi));
    const auto& rows = GetShortcutsGuide();
    int table_h = table_hdr_h + static_cast<int>(rows.size()) * row_h + 2;
    int footer_gap = static_cast<int>(std::round(12.0f * dpi));
    int footer_h = static_cast<int>(std::round(40.0f * dpi));

    int client_h = pad_y + card1_h + static_cast<int>(std::round(12.0f * dpi)) + section_hdr_h + table_h + footer_gap + footer_h + pad_y;

    RECT wr = {0, 0, client_w, client_h};
    DWORD style = static_cast<DWORD>(GetWindowLongW(hwnd_, GWL_STYLE));
    DWORD ex_style = static_cast<DWORD>(GetWindowLongW(hwnd_, GWL_EXSTYLE));
    AdjustWindowRectEx(&wr, style, FALSE, ex_style);
    int win_w = wr.right - wr.left;
    int win_h = wr.bottom - wr.top;

    int x = 0, y = 0;
    if (center_on_screen) {
        int sw = GetSystemMetrics(SM_CXSCREEN);
        int sh = GetSystemMetrics(SM_CYSCREEN);
        x = std::max(16, (sw - win_w) / 2);
        y = std::max(16, (sh - win_h) / 2 - 20);
    } else {
        RECT cur_rc{};
        GetWindowRect(hwnd_, &cur_rc);
        x = cur_rc.left;
        y = cur_rc.top;
    }

    SetWindowPos(hwnd_, HWND_TOPMOST, x, y, win_w, win_h, SWP_NOACTIVATE);
}

void SettingsAndGuideWindow::Close(bool destroy) {
    if (!hwnd_ || !IsWindow(hwnd_)) {
        hwnd_ = nullptr;
        return;
    }
    if (!destroy) {
        ShowWindow(hwnd_, SW_HIDE);
        return;
    }
    DestroyWindow(hwnd_);
    hwnd_ = nullptr;
}

void SettingsAndGuideWindow::MinimizeToTray() {
    bool was_visible = IsVisible();
    Close(false);
    if (was_visible && on_minimized_to_tray_) {
        on_minimized_to_tray_();
    }
}

SettingsAndGuideWindow::HitZone SettingsAndGuideWindow::HitTest(int x, int y) const {
    Gdiplus::PointF pt(static_cast<float>(x), static_cast<float>(y));
    if (rc_kahub_link_.Contains(pt)) return HitZone::KahubLink;
    if (rc_lang_vi_.Contains(pt)) return HitZone::LangViBtn;
    if (rc_lang_en_.Contains(pt)) return HitZone::LangEnBtn;
    if (rc_autostart_row_.Contains(pt)) return HitZone::AutostartRow;
    if (rc_prtsc_row_.Contains(pt)) return HitZone::PrtScRow;
    return HitZone::None;
}

void SettingsAndGuideWindow::Render(HDC hdc, int width, int height) {
    if (width <= 0 || height <= 0) return;

    Gdiplus::Bitmap back_bmp(width, height, PixelFormat32bppARGB);
    Gdiplus::Graphics g(&back_bmp);
    g.SetSmoothingMode(Gdiplus::SmoothingModeAntiAlias);
    g.SetTextRenderingHint(Gdiplus::TextRenderingHintClearTypeGridFit);

    float dpi = GetWindowDpiScale(hwnd_);

    Gdiplus::Color bg_main = HexToColor(L"#edf2f7");
    Gdiplus::Color bg_card = HexToColor(L"#ffffff");
    Gdiplus::Color bg_row_alt = HexToColor(L"#f8fafc");
    Gdiplus::Color border_soft = HexToColor(L"#cbd5e1");
    Gdiplus::Color divider_col = HexToColor(L"#e2e8f0");
    Gdiplus::Color text_primary = HexToColor(L"#1e293b");
    Gdiplus::Color text_secondary = HexToColor(L"#475569");

    g.Clear(bg_main);

    auto font_row_title = CreateUiFont(14.5f * dpi, true);
    auto font_status = CreateUiFont(12.0f * dpi, true);
    auto font_lang_btn = CreateUiFont(13.0f * dpi, true);
    auto font_sec_hdr = CreateUiFont(13.0f * dpi, true);
    auto font_tbl_hdr = CreateUiFont(12.0f * dpi, true);
    auto font_badge = CreateUiFont(12.0f * dpi, true);
    auto font_act = CreateUiFont(12.5f * dpi, true);
    auto font_desc = CreateUiFont(12.0f * dpi, false);

    float pad_x = std::round(20.0f * dpi);
    float cur_y = std::round(14.0f * dpi);
    float content_w = static_cast<float>(width) - pad_x * 2.0f;

    // ==================== CARD 1: SETTINGS ====================
    float card1_h = std::round(138.0f * dpi);
    Gdiplus::RectF card1_rc(pad_x, cur_y, content_w, card1_h);
    DrawRoundedRect(g, card1_rc, std::round(6.0f * dpi), bg_card, border_soft, 1.0f);

    float inner_x = pad_x + std::round(16.0f * dpi);
    float inner_right = pad_x + content_w - std::round(16.0f * dpi);
    float row_h = std::round(38.0f * dpi);
    float box_sz = std::round(22.0f * dpi);

    Gdiplus::SolidBrush br_primary(text_primary);
    Gdiplus::SolidBrush br_secondary(text_secondary);
    Gdiplus::StringFormat sf_vcenter;
    sf_vcenter.SetAlignment(Gdiplus::StringAlignmentNear);
    sf_vcenter.SetLineAlignment(Gdiplus::StringAlignmentCenter);

    // Row 1: Autostart
    float r1_y = cur_y + std::round(8.0f * dpi);
    rc_autostart_row_ = Gdiplus::RectF(inner_x, r1_y, inner_right - inner_x, row_h);
    DrawCustomCheckbox(
        g,
        inner_x,
        r1_y + (row_h - box_sz) * 0.5f,
        box_sz,
        autostart_checked_,
        hovered_zone_ == HitZone::AutostartRow,
        dpi);
    std::wstring auto_title = Tr(L"settings_autostart_title");
    g.DrawString(
        auto_title.c_str(),
        -1,
        font_row_title.get(),
        Gdiplus::RectF(inner_x + box_sz + std::round(12.0f * dpi), r1_y, inner_right - inner_x - box_sz - 120.0f * dpi, row_h),
        &sf_vcenter,
        &br_primary);
    DrawStatusBadge(g, inner_right, r1_y + row_h * 0.5f, autostart_checked_, dpi, font_status.get());

    // Divider 1
    float div1_y = r1_y + row_h + std::round(3.0f * dpi);
    Gdiplus::Pen div_pen(divider_col, 1.0f);
    g.DrawLine(&div_pen, inner_x, div1_y, inner_right, div1_y);

    // Row 2: PrtSc
    float r2_y = div1_y + std::round(4.0f * dpi);
    rc_prtsc_row_ = Gdiplus::RectF(inner_x, r2_y, inner_right - inner_x, row_h);
    DrawCustomCheckbox(
        g,
        inner_x,
        r2_y + (row_h - box_sz) * 0.5f,
        box_sz,
        prtsc_checked_,
        hovered_zone_ == HitZone::PrtScRow,
        dpi);
    std::wstring prtsc_title = Tr(L"settings_prtsc_title");
    g.DrawString(
        prtsc_title.c_str(),
        -1,
        font_row_title.get(),
        Gdiplus::RectF(inner_x + box_sz + std::round(12.0f * dpi), r2_y, inner_right - inner_x - box_sz - 120.0f * dpi, row_h),
        &sf_vcenter,
        &br_primary);
    DrawStatusBadge(g, inner_right, r2_y + row_h * 0.5f, prtsc_checked_, dpi, font_status.get());

    // Divider 2
    float div2_y = r2_y + row_h + std::round(3.0f * dpi);
    g.DrawLine(&div_pen, inner_x, div2_y, inner_right, div2_y);

    // Row 3: Language
    float r3_y = div2_y + std::round(4.0f * dpi);
    std::wstring lang_title = Tr(L"settings_lang_title");
    g.DrawString(
        lang_title.c_str(),
        -1,
        font_row_title.get(),
        Gdiplus::RectF(inner_x, r3_y, 400.0f * dpi, row_h),
        &sf_vcenter,
        &br_primary);

    std::wstring cur_lang = GetLanguage();
    float btn_h = std::round(28.0f * dpi);
    float btn_y = r3_y + (row_h - btn_h) * 0.5f;
    float btn_en_w = std::round(86.0f * dpi);
    float btn_vi_w = std::round(100.0f * dpi);
    float btn_gap = std::round(6.0f * dpi);

    rc_lang_en_ = Gdiplus::RectF(inner_right - btn_en_w, btn_y, btn_en_w, btn_h);
    rc_lang_vi_ = Gdiplus::RectF(rc_lang_en_.X - btn_gap - btn_vi_w, btn_y, btn_vi_w, btn_h);

    auto draw_lang_pill = [&](const Gdiplus::RectF& rc, const wchar_t* label, bool active, bool hovered) {
        Gdiplus::Color bg = active ? HexToColor(L"#0284c7") : (hovered ? HexToColor(L"#e0f2fe") : HexToColor(L"#f1f5f9"));
        Gdiplus::Color fg = active ? HexToColor(L"#ffffff") : (hovered ? HexToColor(L"#0369a1") : HexToColor(L"#334155"));
        Gdiplus::Color bd = active ? HexToColor(L"#0284c7") : (hovered ? HexToColor(L"#7dd3fc") : HexToColor(L"#cbd5e1"));
        DrawRoundedRect(g, rc, std::round(5.5f * dpi), bg, bd, 1.0f);
        Gdiplus::SolidBrush fb(fg);
        Gdiplus::StringFormat sfc;
        sfc.SetAlignment(Gdiplus::StringAlignmentCenter);
        sfc.SetLineAlignment(Gdiplus::StringAlignmentCenter);
        g.DrawString(label, -1, font_lang_btn.get(), rc, &sfc, &fb);
    };

    draw_lang_pill(rc_lang_vi_, L"Ti\u1EBFng Vi\u1EC7t", cur_lang == L"vi", hovered_zone_ == HitZone::LangViBtn);
    draw_lang_pill(rc_lang_en_, L"English", cur_lang == L"en", hovered_zone_ == HitZone::LangEnBtn);

    cur_y += card1_h + std::round(12.0f * dpi);

    // ==================== CARD 2: SHORTCUTS GUIDE TABLE ====================
    int micro_icon_sz = std::max(16, static_cast<int>(std::round(16.0f * dpi)));
    float sec_text_x = pad_x + static_cast<float>(micro_icon_sz) + std::round(6.0f * dpi);
    float sec_hdr_y = cur_y;
    std::wstring sec_title = Tr(L"guide_section_title");
    Gdiplus::SolidBrush br_sec(HexToColor(L"#0369a1"));
    g.DrawString(sec_title.c_str(), -1, font_sec_hdr.get(), Gdiplus::PointF(sec_text_x, sec_hdr_y), &br_sec);
    cur_y += std::round(26.0f * dpi);

    float col0_w = std::round(156.0f * dpi);
    float col1_w = std::round(192.0f * dpi);
    float col2_w = content_w - col0_w - col1_w;

    float tbl_hdr_h = std::round(34.0f * dpi);
    const auto& rows = GetShortcutsGuide();
    float tbl_row_h = std::round(44.0f * dpi);
    float tbl_total_h = tbl_hdr_h + static_cast<float>(rows.size()) * tbl_row_h;

    Gdiplus::RectF tbl_rc(pad_x, cur_y, content_w, tbl_total_h);
    Gdiplus::SolidBrush br_hdr_bg(HexToColor(L"#e2e8f0"));
    g.FillRectangle(&br_hdr_bg, pad_x, cur_y, content_w, tbl_hdr_h);

    Gdiplus::SolidBrush br_hdr_fg(HexToColor(L"#334155"));
    Gdiplus::StringFormat sf_center;
    sf_center.SetAlignment(Gdiplus::StringAlignmentCenter);
    sf_center.SetLineAlignment(Gdiplus::StringAlignmentCenter);

    std::wstring h0 = Tr(L"table_col_shortcut");
    std::wstring h1 = Tr(L"table_col_function");
    std::wstring h2 = Tr(L"table_col_desc");

    g.DrawString(h0.c_str(), -1, font_tbl_hdr.get(), Gdiplus::RectF(pad_x, cur_y, col0_w, tbl_hdr_h), &sf_center, &br_hdr_fg);
    g.DrawString(
        h1.c_str(),
        -1,
        font_tbl_hdr.get(),
        Gdiplus::RectF(pad_x + col0_w + std::round(14.0f * dpi), cur_y, col1_w - std::round(14.0f * dpi), tbl_hdr_h),
        &sf_vcenter,
        &br_hdr_fg);
    g.DrawString(
        h2.c_str(),
        -1,
        font_tbl_hdr.get(),
        Gdiplus::RectF(pad_x + col0_w + col1_w + std::round(14.0f * dpi), cur_y, col2_w - std::round(14.0f * dpi), tbl_hdr_h),
        &sf_vcenter,
        &br_hdr_fg);

    Gdiplus::Pen grid_pen(border_soft, 1.0f);
    float ry = cur_y + tbl_hdr_h;
    for (size_t i = 0; i < rows.size(); ++i) {
        const auto& r = rows[i];
        Gdiplus::Color r_bg = (i % 2 == 0) ? bg_card : bg_row_alt;
        Gdiplus::SolidBrush br_rbg(r_bg);
        g.FillRectangle(&br_rbg, pad_x, ry, content_w, tbl_row_h);
        g.DrawLine(&grid_pen, pad_x, ry, pad_x + content_w, ry);

        // Col 0: Key badge
        float bw = col0_w - std::round(24.0f * dpi);
        float bh = std::round(24.0f * dpi);
        Gdiplus::RectF badge_rc(
            pad_x + (col0_w - bw) * 0.5f,
            ry + (tbl_row_h - bh) * 0.5f,
            bw,
            bh);
        Gdiplus::Color k_fg = HexToColor(r.key_fg);
        Gdiplus::Color k_bg = HexToColor(r.key_bg);
        DrawRoundedRect(g, badge_rc, std::round(4.0f * dpi), k_bg, k_fg, 1.0f);
        Gdiplus::SolidBrush br_kfg(k_fg);
        g.DrawString(r.key_text.c_str(), -1, font_badge.get(), badge_rc, &sf_center, &br_kfg);

        // Col 1: Action title
        Gdiplus::RectF c1_rc(
            pad_x + col0_w + std::round(14.0f * dpi),
            ry,
            col1_w - std::round(20.0f * dpi),
            tbl_row_h);
        g.DrawString(r.action_title.c_str(), -1, font_act.get(), c1_rc, &sf_vcenter, &br_primary);

        // Col 2: Description
        Gdiplus::RectF c2_rc(
            pad_x + col0_w + col1_w + std::round(14.0f * dpi),
            ry + std::round(3.0f * dpi),
            col2_w - std::round(24.0f * dpi),
            tbl_row_h - std::round(6.0f * dpi));
        g.DrawString(r.desc_text.c_str(), -1, font_desc.get(), c2_rc, &sf_vcenter, &br_secondary);

        ry += tbl_row_h;
    }

    // Vertical column dividers and outer table border
    g.DrawLine(&grid_pen, pad_x + col0_w, cur_y, pad_x + col0_w, cur_y + tbl_total_h);
    g.DrawLine(&grid_pen, pad_x + col0_w + col1_w, cur_y, pad_x + col0_w + col1_w, cur_y + tbl_total_h);
    g.DrawRectangle(&grid_pen, tbl_rc);

    cur_y += tbl_total_h + std::round(12.0f * dpi);

    // ==================== CARD 3: FOOTER (APP LOGO, VERSION & KAHUB PLATFORM BADGE) ====================
    float footer_h = std::round(40.0f * dpi);
    Gdiplus::RectF footer_rc(pad_x, cur_y, content_w, footer_h);
    DrawRoundedRect(g, footer_rc, std::round(6.0f * dpi), bg_card, border_soft, 1.0f);

    int footer_logo_sz = std::max(22, static_cast<int>(std::round(24.0f * dpi)));
    float footer_logo_x = pad_x + std::round(12.0f * dpi);
    float footer_logo_y = cur_y + (footer_h - static_cast<float>(footer_logo_sz)) * 0.5f;
    float footer_title_x = footer_logo_x + static_cast<float>(footer_logo_sz) + std::round(8.0f * dpi);

    g.DrawString(
        APP_TITLE_WITH_VERSION_W,
        -1,
        font_act.get(),
        Gdiplus::RectF(footer_title_x, cur_y, std::round(280.0f * dpi), footer_h),
        &sf_vcenter,
        &br_primary);

    // Clickable KAHUB PLATFORM badge on the right
    std::wstring dev_text = L"\u26A1 " + Tr(L"footer_developer") + L" \u2197";
    Gdiplus::RectF dev_box;
    g.MeasureString(dev_text.c_str(), -1, font_status.get(), Gdiplus::PointF(0, 0), &dev_box);
    float dev_w = std::ceil(dev_box.Width) + std::round(20.0f * dpi);
    float dev_h = std::round(26.0f * dpi);
    float dev_x = pad_x + content_w - std::round(12.0f * dpi) - dev_w;
    float dev_y = cur_y + (footer_h - dev_h) * 0.5f;
    rc_kahub_link_ = Gdiplus::RectF(dev_x, dev_y, dev_w, dev_h);

    bool kahub_hovered = (hovered_zone_ == HitZone::KahubLink);
    Gdiplus::Color dev_bg = kahub_hovered ? HexToColor(L"#bae6fd") : HexToColor(L"#e0f2fe");
    Gdiplus::Color dev_fg = kahub_hovered ? HexToColor(L"#0369a1") : HexToColor(L"#0284c7");
    Gdiplus::Color dev_bd = kahub_hovered ? HexToColor(L"#38bdf8") : HexToColor(L"#7dd3fc");
    DrawRoundedRect(g, rc_kahub_link_, std::round(5.0f * dpi), dev_bg, dev_bd, 1.0f);
    Gdiplus::SolidBrush br_dev_fg(dev_fg);
    g.DrawString(dev_text.c_str(), -1, font_status.get(), rc_kahub_link_, &sf_center, &br_dev_fg);

    // Blit backbuffer to window DC, then draw crisp Win32 icons at exact positions
    HDC hdc_mem = CreateCompatibleDC(hdc);
    HBITMAP hbm_mem = nullptr;
    back_bmp.GetHBITMAP(bg_main, &hbm_mem);
    if (hdc_mem && hbm_mem) {
        HGDIOBJ old_bm = SelectObject(hdc_mem, hbm_mem);
        HICON h_micro = GetAppIcon(micro_icon_sz);
        if (h_micro) {
            DrawIconEx(
                hdc_mem,
                static_cast<int>(std::round(pad_x)),
                static_cast<int>(std::round(sec_hdr_y + 1.0f * dpi)),
                h_micro,
                micro_icon_sz,
                micro_icon_sz,
                0,
                nullptr,
                DI_NORMAL);
        }
        HICON h_footer = GetAppIcon(footer_logo_sz);
        if (h_footer) {
            DrawIconEx(
                hdc_mem,
                static_cast<int>(std::round(footer_logo_x)),
                static_cast<int>(std::round(footer_logo_y)),
                h_footer,
                footer_logo_sz,
                footer_logo_sz,
                0,
                nullptr,
                DI_NORMAL);
        }
        BitBlt(hdc, 0, 0, width, height, hdc_mem, 0, 0, SRCCOPY);
        SelectObject(hdc_mem, old_bm);
    } else {
        Gdiplus::Graphics screen_g(hdc);
        screen_g.DrawImage(&back_bmp, 0, 0);
    }
    if (hbm_mem) DeleteObject(hbm_mem);
    if (hdc_mem) DeleteDC(hdc_mem);
}

LRESULT CALLBACK SettingsAndGuideWindow::WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    SettingsAndGuideWindow* self = nullptr;
    if (msg == WM_NCCREATE) {
        auto* cs = reinterpret_cast<CREATESTRUCTW*>(lparam);
        self = static_cast<SettingsAndGuideWindow*>(cs->lpCreateParams);
        SetWindowLongPtrW(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(self));
    } else {
        self = reinterpret_cast<SettingsAndGuideWindow*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA));
    }
    if (self) {
        return self->HandleMessage(hwnd, msg, wparam, lparam);
    }
    return DefWindowProcW(hwnd, msg, wparam, lparam);
}

LRESULT SettingsAndGuideWindow::HandleMessage(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    switch (msg) {
    case WM_ERASEBKGND:
        return 1;

    case WM_SETCURSOR:
        if (LOWORD(lparam) == HTCLIENT) {
            SetCursor(LoadCursorW(nullptr, hovered_zone_ != HitZone::None ? IDC_HAND : IDC_ARROW));
            return TRUE;
        }
        break;

    case WM_MOUSEMOVE: {
        HitZone hz = HitTest(GET_X_LPARAM(lparam), GET_Y_LPARAM(lparam));
        if (hz != hovered_zone_) {
            hovered_zone_ = hz;
            SetCursor(LoadCursorW(nullptr, hovered_zone_ != HitZone::None ? IDC_HAND : IDC_ARROW));
            InvalidateRect(hwnd, nullptr, FALSE);
        }
        return 0;
    }

    case WM_LBUTTONDOWN: {
        HitZone hz = HitTest(GET_X_LPARAM(lparam), GET_Y_LPARAM(lparam));
        if (hz == HitZone::AutostartRow) {
            bool target = !autostart_checked_;
            auto [ok, _msg] = SetAutostartEnabled(target);
            autostart_checked_ = ok ? target : IsAutostartEnabled();
            InvalidateRect(hwnd, nullptr, FALSE);
            if (on_autostart_changed_) on_autostart_changed_(autostart_checked_);
        } else if (hz == HitZone::PrtScRow) {
            bool target = !prtsc_checked_;
            auto [ok, _msg] = SetPrtScEnabled(target);
            prtsc_checked_ = ok ? target : IsPrtScEnabled();
            InvalidateRect(hwnd, nullptr, FALSE);
            if (on_prtsc_changed_) on_prtsc_changed_(prtsc_checked_);
        } else if (hz == HitZone::LangViBtn && GetLanguage() != L"vi") {
            SetLanguage(L"vi");
            ComputeLayoutAndResize(false);
            InvalidateRect(hwnd, nullptr, FALSE);
            if (on_language_changed_) on_language_changed_(L"vi");
        } else if (hz == HitZone::LangEnBtn && GetLanguage() != L"en") {
            SetLanguage(L"en");
            ComputeLayoutAndResize(false);
            InvalidateRect(hwnd, nullptr, FALSE);
            if (on_language_changed_) on_language_changed_(L"en");
        } else if (hz == HitZone::KahubLink) {
            ShellExecuteW(nullptr, L"open", L"https://kahub.vn", nullptr, nullptr, SW_SHOWNORMAL);
        }
        return 0;
    }

    case WM_KEYDOWN:
        if (wparam == VK_ESCAPE || ((GetKeyState(VK_CONTROL) & 0x8000) && wparam == 'W')) {
            MinimizeToTray();
            return 0;
        }
        break;

    case WM_SYSCOMMAND:
        if ((wparam & 0xFFF0) == SC_MINIMIZE) {
            MinimizeToTray();
            return 0;
        }
        break;

    case WM_CLOSE:
        MinimizeToTray();
        return 0;

    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);
        RECT rc;
        GetClientRect(hwnd, &rc);
        Render(hdc, rc.right - rc.left, rc.bottom - rc.top);
        EndPaint(hwnd, &ps);
        return 0;
    }
    }
    return DefWindowProcW(hwnd, msg, wparam, lparam);
}

} // namespace app
