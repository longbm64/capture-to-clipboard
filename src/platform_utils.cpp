#include "platform_utils.h"
#include "resource.h"

namespace app {

namespace {

Gdiplus::PrivateFontCollection* g_font_collection = nullptr;
Gdiplus::FontFamily* g_roboto_family = nullptr;
bool g_fonts_initialized = false;

bool GetEncoderClsid(const WCHAR* format, CLSID* pClsid) {
    UINT num = 0;
    UINT size = 0;
    Gdiplus::GetImageEncodersSize(&num, &size);
    if (size == 0) return false;

    std::vector<uint8_t> buf(size);
    auto* pImageCodecInfo = reinterpret_cast<Gdiplus::ImageCodecInfo*>(buf.data());
    Gdiplus::GetImageEncoders(num, size, pImageCodecInfo);

    for (UINT j = 0; j < num; ++j) {
        if (wcscmp(pImageCodecInfo[j].MimeType, format) == 0) {
            *pClsid = pImageCodecInfo[j].Clsid;
            return true;
        }
    }
    return false;
}

void LoadEmbeddedFontResource(UINT res_id) {
    HMODULE hmod = GetModuleHandleW(nullptr);
    HRSRC hrsrc = FindResourceW(hmod, MAKEINTRESOURCEW(res_id), RT_RCDATA);
    if (!hrsrc) return;
    HGLOBAL hglob = LoadResource(hmod, hrsrc);
    if (!hglob) return;
    DWORD sz = SizeofResource(hmod, hrsrc);
    const void* data = LockResource(hglob);
    if (!data || sz == 0) return;

    DWORD num_fonts = 0;
    AddFontMemResourceEx(const_cast<void*>(data), sz, nullptr, &num_fonts);
    if (g_font_collection) {
        g_font_collection->AddMemoryFont(data, static_cast<INT>(sz));
    }
}

} // namespace

std::filesystem::path GetExecutableDir() {
    wchar_t buf[MAX_PATH] = {0};
    GetModuleFileNameW(nullptr, buf, MAX_PATH);
    return std::filesystem::path(buf).parent_path();
}

std::filesystem::path GetWritableDataDir() {
    std::filesystem::path exe_dir = GetExecutableDir();
    std::error_code ec;

    // If running inside dist/, check if parent has assets/settings.json or use dist/assets
    std::filesystem::path local_assets = exe_dir / L"assets";
    std::filesystem::create_directories(local_assets, ec);
    if (!ec) {
        std::filesystem::path test_file = local_assets / L".write_test";
        std::ofstream ofs(test_file, std::ios::binary);
        if (ofs) {
            ofs.close();
            std::filesystem::remove(test_file, ec);
            return local_assets;
        }
    }

    wchar_t* local_appdata = nullptr;
    if (SUCCEEDED(SHGetKnownFolderPath(FOLDERID_LocalAppData, 0, nullptr, &local_appdata)) && local_appdata) {
        std::filesystem::path fallback = std::filesystem::path(local_appdata) / L"CaptureToClipboard";
        CoTaskMemFree(local_appdata);
        std::filesystem::create_directories(fallback, ec);
        return fallback;
    }
    return exe_dir;
}

void EnableDpiAwareness() {
    HMODULE user32 = GetModuleHandleW(L"user32.dll");
    if (user32) {
        using SetProcessDpiAwarenessContextFn = BOOL(WINAPI*)(DPI_AWARENESS_CONTEXT);
        auto fn = reinterpret_cast<SetProcessDpiAwarenessContextFn>(
            GetProcAddress(user32, "SetProcessDpiAwarenessContext"));
        if (fn && fn(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)) {
            return;
        }
    }
    HMODULE shcore = LoadLibraryW(L"shcore.dll");
    if (shcore) {
        using SetProcessDpiAwarenessFn = HRESULT(WINAPI*)(int);
        auto fn = reinterpret_cast<SetProcessDpiAwarenessFn>(
            GetProcAddress(shcore, "SetProcessDpiAwareness"));
        if (fn && SUCCEEDED(fn(2))) {
            return;
        }
    }
    SetProcessDPIAware();
}

void InitFonts() {
    if (g_fonts_initialized) return;
    g_fonts_initialized = true;

    g_font_collection = new Gdiplus::PrivateFontCollection();
    LoadEmbeddedFontResource(IDR_FONT_ROBOTO_REGULAR);
    LoadEmbeddedFontResource(IDR_FONT_ROBOTO_BOLD);

    // Also register from disk assets/fonts if present
    std::vector<std::filesystem::path> font_dirs = {
        GetExecutableDir() / L"assets" / L"fonts",
        GetExecutableDir().parent_path() / L"assets" / L"fonts"
    };
    std::error_code ec;
    for (const auto& dir : font_dirs) {
        if (std::filesystem::exists(dir, ec)) {
            for (const auto& entry : std::filesystem::directory_iterator(dir, ec)) {
                if (entry.path().extension() == L".ttf") {
                    AddFontResourceExW(entry.path().c_str(), FR_PRIVATE, nullptr);
                    g_font_collection->AddFontFile(entry.path().c_str());
                }
            }
        }
    }

    int count = g_font_collection->GetFamilyCount();
    if (count > 0) {
        std::vector<Gdiplus::FontFamily> families(count);
        int found = 0;
        g_font_collection->GetFamilies(count, families.data(), &found);
        if (found > 0) {
            g_roboto_family = families[0].Clone();
        }
    }
}

std::unique_ptr<Gdiplus::Font> CreateUiFont(float size_px, bool bold) {
    InitFonts();
    INT style = bold ? Gdiplus::FontStyleBold : Gdiplus::FontStyleRegular;
    float px = std::max(8.0f, size_px);

    if (g_roboto_family && g_roboto_family->IsAvailable()) {
        auto f = std::make_unique<Gdiplus::Font>(g_roboto_family, px, style, Gdiplus::UnitPixel);
        if (f->IsAvailable()) return f;
    }
    auto f_sys = std::make_unique<Gdiplus::Font>(L"Roboto", px, style, Gdiplus::UnitPixel);
    if (f_sys->IsAvailable()) return f_sys;

    return std::make_unique<Gdiplus::Font>(L"Segoe UI", px, style, Gdiplus::UnitPixel);
}

HFONT CreateWin32UiFont(int height_px, bool bold) {
    InitFonts();
    return CreateFontW(
        -std::max(10, height_px),
        0,
        0,
        0,
        bold ? FW_BOLD : FW_NORMAL,
        FALSE,
        FALSE,
        FALSE,
        DEFAULT_CHARSET,
        OUT_TT_PRECIS,
        CLIP_DEFAULT_PRECIS,
        CLEARTYPE_QUALITY,
        DEFAULT_PITCH | FF_SWISS,
        L"Roboto");
}

std::unique_ptr<Gdiplus::Bitmap> ScreenCaptureData::CropToBitmap(int x, int y, int w, int h) const {
    if (!bits_bright || width <= 0 || height <= 0 || w <= 0 || h <= 0) return nullptr;
    int x1 = std::max(0, std::min(width, x));
    int y1 = std::max(0, std::min(height, y));
    int x2 = std::max(0, std::min(width, x + w));
    int y2 = std::max(0, std::min(height, y + h));
    int cw = x2 - x1;
    int ch = y2 - y1;
    if (cw <= 0 || ch <= 0) return nullptr;

    auto out = std::make_unique<Gdiplus::Bitmap>(cw, ch, PixelFormat32bppARGB);
    Gdiplus::Rect lock_rect(0, 0, cw, ch);
    Gdiplus::BitmapData bd{};
    if (out->LockBits(&lock_rect, Gdiplus::ImageLockModeWrite, PixelFormat32bppARGB, &bd) == Gdiplus::Ok) {
        const int src_stride = width * 4;
        for (int row = 0; row < ch; ++row) {
            const uint8_t* src_row = bits_bright + (y1 + row) * src_stride + x1 * 4;
            uint8_t* dst_row = static_cast<uint8_t*>(bd.Scan0) + row * bd.Stride;
            for (int col = 0; col < cw; ++col) {
                dst_row[col * 4 + 0] = src_row[col * 4 + 0]; // B
                dst_row[col * 4 + 1] = src_row[col * 4 + 1]; // G
                dst_row[col * 4 + 2] = src_row[col * 4 + 2]; // R
                dst_row[col * 4 + 3] = 255;                  // A = 255
            }
        }
        out->UnlockBits(&bd);
    }
    return out;
}

bool CaptureVirtualScreen(ScreenCaptureData& out_capture, std::wstring& out_err) {
    out_capture.Reset();

    int left = GetSystemMetrics(SM_XVIRTUALSCREEN);
    int top = GetSystemMetrics(SM_YVIRTUALSCREEN);
    int width = GetSystemMetrics(SM_CXVIRTUALSCREEN);
    int height = GetSystemMetrics(SM_CYVIRTUALSCREEN);
    if (width <= 0 || height <= 0) {
        width = GetSystemMetrics(SM_CXSCREEN);
        height = GetSystemMetrics(SM_CYSCREEN);
        left = 0;
        top = 0;
    }
    if (width <= 0 || height <= 0) {
        out_err = L"Invalid virtual screen dimensions.";
        return false;
    }

    HDC hdc_screen = GetDC(nullptr);
    if (!hdc_screen) {
        out_err = L"GetDC(NULL) failed.";
        return false;
    }

    HDC hdc_mem = CreateCompatibleDC(hdc_screen);
    if (!hdc_mem) {
        ReleaseDC(nullptr, hdc_screen);
        out_err = L"CreateCompatibleDC failed.";
        return false;
    }

    BITMAPINFO bmi{};
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = width;
    bmi.bmiHeader.biHeight = -height; // Top-down DIB
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 32;
    bmi.bmiHeader.biCompression = BI_RGB;

    void* pv_bright = nullptr;
    HBITMAP hbm_bright = CreateDIBSection(hdc_screen, &bmi, DIB_RGB_COLORS, &pv_bright, nullptr, 0);
    if (!hbm_bright || !pv_bright) {
        DeleteDC(hdc_mem);
        ReleaseDC(nullptr, hdc_screen);
        out_err = L"CreateDIBSection (bright) failed.";
        return false;
    }

    HGDIOBJ old_obj = SelectObject(hdc_mem, hbm_bright);
    BOOL blt_ok = BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, left, top, SRCCOPY | CAPTUREBLT);
    SelectObject(hdc_mem, old_obj);
    DeleteDC(hdc_mem);
    ReleaseDC(nullptr, hdc_screen);

    if (!blt_ok) {
        DeleteObject(hbm_bright);
        out_err = L"BitBlt failed.";
        return false;
    }

    void* pv_dimmed = nullptr;
    HDC hdc_tmp = GetDC(nullptr);
    HBITMAP hbm_dimmed = CreateDIBSection(hdc_tmp, &bmi, DIB_RGB_COLORS, &pv_dimmed, nullptr, 0);
    ReleaseDC(nullptr, hdc_tmp);
    if (!hbm_dimmed || !pv_dimmed) {
        DeleteObject(hbm_bright);
        out_err = L"CreateDIBSection (dimmed) failed.";
        return false;
    }

    // Fast integer dimming to 78% brightness (200 / 256 = 0.78125)
    const size_t total_pixels = static_cast<size_t>(width) * static_cast<size_t>(height);
    const uint8_t* src = static_cast<const uint8_t*>(pv_bright);
    uint8_t* dst = static_cast<uint8_t*>(pv_dimmed);
    for (size_t i = 0; i < total_pixels * 4; i += 4) {
        dst[i + 0] = static_cast<uint8_t>((static_cast<uint32_t>(src[i + 0]) * 200u) >> 8);
        dst[i + 1] = static_cast<uint8_t>((static_cast<uint32_t>(src[i + 1]) * 200u) >> 8);
        dst[i + 2] = static_cast<uint8_t>((static_cast<uint32_t>(src[i + 2]) * 200u) >> 8);
        dst[i + 3] = 255;
    }

    out_capture.left = left;
    out_capture.top = top;
    out_capture.width = width;
    out_capture.height = height;
    out_capture.hbm_bright = hbm_bright;
    out_capture.hbm_dimmed = hbm_dimmed;
    out_capture.bits_bright = static_cast<uint8_t*>(pv_bright);
    out_capture.bits_dimmed = static_cast<uint8_t*>(pv_dimmed);
    return true;
}

std::vector<uint8_t> EncodeLosslessPngBytes(Gdiplus::Bitmap* bmp) {
    std::vector<uint8_t> result;
    if (!bmp) return result;

    CLSID png_clsid{};
    if (!GetEncoderClsid(L"image/png", &png_clsid)) return result;

    IStream* stream = nullptr;
    if (FAILED(CreateStreamOnHGlobal(nullptr, TRUE, &stream)) || !stream) {
        return result;
    }

    if (bmp->Save(stream, &png_clsid, nullptr) == Gdiplus::Ok) {
        HGLOBAL hglob = nullptr;
        if (SUCCEEDED(GetHGlobalFromStream(stream, &hglob)) && hglob) {
            SIZE_T sz = GlobalSize(hglob);
            const void* ptr = GlobalLock(hglob);
            if (ptr && sz > 0) {
                const auto* bytes = static_cast<const uint8_t*>(ptr);
                result.assign(bytes, bytes + sz);
                GlobalUnlock(hglob);
            }
        }
    }
    stream->Release();
    return result;
}

std::pair<bool, std::wstring> CopyBitmapToClipboard(Gdiplus::Bitmap* bmp) {
    if (!bmp || bmp->GetWidth() == 0 || bmp->GetHeight() == 0) {
        return {false, L"Invalid image for clipboard."};
    }

    const int w = static_cast<int>(bmp->GetWidth());
    const int h = static_cast<int>(bmp->GetHeight());

    // 1. Encode lossless PNG bytes
    std::vector<uint8_t> png_bytes = EncodeLosslessPngBytes(bmp);

    // 2. Build native 1:1 CF_DIB (24-bit bottom-up BGR with biXPelsPerMeter=0, biYPelsPerMeter=0)
    const int row_stride = ((w * 3 + 3) & ~3);
    const size_t pixel_bytes_size = static_cast<size_t>(row_stride) * static_cast<size_t>(h);
    const size_t dib_total_size = sizeof(BITMAPINFOHEADER) + pixel_bytes_size;

    std::vector<uint8_t> dib_buf(dib_total_size, 0);
    auto* bih = reinterpret_cast<BITMAPINFOHEADER*>(dib_buf.data());
    bih->biSize = sizeof(BITMAPINFOHEADER);
    bih->biWidth = w;
    bih->biHeight = h; // Bottom-up DIB for maximum compatibility with Win32 apps
    bih->biPlanes = 1;
    bih->biBitCount = 24;
    bih->biCompression = BI_RGB;
    bih->biSizeImage = static_cast<DWORD>(pixel_bytes_size);
    bih->biXPelsPerMeter = 0; // Prevents fractional DPI scaling in Word/Zalo/Slack
    bih->biYPelsPerMeter = 0;

    Gdiplus::Rect lock_rect(0, 0, w, h);
    Gdiplus::BitmapData bd{};
    if (bmp->LockBits(&lock_rect, Gdiplus::ImageLockModeRead, PixelFormat32bppARGB, &bd) == Gdiplus::Ok) {
        uint8_t* dst_pixels = dib_buf.data() + sizeof(BITMAPINFOHEADER);
        for (int y = 0; y < h; ++y) {
            const uint8_t* src_row = static_cast<const uint8_t*>(bd.Scan0) + y * bd.Stride;
            uint8_t* dst_row = dst_pixels + (h - 1 - y) * row_stride;
            for (int x = 0; x < w; ++x) {
                dst_row[x * 3 + 0] = src_row[x * 4 + 0]; // B
                dst_row[x * 3 + 1] = src_row[x * 4 + 1]; // G
                dst_row[x * 3 + 2] = src_row[x * 4 + 2]; // R
            }
        }
        bmp->UnlockBits(&bd);
    }

    auto alloc_hglobal = [](const uint8_t* data, size_t len) -> HGLOBAL {
        HGLOBAL hmem = GlobalAlloc(GMEM_MOVEABLE, len);
        if (!hmem) return nullptr;
        void* ptr = GlobalLock(hmem);
        if (!ptr) {
            GlobalFree(hmem);
            return nullptr;
        }
        memcpy(ptr, data, len);
        GlobalUnlock(hmem);
        return hmem;
    };

    bool opened = false;
    for (int attempt = 0; attempt < 8; ++attempt) {
        if (OpenClipboard(nullptr)) {
            opened = true;
            break;
        }
        Sleep(25);
    }
    if (!opened) {
        return {false, L"Kh\u00F4ng th\u1EC3 m\u1EDF Clipboard tr\u00EAn Windows (\u0111ang b\u1ECB \u1EE9ng d\u1EE5ng kh\u00E1c kh\u00F3a)."};
    }

    EmptyClipboard();

    if (!png_bytes.empty()) {
        const wchar_t* png_formats[] = {L"PNG", L"image/png"};
        for (const wchar_t* fmt_name : png_formats) {
            UINT cf = RegisterClipboardFormatW(fmt_name);
            if (cf) {
                HGLOBAL h_png = alloc_hglobal(png_bytes.data(), png_bytes.size());
                if (h_png) {
                    if (!SetClipboardData(cf, h_png)) {
                        GlobalFree(h_png);
                    }
                }
            }
        }
    }

    HGLOBAL h_dib = alloc_hglobal(dib_buf.data(), dib_buf.size());
    if (!h_dib || !SetClipboardData(CF_DIB, h_dib)) {
        if (h_dib) GlobalFree(h_dib);
        CloseClipboard();
        return {false, L"SetClipboardData(CF_DIB) th\u1EA5t b\u1EA1i."};
    }

    CloseClipboard();
    return {true, L"\u0110\u00E3 copy \u1EA3nh ch\u1EA5t l\u01B0\u1EE3ng cao v\u00E0o Clipboard!"};
}

bool SaveBitmapToFile(Gdiplus::Bitmap* bmp, const std::wstring& file_path) {
    if (!bmp || file_path.empty()) return false;

    std::wstring ext = std::filesystem::path(file_path).extension().wstring();
    std::transform(ext.begin(), ext.end(), ext.begin(), ::towlower);

    CLSID clsid{};
    if (ext == L".jpg" || ext == L".jpeg") {
        if (!GetEncoderClsid(L"image/jpeg", &clsid)) return false;
        Gdiplus::EncoderParameters params{};
        params.Count = 1;
        params.Parameter[0].Guid = Gdiplus::EncoderQuality;
        params.Parameter[0].Type = Gdiplus::EncoderParameterValueTypeLong;
        params.Parameter[0].NumberOfValues = 1;
        ULONG quality = 100;
        params.Parameter[0].Value = &quality;
        return bmp->Save(file_path.c_str(), &clsid, &params) == Gdiplus::Ok;
    } else if (ext == L".bmp") {
        if (!GetEncoderClsid(L"image/bmp", &clsid)) return false;
        return bmp->Save(file_path.c_str(), &clsid, nullptr) == Gdiplus::Ok;
    } else {
        if (!GetEncoderClsid(L"image/png", &clsid)) return false;
        return bmp->Save(file_path.c_str(), &clsid, nullptr) == Gdiplus::Ok;
    }
}

HICON GetAppIcon(int size) {
    HMODULE hmod = GetModuleHandleW(nullptr);
    HICON hicon = static_cast<HICON>(LoadImageW(
        hmod,
        MAKEINTRESOURCEW(IDI_APP_ICON),
        IMAGE_ICON,
        size,
        size,
        LR_DEFAULTCOLOR));
    if (hicon) return hicon;

    std::filesystem::path ico_path = GetExecutableDir() / L"assets" / L"logo.ico";
    std::error_code ec;
    if (!std::filesystem::exists(ico_path, ec)) {
        ico_path = GetExecutableDir().parent_path() / L"assets" / L"logo.ico";
    }
    if (std::filesystem::exists(ico_path, ec)) {
        hicon = static_cast<HICON>(LoadImageW(
            nullptr,
            ico_path.c_str(),
            IMAGE_ICON,
            size,
            size,
            LR_LOADFROMFILE));
        if (hicon) return hicon;
    }
    return LoadIconW(nullptr, IDI_APPLICATION);
}

void ApplyWindowIcon(HWND hwnd) {
    if (!hwnd) return;
    static HICON hicon_sm = GetAppIcon(std::max(16, GetSystemMetrics(SM_CXSMICON)));
    static HICON hicon_lg = GetAppIcon(std::max(32, GetSystemMetrics(SM_CXICON)));
    if (hicon_sm) {
        SendMessageW(hwnd, WM_SETICON, ICON_SMALL, reinterpret_cast<LPARAM>(hicon_sm));
    }
    if (hicon_lg) {
        SendMessageW(hwnd, WM_SETICON, ICON_BIG, reinterpret_cast<LPARAM>(hicon_lg));
    }
}

void DrawToolVectorIcon(
    Gdiplus::Graphics& g,
    const std::wstring& icon_name,
    float cx,
    float cy,
    float size,
    Gdiplus::Color color) {

    float half = size * 0.5f;
    float x1 = cx - half;
    float y1 = cy - half;
    float x2 = cx + half;
    float y2 = cy + half;
    float w = std::max(1.6f, size * 0.135f);

    Gdiplus::Pen pen(color, w);
    pen.SetStartCap(Gdiplus::LineCapRound);
    pen.SetEndCap(Gdiplus::LineCapRound);
    pen.SetLineJoin(Gdiplus::LineJoinRound);
    Gdiplus::SolidBrush brush(color);

    if (icon_name == L"arrow") {
        float sx = x1 + size * 0.14f;
        float sy = y2 - size * 0.14f;
        float ex = x2 - size * 0.10f;
        float ey = y1 + size * 0.10f;
        Gdiplus::Pen thick_pen(color, w + 0.5f);
        thick_pen.SetStartCap(Gdiplus::LineCapRound);
        g.DrawLine(&thick_pen, sx, sy, ex - size * 0.14f, ey + size * 0.14f);
        Gdiplus::PointF pts[4] = {
            {ex, ey},
            {ex - size * 0.54f, ey + size * 0.08f},
            {ex - size * 0.25f, ey + size * 0.25f},
            {ex - size * 0.08f, ey + size * 0.54f}
        };
        g.FillPolygon(&brush, pts, 4);
    } else if (icon_name == L"pen") {
        Gdiplus::PointF pts[5] = {
            {x1 + size * 0.12f, y2 - size * 0.12f},
            {x1 + size * 0.28f, y2 - size * 0.44f},
            {x2 - size * 0.24f, y1 + size * 0.12f},
            {x2 - size * 0.12f, y1 + size * 0.24f},
            {x1 + size * 0.44f, y2 - size * 0.28f}
        };
        g.DrawPolygon(&pen, pts, 5);
        g.DrawLine(&pen, x1 + size * 0.12f, y2 - size * 0.12f, x1 + size * 0.30f, y2 - size * 0.30f);
    } else if (icon_name == L"highlighter") {
        Gdiplus::PointF pts[4] = {
            {x1 + size * 0.20f, y2 - size * 0.36f},
            {x2 - size * 0.22f, y1 + size * 0.10f},
            {x2 - size * 0.08f, y1 + size * 0.26f},
            {x1 + size * 0.38f, y2 - size * 0.18f}
        };
        g.DrawPolygon(&pen, pts, 4);
        Gdiplus::Color bar_c(195, color.GetR(), color.GetG(), color.GetB());
        FillRoundedRect(g, Gdiplus::RectF(x1 + size * 0.10f, y2 - size * 0.16f, size * 0.80f, size * 0.16f), size * 0.08f, bar_c);
    } else if (icon_name == L"rect") {
        DrawRoundedRect(
            g,
            Gdiplus::RectF(x1 + size * 0.10f, y1 + size * 0.16f, size * 0.80f, size * 0.68f),
            size * 0.11f,
            Gdiplus::Color(0, 0, 0, 0),
            color,
            w);
    } else if (icon_name == L"ellipse") {
        g.DrawEllipse(&pen, Gdiplus::RectF(x1 + size * 0.10f, y1 + size * 0.14f, size * 0.80f, size * 0.72f));
    } else if (icon_name == L"line") {
        float p1x = x1 + size * 0.15f, p1y = y2 - size * 0.16f;
        float p2x = x2 - size * 0.15f, p2y = y1 + size * 0.16f;
        g.DrawLine(&pen, p1x, p1y, p2x, p2y);
        float r = std::max(2.0f, w * 1.15f);
        g.FillEllipse(&brush, p1x - r, p1y - r, r * 2.0f, r * 2.0f);
        g.FillEllipse(&brush, p2x - r, p2y - r, r * 2.0f, r * 2.0f);
    } else if (icon_name == L"text") {
        float top_y = y1 + size * 0.14f;
        float bot_y = y2 - size * 0.14f;
        float lx = x1 + size * 0.16f;
        float rx = x2 - size * 0.16f;
        float serif = size * 0.18f;
        g.DrawLine(&pen, lx, top_y, rx, top_y);
        g.DrawLine(&pen, lx, top_y, lx, top_y + serif);
        g.DrawLine(&pen, rx, top_y, rx, top_y + serif);
        g.DrawLine(&pen, cx, top_y, cx, bot_y);
        g.DrawLine(&pen, cx - size * 0.20f, bot_y, cx + size * 0.20f, bot_y);
    } else if (icon_name == L"pixelate") {
        int grid = 3;
        float cell = (size * 0.81f) / grid;
        float start_x = cx - (cell * grid) * 0.5f;
        float start_y = cy - (cell * grid) * 0.5f;
        for (int r_idx = 0; r_idx < grid; ++r_idx) {
            for (int c_idx = 0; c_idx < grid; ++c_idx) {
                BYTE alpha = ((r_idx + c_idx) % 2 == 0) ? 245 : 110;
                Gdiplus::SolidBrush cell_b(Gdiplus::Color(alpha, color.GetR(), color.GetG(), color.GetB()));
                float gx = start_x + c_idx * cell;
                float gy = start_y + r_idx * cell;
                g.FillRectangle(&cell_b, gx + 0.4f, gy + 0.4f, cell - 0.8f, cell - 0.8f);
            }
        }
    } else if (icon_name == L"undo") {
        g.DrawArc(&pen, x1 + size * 0.12f, y1 + size * 0.20f, size * 0.78f, size * 0.72f, 200.0f, 205.0f);
        float ax = x1 + size * 0.18f, ay = cy - size * 0.04f;
        float d = size * 0.25f;
        Gdiplus::PointF pts[3] = {
            {ax - d * 0.33f, ay + d * 0.33f},
            {ax + d, ay - d * 0.5f},
            {ax + d, ay + d}
        };
        g.FillPolygon(&brush, pts, 3);
    } else if (icon_name == L"redo") {
        g.DrawArc(&pen, x1 + size * 0.10f, y1 + size * 0.20f, size * 0.78f, size * 0.72f, 135.0f, 205.0f);
        float ax = x2 - size * 0.18f, ay = cy - size * 0.04f;
        float d = size * 0.25f;
        Gdiplus::PointF pts[3] = {
            {ax + d * 0.33f, ay + d * 0.33f},
            {ax - d, ay - d * 0.5f},
            {ax - d, ay + d}
        };
        g.FillPolygon(&brush, pts, 3);
    } else if (icon_name == L"clear") {
        float top_lid = y1 + size * 0.24f;
        g.DrawLine(&pen, x1 + size * 0.14f, top_lid, x2 - size * 0.14f, top_lid);
        g.DrawRectangle(&pen, x1 + size * 0.22f, top_lid, size * 0.56f, y2 - size * 0.10f - top_lid);
        g.DrawLine(&pen, cx - size * 0.12f, y1 + size * 0.13f, cx + size * 0.12f, y1 + size * 0.13f);
    } else if (icon_name == L"copy") {
        DrawRoundedRect(
            g,
            Gdiplus::RectF(x1 + size * 0.12f, y1 + size * 0.12f, size * 0.76f, size * 0.76f),
            size * 0.15f,
            Gdiplus::Color(0, 0, 0, 0),
            color,
            w);
        Gdiplus::PointF chk[3] = {
            {x1 + size * 0.28f, cy + size * 0.04f},
            {cx - size * 0.04f, y2 - size * 0.26f},
            {x2 - size * 0.24f, y1 + size * 0.30f}
        };
        g.DrawLines(&pen, chk, 3);
    } else if (icon_name == L"save") {
        g.DrawLine(&pen, cx, y1 + size * 0.12f, cx, cy + size * 0.16f);
        float aw = size * 0.24f;
        Gdiplus::PointF arr[3] = {
            {cx - aw, cy - size * 0.04f},
            {cx, cy + size * 0.20f},
            {cx + aw, cy - size * 0.04f}
        };
        g.DrawLines(&pen, arr, 3);
        float tray_y = y2 - size * 0.12f;
        float tray_top = y2 - size * 0.28f;
        float lx = x1 + size * 0.16f;
        float rx = x2 - size * 0.16f;
        Gdiplus::PointF tray[4] = {{lx, tray_top}, {lx, tray_y}, {rx, tray_y}, {rx, tray_top}};
        g.DrawLines(&pen, tray, 4);
    } else if (icon_name == L"palette") {
        float r = size * 0.38f;
        g.DrawEllipse(&pen, cx - r, cy - r, r * 2.0f, r * 2.0f);
        float dot = std::max(1.5f, size * 0.10f);
        Gdiplus::PointF dots[3] = {
            {cx - r * 0.45f, cy - r * 0.30f},
            {cx + r * 0.30f, cy - r * 0.45f},
            {cx - r * 0.30f, cy + r * 0.30f}
        };
        for (const auto& d : dots) {
            g.FillEllipse(&brush, d.X - dot, d.Y - dot, dot * 2.0f, dot * 2.0f);
        }
    } else if (icon_name == L"close") {
        float m = size * 0.25f;
        g.DrawLine(&pen, x1 + m, y1 + m, x2 - m, y2 - m);
        g.DrawLine(&pen, x2 - m, y1 + m, x1 + m, y2 - m);
    }
}

} // namespace app
