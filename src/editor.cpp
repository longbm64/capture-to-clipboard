#include "editor.h"
#include "i18n.h"
#include "platform_utils.h"

namespace app {

namespace {

constexpr const wchar_t* kEditorClassName = L"CaptureToClipboard_EditorWnd";

float PointToSegmentDist(float px, float py, float x1, float y1, float x2, float y2) {
    float dx = x2 - x1;
    float dy = y2 - y1;
    float len_sq = dx * dx + dy * dy;
    if (len_sq < 1e-5f) {
        return std::hypot(px - x1, py - y1);
    }
    float t = std::max(0.0f, std::min(1.0f, ((px - x1) * dx + (py - y1) * dy) / len_sq));
    float proj_x = x1 + t * dx;
    float proj_y = y1 + t * dy;
    return std::hypot(px - proj_x, py - proj_y);
}

const std::vector<std::wstring>& GetEditorColorPalette() {
    static const std::vector<std::wstring> colors = {
        L"#ef4444",
        L"#f97316",
        L"#eab308",
        L"#22c55e",
        L"#06b6d4",
        L"#3b82f6",
        L"#a855f7",
        L"#ffffff",
        L"#111827"
    };
    return colors;
}

} // namespace

// ==================== AnnotationItem ====================

void AnnotationItem::Translate(int dx, int dy, int max_w, int max_h) {
    if (points.empty()) return;
    int min_x = points[0].X, max_x = points[0].X;
    int min_y = points[0].Y, max_y = points[0].Y;
    for (const auto& p : points) {
        min_x = std::min(min_x, p.X);
        max_x = std::max(max_x, p.X);
        min_y = std::min(min_y, p.Y);
        max_y = std::max(max_y, p.Y);
    }
    if (min_x + dx < 0) dx = -min_x;
    if (max_x + dx >= max_w) dx = (max_w - 1) - max_x;
    if (min_y + dy < 0) dy = -min_y;
    if (max_y + dy >= max_h) dy = (max_h - 1) - max_y;

    for (auto& p : points) {
        p.X += dx;
        p.Y += dy;
    }
}

Gdiplus::Rect AnnotationItem::GetBBox() const {
    if (points.empty()) return Gdiplus::Rect(0, 0, 0, 0);

    if (tool == L"text") {
        int ix = points[0].X;
        int iy = points[0].Y;
        auto font = CreateUiFont(static_cast<float>(font_px), true);
        HDC hdc = GetDC(nullptr);
        Gdiplus::RectF box(static_cast<float>(ix), static_cast<float>(iy), 100.0f, static_cast<float>(font_px));
        if (hdc) {
            Gdiplus::Graphics g(hdc);
            std::wstring sample = text.empty() ? L" " : text;
            g.MeasureString(sample.c_str(), -1, font.get(), Gdiplus::PointF(static_cast<float>(ix), static_cast<float>(iy)), &box);
            ReleaseDC(nullptr, hdc);
        }
        int pad = std::max(6, font_px / 6);
        int x1 = static_cast<int>(std::floor(box.X)) - pad;
        int y1 = static_cast<int>(std::floor(box.Y)) - pad;
        int x2 = static_cast<int>(std::ceil(box.X + box.Width)) + pad;
        int y2 = static_cast<int>(std::ceil(box.Y + box.Height)) + pad;
        return Gdiplus::Rect(x1, y1, x2 - x1, y2 - y1);
    }

    int min_x = points[0].X, max_x = points[0].X;
    int min_y = points[0].Y, max_y = points[0].Y;
    for (const auto& p : points) {
        min_x = std::min(min_x, p.X);
        max_x = std::max(max_x, p.X);
        min_y = std::min(min_y, p.Y);
        max_y = std::max(max_y, p.Y);
    }
    int pad = std::max(6, stroke_px);
    return Gdiplus::Rect(min_x - pad, min_y - pad, (max_x - min_x) + pad * 2, (max_y - min_y) + pad * 2);
}

std::vector<Gdiplus::Point> AnnotationItem::GetHandles() const {
    if (points.size() < 2) return {};
    if (tool == L"arrow" || tool == L"line") {
        return {points.front(), points.back()};
    }
    if (tool == L"rect" || tool == L"ellipse" || tool == L"pixelate") {
        int x1 = points.front().X, y1 = points.front().Y;
        int x2 = points.back().X, y2 = points.back().Y;
        return {{x1, y1}, {x2, y1}, {x2, y2}, {x1, y2}};
    }
    return {};
}

void AnnotationItem::MoveHandle(int handle_idx, int new_x, int new_y) {
    if (points.size() < 2) return;
    if (tool == L"arrow" || tool == L"line") {
        if (handle_idx == 0) points.front() = {new_x, new_y};
        else if (handle_idx == 1) points.back() = {new_x, new_y};
    } else if (tool == L"rect" || tool == L"ellipse" || tool == L"pixelate") {
        int x1 = points.front().X, y1 = points.front().Y;
        int x2 = points.back().X, y2 = points.back().Y;
        if (handle_idx == 0) {
            points.front() = {new_x, new_y};
        } else if (handle_idx == 1) {
            points.front() = {x1, new_y};
            points.back() = {new_x, y2};
        } else if (handle_idx == 2) {
            points.back() = {new_x, new_y};
        } else if (handle_idx == 3) {
            points.front() = {new_x, y1};
            points.back() = {x2, new_y};
        }
    }
}

bool AnnotationItem::HitTest(int ix, int iy, int base_tol) const {
    if (points.empty()) return false;
    float tol = static_cast<float>(std::max(base_tol, stroke_px + 10));
    float fx = static_cast<float>(ix);
    float fy = static_cast<float>(iy);

    if (tool == L"text") {
        Gdiplus::Rect b = GetBBox();
        return (ix >= b.X - 6 && ix <= b.GetRight() + 6 && iy >= b.Y - 6 && iy <= b.GetBottom() + 6);
    }

    if (tool == L"arrow" || tool == L"line") {
        float x1 = static_cast<float>(points.front().X);
        float y1 = static_cast<float>(points.front().Y);
        float x2 = static_cast<float>(points.back().X);
        float y2 = static_cast<float>(points.back().Y);
        if (PointToSegmentDist(fx, fy, x1, y1, x2, y2) <= tol * 1.3f) {
            return true;
        }
        if (tool == L"arrow") {
            float head_r = std::max(tol * 2.0f, stroke_px * 4.5f);
            float dx = x2 - x1;
            float dy = y2 - y1;
            float len = std::hypot(dx, dy);
            if (len > 1.0f) {
                float hx = x2 - (dx / len) * (head_r * 0.45f);
                float hy = y2 - (dy / len) * (head_r * 0.45f);
                if (std::hypot(fx - hx, fy - hy) <= head_r * 0.65f) {
                    return true;
                }
            }
        }
        return false;
    }

    if (tool == L"rect") {
        float x1 = static_cast<float>(points.front().X);
        float y1 = static_cast<float>(points.front().Y);
        float x2 = static_cast<float>(points.back().X);
        float y2 = static_cast<float>(points.back().Y);
        float rx1 = std::min(x1, x2), rx2 = std::max(x1, x2);
        float ry1 = std::min(y1, y2), ry2 = std::max(y1, y2);
        if ((rx2 - rx1 < 80.0f && ry2 - ry1 < 80.0f) &&
            (fx >= rx1 - tol && fx <= rx2 + tol && fy >= ry1 - tol && fy <= ry2 + tol)) {
            return true;
        }
        bool near_top = PointToSegmentDist(fx, fy, rx1, ry1, rx2, ry1) <= tol;
        bool near_bot = PointToSegmentDist(fx, fy, rx1, ry2, rx2, ry2) <= tol;
        bool near_left = PointToSegmentDist(fx, fy, rx1, ry1, rx1, ry2) <= tol;
        bool near_right = PointToSegmentDist(fx, fy, rx2, ry1, rx2, ry2) <= tol;
        return near_top || near_bot || near_left || near_right;
    }

    if (tool == L"ellipse") {
        float x1 = static_cast<float>(points.front().X);
        float y1 = static_cast<float>(points.front().Y);
        float x2 = static_cast<float>(points.back().X);
        float y2 = static_cast<float>(points.back().Y);
        float rx1 = std::min(x1, x2), rx2 = std::max(x1, x2);
        float ry1 = std::min(y1, y2), ry2 = std::max(y1, y2);
        float cx = (rx1 + rx2) * 0.5f;
        float cy = (ry1 + ry2) * 0.5f;
        float a = std::max(1.0f, (rx2 - rx1) * 0.5f);
        float b = std::max(1.0f, (ry2 - ry1) * 0.5f);
        if (a < 40.0f && b < 40.0f) {
            float nx = (fx - cx) / (a + tol);
            float ny = (fy - cy) / (b + tol);
            return (nx * nx + ny * ny) <= 1.0f;
        }
        float norm_r = std::hypot((fx - cx) / a, (fy - cy) / b);
        float avg_rad = (a + b) * 0.5f;
        float rel_tol = tol / std::max(10.0f, avg_rad);
        return std::fabs(norm_r - 1.0f) <= std::max(0.18f, rel_tol);
    }

    if (tool == L"pixelate") {
        int x1 = points.front().X, y1 = points.front().Y;
        int x2 = points.back().X, y2 = points.back().Y;
        int rx1 = std::min(x1, x2), rx2 = std::max(x1, x2);
        int ry1 = std::min(y1, y2), ry2 = std::max(y1, y2);
        return (ix >= rx1 - 6 && ix <= rx2 + 6 && iy >= ry1 - 6 && iy <= ry2 + 6);
    }

    if (tool == L"pen" || tool == L"highlighter") {
        float hit_r = tol * (tool == L"highlighter" ? 1.6f : 1.15f);
        if (points.size() == 1) {
            return std::hypot(fx - points[0].X, fy - points[0].Y) <= hit_r;
        }
        for (size_t i = 0; i + 1 < points.size(); ++i) {
            if (PointToSegmentDist(
                    fx, fy,
                    static_cast<float>(points[i].X), static_cast<float>(points[i].Y),
                    static_cast<float>(points[i + 1].X), static_cast<float>(points[i + 1].Y)) <= hit_r) {
                return true;
            }
        }
        return false;
    }

    return false;
}

// ==================== AnnotationEditor ====================

AnnotationEditor::AnnotationEditor(
    std::unique_ptr<Gdiplus::Bitmap> image,
    OnCopyClipboard on_copy_clipboard,
    OnClose on_close)
    : base_image_(std::move(image)),
      on_copy_clipboard_(std::move(on_copy_clipboard)),
      on_close_(std::move(on_close)) {

    for (int i = 0; i < 16; ++i) {
        custom_colors_[i] = RGB(2, 132, 199);
    }

    static bool class_registered = false;
    if (!class_registered) {
        WNDCLASSEXW wc{};
        wc.cbSize = sizeof(wc);
        wc.style = CS_HREDRAW | CS_VREDRAW | CS_DBLCLKS;
        wc.lpfnWndProc = AnnotationEditor::WndProc;
        wc.hInstance = GetModuleHandleW(nullptr);
        wc.hCursor = LoadCursorW(nullptr, IDC_CROSS);
        wc.hIcon = GetAppIcon(std::max(32, GetSystemMetrics(SM_CXICON)));
        wc.hIconSm = GetAppIcon(std::max(16, GetSystemMetrics(SM_CXSMICON)));
        wc.lpszClassName = kEditorClassName;
        RegisterClassExW(&wc);
        class_registered = true;
    }

    InitToolbarItems();
    RebuildComposite();

    float dpi = GetWindowDpiScale(nullptr);
    int screen_w = GetSystemMetrics(SM_CXSCREEN);
    int screen_h = GetSystemMetrics(SM_CYSCREEN);

    int img_w = static_cast<int>(base_image_->GetWidth());
    int img_h = static_cast<int>(base_image_->GetHeight());

    int max_canvas_w = std::max(560, static_cast<int>(screen_w * 0.86f));
    int max_canvas_h = std::max(380, static_cast<int>(screen_h * 0.72f));
    float fit_scale = std::min({
        1.0f,
        static_cast<float>(max_canvas_w) / std::max(1, img_w),
        static_cast<float>(max_canvas_h) / std::max(1, img_h)
    });

    int init_cw = std::max(1, static_cast<int>(std::round(img_w * fit_scale)));
    int init_ch = std::max(1, static_cast<int>(std::round(img_h * fit_scale)));
    display_scale_x_ = static_cast<float>(init_cw) / std::max(1, img_w);
    display_scale_y_ = static_cast<float>(init_ch) / std::max(1, img_h);

    min_win_w_ = std::min(screen_w - 40, std::max(720, static_cast<int>(std::round(700.0f * dpi))));
    min_win_h_ = std::min(screen_h - 60, static_cast<int>(std::round(360.0f * dpi)));

    float single_row1_w = 32.0f * dpi;
    for (const auto& it : row1_items_) single_row1_w += it.req_w + it.gap_x;
    float single_row2_w = 32.0f * dpi;
    for (const auto& it : row2_items_) single_row2_w += it.req_w + it.gap_x;
    int desired_toolbar_w = static_cast<int>(std::ceil(std::max(single_row1_w, single_row2_w)));

    int max_win_w = std::max(min_win_w_, static_cast<int>(screen_w * 0.92f));
    int client_w = std::min(max_win_w, std::max({min_win_w_, desired_toolbar_w, init_cw + static_cast<int>(36.0f * dpi)}));

    float r1_h = LayoutFlowRow(row1_items_, 0.0f, static_cast<float>(client_w), 14.0f * dpi, 8.0f * dpi, 6.0f * dpi);
    float r2_h = LayoutFlowRow(row2_items_, r1_h + 1.0f, static_cast<float>(client_w), 14.0f * dpi, 8.0f * dpi, 6.0f * dpi);
    status_h_ = std::round(30.0f * dpi);

    int max_win_h = std::max(min_win_h_, static_cast<int>(screen_h * 0.90f));
    int client_h = std::min(
        max_win_h,
        std::max(min_win_h_, static_cast<int>(r1_h + r2_h + init_ch + std::round(32.0f * dpi) + status_h_)));

    RECT wr = {0, 0, client_w, client_h};
    DWORD style = WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN;
    DWORD ex_style = WS_EX_TOPMOST;
    AdjustWindowRectEx(&wr, style, FALSE, ex_style);
    int win_w = wr.right - wr.left;
    int win_h = wr.bottom - wr.top;
    int pos_x = std::max(10, (screen_w - win_w) / 2);
    int pos_y = std::max(10, (screen_h - win_h) / 2 - 20);

    hwnd_ = CreateWindowExW(
        ex_style,
        kEditorClassName,
        APP_TITLE_WITH_VERSION_W,
        style,
        pos_x,
        pos_y,
        win_w,
        win_h,
        nullptr,
        nullptr,
        GetModuleHandleW(nullptr),
        this);

    if (!hwnd_) return;

    ApplyWindowIcon(hwnd_);
    RECT crc{};
    GetClientRect(hwnd_, &crc);
    RecalculateLayout(crc.right - crc.left, crc.bottom - crc.top);

    ShowWindow(hwnd_, SW_SHOW);
    SetForegroundWindow(hwnd_);
    SetFocus(hwnd_);
    UpdateWindow(hwnd_);
}

AnnotationEditor::~AnnotationEditor() {
    CloseEditor();
}

void AnnotationEditor::CloseEditor() {
    if (closing_) return;
    closing_ = true;
    CancelActiveText();
    if (edit_hfont_) {
        DeleteObject(edit_hfont_);
        edit_hfont_ = nullptr;
    }
    if (edit_bg_brush_) {
        DeleteObject(edit_bg_brush_);
        edit_bg_brush_ = nullptr;
    }
    if (hwnd_ && IsWindow(hwnd_)) {
        DestroyWindow(hwnd_);
    }
    hwnd_ = nullptr;
    if (on_close_) {
        auto cb = std::move(on_close_);
        on_close_ = nullptr;
        cb();
    }
}

void AnnotationEditor::InitToolbarItems() {
    row1_items_.clear();
    row2_items_.clear();

    float dpi = GetWindowDpiScale(nullptr);
    HDC hdc = GetDC(nullptr);
    Gdiplus::Graphics g(hdc);
    auto font_r1 = CreateUiFont(13.5f * dpi, true);
    auto font_r2 = CreateUiFont(12.5f * dpi, true);
    auto font_lbl = CreateUiFont(12.5f * dpi, true);

    auto measure_pill = [&](const std::wstring& txt, bool has_icon, Gdiplus::Font* f, float pad_x_pt, float h_pt) -> std::pair<float, float> {
        Gdiplus::RectF box;
        g.MeasureString(txt.c_str(), -1, f, Gdiplus::PointF(0, 0), &box);
        float text_w = std::ceil(box.Width);
        float icon_w = has_icon ? std::round(16.0f * dpi) : 0.0f;
        float gap = has_icon ? std::round(6.5f * dpi) : 0.0f;
        float pad_x = std::round(pad_x_pt * dpi);
        return {pad_x * 2.0f + icon_w + gap + text_w, std::round(h_pt * dpi)};
    };

    // Row 1: Drawing tools
    for (const auto& t : GetEditorTools()) {
        auto [w, h] = measure_pill(t.label, true, font_r1.get(), 11.5f, 32.0f);
        ToolbarItem it{};
        it.kind = BtnKind::Tool;
        it.id = t.id;
        it.label = t.label;
        it.icon_name = t.id;
        it.req_w = w;
        it.req_h = h;
        it.gap_x = std::round(7.0f * dpi);
        row1_items_.push_back(it);
    }

    // Divider
    {
        ToolbarItem div{};
        div.kind = BtnKind::Divider;
        div.req_w = 1.0f;
        div.req_h = std::round(26.0f * dpi);
        div.gap_x = std::round(12.0f * dpi);
        row1_items_.push_back(div);
    }

    // Undo, Redo, Clear
    auto add_r1_action = [&](BtnKind kind, const std::wstring& key, const std::wstring& icon) {
        std::wstring lbl = Tr(key);
        auto [w, h] = measure_pill(lbl, true, font_r1.get(), 11.5f, 32.0f);
        ToolbarItem it{};
        it.kind = kind;
        it.label = lbl;
        it.icon_name = icon;
        it.req_w = w;
        it.req_h = h;
        it.gap_x = std::round(6.0f * dpi);
        row1_items_.push_back(it);
    };
    add_r1_action(BtnKind::ActionUndo, L"editor_undo", L"undo");
    add_r1_action(BtnKind::ActionRedo, L"editor_redo", L"redo");
    add_r1_action(BtnKind::ActionClear, L"editor_clear", L"clear");

    // Row 2: Color label + swatches + Custom Color
    {
        std::wstring lbl = Tr(L"editor_color_label");
        Gdiplus::RectF box;
        g.MeasureString(lbl.c_str(), -1, font_lbl.get(), Gdiplus::PointF(0, 0), &box);
        ToolbarItem it{};
        it.kind = BtnKind::LabelOnly;
        it.label = lbl;
        it.req_w = std::ceil(box.Width) + std::round(4.0f * dpi);
        it.req_h = std::round(28.0f * dpi);
        it.gap_x = std::round(6.0f * dpi);
        row2_items_.push_back(it);
    }

    float swatch_sz = std::round(26.0f * dpi);
    for (const auto& hex : GetEditorColorPalette()) {
        ToolbarItem it{};
        it.kind = BtnKind::ColorSwatch;
        it.color_hex = hex;
        it.req_w = swatch_sz;
        it.req_h = swatch_sz;
        it.gap_x = std::round(5.0f * dpi);
        row2_items_.push_back(it);
    }

    {
        std::wstring lbl = Tr(L"editor_custom_color");
        auto [w, h] = measure_pill(lbl, true, font_r2.get(), 10.5f, 30.0f);
        ToolbarItem it{};
        it.kind = BtnKind::CustomColor;
        it.label = lbl;
        it.icon_name = L"palette";
        it.req_w = w;
        it.req_h = h;
        it.gap_x = std::round(10.0f * dpi);
        row2_items_.push_back(it);
    }

    // Divider
    {
        ToolbarItem div{};
        div.kind = BtnKind::Divider;
        div.req_w = 1.0f;
        div.req_h = std::round(24.0f * dpi);
        div.gap_x = std::round(10.0f * dpi);
        row2_items_.push_back(div);
    }

    // Size label + 4 stroke sizes
    {
        std::wstring lbl = Tr(L"editor_size_label");
        Gdiplus::RectF box;
        g.MeasureString(lbl.c_str(), -1, font_lbl.get(), Gdiplus::PointF(0, 0), &box);
        ToolbarItem it{};
        it.kind = BtnKind::LabelOnly;
        it.label = lbl;
        it.req_w = std::ceil(box.Width) + std::round(4.0f * dpi);
        it.req_h = std::round(28.0f * dpi);
        it.gap_x = std::round(6.0f * dpi);
        row2_items_.push_back(it);
    }

    for (const auto& sz : GetEditorSizes()) {
        Gdiplus::RectF box;
        g.MeasureString(sz.label.c_str(), -1, font_r2.get(), Gdiplus::PointF(0, 0), &box);
        float dot_d = std::round(sz.dot_radius_pt * 2.0f * dpi);
        float pad_x = std::round(10.5f * dpi);
        float gap = std::round(6.0f * dpi);
        ToolbarItem it{};
        it.kind = BtnKind::StrokeSize;
        it.label = sz.label;
        it.size_val = sz.size_val;
        it.dot_r_pt = sz.dot_radius_pt;
        it.req_w = pad_x * 2.0f + dot_d + gap + std::ceil(box.Width);
        it.req_h = std::round(30.0f * dpi);
        it.gap_x = std::round(5.0f * dpi);
        row2_items_.push_back(it);
    }

    // Divider
    {
        ToolbarItem div{};
        div.kind = BtnKind::Divider;
        div.req_w = 1.0f;
        div.req_h = std::round(24.0f * dpi);
        div.gap_x = std::round(10.0f * dpi);
        row2_items_.push_back(div);
    }

    // Copy, Save, Close
    auto add_r2_action = [&](BtnKind kind, const std::wstring& key, const std::wstring& icon) {
        std::wstring lbl = Tr(key);
        auto [w, h] = measure_pill(lbl, true, font_r2.get(), 11.0f, 30.0f);
        ToolbarItem it{};
        it.kind = kind;
        it.label = lbl;
        it.icon_name = icon;
        it.req_w = w;
        it.req_h = h;
        it.gap_x = std::round(6.0f * dpi);
        row2_items_.push_back(it);
    };
    add_r2_action(BtnKind::ActionCopy, L"editor_copy_btn", L"copy");
    add_r2_action(BtnKind::ActionSave, L"editor_save_btn", L"save");
    add_r2_action(BtnKind::ActionClose, L"editor_close_btn", L"close");

    if (hdc) ReleaseDC(nullptr, hdc);
}

float AnnotationEditor::LayoutFlowRow(
    std::vector<ToolbarItem>& row_items,
    float start_y,
    float total_width,
    float pad_x,
    float pad_y,
    float row_gap) {

    float avail_w = std::max(200.0f, total_width - pad_x * 2.0f);
    std::vector<std::vector<size_t>> lines;
    std::vector<size_t> cur_line;
    float cur_w = 0.0f;

    for (size_t i = 0; i < row_items.size(); ++i) {
        auto& it = row_items[i];
        it.visible = true;
        if (it.kind == BtnKind::Divider) {
            if (cur_line.empty() || row_items[cur_line.back()].kind == BtnKind::Divider) {
                it.visible = false;
                continue;
            }
        }
        if (cur_line.empty()) {
            cur_line.push_back(i);
            cur_w = it.req_w;
        } else {
            float prev_gap = row_items[cur_line.back()].gap_x;
            if (cur_w + prev_gap + it.req_w <= avail_w) {
                cur_line.push_back(i);
                cur_w += prev_gap + it.req_w;
            } else {
                if (row_items[cur_line.back()].kind == BtnKind::Divider) {
                    row_items[cur_line.back()].visible = false;
                    cur_line.pop_back();
                }
                if (!cur_line.empty()) {
                    lines.push_back(cur_line);
                }
                cur_line.clear();
                if (it.kind == BtnKind::Divider) {
                    it.visible = false;
                } else {
                    cur_line.push_back(i);
                    cur_w = it.req_w;
                }
            }
        }
    }
    if (!cur_line.empty() && row_items[cur_line.back()].kind == BtnKind::Divider) {
        row_items[cur_line.back()].visible = false;
        cur_line.pop_back();
    }
    if (!cur_line.empty()) {
        lines.push_back(cur_line);
    }

    float y = start_y + pad_y;
    for (const auto& line : lines) {
        float line_w = 0.0f;
        float line_h = 0.0f;
        for (size_t k = 0; k < line.size(); ++k) {
            const auto& it = row_items[line[k]];
            line_w += it.req_w;
            if (k + 1 < line.size()) line_w += it.gap_x;
            line_h = std::max(line_h, it.req_h);
        }
        float x = pad_x + std::max(0.0f, (avail_w - line_w) * 0.5f);
        for (size_t k = 0; k < line.size(); ++k) {
            auto& it = row_items[line[k]];
            float iy = y + (line_h - it.req_h) * 0.5f;
            it.rect = Gdiplus::RectF(std::round(x), std::round(iy), it.req_w, it.req_h);
            x += it.req_w + (k + 1 < line.size() ? it.gap_x : 0.0f);
        }
        y += line_h + row_gap;
    }

    float total_h = (y - start_y) - (lines.empty() ? 0.0f : row_gap) + pad_y;
    return std::max(36.0f, std::round(total_h));
}

void AnnotationEditor::RecalculateLayout(int client_w, int client_h) {
    if (client_w <= 0 || client_h <= 0 || !base_image_) return;
    float dpi = GetWindowDpiScale(hwnd_);

    row1_h_ = LayoutFlowRow(
        row1_items_,
        0.0f,
        static_cast<float>(client_w),
        std::round(14.0f * dpi),
        std::round(8.0f * dpi),
        std::round(6.0f * dpi));

    row2_h_ = LayoutFlowRow(
        row2_items_,
        row1_h_ + 1.0f,
        static_cast<float>(client_w),
        std::round(14.0f * dpi),
        std::round(8.0f * dpi),
        std::round(6.0f * dpi));

    status_h_ = std::round(30.0f * dpi);

    float top_bars_h = row1_h_ + 1.0f + row2_h_ + 1.0f;
    float avail_area_w = std::max(80.0f, static_cast<float>(client_w));
    float avail_area_h = std::max(80.0f, static_cast<float>(client_h) - top_bars_h - status_h_);

    canvas_area_rc_ = Gdiplus::RectF(0.0f, top_bars_h, avail_area_w, avail_area_h);

    float pad_cw = std::round(36.0f * dpi);
    float pad_ch = std::round(28.0f * dpi);
    float max_cw = std::max(60.0f, avail_area_w - pad_cw);
    float max_ch = std::max(60.0f, avail_area_h - pad_ch);

    float img_w = static_cast<float>(base_image_->GetWidth());
    float img_h = static_cast<float>(base_image_->GetHeight());

    float max_scale = 1.0f;
    if (max_cw > img_w + 60.0f && max_ch > img_h + 60.0f) {
        max_scale = std::min({2.0f, max_cw / img_w, max_ch / img_h});
    }
    float fit_scale = std::min({max_scale, max_cw / img_w, max_ch / img_h});
    float cw = std::max(1.0f, std::round(img_w * fit_scale));
    float ch = std::max(1.0f, std::round(img_h * fit_scale));

    float cx = std::round((avail_area_w - cw) * 0.5f);
    float cy = std::round(top_bars_h + (avail_area_h - ch) * 0.5f);
    canvas_rc_ = Gdiplus::RectF(cx, cy, cw, ch);

    display_scale_x_ = cw / std::max(1.0f, img_w);
    display_scale_y_ = ch / std::max(1.0f, img_h);

    if (hwnd_edit_ && IsWindow(hwnd_edit_)) {
        Gdiplus::PointF ep = ImageToCanvasCoords(static_cast<float>(text_img_pos_.X), static_cast<float>(text_img_pos_.Y));
        SetWindowPos(hwnd_edit_, HWND_TOP, static_cast<int>(ep.X), static_cast<int>(ep.Y), 0, 0, SWP_NOSIZE | SWP_NOACTIVATE);
    }
}

void AnnotationEditor::SelectTool(const std::wstring& tool_id) {
    CommitActiveText();
    current_tool_ = tool_id;
    if (hwnd_) InvalidateRect(hwnd_, nullptr, FALSE);
}

void AnnotationEditor::SelectColor(const std::wstring& hex_color) {
    current_color_ = hex_color;
    if (selected_idx_ >= 0 && selected_idx_ < static_cast<int>(items_.size())) {
        if (items_[selected_idx_].color != hex_color) {
            SaveUndoSnapshot();
            items_[selected_idx_].color = hex_color;
            RebuildComposite();
        }
    }
    if (hwnd_) InvalidateRect(hwnd_, nullptr, FALSE);
}

void AnnotationEditor::PickCustomColor() {
    CHOOSECOLORW cc{};
    cc.lStructSize = sizeof(cc);
    cc.hwndOwner = hwnd_;
    cc.lpCustColors = custom_colors_;
    cc.rgbResult = HexToColorRef(current_color_);
    cc.Flags = CC_FULLOPEN | CC_RGBINIT;
    if (ChooseColorW(&cc)) {
        SelectColor(ColorRefToHex(cc.rgbResult));
    }
}

void AnnotationEditor::SelectSize(int size_val) {
    current_size_ = size_val;
    if (selected_idx_ >= 0 && selected_idx_ < static_cast<int>(items_.size())) {
        if (items_[selected_idx_].size != size_val) {
            SaveUndoSnapshot();
            items_[selected_idx_].size = size_val;
            items_[selected_idx_].stroke_px = ScaledStrokeWidth(size_val);
            items_[selected_idx_].font_px = ScaledFontPx(size_val);
            RebuildComposite();
        }
    }
    if (hwnd_) InvalidateRect(hwnd_, nullptr, FALSE);
}

int AnnotationEditor::ScaledStrokeWidth(int size_override) const {
    int sz = (size_override > 0) ? size_override : current_size_;
    float inv = 1.0f / std::max(0.25f, std::min(display_scale_x_, display_scale_y_));
    return std::max(2, static_cast<int>(std::round(sz * inv)));
}

int AnnotationEditor::ScaledFontPx(int size_override) const {
    int sz = (size_override > 0) ? size_override : current_size_;
    float inv = 1.0f / std::max(0.25f, std::min(display_scale_x_, display_scale_y_));
    return std::max(18, static_cast<int>(std::round(sz * 4.5f * inv)));
}

void AnnotationEditor::SaveUndoSnapshot() {
    undo_stack_.push_back(items_);
    if (undo_stack_.size() > 50) {
        undo_stack_.erase(undo_stack_.begin());
    }
    redo_stack_.clear();
}

void AnnotationEditor::Undo() {
    CommitActiveText();
    if (!undo_stack_.empty()) {
        redo_stack_.push_back(items_);
        items_ = std::move(undo_stack_.back());
        undo_stack_.pop_back();
        selected_idx_ = items_.empty() ? -1 : static_cast<int>(items_.size()) - 1;
        RebuildComposite();
        if (hwnd_) InvalidateRect(hwnd_, nullptr, FALSE);
    }
}

void AnnotationEditor::Redo() {
    CommitActiveText();
    if (!redo_stack_.empty()) {
        undo_stack_.push_back(items_);
        items_ = std::move(redo_stack_.back());
        redo_stack_.pop_back();
        selected_idx_ = items_.empty() ? -1 : static_cast<int>(items_.size()) - 1;
        RebuildComposite();
        if (hwnd_) InvalidateRect(hwnd_, nullptr, FALSE);
    }
}

void AnnotationEditor::ClearAll() {
    CommitActiveText();
    if (!items_.empty()) {
        SaveUndoSnapshot();
        items_.clear();
        selected_idx_ = -1;
        RebuildComposite();
        if (hwnd_) InvalidateRect(hwnd_, nullptr, FALSE);
    }
}

void AnnotationEditor::DeleteSelected() {
    if (hwnd_edit_) return;
    if (selected_idx_ >= 0 && selected_idx_ < static_cast<int>(items_.size())) {
        SaveUndoSnapshot();
        items_.erase(items_.begin() + selected_idx_);
        selected_idx_ = items_.empty() ? -1 : static_cast<int>(items_.size()) - 1;
        RebuildComposite();
        if (hwnd_) InvalidateRect(hwnd_, nullptr, FALSE);
    }
}

Gdiplus::Point AnnotationEditor::CanvasToImageCoords(int cx, int cy) const {
    float rel_x = static_cast<float>(cx) - canvas_rc_.X;
    float rel_y = static_cast<float>(cy) - canvas_rc_.Y;
    int ix = static_cast<int>(std::round(rel_x / std::max(0.01f, display_scale_x_)));
    int iy = static_cast<int>(std::round(rel_y / std::max(0.01f, display_scale_y_)));
    int max_w = static_cast<int>(base_image_->GetWidth());
    int max_h = static_cast<int>(base_image_->GetHeight());
    ix = std::max(0, std::min(max_w - 1, ix));
    iy = std::max(0, std::min(max_h - 1, iy));
    return Gdiplus::Point(ix, iy);
}

Gdiplus::PointF AnnotationEditor::ImageToCanvasCoords(float ix, float iy) const {
    return Gdiplus::PointF(
        canvas_rc_.X + ix * display_scale_x_,
        canvas_rc_.Y + iy * display_scale_y_);
}

int AnnotationEditor::FindHandleAt(int ix, int iy) const {
    if (selected_idx_ < 0 || selected_idx_ >= static_cast<int>(items_.size())) return -1;
    float inv = 1.0f / std::max(0.25f, std::min(display_scale_x_, display_scale_y_));
    float tol = std::max(14.0f, 12.0f * inv);
    auto handles = items_[selected_idx_].GetHandles();
    for (size_t i = 0; i < handles.size(); ++i) {
        if (std::hypot(static_cast<float>(ix - handles[i].X), static_cast<float>(iy - handles[i].Y)) <= tol) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

int AnnotationEditor::FindItemAt(int ix, int iy) const {
    float inv = 1.0f / std::max(0.25f, std::min(display_scale_x_, display_scale_y_));
    int base_tol = std::max(12, static_cast<int>(std::round(10.0f * inv)));
    if (selected_idx_ >= 0 && selected_idx_ < static_cast<int>(items_.size())) {
        if (items_[selected_idx_].HitTest(ix, iy, base_tol)) {
            return selected_idx_;
        }
    }
    for (int i = static_cast<int>(items_.size()) - 1; i >= 0; --i) {
        if (items_[i].HitTest(ix, iy, base_tol)) {
            return i;
        }
    }
    return -1;
}

std::unique_ptr<Gdiplus::Bitmap> AnnotationEditor::CloneBitmap(Gdiplus::Bitmap* src) {
    if (!src) return nullptr;
    int w = static_cast<int>(src->GetWidth());
    int h = static_cast<int>(src->GetHeight());
    auto out = std::make_unique<Gdiplus::Bitmap>(w, h, PixelFormat32bppARGB);
    Gdiplus::Graphics g(out.get());
    g.DrawImage(src, 0, 0, w, h);
    return out;
}

void AnnotationEditor::DrawProArrow(
    Gdiplus::Graphics& g,
    float x1,
    float y1,
    float x2,
    float y2,
    Gdiplus::Color color,
    float width) {

    float dx = x2 - x1;
    float dy = y2 - y1;
    float length = std::hypot(dx, dy);
    if (length < 4.0f) return;

    float ux = dx / length;
    float uy = dy / length;
    float px = -uy;
    float py = ux;

    float head_len = std::min(std::max(width * 4.5f, 22.0f), std::max(24.0f, length * 0.55f));
    float head_half_w = head_len * 0.52f;
    float neck_indent = head_len * 0.78f;

    float tail_half_w = std::max(1.5f, width * 0.28f);
    float neck_half_w = std::max(2.5f, width * 0.58f);

    float nx = x2 - ux * neck_indent;
    float ny = y2 - uy * neck_indent;
    float bx = x2 - ux * head_len;
    float by = y2 - uy * head_len;

    Gdiplus::PointF poly[7] = {
        {x1 + px * tail_half_w, y1 + py * tail_half_w},
        {nx + px * neck_half_w, ny + py * neck_half_w},
        {bx + px * head_half_w, by + py * head_half_w},
        {x2, y2},
        {bx - px * head_half_w, by - py * head_half_w},
        {nx - px * neck_half_w, ny - py * neck_half_w},
        {x1 - px * tail_half_w, y1 - py * tail_half_w}
    };

    float lum = 0.299f * color.GetR() + 0.587f * color.GetG() + 0.114f * color.GetB();
    Gdiplus::Color outline_c = (lum > 90.0f)
        ? Gdiplus::Color(180, 15, 23, 42)
        : Gdiplus::Color(190, 255, 255, 255);

    Gdiplus::SolidBrush fill_b(color);
    Gdiplus::Pen out_pen(outline_c, std::max(1.5f, width * 0.20f));
    out_pen.SetLineJoin(Gdiplus::LineJoinRound);

    g.FillPolygon(&fill_b, poly, 7);
    g.DrawPolygon(&out_pen, poly, 7);
    g.FillEllipse(&fill_b, x1 - tail_half_w, y1 - tail_half_w, tail_half_w * 2.0f, tail_half_w * 2.0f);
}

void AnnotationEditor::DrawSingleItem(
    Gdiplus::Graphics& g,
    Gdiplus::Bitmap* pixelate_source,
    const AnnotationItem& item) {

    if (item.points.empty()) return;

    Gdiplus::Color col = HexToColor(item.color, 255);
    float sw = static_cast<float>(std::max(2, item.stroke_px));
    float x1 = static_cast<float>(item.points.front().X);
    float y1 = static_cast<float>(item.points.front().Y);
    float x2 = static_cast<float>(item.points.back().X);
    float y2 = static_cast<float>(item.points.back().Y);

    if (item.tool == L"pixelate" && item.points.size() >= 2 && pixelate_source) {
        int img_w = static_cast<int>(pixelate_source->GetWidth());
        int img_h = static_cast<int>(pixelate_source->GetHeight());
        int rx1 = std::max(0, std::min(static_cast<int>(x1), static_cast<int>(x2)));
        int rx2 = std::min(img_w, std::max(static_cast<int>(x1), static_cast<int>(x2)));
        int ry1 = std::max(0, std::min(static_cast<int>(y1), static_cast<int>(y2)));
        int ry2 = std::min(img_h, std::max(static_cast<int>(y1), static_cast<int>(y2)));
        int rw = rx2 - rx1;
        int rh = ry2 - ry1;
        if (rw >= 4 && rh >= 4) {
            int block_sz = std::max(10, item.stroke_px * 2);
            int small_w = std::max(1, rw / block_sz);
            int small_h = std::max(1, rh / block_sz);

            Gdiplus::Bitmap small_bmp(small_w, small_h, PixelFormat32bppARGB);
            {
                Gdiplus::Graphics gs(&small_bmp);
                gs.SetInterpolationMode(Gdiplus::InterpolationModeBilinear);
                gs.DrawImage(
                    pixelate_source,
                    Gdiplus::Rect(0, 0, small_w, small_h),
                    rx1, ry1, rw, rh,
                    Gdiplus::UnitPixel);
            }
            auto old_interp = g.GetInterpolationMode();
            auto old_offset = g.GetPixelOffsetMode();
            g.SetInterpolationMode(Gdiplus::InterpolationModeNearestNeighbor);
            g.SetPixelOffsetMode(Gdiplus::PixelOffsetModeHalf);
            g.DrawImage(&small_bmp, Gdiplus::Rect(rx1, ry1, rw, rh), 0, 0, small_w, small_h, Gdiplus::UnitPixel);
            g.SetInterpolationMode(old_interp);
            g.SetPixelOffsetMode(old_offset);
        }
        return;
    }

    if (item.tool == L"pen") {
        Gdiplus::Pen pen(col, sw);
        pen.SetStartCap(Gdiplus::LineCapRound);
        pen.SetEndCap(Gdiplus::LineCapRound);
        pen.SetLineJoin(Gdiplus::LineJoinRound);
        if (item.points.size() == 1) {
            Gdiplus::SolidBrush br(col);
            float r = sw * 0.5f;
            g.FillEllipse(&br, x1 - r, y1 - r, r * 2.0f, r * 2.0f);
        } else {
            g.DrawLines(&pen, item.points.data(), static_cast<INT>(item.points.size()));
        }
    } else if (item.tool == L"highlighter") {
        Gdiplus::Color hl_col = HexToColor(item.color, 96);
        float hl_w = std::max(14.0f, sw * 3.0f);
        Gdiplus::Pen pen(hl_col, hl_w);
        pen.SetStartCap(Gdiplus::LineCapRound);
        pen.SetEndCap(Gdiplus::LineCapRound);
        pen.SetLineJoin(Gdiplus::LineJoinRound);
        if (item.points.size() == 1) {
            Gdiplus::SolidBrush br(hl_col);
            float r = hl_w * 0.5f;
            g.FillEllipse(&br, x1 - r, y1 - r, r * 2.0f, r * 2.0f);
        } else {
            g.DrawLines(&pen, item.points.data(), static_cast<INT>(item.points.size()));
        }
    } else if (item.tool == L"line") {
        Gdiplus::Pen pen(col, sw);
        pen.SetStartCap(Gdiplus::LineCapRound);
        pen.SetEndCap(Gdiplus::LineCapRound);
        g.DrawLine(&pen, x1, y1, x2, y2);
    } else if (item.tool == L"arrow") {
        DrawProArrow(g, x1, y1, x2, y2, col, sw);
    } else if (item.tool == L"rect") {
        Gdiplus::Pen pen(col, sw);
        pen.SetLineJoin(Gdiplus::LineJoinMiter);
        float rx = std::min(x1, x2);
        float ry = std::min(y1, y2);
        float rw = std::fabs(x2 - x1);
        float rh = std::fabs(y2 - y1);
        g.DrawRectangle(&pen, rx, ry, rw, rh);
    } else if (item.tool == L"ellipse") {
        Gdiplus::Pen pen(col, sw);
        float rx = std::min(x1, x2);
        float ry = std::min(y1, y2);
        float rw = std::fabs(x2 - x1);
        float rh = std::fabs(y2 - y1);
        g.DrawEllipse(&pen, rx, ry, rw, rh);
    } else if (item.tool == L"text" && !item.text.empty()) {
        auto font = CreateUiFont(static_cast<float>(item.font_px), true);
        Gdiplus::FontFamily fam;
        font->GetFamily(&fam);
        Gdiplus::GraphicsPath path;
        Gdiplus::StringFormat sf;
        path.AddString(
            item.text.c_str(),
            -1,
            &fam,
            Gdiplus::FontStyleBold,
            static_cast<float>(item.font_px),
            Gdiplus::PointF(x1, y1),
            &sf);

        float lum = 0.299f * col.GetR() + 0.587f * col.GetG() + 0.114f * col.GetB();
        Gdiplus::Color stroke_c = (lum > 110.0f)
            ? Gdiplus::Color(245, 15, 23, 42)
            : Gdiplus::Color(245, 255, 255, 255);
        float stroke_w = std::max(2.5f, static_cast<float>(item.font_px) / 7.5f);
        Gdiplus::Pen stroke_pen(stroke_c, stroke_w);
        stroke_pen.SetLineJoin(Gdiplus::LineJoinRound);
        Gdiplus::SolidBrush fill_b(col);
        g.DrawPath(&stroke_pen, &path);
        g.FillPath(&fill_b, &path);
    }
}

std::unique_ptr<Gdiplus::Bitmap> AnnotationEditor::RenderItemsOnto(
    Gdiplus::Bitmap* base,
    const std::vector<AnnotationItem>& items_to_draw) {

    auto out = CloneBitmap(base);
    if (!out || items_to_draw.empty()) return out;

    Gdiplus::Graphics g(out.get());
    g.SetSmoothingMode(Gdiplus::SmoothingModeAntiAlias);
    g.SetTextRenderingHint(Gdiplus::TextRenderingHintAntiAliasGridFit);

    // 1. Render pixelate items first (just like the original Python version)
    for (const auto& it : items_to_draw) {
        if (it.tool == L"pixelate") {
            DrawSingleItem(g, out.get(), it);
        }
    }
    // 2. Render vector items on top
    for (const auto& it : items_to_draw) {
        if (it.tool != L"pixelate") {
            DrawSingleItem(g, out.get(), it);
        }
    }
    return out;
}

void AnnotationEditor::RebuildComposite() {
    cached_composite_ = RenderItemsOnto(base_image_.get(), items_);
}

void AnnotationEditor::DrawToolbarItem(
    Gdiplus::Graphics& g,
    const ToolbarItem& item,
    bool hovered,
    float dpi) {

    if (!item.visible) return;

    if (item.kind == BtnKind::Divider) {
        Gdiplus::Pen div_pen(HexToColor(L"#cbd5e1"), 1.0f);
        g.DrawLine(&div_pen, item.rect.X, item.rect.Y, item.rect.X, item.rect.GetBottom());
        return;
    }

    if (item.kind == BtnKind::LabelOnly) {
        auto font = CreateUiFont(12.5f * dpi, true);
        Gdiplus::SolidBrush br(HexToColor(L"#1e293b"));
        Gdiplus::StringFormat sf;
        sf.SetAlignment(Gdiplus::StringAlignmentNear);
        sf.SetLineAlignment(Gdiplus::StringAlignmentCenter);
        g.DrawString(item.label.c_str(), -1, font.get(), item.rect, &sf, &br);
        return;
    }

    if (item.kind == BtnKind::ColorSwatch) {
        bool active = (_wcsicmp(item.color_hex.c_str(), current_color_.c_str()) == 0);
        float cx = item.rect.X + item.rect.Width * 0.5f;
        float cy = item.rect.Y + item.rect.Height * 0.5f;
        float r_outer = item.rect.Width * 0.5f - std::round(1.5f * dpi);

        if (active) {
            Gdiplus::Pen ring_pen(HexToColor(L"#0284c7"), std::max(2.0f, 2.2f * dpi));
            g.DrawEllipse(&ring_pen, cx - r_outer, cy - r_outer, r_outer * 2.0f, r_outer * 2.0f);
        } else if (hovered) {
            Gdiplus::Pen ring_pen(HexToColor(L"#64748b", 220), std::max(1.5f, 1.5f * dpi));
            g.DrawEllipse(&ring_pen, cx - r_outer, cy - r_outer, r_outer * 2.0f, r_outer * 2.0f);
        }

        float r_inner = r_outer - std::round((active ? 3.5f : 3.0f) * dpi);
        Gdiplus::SolidBrush fill_b(HexToColor(item.color_hex));
        Gdiplus::Pen border_p(Gdiplus::Color(185, 100, 116, 139), 1.0f);
        g.FillEllipse(&fill_b, cx - r_inner, cy - r_inner, r_inner * 2.0f, r_inner * 2.0f);
        g.DrawEllipse(&border_p, cx - r_inner, cy - r_inner, r_inner * 2.0f, r_inner * 2.0f);
        return;
    }

    if (item.kind == BtnKind::StrokeSize) {
        bool active = (item.size_val == current_size_);
        Gdiplus::Color bg = active ? HexToColor(L"#0284c7") : (hovered ? HexToColor(L"#e0f2fe") : HexToColor(L"#ffffff"));
        Gdiplus::Color fg = active ? HexToColor(L"#ffffff") : (hovered ? HexToColor(L"#0369a1") : HexToColor(L"#1e293b"));
        Gdiplus::Color bd = active ? HexToColor(L"#0284c7") : (hovered ? HexToColor(L"#7dd3fc") : HexToColor(L"#cbd5e1"));

        DrawRoundedRect(g, item.rect, std::round(5.5f * dpi), bg, bd, 1.0f);

        auto font = CreateUiFont(12.5f * dpi, true);
        Gdiplus::RectF tbox;
        g.MeasureString(item.label.c_str(), -1, font.get(), Gdiplus::PointF(0, 0), &tbox);
        float dot_r = std::max(2.5f, std::round(item.dot_r_pt * dpi * 0.85f));
        float gap = std::round(5.0f * dpi);
        float total_w = dot_r * 2.0f + gap + tbox.Width;
        float sx = item.rect.X + (item.rect.Width - total_w) * 0.5f;
        float cy = item.rect.Y + item.rect.Height * 0.5f;

        Gdiplus::SolidBrush fg_b(fg);
        g.FillEllipse(&fg_b, sx, cy - dot_r, dot_r * 2.0f, dot_r * 2.0f);

        Gdiplus::StringFormat sf;
        sf.SetAlignment(Gdiplus::StringAlignmentNear);
        sf.SetLineAlignment(Gdiplus::StringAlignmentCenter);
        Gdiplus::RectF trc(sx + dot_r * 2.0f + gap, item.rect.Y, tbox.Width + 6.0f, item.rect.Height);
        g.DrawString(item.label.c_str(), -1, font.get(), trc, &sf, &fg_b);
        return;
    }

    // Pill button (Tool, Undo, Redo, Clear, CustomColor, Copy, Save, Close)
    bool active = (item.kind == BtnKind::Tool && item.id == current_tool_);
    Gdiplus::Color bg, fg, bd;
    bool has_border = true;

    if (item.kind == BtnKind::ActionClear) {
        bg = hovered ? HexToColor(L"#ffe4e6") : HexToColor(L"#fff1f2");
        fg = hovered ? HexToColor(L"#9f1239") : HexToColor(L"#be123c");
        bd = hovered ? HexToColor(L"#fda4af") : HexToColor(L"#fecdd3");
    } else if (item.kind == BtnKind::ActionCopy) {
        bg = hovered ? HexToColor(L"#047857") : HexToColor(L"#059669");
        fg = HexToColor(L"#ffffff");
        has_border = false;
    } else if (item.kind == BtnKind::ActionSave) {
        bg = hovered ? HexToColor(L"#0369a1") : HexToColor(L"#0284c7");
        fg = HexToColor(L"#ffffff");
        has_border = false;
    } else if (item.kind == BtnKind::ActionClose) {
        bg = hovered ? HexToColor(L"#fee2e2") : HexToColor(L"#e2e8f0");
        fg = hovered ? HexToColor(L"#b91c1c") : HexToColor(L"#334155");
        has_border = false;
    } else if (active) {
        bg = hovered ? HexToColor(L"#0369a1") : HexToColor(L"#0284c7");
        fg = HexToColor(L"#ffffff");
        has_border = false;
    } else {
        bg = hovered ? HexToColor(L"#e0f2fe") : HexToColor(L"#ffffff");
        fg = hovered ? HexToColor(L"#0369a1") : HexToColor(L"#1e293b");
        bd = hovered ? HexToColor(L"#7dd3fc") : HexToColor(L"#cbd5e1");
    }

    DrawRoundedRect(
        g,
        item.rect,
        std::round(5.5f * dpi),
        bg,
        has_border ? bd : Gdiplus::Color(0, 0, 0, 0),
        has_border ? 1.0f : 0.0f);

    float font_sz = (item.kind == BtnKind::Tool || item.kind == BtnKind::ActionUndo ||
                     item.kind == BtnKind::ActionRedo || item.kind == BtnKind::ActionClear)
        ? (13.0f * dpi)
        : (12.5f * dpi);
    auto font = CreateUiFont(font_sz, true);
    Gdiplus::RectF tbox;
    g.MeasureString(item.label.c_str(), -1, font.get(), Gdiplus::PointF(0, 0), &tbox);

    float icon_sz = item.icon_name.empty() ? 0.0f : std::round(15.5f * dpi);
    float gap = item.icon_name.empty() ? 0.0f : std::round(5.5f * dpi);
    float total_w = icon_sz + gap + tbox.Width;
    float sx = item.rect.X + (item.rect.Width - total_w) * 0.5f;
    float cy = item.rect.Y + item.rect.Height * 0.5f;

    if (!item.icon_name.empty()) {
        DrawToolVectorIcon(g, item.icon_name, sx + icon_sz * 0.5f, cy, icon_sz, fg);
    }

    Gdiplus::SolidBrush fg_b(fg);
    Gdiplus::StringFormat sf;
    sf.SetAlignment(Gdiplus::StringAlignmentNear);
    sf.SetLineAlignment(Gdiplus::StringAlignmentCenter);
    Gdiplus::RectF trc(sx + icon_sz + gap, item.rect.Y, tbox.Width + 6.0f, item.rect.Height);
    g.DrawString(item.label.c_str(), -1, font.get(), trc, &sf, &fg_b);
}

void AnnotationEditor::RenderWindow(HDC hdc, int client_w, int client_h) {
    if (client_w <= 0 || client_h <= 0 || !base_image_) return;

    Gdiplus::Bitmap back_bmp(client_w, client_h, PixelFormat32bppARGB);
    Gdiplus::Graphics g(&back_bmp);
    g.SetSmoothingMode(Gdiplus::SmoothingModeAntiAlias);
    g.SetTextRenderingHint(Gdiplus::TextRenderingHintClearTypeGridFit);

    float dpi = GetWindowDpiScale(hwnd_);

    // 1. Canvas Area Background
    g.Clear(HexToColor(L"#d5dfec"));

    // 2. Top Toolbar Row 1 & Row 2 Backgrounds
    Gdiplus::SolidBrush br_r1(HexToColor(L"#e8eef5"));
    Gdiplus::SolidBrush br_r2(HexToColor(L"#f1f5f9"));
    g.FillRectangle(&br_r1, 0.0f, 0.0f, static_cast<float>(client_w), row1_h_);
    g.FillRectangle(&br_r2, 0.0f, row1_h_ + 1.0f, static_cast<float>(client_w), row2_h_);

    Gdiplus::Pen pen_div_soft(HexToColor(L"#cbd5e1"), 1.0f);
    Gdiplus::Pen pen_div_slate(HexToColor(L"#94a3b8"), 1.0f);
    g.DrawLine(&pen_div_soft, 0.0f, row1_h_, static_cast<float>(client_w), row1_h_);
    float r2_bot = row1_h_ + 1.0f + row2_h_;
    g.DrawLine(&pen_div_slate, 0.0f, r2_bot, static_cast<float>(client_w), r2_bot);

    for (size_t i = 0; i < row1_items_.size(); ++i) {
        DrawToolbarItem(g, row1_items_[i], hovered_row_ == 1 && hovered_idx_ == static_cast<int>(i), dpi);
    }
    for (size_t i = 0; i < row2_items_.size(); ++i) {
        DrawToolbarItem(g, row2_items_[i], hovered_row_ == 2 && hovered_idx_ == static_cast<int>(i), dpi);
    }

    // 3. Bottom Status Bar
    float status_y = static_cast<float>(client_h) - status_h_;
    g.FillRectangle(&br_r1, 0.0f, status_y, static_cast<float>(client_w), status_h_);
    g.DrawLine(&pen_div_soft, 0.0f, status_y, static_cast<float>(client_w), status_y);

    std::wstring status_txt = TrFmtInt2(
        L"editor_status_bar",
        static_cast<int>(base_image_->GetWidth()),
        static_cast<int>(base_image_->GetHeight()));
    auto font_status = CreateUiFont(12.0f * dpi, true);
    Gdiplus::SolidBrush br_status_fg(HexToColor(L"#334155"));
    Gdiplus::StringFormat sf_center;
    sf_center.SetAlignment(Gdiplus::StringAlignmentCenter);
    sf_center.SetLineAlignment(Gdiplus::StringAlignmentCenter);
    g.DrawString(
        status_txt.c_str(),
        -1,
        font_status.get(),
        Gdiplus::RectF(0.0f, status_y, static_cast<float>(client_w), status_h_),
        &sf_center,
        &br_status_fg);

    // 4. Canvas Image & Live Dragging Layer
    Gdiplus::Pen canvas_border_pen(HexToColor(L"#64748b"), 1.0f);
    g.DrawRectangle(
        &canvas_border_pen,
        canvas_rc_.X - 1.0f,
        canvas_rc_.Y - 1.0f,
        canvas_rc_.Width + 1.0f,
        canvas_rc_.Height + 1.0f);

    g.SetInterpolationMode(
        interaction_mode_ == InteractionMode::None
            ? Gdiplus::InterpolationModeHighQualityBicubic
            : Gdiplus::InterpolationModeBilinear);

    if (interaction_mode_ == InteractionMode::None) {
        Gdiplus::Bitmap* src = cached_composite_ ? cached_composite_.get() : base_image_.get();
        g.DrawImage(src, canvas_rc_);
    } else {
        Gdiplus::Bitmap* bg = drag_bg_image_ ? drag_bg_image_.get() : (cached_composite_ ? cached_composite_.get() : base_image_.get());
        const AnnotationItem* active_item = nullptr;
        if (interaction_mode_ == InteractionMode::Drawing) {
            active_item = &drawing_item_;
        } else if (selected_idx_ >= 0 && selected_idx_ < static_cast<int>(items_.size())) {
            active_item = &items_[selected_idx_];
        }

        if (active_item && active_item->tool == L"pixelate") {
            auto temp = RenderItemsOnto(bg, {*active_item});
            g.DrawImage(temp.get(), canvas_rc_);
        } else {
            g.DrawImage(bg, canvas_rc_);
            if (active_item) {
                Gdiplus::GraphicsState state = g.Save();
                g.SetClip(canvas_rc_);
                g.TranslateTransform(canvas_rc_.X, canvas_rc_.Y);
                g.ScaleTransform(display_scale_x_, display_scale_y_);
                DrawSingleItem(g, bg, *active_item);
                g.Restore(state);
            }
        }
    }

    // 5. Selection Overlay (dashed bounding box & control handles)
    if (selected_idx_ >= 0 && selected_idx_ < static_cast<int>(items_.size())) {
        const auto& sel = items_[selected_idx_];
        if (sel.tool != L"arrow" && sel.tool != L"line") {
            Gdiplus::Rect bbox = sel.GetBBox();
            Gdiplus::PointF p1 = ImageToCanvasCoords(static_cast<float>(bbox.X), static_cast<float>(bbox.Y));
            Gdiplus::PointF p2 = ImageToCanvasCoords(static_cast<float>(bbox.GetRight()), static_cast<float>(bbox.GetBottom()));
            Gdiplus::Pen dash_pen(HexToColor(L"#38bdf8"), 1.2f);
            float dash_vals[2] = {4.0f, 4.0f};
            dash_pen.SetDashPattern(dash_vals, 2);
            g.DrawRectangle(&dash_pen, p1.X, p1.Y, p2.X - p1.X, p2.Y - p1.Y);
        }

        float hr = 5.0f * dpi;
        Gdiplus::SolidBrush h_fill(HexToColor(L"#ffffff"));
        Gdiplus::Pen h_pen(HexToColor(L"#0284c7"), 2.0f);
        for (const auto& hp : sel.GetHandles()) {
            Gdiplus::PointF ch = ImageToCanvasCoords(static_cast<float>(hp.X), static_cast<float>(hp.Y));
            g.FillEllipse(&h_fill, ch.X - hr, ch.Y - hr, hr * 2.0f, hr * 2.0f);
            g.DrawEllipse(&h_pen, ch.X - hr, ch.Y - hr, hr * 2.0f, hr * 2.0f);
        }
    }

    Gdiplus::Graphics screen_g(hdc);
    screen_g.DrawImage(&back_bmp, 0, 0);
}

// ==================== Inline Text Editing ====================

LRESULT CALLBACK AnnotationEditor::TextEditSubclassProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    auto* self = reinterpret_cast<AnnotationEditor*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA));
    if (self) {
        if (msg == WM_KEYDOWN) {
            if (wparam == VK_RETURN) {
                self->CommitActiveText();
                return 0;
            }
            if (wparam == VK_ESCAPE) {
                self->CancelActiveText();
                return 0;
            }
        } else if (msg == WM_CHAR && (wparam == L'\r' || wparam == L'\n' || wparam == 27)) {
            return 0;
        }
    }
    return CallWindowProcW(self ? self->orig_edit_proc_ : DefWindowProcW, hwnd, msg, wparam, lparam);
}

void AnnotationEditor::SpawnTextEntry(int canvas_x, int canvas_y, const std::wstring& initial_text) {
    CancelActiveText();
    text_img_pos_ = CanvasToImageCoords(canvas_x, canvas_y);

    float dpi = GetWindowDpiScale(hwnd_);
    int font_px = std::max(16, static_cast<int>(std::round(current_size_ * 3.6f * dpi)));
    if (edit_hfont_) DeleteObject(edit_hfont_);
    edit_hfont_ = CreateWin32UiFont(font_px, true);
    if (!edit_bg_brush_) {
        edit_bg_brush_ = CreateSolidBrush(RGB(15, 23, 42));
    }

    int edit_w = static_cast<int>(std::round(260.0f * dpi));
    int edit_h = font_px + static_cast<int>(std::round(12.0f * dpi));
    int ex = std::max(static_cast<int>(canvas_rc_.X), std::min(static_cast<int>(canvas_rc_.GetRight()) - 60, canvas_x));
    int ey = std::max(static_cast<int>(canvas_rc_.Y), std::min(static_cast<int>(canvas_rc_.GetBottom()) - edit_h, canvas_y));

    hwnd_edit_ = CreateWindowExW(
        0,
        L"EDIT",
        initial_text.c_str(),
        WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL,
        ex, ey, edit_w, edit_h,
        hwnd_,
        nullptr,
        GetModuleHandleW(nullptr),
        nullptr);

    if (!hwnd_edit_) return;

    SendMessageW(hwnd_edit_, WM_SETFONT, reinterpret_cast<WPARAM>(edit_hfont_), TRUE);
    SetWindowLongPtrW(hwnd_edit_, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(this));
    orig_edit_proc_ = reinterpret_cast<WNDPROC>(
        SetWindowLongPtrW(hwnd_edit_, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(TextEditSubclassProc)));

    SetFocus(hwnd_edit_);
    if (!initial_text.empty()) {
        SendMessageW(hwnd_edit_, EM_SETSEL, 0, -1);
    }
}

void AnnotationEditor::CancelActiveText() {
    editing_item_idx_ = -1;
    if (hwnd_edit_ && IsWindow(hwnd_edit_)) {
        DestroyWindow(hwnd_edit_);
    }
    hwnd_edit_ = nullptr;
    if (hwnd_ && IsWindow(hwnd_)) {
        SetFocus(hwnd_);
        InvalidateRect(hwnd_, nullptr, FALSE);
    }
}

void AnnotationEditor::CommitActiveText() {
    if (!hwnd_edit_ || !IsWindow(hwnd_edit_)) {
        hwnd_edit_ = nullptr;
        editing_item_idx_ = -1;
        return;
    }

    int len = GetWindowTextLengthW(hwnd_edit_);
    std::wstring txt;
    if (len > 0) {
        txt.resize(len + 1, L'\0');
        GetWindowTextW(hwnd_edit_, txt.data(), len + 1);
        txt.resize(wcslen(txt.c_str()));
    }
    // Trim whitespace
    size_t first = txt.find_first_not_of(L" \t\r\n");
    size_t last = txt.find_last_not_of(L" \t\r\n");
    txt = (first == std::wstring::npos) ? L"" : txt.substr(first, last - first + 1);

    int edit_idx = editing_item_idx_;
    editing_item_idx_ = -1;
    DestroyWindow(hwnd_edit_);
    hwnd_edit_ = nullptr;
    if (hwnd_) SetFocus(hwnd_);

    if (edit_idx >= 0 && edit_idx < static_cast<int>(items_.size())) {
        SaveUndoSnapshot();
        if (txt.empty()) {
            items_.erase(items_.begin() + edit_idx);
            selected_idx_ = -1;
        } else {
            items_[edit_idx].text = txt;
            selected_idx_ = edit_idx;
        }
        RebuildComposite();
        if (hwnd_) InvalidateRect(hwnd_, nullptr, FALSE);
        return;
    }

    if (txt.empty()) return;

    SaveUndoSnapshot();
    AnnotationItem new_item{};
    new_item.tool = L"text";
    new_item.color = current_color_;
    new_item.size = current_size_;
    new_item.stroke_px = ScaledStrokeWidth();
    new_item.points = {text_img_pos_};
    new_item.text = txt;
    new_item.font_px = ScaledFontPx();
    items_.push_back(std::move(new_item));
    selected_idx_ = static_cast<int>(items_.size()) - 1;
    RebuildComposite();
    if (hwnd_) InvalidateRect(hwnd_, nullptr, FALSE);
}

// ==================== Export & Window Events ====================

void AnnotationEditor::CopyAndFinish() {
    CommitActiveText();
    auto final_img = RenderItemsOnto(base_image_.get(), items_);
    auto cb = on_copy_clipboard_;
    CloseEditor();
    if (cb && final_img) {
        cb(final_img.get());
    }
}

void AnnotationEditor::SaveToFile() {
    CommitActiveText();

    SYSTEMTIME st{};
    GetLocalTime(&st);
    wchar_t file_buf[MAX_PATH] = {0};
    swprintf_s(
        file_buf,
        L"screenshot_%04d%02d%02d_%02d%02d%02d.png",
        st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);

    std::wstring title = Tr(L"editor_save_dialog_title");
    OPENFILENAMEW ofn{};
    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = hwnd_;
    ofn.lpstrFilter =
        L"PNG Lossless (*.png)\0*.png\0"
        L"JPEG High Quality (*.jpg)\0*.jpg;*.jpeg\0"
        L"Bitmap (*.bmp)\0*.bmp\0\0";
    ofn.lpstrFile = file_buf;
    ofn.nMaxFile = MAX_PATH;
    ofn.lpstrTitle = title.c_str();
    ofn.lpstrDefExt = L"png";
    ofn.Flags = OFN_OVERWRITEPROMPT | OFN_PATHMUSTEXIST | OFN_EXPLORER;

    if (GetSaveFileNameW(&ofn)) {
        auto final_img = RenderItemsOnto(base_image_.get(), items_);
        SaveBitmapToFile(final_img.get(), file_buf);
    }
}

LRESULT CALLBACK AnnotationEditor::WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    AnnotationEditor* self = nullptr;
    if (msg == WM_NCCREATE) {
        auto* cs = reinterpret_cast<CREATESTRUCTW*>(lparam);
        self = static_cast<AnnotationEditor*>(cs->lpCreateParams);
        SetWindowLongPtrW(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(self));
    } else {
        self = reinterpret_cast<AnnotationEditor*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA));
    }
    if (self) {
        return self->HandleMessage(hwnd, msg, wparam, lparam);
    }
    return DefWindowProcW(hwnd, msg, wparam, lparam);
}

LRESULT AnnotationEditor::HandleMessage(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    switch (msg) {
    case WM_ERASEBKGND:
        return 1;

    case WM_CTLCOLOREDIT: {
        HDC hdc_edit = reinterpret_cast<HDC>(wparam);
        SetTextColor(hdc_edit, HexToColorRef(current_color_));
        SetBkColor(hdc_edit, RGB(15, 23, 42));
        return reinterpret_cast<LRESULT>(edit_bg_brush_);
    }

    case WM_GETMINMAXINFO: {
        auto* mmi = reinterpret_cast<MINMAXINFO*>(lparam);
        mmi->ptMinTrackSize.x = min_win_w_;
        mmi->ptMinTrackSize.y = min_win_h_;
        return 0;
    }

    case WM_SIZE: {
        if (wparam == SIZE_MINIMIZED) {
            CloseEditor();
            return 0;
        }
        int cw = LOWORD(lparam);
        int ch = HIWORD(lparam);
        RecalculateLayout(cw, ch);
        InvalidateRect(hwnd, nullptr, FALSE);
        return 0;
    }

    case WM_MOUSEMOVE: {
        int mx = GET_X_LPARAM(lparam);
        int my = GET_Y_LPARAM(lparam);
        Gdiplus::PointF mpt(static_cast<float>(mx), static_cast<float>(my));

        if (interaction_mode_ != InteractionMode::None) {
            Gdiplus::Point ip = CanvasToImageCoords(mx, my);
            if (interaction_mode_ == InteractionMode::Moving && selected_idx_ >= 0) {
                int dx = ip.X - drag_last_img_pos_.X;
                int dy = ip.Y - drag_last_img_pos_.Y;
                if (dx != 0 || dy != 0) {
                    items_[selected_idx_].Translate(
                        dx,
                        dy,
                        static_cast<int>(base_image_->GetWidth()),
                        static_cast<int>(base_image_->GetHeight()));
                    drag_last_img_pos_ = ip;
                    InvalidateRect(hwnd, nullptr, FALSE);
                    UpdateWindow(hwnd);
                }
            } else if (interaction_mode_ == InteractionMode::Handle && selected_idx_ >= 0) {
                items_[selected_idx_].MoveHandle(active_handle_idx_, ip.X, ip.Y);
                drag_last_img_pos_ = ip;
                InvalidateRect(hwnd, nullptr, FALSE);
                UpdateWindow(hwnd);
            } else if (interaction_mode_ == InteractionMode::Drawing) {
                if (drawing_item_.tool == L"pen" || drawing_item_.tool == L"highlighter") {
                    drawing_item_.points.push_back(ip);
                } else {
                    if (drawing_item_.points.size() == 1) {
                        drawing_item_.points.push_back(ip);
                    } else {
                        drawing_item_.points.back() = ip;
                    }
                }
                InvalidateRect(hwnd, nullptr, FALSE);
                UpdateWindow(hwnd);
            }
            return 0;
        }

        // Check toolbar hover
        int new_h_row = 0;
        int new_h_idx = -1;
        for (size_t i = 0; i < row1_items_.size(); ++i) {
            const auto& it = row1_items_[i];
            if (it.visible && it.kind != BtnKind::Divider && it.kind != BtnKind::LabelOnly && it.rect.Contains(mpt)) {
                new_h_row = 1;
                new_h_idx = static_cast<int>(i);
                break;
            }
        }
        if (new_h_row == 0) {
            for (size_t i = 0; i < row2_items_.size(); ++i) {
                const auto& it = row2_items_[i];
                if (it.visible && it.kind != BtnKind::Divider && it.kind != BtnKind::LabelOnly && it.rect.Contains(mpt)) {
                    new_h_row = 2;
                    new_h_idx = static_cast<int>(i);
                    break;
                }
            }
        }
        if (new_h_row != hovered_row_ || new_h_idx != hovered_idx_) {
            hovered_row_ = new_h_row;
            hovered_idx_ = new_h_idx;
            InvalidateRect(hwnd, nullptr, FALSE);
        }

        // Set appropriate cursor
        if (new_h_row != 0) {
            SetCursor(LoadCursorW(nullptr, IDC_HAND));
        } else if (canvas_rc_.Contains(mpt)) {
            Gdiplus::Point ip = CanvasToImageCoords(mx, my);
            if (FindHandleAt(ip.X, ip.Y) >= 0) {
                SetCursor(LoadCursorW(nullptr, IDC_HAND));
            } else if (FindItemAt(ip.X, ip.Y) >= 0) {
                SetCursor(LoadCursorW(nullptr, IDC_SIZEALL));
            } else {
                SetCursor(LoadCursorW(nullptr, IDC_CROSS));
            }
        } else {
            SetCursor(LoadCursorW(nullptr, IDC_ARROW));
        }
        return 0;
    }

    case WM_LBUTTONDBLCLK: {
        int mx = GET_X_LPARAM(lparam);
        int my = GET_Y_LPARAM(lparam);
        if (canvas_rc_.Contains(Gdiplus::PointF(static_cast<float>(mx), static_cast<float>(my)))) {
            Gdiplus::Point ip = CanvasToImageCoords(mx, my);
            int hit = FindItemAt(ip.X, ip.Y);
            if (hit >= 0 && items_[hit].tool == L"text") {
                CommitActiveText();
                selected_idx_ = hit;
                editing_item_idx_ = hit;
                Gdiplus::PointF cp = ImageToCanvasCoords(
                    static_cast<float>(items_[hit].points[0].X),
                    static_cast<float>(items_[hit].points[0].Y));
                SpawnTextEntry(static_cast<int>(cp.X), static_cast<int>(cp.Y), items_[hit].text);
                return 0;
            }
        }
        break;
    }

    case WM_LBUTTONDOWN: {
        int mx = GET_X_LPARAM(lparam);
        int my = GET_Y_LPARAM(lparam);
        Gdiplus::PointF mpt(static_cast<float>(mx), static_cast<float>(my));

        if (hwnd_edit_) {
            CommitActiveText();
        }

        // Check toolbar clicks
        auto handle_toolbar_click = [&](const ToolbarItem& it) {
            switch (it.kind) {
            case BtnKind::Tool:
                SelectTool(it.id);
                break;
            case BtnKind::ActionUndo:
                Undo();
                break;
            case BtnKind::ActionRedo:
                Redo();
                break;
            case BtnKind::ActionClear:
                ClearAll();
                break;
            case BtnKind::ColorSwatch:
                SelectColor(it.color_hex);
                break;
            case BtnKind::CustomColor:
                PickCustomColor();
                break;
            case BtnKind::StrokeSize:
                SelectSize(it.size_val);
                break;
            case BtnKind::ActionCopy:
                CopyAndFinish();
                break;
            case BtnKind::ActionSave:
                SaveToFile();
                break;
            case BtnKind::ActionClose:
                CloseEditor();
                break;
            default:
                break;
            }
        };

        for (const auto& it : row1_items_) {
            if (it.visible && it.rect.Contains(mpt) && it.kind != BtnKind::Divider && it.kind != BtnKind::LabelOnly) {
                handle_toolbar_click(it);
                return 0;
            }
        }
        for (const auto& it : row2_items_) {
            if (it.visible && it.rect.Contains(mpt) && it.kind != BtnKind::Divider && it.kind != BtnKind::LabelOnly) {
                handle_toolbar_click(it);
                return 0;
            }
        }

        // Check canvas interaction
        if (!canvas_rc_.Contains(mpt)) {
            if (selected_idx_ != -1) {
                selected_idx_ = -1;
                InvalidateRect(hwnd, nullptr, FALSE);
            }
            return 0;
        }

        Gdiplus::Point ip = CanvasToImageCoords(mx, my);

        int h_idx = FindHandleAt(ip.X, ip.Y);
        if (h_idx >= 0 && selected_idx_ >= 0) {
            SaveUndoSnapshot();
            interaction_mode_ = InteractionMode::Handle;
            active_handle_idx_ = h_idx;
            drag_last_img_pos_ = ip;
            std::vector<AnnotationItem> others;
            for (int i = 0; i < static_cast<int>(items_.size()); ++i) {
                if (i != selected_idx_) others.push_back(items_[i]);
            }
            drag_bg_image_ = RenderItemsOnto(base_image_.get(), others);
            SetCapture(hwnd);
            SetCursor(LoadCursorW(nullptr, IDC_HAND));
            return 0;
        }

        int hit_idx = FindItemAt(ip.X, ip.Y);
        if (hit_idx >= 0) {
            SaveUndoSnapshot();
            selected_idx_ = hit_idx;
            interaction_mode_ = InteractionMode::Moving;
            drag_last_img_pos_ = ip;
            std::vector<AnnotationItem> others;
            for (int i = 0; i < static_cast<int>(items_.size()); ++i) {
                if (i != selected_idx_) others.push_back(items_[i]);
            }
            drag_bg_image_ = RenderItemsOnto(base_image_.get(), others);
            SetCapture(hwnd);
            SetCursor(LoadCursorW(nullptr, IDC_SIZEALL));
            InvalidateRect(hwnd, nullptr, FALSE);
            return 0;
        }

        selected_idx_ = -1;

        if (current_tool_ == L"text") {
            editing_item_idx_ = -1;
            SpawnTextEntry(mx, my);
            InvalidateRect(hwnd, nullptr, FALSE);
            return 0;
        }

        interaction_mode_ = InteractionMode::Drawing;
        drag_bg_image_ = CloneBitmap(cached_composite_.get());
        drawing_item_ = AnnotationItem{};
        drawing_item_.tool = current_tool_;
        drawing_item_.color = current_color_;
        drawing_item_.size = current_size_;
        drawing_item_.stroke_px = ScaledStrokeWidth();
        drawing_item_.points = {ip};
        drawing_item_.font_px = ScaledFontPx();
        SetCapture(hwnd);
        SetCursor(LoadCursorW(nullptr, IDC_CROSS));
        return 0;
    }

    case WM_LBUTTONUP: {
        if (interaction_mode_ == InteractionMode::None) return 0;
        if (GetCapture() == hwnd) {
            ReleaseCapture();
        }

        int mx = GET_X_LPARAM(lparam);
        int my = GET_Y_LPARAM(lparam);
        Gdiplus::Point ip = CanvasToImageCoords(mx, my);

        InteractionMode mode = interaction_mode_;
        interaction_mode_ = InteractionMode::None;
        active_handle_idx_ = -1;
        drag_bg_image_.reset();

        if (mode == InteractionMode::Moving || mode == InteractionMode::Handle) {
            RebuildComposite();
            InvalidateRect(hwnd, nullptr, FALSE);
            return 0;
        }

        if (mode == InteractionMode::Drawing) {
            if (drawing_item_.tool == L"pen" || drawing_item_.tool == L"highlighter") {
                drawing_item_.points.push_back(ip);
            } else {
                if (drawing_item_.points.size() == 1) {
                    drawing_item_.points.push_back(ip);
                } else {
                    drawing_item_.points.back() = ip;
                }
                const auto& p0 = drawing_item_.points.front();
                const auto& p1 = drawing_item_.points.back();
                if (std::hypot(static_cast<float>(p1.X - p0.X), static_cast<float>(p1.Y - p0.Y)) < 4.0f) {
                    RebuildComposite();
                    InvalidateRect(hwnd, nullptr, FALSE);
                    return 0;
                }
            }
            SaveUndoSnapshot();
            items_.push_back(std::move(drawing_item_));
            selected_idx_ = static_cast<int>(items_.size()) - 1;
            RebuildComposite();
            InvalidateRect(hwnd, nullptr, FALSE);
        }
        return 0;
    }

    case WM_KEYDOWN: {
        bool ctrl = (GetKeyState(VK_CONTROL) & 0x8000) != 0;
        if (ctrl && (wparam == 'Z' || wparam == 'z')) {
            Undo();
            return 0;
        }
        if (ctrl && (wparam == 'Y' || wparam == 'y')) {
            Redo();
            return 0;
        }
        if (ctrl && (wparam == 'S' || wparam == 's')) {
            SaveToFile();
            return 0;
        }
        if (ctrl && (wparam == 'C' || wparam == 'c')) {
            if (!hwnd_edit_) {
                CopyAndFinish();
                return 0;
            }
        }
        if (ctrl && (wparam == 'W' || wparam == 'w')) {
            CloseEditor();
            return 0;
        }
        if (wparam == VK_DELETE || wparam == VK_BACK) {
            if (!hwnd_edit_) {
                DeleteSelected();
                return 0;
            }
        }
        if (wparam == VK_RETURN) {
            if (hwnd_edit_) {
                CommitActiveText();
            }
            return 0;
        }
        if (wparam == VK_ESCAPE) {
            if (hwnd_edit_) {
                CancelActiveText();
                return 0;
            }
            if (selected_idx_ >= 0) {
                selected_idx_ = -1;
                InvalidateRect(hwnd, nullptr, FALSE);
                return 0;
            }
            CloseEditor();
            return 0;
        }
        break;
    }

    case WM_CLOSE:
        CloseEditor();
        return 0;

    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);
        RECT rc;
        GetClientRect(hwnd, &rc);
        RenderWindow(hdc, rc.right - rc.left, rc.bottom - rc.top);
        EndPaint(hwnd, &ps);
        return 0;
    }
    }
    return DefWindowProcW(hwnd, msg, wparam, lparam);
}

} // namespace app
