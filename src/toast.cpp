#include "toast.h"
#include "platform_utils.h"

namespace app {

namespace {

constexpr const wchar_t* kToastClassName = L"CaptureToClipboard_ToastWnd";
constexpr UINT_PTR kToastTimerId = 1;

HWND g_toast_hwnd = nullptr;
std::wstring g_toast_msg;
bool g_toast_success = true;

void RegisterToastWindowClass() {
    static bool registered = false;
    if (registered) return;
    WNDCLASSEXW wc{};
    wc.cbSize = sizeof(wc);
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = ToastNotification::WndProc;
    wc.hInstance = GetModuleHandleW(nullptr);
    wc.hCursor = LoadCursorW(nullptr, IDC_HAND);
    wc.lpszClassName = kToastClassName;
    RegisterClassExW(&wc);
    registered = true;
}

} // namespace

void ToastNotification::Dismiss() {
    if (g_toast_hwnd && IsWindow(g_toast_hwnd)) {
        KillTimer(g_toast_hwnd, kToastTimerId);
        DestroyWindow(g_toast_hwnd);
    }
    g_toast_hwnd = nullptr;
}

void ToastNotification::Show(const std::wstring& message, bool success, int duration_ms) {
    Dismiss();
    RegisterToastWindowClass();

    g_toast_msg = message;
    g_toast_success = success;

    float dpi = GetWindowDpiScale(nullptr);
    auto font_msg = CreateUiFont(13.5f * dpi, true);
    auto font_icon = CreateUiFont(16.0f * dpi, true);

    int text_w = 240;
    int text_h = static_cast<int>(20 * dpi);
    {
        HDC hdc = GetDC(nullptr);
        if (hdc) {
            Gdiplus::Graphics g(hdc);
            Gdiplus::RectF box;
            g.MeasureString(message.c_str(), -1, font_msg.get(), Gdiplus::PointF(0, 0), &box);
            text_w = static_cast<int>(std::ceil(box.Width));
            text_h = static_cast<int>(std::ceil(box.Height));
            ReleaseDC(nullptr, hdc);
        }
    }

    int stripe_w = static_cast<int>(std::round(6.0f * dpi));
    int icon_area_w = static_cast<int>(std::round(34.0f * dpi));
    int pad_right = static_cast<int>(std::round(18.0f * dpi));
    int pad_y = static_cast<int>(std::round(12.0f * dpi));

    int win_w = stripe_w + icon_area_w + text_w + pad_right;
    int win_h = std::max(static_cast<int>(std::round(44.0f * dpi)), text_h + pad_y * 2);

    int screen_w = GetSystemMetrics(SM_CXSCREEN);
    int screen_h = GetSystemMetrics(SM_CYSCREEN);
    int x = std::max(16, screen_w - win_w - static_cast<int>(std::round(28.0f * dpi)));
    int y = std::max(16, screen_h - win_h - static_cast<int>(std::round(68.0f * dpi)));

    g_toast_hwnd = CreateWindowExW(
        WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
        kToastClassName,
        L"",
        WS_POPUP,
        x, y, win_w, win_h,
        nullptr,
        nullptr,
        GetModuleHandleW(nullptr),
        nullptr);

    if (!g_toast_hwnd) return;

    ShowWindow(g_toast_hwnd, SW_SHOWNOACTIVATE);
    UpdateWindow(g_toast_hwnd);
    SetTimer(g_toast_hwnd, kToastTimerId, static_cast<UINT>(std::max(500, duration_ms)), nullptr);
}

LRESULT CALLBACK ToastNotification::WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    switch (msg) {
    case WM_ERASEBKGND:
        return 1;

    case WM_LBUTTONDOWN:
    case WM_RBUTTONDOWN:
        Dismiss();
        return 0;

    case WM_TIMER:
        if (wparam == kToastTimerId) {
            Dismiss();
        }
        return 0;

    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);
        RECT rc;
        GetClientRect(hwnd, &rc);
        int w = rc.right - rc.left;
        int h = rc.bottom - rc.top;

        if (w > 0 && h > 0) {
            Gdiplus::Bitmap back_bmp(w, h, PixelFormat32bppARGB);
            Gdiplus::Graphics g(&back_bmp);
            g.SetSmoothingMode(Gdiplus::SmoothingModeAntiAlias);
            g.SetTextRenderingHint(Gdiplus::TextRenderingHintClearTypeGridFit);

            float dpi = GetWindowDpiScale(hwnd);
            Gdiplus::Color bg_color(255, 255, 255, 255);
            Gdiplus::Color border_color(255, 148, 163, 184); // #94a3b8
            Gdiplus::Color accent_color = g_toast_success
                ? Gdiplus::Color(255, 16, 185, 129)  // #10b981
                : Gdiplus::Color(255, 239, 68, 68);  // #ef4444
            Gdiplus::Color fg_color(255, 30, 41, 59); // #1e293b

            Gdiplus::SolidBrush bg_brush(bg_color);
            g.FillRectangle(&bg_brush, 0, 0, w, h);

            float stripe_w = std::round(6.0f * dpi);
            Gdiplus::SolidBrush stripe_brush(accent_color);
            g.FillRectangle(&stripe_brush, 0.0f, 0.0f, stripe_w, static_cast<float>(h));

            Gdiplus::Pen border_pen(border_color, 1.0f);
            g.DrawRectangle(&border_pen, 0, 0, w - 1, h - 1);

            auto font_icon = CreateUiFont(16.0f * dpi, true);
            auto font_msg = CreateUiFont(13.5f * dpi, true);

            Gdiplus::SolidBrush icon_brush(accent_color);
            Gdiplus::SolidBrush text_brush(fg_color);

            Gdiplus::StringFormat sf;
            sf.SetAlignment(Gdiplus::StringAlignmentCenter);
            sf.SetLineAlignment(Gdiplus::StringAlignmentCenter);

            float icon_area_w = std::round(34.0f * dpi);
            Gdiplus::RectF icon_rc(stripe_w, 0.0f, icon_area_w, static_cast<float>(h));
            const wchar_t* icon_txt = g_toast_success ? L"\u2713" : L"!";
            g.DrawString(icon_txt, -1, font_icon.get(), icon_rc, &sf, &icon_brush);

            Gdiplus::StringFormat sf_left;
            sf_left.SetAlignment(Gdiplus::StringAlignmentNear);
            sf_left.SetLineAlignment(Gdiplus::StringAlignmentCenter);
            sf_left.SetFormatFlags(Gdiplus::StringFormatFlagsNoWrap);
            Gdiplus::RectF msg_rc(
                stripe_w + icon_area_w,
                0.0f,
                static_cast<float>(w) - (stripe_w + icon_area_w),
                static_cast<float>(h));
            g.DrawString(g_toast_msg.c_str(), -1, font_msg.get(), msg_rc, &sf_left, &text_brush);

            Gdiplus::Graphics screen_g(hdc);
            screen_g.DrawImage(&back_bmp, 0, 0);
        }
        EndPaint(hwnd, &ps);
        return 0;
    }

    case WM_DESTROY:
        if (g_toast_hwnd == hwnd) {
            g_toast_hwnd = nullptr;
        }
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wparam, lparam);
}

} // namespace app
