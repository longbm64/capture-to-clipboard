#include "common.h"
#include "autostart.h"
#include "editor.h"
#include "hotkeys.h"
#include "i18n.h"
#include "overlay.h"
#include "platform_utils.h"
#include "settings_window.h"
#include "toast.h"
#include "tray.h"

#include <cstdio>

namespace app {

namespace {

constexpr const wchar_t* kCoordinatorClassName = L"CaptureToClipboard_CoordinatorWnd";
HANDLE g_single_instance_mutex = nullptr;
HANDLE g_show_settings_event = nullptr;
UINT g_wm_taskbar_created = 0;

bool EnsureSingleInstance(bool minimized) {
    g_show_settings_event = CreateEventW(
        nullptr,
        TRUE,
        FALSE,
        L"Local\\CaptureToClipboard_ShowSettings_Event");
    g_single_instance_mutex = CreateMutexW(
        nullptr,
        FALSE,
        L"Local\\CaptureToClipboard_SingleInstance_Mutex");

    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        if (!minimized && g_show_settings_event) {
            SetEvent(g_show_settings_event);
        }
        return false;
    }
    return true;
}

int RunSelfTest() {
    HANDLE h_out = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD file_type = h_out ? GetFileType(h_out) : FILE_TYPE_UNKNOWN;
    if (file_type == FILE_TYPE_UNKNOWN || file_type == FILE_TYPE_CHAR) {
        if (AttachConsole(ATTACH_PARENT_PROCESS) || AllocConsole()) {
            FILE* fp = nullptr;
            freopen_s(&fp, "CONOUT$", "w", stdout);
            freopen_s(&fp, "CONOUT$", "w", stderr);
        }
    }
    SetConsoleOutputCP(CP_UTF8);

    auto log_line = [](const std::string& line) {
        HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);
        if (h && h != INVALID_HANDLE_VALUE) {
            DWORD written = 0;
            WriteFile(h, line.data(), static_cast<DWORD>(line.size()), &written, nullptr);
        } else {
            fwrite(line.data(), 1, line.size(), stdout);
            fflush(stdout);
        }
    };

    log_line("[Self-Test] 1. Kiem tra tao icon System Tray...\n");
    HICON hicon = GetAppIcon(64);
    if (!hicon) {
        log_line("  -> FAILED: GetAppIcon returned NULL\n");
        return 1;
    }
    log_line("  -> OK\n");

    log_line("[Self-Test] 2. Kiem tra giu nguyen chat luong anh goc Lossless 1:1 & copy vao Clipboard...\n");
    Gdiplus::Bitmap test_bmp(240, 120, PixelFormat32bppARGB);
    {
        Gdiplus::Graphics g(&test_bmp);
        g.Clear(Gdiplus::Color(255, 37, 99, 235));
    }
    auto [ok, msg] = CopyBitmapToClipboard(&test_bmp);
    std::string msg_utf8 = WideToUtf8(msg);
    char buf[512];
    snprintf(buf, sizeof(buf), "  -> %s: %s (Size: %ux%u)\n", ok ? "True" : "False", msg_utf8.c_str(), test_bmp.GetWidth(), test_bmp.GetHeight());
    log_line(buf);
    if (!ok) return 1;

    log_line("[Self-Test] 3. Kiem tra ma hoa Lossless PNG & cau hinh da ngon ngu...\n");
    auto png_bytes = EncodeLosslessPngBytes(&test_bmp);
    if (png_bytes.size() < 64) {
        log_line("  -> FAILED: EncodeLosslessPngBytes returned empty buffer\n");
        return 1;
    }
    snprintf(buf, sizeof(buf), "  -> OK (Lossless PNG size: %zu bytes, Lang: %s)\n", png_bytes.size(), WideToUtf8(GetLanguage()).c_str());
    log_line(buf);

    log_line("[Self-Test] 4. Kiem tra trang thai Autostart & cua so Cai dat...\n");
    bool auto_state = IsAutostartEnabled();
    snprintf(buf, sizeof(buf), "  -> Autostart hien tai: %s\n", auto_state ? "True" : "False");
    log_line(buf);
    log_line("[Self-Test] Hoan tat thanh cong!\n");
    return 0;
}

class CaptureApp {
public:
    CaptureApp() {
        EnableDpiAwareness();
        InitFonts();
        SyncAutostartOnStartup();
        SetCurrentProcessExplicitAppUserModelID(L"CaptureToClipboard.HD.App");

        g_wm_taskbar_created = RegisterWindowMessageW(L"TaskbarCreated");

        WNDCLASSEXW wc{};
        wc.cbSize = sizeof(wc);
        wc.lpfnWndProc = CaptureApp::WndProc;
        wc.hInstance = GetModuleHandleW(nullptr);
        wc.hIcon = GetAppIcon(std::max(32, GetSystemMetrics(SM_CXICON)));
        wc.hIconSm = GetAppIcon(std::max(16, GetSystemMetrics(SM_CXSMICON)));
        wc.lpszClassName = kCoordinatorClassName;
        RegisterClassExW(&wc);

        hwnd_ = CreateWindowExW(
            0,
            kCoordinatorClassName,
            APP_NAME_W,
            WS_OVERLAPPEDWINDOW,
            0, 0, 0, 0,
            nullptr,
            nullptr,
            GetModuleHandleW(nullptr),
            this);

        settings_window_ = std::make_unique<SettingsAndGuideWindow>(
            [this](bool enabled) { OnAutostartChangedFromUi(enabled); },
            [this](bool enabled) { OnPrtScChangedFromUi(enabled); },
            [this](const std::wstring& lang) { OnLanguageChangedFromUi(lang); },
            [this]() { OnWindowMinimizedToTray(); });

        hotkeys_ = std::make_unique<GlobalHotkeyManager>(hwnd_, IsPrtScEnabled());
        tray_ = std::make_unique<SystemTrayController>(hwnd_);
        overlay_ = std::make_unique<RegionSelectorOverlay>();
    }

    ~CaptureApp() {
        Shutdown();
    }

    void Start(bool minimized, bool show_settings) {
        hotkeys_->Start();
        tray_->Start();

        SetTimer(hwnd_, IDT_SINGLE_INSTANCE_POLL, 150, nullptr);
        SetTimer(hwnd_, IDT_TRAY_ENSURE_VISIBLE, 2500, nullptr);

        if (show_settings || !minimized) {
            PostMessageW(hwnd_, WM_APP_OPEN_SETTINGS, 0, 0);
        }

        MSG msg{};
        while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }

    void Shutdown() {
        if (shutting_down_) return;
        shutting_down_ = true;

        ToastNotification::Dismiss();
        if (overlay_) overlay_->Close();
        editor_.reset();
        if (settings_window_) settings_window_->Close(true);
        if (hotkeys_) hotkeys_->Stop();
        if (tray_) tray_->Stop();

        if (hwnd_ && IsWindow(hwnd_)) {
            DestroyWindow(hwnd_);
        }
        hwnd_ = nullptr;
    }

private:
    static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
        CaptureApp* self = nullptr;
        if (msg == WM_NCCREATE) {
            auto* cs = reinterpret_cast<CREATESTRUCTW*>(lparam);
            self = static_cast<CaptureApp*>(cs->lpCreateParams);
            SetWindowLongPtrW(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(self));
        } else {
            self = reinterpret_cast<CaptureApp*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA));
        }
        if (self) {
            return self->HandleMessage(hwnd, msg, wparam, lparam);
        }
        return DefWindowProcW(hwnd, msg, wparam, lparam);
    }

    LRESULT HandleMessage(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
        if (g_wm_taskbar_created != 0 && msg == g_wm_taskbar_created) {
            if (tray_) tray_->EnsureVisible();
            return 0;
        }

        switch (msg) {
        case WM_HOTKEY:
            if (hotkeys_) hotkeys_->HandleWmHotkey(wparam);
            return 0;

        case WM_APP_TRAYICON:
            if (tray_) tray_->HandleTrayMessage(wparam, lparam);
            return 0;

        case WM_APP_OPEN_SETTINGS:
            if (settings_window_) settings_window_->Show();
            return 0;

        case WM_APP_TOGGLE_AUTOSTART: {
            bool new_state = !IsAutostartEnabled();
            auto [ok, status_msg] = SetAutostartEnabled(new_state);
            (void)ok;
            (void)status_msg;
            if (tray_) tray_->RefreshMenu();
            if (settings_window_) settings_window_->RefreshState();
            return 0;
        }

        case WM_APP_BEGIN_CAPTURE: {
            int mode = static_cast<int>(wparam);
            bool from_tray = (lparam != 0);
            BeginCapture(mode, from_tray);
            return 0;
        }

        case WM_APP_EXIT:
            Shutdown();
            PostQuitMessage(0);
            return 0;

        case WM_TIMER:
            if (wparam == IDT_SINGLE_INSTANCE_POLL) {
                if (g_show_settings_event && WaitForSingleObject(g_show_settings_event, 0) == WAIT_OBJECT_0) {
                    ResetEvent(g_show_settings_event);
                    PostMessageW(hwnd, WM_APP_OPEN_SETTINGS, 0, 0);
                }
            } else if (wparam == IDT_TRAY_ENSURE_VISIBLE) {
                if (tray_) tray_->EnsureVisible();
                ++tray_check_count_;
                if (tray_check_count_ >= 4) {
                    KillTimer(hwnd, IDT_TRAY_ENSURE_VISIBLE);
                }
            } else if (wparam == IDT_INITIAL_TOAST) {
                KillTimer(hwnd, IDT_INITIAL_TOAST);
                ToastNotification::Show(Tr(L"toast_ready"), true, 2800);
            } else if (wparam == IDT_DELAYED_CAPTURE_1) {
                KillTimer(hwnd, IDT_DELAYED_CAPTURE_1);
                ExecuteCapture(1);
            } else if (wparam == IDT_DELAYED_CAPTURE_2) {
                KillTimer(hwnd, IDT_DELAYED_CAPTURE_2);
                ExecuteCapture(2);
            }
            return 0;

        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
        }

        return DefWindowProcW(hwnd, msg, wparam, lparam);
    }

    void OnAutostartChangedFromUi(bool /*enabled*/) {
        if (tray_) tray_->RefreshMenu();
    }

    void OnPrtScChangedFromUi(bool enabled) {
        if (hotkeys_) hotkeys_->SetPrtScEnabled(enabled);
    }

    void OnLanguageChangedFromUi(const std::wstring& /*lang*/) {
        if (tray_) tray_->RefreshMenu();
    }

    void OnWindowMinimizedToTray() {
    }

    void BeginCapture(int mode, bool from_tray) {
        if (shutting_down_ || (overlay_ && overlay_->IsActive())) {
            return;
        }

        bool was_settings_visible = settings_window_ && settings_window_->IsVisible();
        if (settings_window_) {
            settings_window_->Close(false);
        }
        ToastNotification::Dismiss();

        if (from_tray) {
            SetTimer(hwnd_, mode == 1 ? IDT_DELAYED_CAPTURE_1 : IDT_DELAYED_CAPTURE_2, 160, nullptr);
        } else if (was_settings_visible) {
            SetTimer(hwnd_, mode == 1 ? IDT_DELAYED_CAPTURE_1 : IDT_DELAYED_CAPTURE_2, 55, nullptr);
        } else {
            ExecuteCapture(mode);
        }
    }

    void ExecuteCapture(int mode) {
        if (shutting_down_ || (overlay_ && overlay_->IsActive())) {
            return;
        }

        ScreenCaptureData cap;
        std::wstring err;
        if (!CaptureVirtualScreen(cap, err)) {
            ToastNotification::Show(TrFmtErr(L"toast_capture_err", err), false, 3000);
            return;
        }

        overlay_->Open(
            std::move(cap),
            mode,
            [this](std::unique_ptr<Gdiplus::Bitmap> cropped, int m) {
                OnRegionSelected(std::move(cropped), m);
            },
            []() {});
    }

    void OnRegionSelected(std::unique_ptr<Gdiplus::Bitmap> cropped, int mode) {
        if (!cropped) return;

        if (mode == 1) {
            int w = static_cast<int>(cropped->GetWidth());
            int h = static_cast<int>(cropped->GetHeight());
            auto [ok, msg] = CopyBitmapToClipboard(cropped.get());
            if (ok) {
                ToastNotification::Show(TrFmtInt2(L"toast_copied_fast", w, h), true, 2000);
            } else {
                ToastNotification::Show(msg, false, 3200);
            }
            return;
        }

        // Mode 2: Open Annotation Editor
        if (editor_) {
            editor_->CloseEditor();
            editor_.reset();
        }

        editor_ = std::make_unique<AnnotationEditor>(
            std::move(cropped),
            [this](Gdiplus::Bitmap* edited) {
                int w = static_cast<int>(edited->GetWidth());
                int h = static_cast<int>(edited->GetHeight());
                auto [ok, msg] = CopyBitmapToClipboard(edited);
                if (ok) {
                    ToastNotification::Show(TrFmtInt2(L"toast_copied_draw", w, h), true, 2200);
                } else {
                    ToastNotification::Show(msg, false, 3200);
                }
            },
            []() {});
    }

    HWND hwnd_ = nullptr;
    bool shutting_down_ = false;
    int tray_check_count_ = 0;

    std::unique_ptr<SettingsAndGuideWindow> settings_window_;
    std::unique_ptr<GlobalHotkeyManager> hotkeys_;
    std::unique_ptr<SystemTrayController> tray_;
    std::unique_ptr<RegionSelectorOverlay> overlay_;
    std::unique_ptr<AnnotationEditor> editor_;
};

} // namespace

} // namespace app

int WINAPI wWinMain(HINSTANCE /*hInstance*/, HINSTANCE /*hPrevInstance*/, PWSTR /*pCmdLine*/, int /*nCmdShow*/) {
    HRESULT hr_co = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    (void)hr_co;

    Gdiplus::GdiplusStartupInput gdiplusStartupInput;
    ULONG_PTR gdiplusToken = 0;
    Gdiplus::GdiplusStartup(&gdiplusToken, &gdiplusStartupInput, nullptr);

    // Set working directory to executable directory
    std::error_code ec;
    std::filesystem::current_path(app::GetExecutableDir(), ec);

    bool self_test = false;
    bool show_settings = false;
    bool minimized = false;

    int argc = 0;
    LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (argv) {
        for (int i = 1; i < argc; ++i) {
            std::wstring arg(argv[i]);
            if (arg == L"--self-test") self_test = true;
            else if (arg == L"--show-settings") show_settings = true;
            else if (arg == L"--minimized") minimized = true;
        }
        LocalFree(argv);
    }

    int exit_code = 0;
    if (self_test) {
        app::EnableDpiAwareness();
        app::InitFonts();
        exit_code = app::RunSelfTest();
    } else if (app::EnsureSingleInstance(minimized)) {
        app::CaptureApp application;
        application.Start(minimized, show_settings);
    }

    if (app::g_show_settings_event) {
        CloseHandle(app::g_show_settings_event);
        app::g_show_settings_event = nullptr;
    }
    if (app::g_single_instance_mutex) {
        CloseHandle(app::g_single_instance_mutex);
        app::g_single_instance_mutex = nullptr;
    }

    Gdiplus::GdiplusShutdown(gdiplusToken);
    CoUninitialize();
    return exit_code;
}
