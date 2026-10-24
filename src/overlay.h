#pragma once
#include "common.h"
#include "platform_utils.h"

namespace app {

class RegionSelectorOverlay {
public:
    using OnSelectedCallback = std::function<void(std::unique_ptr<Gdiplus::Bitmap>, int mode)>;
    using OnCancelCallback = std::function<void()>;

    RegionSelectorOverlay();
    ~RegionSelectorOverlay();

    bool Open(
        ScreenCaptureData&& capture,
        int mode,
        OnSelectedCallback on_selected,
        OnCancelCallback on_cancel);

    void Close();
    bool IsActive() const { return hwnd_ != nullptr && IsWindow(hwnd_); }

    static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam);

private:
    LRESULT HandleMessage(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam);

    void RenderBackbuffer();
    void FinishSelection();
    void SelectFullscreen();
    void CancelSelection();
    void CleanupGdi();

    HWND hwnd_ = nullptr;
    ScreenCaptureData capture_;
    int mode_ = 1;
    Gdiplus::Color accent_color_{255, 2, 132, 199};
    COLORREF accent_cref_ = RGB(2, 132, 199);

    OnSelectedCallback on_selected_;
    OnCancelCallback on_cancel_;

    bool dragging_ = false;
    bool closed_ = false;
    int start_x_ = 0;
    int start_y_ = 0;
    int cur_x_ = 0;
    int cur_y_ = 0;

    HDC hdc_bright_ = nullptr;
    HDC hdc_dimmed_ = nullptr;
    HDC hdc_back_ = nullptr;
    HBITMAP hbm_back_ = nullptr;
    HGDIOBJ old_bright_ = nullptr;
    HGDIOBJ old_dimmed_ = nullptr;
    HGDIOBJ old_back_ = nullptr;
};

} // namespace app
