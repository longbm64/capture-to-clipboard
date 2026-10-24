#include "overlay.h"
#include "i18n.h"

namespace app {

namespace {
constexpr const wchar_t* kOverlayClassName = L"CaptureToClipboard_OverlayWnd";

void RegisterOverlayClass() {
    static bool registered = false;
    if (registered) return;
    WNDCLASSEXW wc{};
    wc.cbSize = sizeof(wc);
    wc.style = CS_HREDRAW | CS_VREDRAW | CS_DBLCLKS;
    wc.lpfnWndProc = RegionSelectorOverlay::WndProc;
    wc.hInstance = GetModuleHandleW(nullptr);
    wc.hCursor = nullptr; // Hidden cursor; replaced by full-screen crosshair
    wc.lpszClassName = kOverlayClassName;
    RegisterClassExW(&wc);
    registered = true;
}
} // namespace

RegionSelectorOverlay::RegionSelectorOverlay() = default;

RegionSelectorOverlay::~RegionSelectorOverlay() {
    Close();
}

void RegionSelectorOverlay::CleanupGdi() {
    if (hdc_bright_) {
        if (old_bright_) SelectObject(hdc_bright_, old_bright_);
        DeleteDC(hdc_bright_);
        hdc_bright_ = nullptr;
        old_bright_ = nullptr;
    }
    if (hdc_dimmed_) {
        if (old_dimmed_) SelectObject(hdc_dimmed_, old_dimmed_);
        DeleteDC(hdc_dimmed_);
        hdc_dimmed_ = nullptr;
        old_dimmed_ = nullptr;
    }
    if (hdc_back_) {
        if (old_back_) SelectObject(hdc_back_, old_back_);
        DeleteDC(hdc_back_);
        hdc_back_ = nullptr;
        old_back_ = nullptr;
    }
    if (hbm_back_) {
        DeleteObject(hbm_back_);
        hbm_back_ = nullptr;
    }
    capture_.Reset();
}

bool RegionSelectorOverlay::Open(
    ScreenCaptureData&& capture,
    int mode,
    OnSelectedCallback on_selected,
    OnCancelCallback on_cancel) {

    Close();
    RegisterOverlayClass();

    capture_ = std::move(capture);
    mode_ = mode;
    on_selected_ = std::move(on_selected);
    on_cancel_ = std::move(on_cancel);
    dragging_ = false;
    closed_ = false;

    if (mode_ == 1) {
        accent_color_ = HexToColor(L"#0284c7");
        accent_cref_ = RGB(2, 132, 199);
    } else {
        accent_color_ = HexToColor(L"#7c3aed");
        accent_cref_ = RGB(124, 58, 237);
    }

    HDC hdc_screen = GetDC(nullptr);
    hdc_bright_ = CreateCompatibleDC(hdc_screen);
    hdc_dimmed_ = CreateCompatibleDC(hdc_screen);
    hdc_back_ = CreateCompatibleDC(hdc_screen);

    BITMAPINFO bmi{};
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = capture_.width;
    bmi.bmiHeader.biHeight = -capture_.height;
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 32;
    bmi.bmiHeader.biCompression = BI_RGB;
    void* pv_back = nullptr;
    hbm_back_ = CreateDIBSection(hdc_screen, &bmi, DIB_RGB_COLORS, &pv_back, nullptr, 0);
    ReleaseDC(nullptr, hdc_screen);

    if (!hdc_bright_ || !hdc_dimmed_ || !hdc_back_ || !hbm_back_) {
        CleanupGdi();
        return false;
    }

    old_bright_ = SelectObject(hdc_bright_, capture_.hbm_bright);
    old_dimmed_ = SelectObject(hdc_dimmed_, capture_.hbm_dimmed);
    old_back_ = SelectObject(hdc_back_, hbm_back_);

    POINT pt{};
    GetCursorPos(&pt);
    cur_x_ = std::max(0, std::min(capture_.width - 1, static_cast<int>(pt.x) - capture_.left));
    cur_y_ = std::max(0, std::min(capture_.height - 1, static_cast<int>(pt.y) - capture_.top));

    RenderBackbuffer();

    hwnd_ = CreateWindowExW(
        WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
        kOverlayClassName,
        L"CaptureToClipboard Overlay",
        WS_POPUP | WS_VISIBLE,
        capture_.left,
        capture_.top,
        capture_.width,
        capture_.height,
        nullptr,
        nullptr,
        GetModuleHandleW(nullptr),
        this);

    if (!hwnd_) {
        CleanupGdi();
        return false;
    }

    SetWindowPos(
        hwnd_,
        HWND_TOPMOST,
        capture_.left,
        capture_.top,
        capture_.width,
        capture_.height,
        SWP_SHOWWINDOW);
    SetForegroundWindow(hwnd_);
    SetFocus(hwnd_);
    SetCursor(nullptr);
    InvalidateRect(hwnd_, nullptr, FALSE);
    UpdateWindow(hwnd_);
    return true;
}

void RegionSelectorOverlay::Close() {
    closed_ = true;
    if (GetCapture() == hwnd_) {
        ReleaseCapture();
    }
    if (hwnd_ && IsWindow(hwnd_)) {
        DestroyWindow(hwnd_);
    }
    hwnd_ = nullptr;
    CleanupGdi();
}

void RegionSelectorOverlay::RenderBackbuffer() {
    if (!hdc_back_ || !hdc_dimmed_ || !hdc_bright_) return;

    const int W = capture_.width;
    const int H = capture_.height;
    float dpi = GetWindowDpiScale(hwnd_);

    // 1. Copy dimmed screenshot to backbuffer (hardware BitBlt)
    BitBlt(hdc_back_, 0, 0, W, H, hdc_dimmed_, 0, 0, SRCCOPY);

    int x1 = std::min(start_x_, cur_x_);
    int y1 = std::min(start_y_, cur_y_);
    int x2 = std::max(start_x_, cur_x_);
    int y2 = std::max(start_y_, cur_y_);
    int sel_w = x2 - x1;
    int sel_h = y2 - y1;
    bool has_selection = dragging_ && (sel_w >= 2 && sel_h >= 2);

    if (has_selection) {
        // 2. Blit bright screenshot inside selected region (zero memory allocation)
        BitBlt(hdc_back_, x1, y1, sel_w, sel_h, hdc_bright_, x1, y1, SRCCOPY);
    }

    // 3. Full-screen 1px solid crosshair lines in accent color at (cur_x_, cur_y_)
    HPEN hpen_cross = CreatePen(PS_SOLID, 1, accent_cref_);
    if (hpen_cross) {
        HGDIOBJ old_pen = SelectObject(hdc_back_, hpen_cross);
        MoveToEx(hdc_back_, 0, cur_y_, nullptr);
        LineTo(hdc_back_, W, cur_y_);
        MoveToEx(hdc_back_, cur_x_, 0, nullptr);
        LineTo(hdc_back_, cur_x_, H);
        SelectObject(hdc_back_, old_pen);
        DeleteObject(hpen_cross);
    }

    Gdiplus::Graphics g(hdc_back_);
    g.SetSmoothingMode(Gdiplus::SmoothingModeAntiAlias);
    g.SetTextRenderingHint(Gdiplus::TextRenderingHintClearTypeGridFit);

    if (has_selection) {
        // Selection border & 4 corner handles
        Gdiplus::Pen border_pen(accent_color_, 2.0f);
        g.DrawRectangle(&border_pen, x1, y1, sel_w, sel_h);

        float r = 4.0f;
        Gdiplus::SolidBrush white_brush(Gdiplus::Color(255, 255, 255, 255));
        Gdiplus::PointF corners[4] = {
            {static_cast<float>(x1), static_cast<float>(y1)},
            {static_cast<float>(x2), static_cast<float>(y1)},
            {static_cast<float>(x1), static_cast<float>(y2)},
            {static_cast<float>(x2), static_cast<float>(y2)}
        };
        for (const auto& c : corners) {
            Gdiplus::RectF hrc(c.X - r, c.Y - r, r * 2.0f, r * 2.0f);
            g.FillRectangle(&white_brush, hrc);
            g.DrawRectangle(&border_pen, hrc);
        }

        // Resolution badge: "{sel_w} x {sel_h} px"
        wchar_t size_str[64];
        swprintf_s(size_str, L"%d \u00D7 %d px", sel_w, sel_h);
        auto font = CreateUiFont(12.0f * dpi, true);
        Gdiplus::RectF text_box;
        g.MeasureString(size_str, -1, font.get(), Gdiplus::PointF(0, 0), &text_box);

        float badge_w = std::ceil(text_box.Width) + std::round(16.0f * dpi);
        float badge_h = std::ceil(text_box.Height) + std::round(8.0f * dpi);
        float badge_x = static_cast<float>(x2) + 8.0f;
        float badge_y = static_cast<float>(y2) + 8.0f;
        if (badge_x + badge_w > W - 10) {
            badge_x = std::max(6.0f, static_cast<float>(x1) - badge_w - 8.0f);
        }
        if (badge_y + badge_h > H - 10) {
            badge_y = std::max(6.0f, static_cast<float>(y1) - badge_h - 8.0f);
        }

        Gdiplus::RectF badge_rc(badge_x, badge_y, badge_w, badge_h);
        DrawRoundedRect(g, badge_rc, 4.0f * dpi, Gdiplus::Color(255, 255, 255, 255), accent_color_, 1.2f);

        Gdiplus::SolidBrush text_brush(Gdiplus::Color(255, 30, 41, 59));
        Gdiplus::StringFormat sf;
        sf.SetAlignment(Gdiplus::StringAlignmentCenter);
        sf.SetLineAlignment(Gdiplus::StringAlignmentCenter);
        g.DrawString(size_str, -1, font.get(), badge_rc, &sf, &text_brush);
    }

    // 4. Coordinate pill badge near cursor: "{cur_x_}, {cur_y_}" (#0f172a fill, accent border, #f8fafc text)
    {
        wchar_t coord_str[64];
        swprintf_s(coord_str, L"%d, %d", cur_x_, cur_y_);
        auto cfont = CreateUiFont(11.5f * dpi, true);
        Gdiplus::RectF cbox;
        g.MeasureString(coord_str, -1, cfont.get(), Gdiplus::PointF(0, 0), &cbox);

        float cw = std::ceil(cbox.Width) + std::round(14.0f * dpi);
        float ch = std::ceil(cbox.Height) + std::round(6.0f * dpi);
        float cx = static_cast<float>(cur_x_) + 16.0f;
        float cy = has_selection
            ? (static_cast<float>(cur_y_) - ch - 14.0f)
            : (static_cast<float>(cur_y_) + 16.0f);

        if (cx + cw > W - 8) {
            cx = static_cast<float>(cur_x_) - cw - 12.0f;
        }
        if (cy < 8.0f) {
            cy = static_cast<float>(cur_y_) + 16.0f;
        }
        if (cy + ch > H - 8) {
            cy = static_cast<float>(cur_y_) - ch - 12.0f;
        }

        Gdiplus::RectF coord_rc(cx, cy, cw, ch);
        DrawRoundedRect(
            g,
            coord_rc,
            4.0f * dpi,
            Gdiplus::Color(245, 15, 23, 42), // #0f172a
            accent_color_,
            1.0f);

        Gdiplus::SolidBrush coord_text_brush(Gdiplus::Color(255, 248, 250, 252)); // #f8fafc
        Gdiplus::StringFormat csf;
        csf.SetAlignment(Gdiplus::StringAlignmentCenter);
        csf.SetLineAlignment(Gdiplus::StringAlignmentCenter);
        g.DrawString(coord_str, -1, cfont.get(), coord_rc, &csf, &coord_text_brush);
    }
}

void RegionSelectorOverlay::FinishSelection() {
    if (closed_) return;
    int x1 = std::min(start_x_, cur_x_);
    int y1 = std::min(start_y_, cur_y_);
    int x2 = std::max(start_x_, cur_x_);
    int y2 = std::max(start_y_, cur_y_);
    int w = x2 - x1;
    int h = y2 - y1;

    if (w < 5 || h < 5) {
        dragging_ = false;
        RenderBackbuffer();
        InvalidateRect(hwnd_, nullptr, FALSE);
        UpdateWindow(hwnd_);
        return;
    }

    auto cropped = capture_.CropToBitmap(x1, y1, w, h);
    int mode = mode_;
    auto cb = on_selected_;
    Close();
    if (cb && cropped) {
        cb(std::move(cropped), mode);
    }
}

void RegionSelectorOverlay::SelectFullscreen() {
    if (closed_) return;
    auto cropped = capture_.CropToBitmap(0, 0, capture_.width, capture_.height);
    int mode = mode_;
    auto cb = on_selected_;
    Close();
    if (cb && cropped) {
        cb(std::move(cropped), mode);
    }
}

void RegionSelectorOverlay::CancelSelection() {
    if (closed_) return;
    auto cb = on_cancel_;
    Close();
    if (cb) {
        cb();
    }
}

LRESULT CALLBACK RegionSelectorOverlay::WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    RegionSelectorOverlay* self = nullptr;
    if (msg == WM_NCCREATE) {
        auto* cs = reinterpret_cast<CREATESTRUCTW*>(lparam);
        self = static_cast<RegionSelectorOverlay*>(cs->lpCreateParams);
        SetWindowLongPtrW(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(self));
    } else {
        self = reinterpret_cast<RegionSelectorOverlay*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA));
    }
    if (self) {
        return self->HandleMessage(hwnd, msg, wparam, lparam);
    }
    return DefWindowProcW(hwnd, msg, wparam, lparam);
}

LRESULT RegionSelectorOverlay::HandleMessage(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    switch (msg) {
    case WM_ERASEBKGND:
        return 1;

    case WM_SETCURSOR:
        SetCursor(nullptr);
        return TRUE;

    case WM_MOUSEMOVE: {
        if (closed_) return 0;
        int mx = std::max(0, std::min(capture_.width - 1, GET_X_LPARAM(lparam)));
        int my = std::max(0, std::min(capture_.height - 1, GET_Y_LPARAM(lparam)));
        if (mx == cur_x_ && my == cur_y_) return 0;
        cur_x_ = mx;
        cur_y_ = my;
        RenderBackbuffer();
        InvalidateRect(hwnd, nullptr, FALSE);
        UpdateWindow(hwnd);
        return 0;
    }

    case WM_LBUTTONDOWN: {
        if (closed_) return 0;
        SetCapture(hwnd);
        dragging_ = true;
        start_x_ = std::max(0, std::min(capture_.width - 1, GET_X_LPARAM(lparam)));
        start_y_ = std::max(0, std::min(capture_.height - 1, GET_Y_LPARAM(lparam)));
        cur_x_ = start_x_;
        cur_y_ = start_y_;
        RenderBackbuffer();
        InvalidateRect(hwnd, nullptr, FALSE);
        UpdateWindow(hwnd);
        return 0;
    }

    case WM_LBUTTONUP: {
        if (closed_ || !dragging_) return 0;
        if (GetCapture() == hwnd) {
            ReleaseCapture();
        }
        cur_x_ = std::max(0, std::min(capture_.width - 1, GET_X_LPARAM(lparam)));
        cur_y_ = std::max(0, std::min(capture_.height - 1, GET_Y_LPARAM(lparam)));
        FinishSelection();
        return 0;
    }

    case WM_LBUTTONDBLCLK: {
        if (closed_) return 0;
        SelectFullscreen();
        return 0;
    }

    case WM_RBUTTONDOWN:
    case WM_MBUTTONDOWN:
        CancelSelection();
        return 0;

    case WM_KEYDOWN:
        if (wparam == VK_ESCAPE) {
            CancelSelection();
        } else if (wparam == VK_SPACE || wparam == VK_RETURN) {
            int w = std::abs(cur_x_ - start_x_);
            int h = std::abs(cur_y_ - start_y_);
            if (dragging_ && w >= 5 && h >= 5) {
                FinishSelection();
            } else {
                SelectFullscreen();
            }
        }
        return 0;

    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);
        if (hdc_back_) {
            BitBlt(hdc, 0, 0, capture_.width, capture_.height, hdc_back_, 0, 0, SRCCOPY);
        }
        EndPaint(hwnd, &ps);
        return 0;
    }
    }
    return DefWindowProcW(hwnd, msg, wparam, lparam);
}

} // namespace app
