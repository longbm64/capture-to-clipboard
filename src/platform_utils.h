#pragma once
#include "common.h"

namespace app {

struct ScreenCaptureData {
    int left = 0;
    int top = 0;
    int width = 0;
    int height = 0;
    HBITMAP hbm_bright = nullptr;
    HBITMAP hbm_dimmed = nullptr;
    uint8_t* bits_bright = nullptr;
    uint8_t* bits_dimmed = nullptr;

    ScreenCaptureData() = default;
    ~ScreenCaptureData() {
        Reset();
    }
    ScreenCaptureData(const ScreenCaptureData&) = delete;
    ScreenCaptureData& operator=(const ScreenCaptureData&) = delete;

    ScreenCaptureData(ScreenCaptureData&& other) noexcept
        : left(other.left),
          top(other.top),
          width(other.width),
          height(other.height),
          hbm_bright(other.hbm_bright),
          hbm_dimmed(other.hbm_dimmed),
          bits_bright(other.bits_bright),
          bits_dimmed(other.bits_dimmed) {
        other.hbm_bright = nullptr;
        other.hbm_dimmed = nullptr;
        other.bits_bright = nullptr;
        other.bits_dimmed = nullptr;
    }

    ScreenCaptureData& operator=(ScreenCaptureData&& other) noexcept {
        if (this != &other) {
            Reset();
            left = other.left;
            top = other.top;
            width = other.width;
            height = other.height;
            hbm_bright = other.hbm_bright;
            hbm_dimmed = other.hbm_dimmed;
            bits_bright = other.bits_bright;
            bits_dimmed = other.bits_dimmed;
            other.hbm_bright = nullptr;
            other.hbm_dimmed = nullptr;
            other.bits_bright = nullptr;
            other.bits_dimmed = nullptr;
        }
        return *this;
    }

    void Reset() {
        if (hbm_bright) {
            DeleteObject(hbm_bright);
            hbm_bright = nullptr;
        }
        if (hbm_dimmed) {
            DeleteObject(hbm_dimmed);
            hbm_dimmed = nullptr;
        }
        bits_bright = nullptr;
        bits_dimmed = nullptr;
    }

    std::unique_ptr<Gdiplus::Bitmap> CropToBitmap(int x, int y, int w, int h) const;
};

std::filesystem::path GetExecutableDir();
std::filesystem::path GetWritableDataDir();

void EnableDpiAwareness();
void InitFonts();
std::unique_ptr<Gdiplus::Font> CreateUiFont(float size_px, bool bold = true);
HFONT CreateWin32UiFont(int height_px, bool bold = true);

bool CaptureVirtualScreen(ScreenCaptureData& out_capture, std::wstring& out_err);

std::vector<uint8_t> EncodeLosslessPngBytes(Gdiplus::Bitmap* bmp);
std::pair<bool, std::wstring> CopyBitmapToClipboard(Gdiplus::Bitmap* bmp);
bool SaveBitmapToFile(Gdiplus::Bitmap* bmp, const std::wstring& file_path);

HICON GetAppIcon(int size = 64);
void ApplyWindowIcon(HWND hwnd);

void DrawToolVectorIcon(
    Gdiplus::Graphics& g,
    const std::wstring& icon_name,
    float cx,
    float cy,
    float size,
    Gdiplus::Color color);

} // namespace app
