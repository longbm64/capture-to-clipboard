#pragma once

#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX

#include <windows.h>
#include <windowsx.h>
#include <shellapi.h>
#include <shlobj.h>
#include <commdlg.h>
#include <objidl.h>
#include <gdiplus.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cwctype>
#include <filesystem>
#include <fstream>
#include <functional>
#include <memory>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "comdlg32.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "shlwapi.lib")

namespace app {

// Custom application messages dispatched to the main hidden coordinator window
constexpr UINT WM_APP_TRAYICON          = WM_APP + 10;
constexpr UINT WM_APP_OPEN_SETTINGS     = WM_APP + 11;
constexpr UINT WM_APP_TOGGLE_AUTOSTART  = WM_APP + 12;
constexpr UINT WM_APP_BEGIN_CAPTURE     = WM_APP + 13; // wParam: mode (1 or 2), lParam: from_tray (0 or 1)
constexpr UINT WM_APP_EXIT              = WM_APP + 14;
constexpr UINT WM_APP_OVERLAY_DONE      = WM_APP + 15;
constexpr UINT WM_APP_OVERLAY_CANCEL    = WM_APP + 16;

// Tray menu command IDs
constexpr UINT IDM_TRAY_OPEN_SETTINGS   = 1001;
constexpr UINT IDM_TRAY_AUTOSTART       = 1002;
constexpr UINT IDM_TRAY_CAPTURE_FAST    = 1003;
constexpr UINT IDM_TRAY_CAPTURE_DRAW    = 1004;
constexpr UINT IDM_TRAY_EXIT            = 1005;

// Timer IDs
constexpr UINT_PTR IDT_SINGLE_INSTANCE_POLL = 2001;
constexpr UINT_PTR IDT_TRAY_ENSURE_VISIBLE  = 2002;
constexpr UINT_PTR IDT_DELAYED_CAPTURE_1    = 2003;
constexpr UINT_PTR IDT_DELAYED_CAPTURE_2    = 2004;
constexpr UINT_PTR IDT_INITIAL_TOAST        = 2005;

inline std::wstring Utf8ToWide(const std::string& str) {
    if (str.empty()) return L"";
    int len = MultiByteToWideChar(CP_UTF8, 0, str.data(), static_cast<int>(str.size()), nullptr, 0);
    if (len <= 0) return L"";
    std::wstring out(len, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, str.data(), static_cast<int>(str.size()), out.data(), len);
    return out;
}

inline std::string WideToUtf8(const std::wstring& wstr) {
    if (wstr.empty()) return "";
    int len = WideCharToMultiByte(CP_UTF8, 0, wstr.data(), static_cast<int>(wstr.size()), nullptr, 0, nullptr, nullptr);
    if (len <= 0) return "";
    std::string out(len, '\0');
    WideCharToMultiByte(CP_UTF8, 0, wstr.data(), static_cast<int>(wstr.size()), out.data(), len, nullptr, nullptr);
    return out;
}

inline Gdiplus::Color HexToColor(const std::wstring& hex, BYTE alpha = 255) {
    std::wstring h = hex;
    if (!h.empty() && h[0] == L'#') h.erase(0, 1);
    if (h.size() == 3) {
        std::wstring expanded;
        for (wchar_t c : h) {
            expanded.push_back(c);
            expanded.push_back(c);
        }
        h = expanded;
    }
    if (h.size() < 6) return Gdiplus::Color(alpha, 30, 41, 59);
    unsigned long val = std::wcstoul(h.substr(0, 6).c_str(), nullptr, 16);
    BYTE r = static_cast<BYTE>((val >> 16) & 0xFF);
    BYTE g = static_cast<BYTE>((val >> 8) & 0xFF);
    BYTE b = static_cast<BYTE>(val & 0xFF);
    return Gdiplus::Color(alpha, r, g, b);
}

inline COLORREF HexToColorRef(const std::wstring& hex) {
    Gdiplus::Color c = HexToColor(hex);
    return RGB(c.GetR(), c.GetG(), c.GetB());
}

inline std::wstring ColorRefToHex(COLORREF cr) {
    wchar_t buf[16];
    swprintf_s(buf, L"#%02x%02x%02x", GetRValue(cr), GetGValue(cr), GetBValue(cr));
    return buf;
}

inline float GetWindowDpiScale(HWND hwnd = nullptr) {
    UINT dpi = 96;
    HMODULE user32 = GetModuleHandleW(L"user32.dll");
    if (user32) {
        if (hwnd) {
            using GetDpiForWindowFn = UINT(WINAPI*)(HWND);
            auto fn = reinterpret_cast<GetDpiForWindowFn>(GetProcAddress(user32, "GetDpiForWindow"));
            if (fn) {
                UINT d = fn(hwnd);
                if (d > 0) dpi = d;
            }
        }
        if (dpi == 96) {
            using GetDpiForSystemFn = UINT(WINAPI*)();
            auto fn = reinterpret_cast<GetDpiForSystemFn>(GetProcAddress(user32, "GetDpiForSystem"));
            if (fn) {
                UINT d = fn();
                if (d > 0) dpi = d;
            }
        }
    }
    if (dpi == 96) {
        HDC hdc = GetDC(nullptr);
        if (hdc) {
            dpi = static_cast<UINT>(GetDeviceCaps(hdc, LOGPIXELSX));
            ReleaseDC(nullptr, hdc);
        }
    }
    float scale = static_cast<float>(dpi) / 96.0f;
    return std::max(1.0f, std::min(3.0f, scale));
}

inline void AddRoundedRectToPath(Gdiplus::GraphicsPath& path, Gdiplus::RectF rect, float radius) {
    if (radius <= 0.5f) {
        path.AddRectangle(rect);
        return;
    }
    float d = std::min({radius * 2.0f, rect.Width, rect.Height});
    path.AddArc(rect.X, rect.Y, d, d, 180.0f, 90.0f);
    path.AddArc(rect.X + rect.Width - d, rect.Y, d, d, 270.0f, 90.0f);
    path.AddArc(rect.X + rect.Width - d, rect.Y + rect.Height - d, d, d, 0.0f, 90.0f);
    path.AddArc(rect.X, rect.Y + rect.Height - d, d, d, 90.0f, 90.0f);
    path.CloseFigure();
}

inline void FillRoundedRect(Gdiplus::Graphics& g, Gdiplus::RectF rect, float radius, Gdiplus::Color fill) {
    Gdiplus::GraphicsPath path;
    AddRoundedRectToPath(path, rect, radius);
    Gdiplus::SolidBrush brush(fill);
    g.FillPath(&brush, &path);
}

inline void DrawRoundedRect(Gdiplus::Graphics& g, Gdiplus::RectF rect, float radius, Gdiplus::Color fill, Gdiplus::Color border, float border_width = 1.0f) {
    Gdiplus::GraphicsPath path;
    AddRoundedRectToPath(path, rect, radius);
    if (fill.GetA() > 0) {
        Gdiplus::SolidBrush brush(fill);
        g.FillPath(&brush, &path);
    }
    if (border.GetA() > 0 && border_width > 0.0f) {
        Gdiplus::Pen pen(border, border_width);
        g.DrawPath(&pen, &path);
    }
}

} // namespace app
