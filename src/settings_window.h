#pragma once
#include "common.h"

namespace app {

class SettingsAndGuideWindow {
public:
    using OnAutostartChanged = std::function<void(bool)>;
    using OnPrtScChanged = std::function<void(bool)>;
    using OnLanguageChanged = std::function<void(const std::wstring&)>;
    using OnMinimizedToTray = std::function<void()>;

    SettingsAndGuideWindow(
        OnAutostartChanged on_autostart_changed,
        OnPrtScChanged on_prtsc_changed,
        OnLanguageChanged on_language_changed,
        OnMinimizedToTray on_minimized_to_tray);
    ~SettingsAndGuideWindow();

    void Show();
    void Close(bool destroy = false);
    bool IsVisible() const;
    void RefreshState();

private:
    static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam);
    LRESULT HandleMessage(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam);

    void ComputeLayoutAndResize(bool center_on_screen);
    void Render(HDC hdc, int width, int height);
    void MinimizeToTray();

    enum class HitZone {
        None,
        AutostartRow,
        PrtScRow,
        LangViBtn,
        LangEnBtn,
        KahubLink
    };
    HitZone HitTest(int x, int y) const;

    HWND hwnd_ = nullptr;
    bool autostart_checked_ = true;
    bool prtsc_checked_ = true;
    HitZone hovered_zone_ = HitZone::None;

    Gdiplus::RectF rc_autostart_row_{};
    Gdiplus::RectF rc_prtsc_row_{};
    Gdiplus::RectF rc_lang_vi_{};
    Gdiplus::RectF rc_lang_en_{};
    Gdiplus::RectF rc_kahub_link_{};

    OnAutostartChanged on_autostart_changed_;
    OnPrtScChanged on_prtsc_changed_;
    OnLanguageChanged on_language_changed_;
    OnMinimizedToTray on_minimized_to_tray_;
};

} // namespace app
