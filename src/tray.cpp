#include "tray.h"
#include "autostart.h"
#include "i18n.h"
#include "platform_utils.h"

namespace app {

namespace {
constexpr UINT kTrayIconId = 1;
}

SystemTrayController::SystemTrayController(HWND hwnd) : hwnd_(hwnd) {}

SystemTrayController::~SystemTrayController() {
    Stop();
}

void SystemTrayController::PopulateNotifyData(NOTIFYICONDATAW& nid) {
    ZeroMemory(&nid, sizeof(nid));
    nid.cbSize = sizeof(NOTIFYICONDATAW);
    nid.hWnd = hwnd_;
    nid.uID = kTrayIconId;
    nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
    nid.uCallbackMessage = WM_APP_TRAYICON;
    nid.hIcon = hicon_;
    std::wstring tip = Tr(L"tray_tooltip");
    wcsncpy_s(nid.szTip, tip.c_str(), _TRUNCATE);
}

void SystemTrayController::Start() {
    if (!hwnd_) return;
    if (!hicon_) {
        hicon_ = GetAppIcon(64);
    }
    NOTIFYICONDATAW nid;
    PopulateNotifyData(nid);
    added_ = Shell_NotifyIconW(NIM_ADD, &nid) != FALSE;
}

void SystemTrayController::Stop() {
    if (added_ && hwnd_) {
        NOTIFYICONDATAW nid{};
        nid.cbSize = sizeof(NOTIFYICONDATAW);
        nid.hWnd = hwnd_;
        nid.uID = kTrayIconId;
        Shell_NotifyIconW(NIM_DELETE, &nid);
        added_ = false;
    }
}

void SystemTrayController::RefreshMenu() {
    if (!hwnd_) return;
    NOTIFYICONDATAW nid;
    PopulateNotifyData(nid);
    if (!Shell_NotifyIconW(NIM_MODIFY, &nid)) {
        added_ = Shell_NotifyIconW(NIM_ADD, &nid) != FALSE;
    }
}

void SystemTrayController::EnsureVisible() {
    if (!hwnd_) return;
    NOTIFYICONDATAW nid;
    PopulateNotifyData(nid);
    if (!Shell_NotifyIconW(NIM_MODIFY, &nid)) {
        added_ = Shell_NotifyIconW(NIM_ADD, &nid) != FALSE;
    } else {
        added_ = true;
    }
}

void SystemTrayController::HandleTrayMessage(WPARAM /*wparam*/, LPARAM lparam) {
    UINT mouse_msg = LOWORD(lparam);
    if (mouse_msg == WM_LBUTTONUP || mouse_msg == WM_LBUTTONDBLCLK) {
        PostMessageW(hwnd_, WM_APP_OPEN_SETTINGS, 0, 0);
    } else if (mouse_msg == WM_RBUTTONUP || mouse_msg == WM_CONTEXTMENU) {
        ShowContextMenu();
    }
}

void SystemTrayController::ShowContextMenu() {
    if (!hwnd_) return;
    HMENU hmenu = CreatePopupMenu();
    if (!hmenu) return;

    std::wstring open_txt = Tr(L"tray_open_settings");
    std::wstring auto_txt = Tr(L"tray_autostart");
    std::wstring fast_txt = Tr(L"tray_capture_fast");
    std::wstring draw_txt = Tr(L"tray_capture_draw");
    std::wstring exit_txt = Tr(L"tray_exit");

    AppendMenuW(hmenu, MF_STRING, IDM_TRAY_OPEN_SETTINGS, open_txt.c_str());
    SetMenuDefaultItem(hmenu, IDM_TRAY_OPEN_SETTINGS, FALSE);

    UINT auto_flags = MF_STRING | (IsAutostartEnabled() ? MF_CHECKED : MF_UNCHECKED);
    AppendMenuW(hmenu, auto_flags, IDM_TRAY_AUTOSTART, auto_txt.c_str());

    AppendMenuW(hmenu, MF_SEPARATOR, 0, nullptr);
    AppendMenuW(hmenu, MF_STRING, IDM_TRAY_CAPTURE_FAST, fast_txt.c_str());
    AppendMenuW(hmenu, MF_STRING, IDM_TRAY_CAPTURE_DRAW, draw_txt.c_str());
    AppendMenuW(hmenu, MF_SEPARATOR, 0, nullptr);
    AppendMenuW(hmenu, MF_STRING, IDM_TRAY_EXIT, exit_txt.c_str());

    POINT pt{};
    GetCursorPos(&pt);
    SetForegroundWindow(hwnd_);
    UINT cmd = TrackPopupMenu(
        hmenu,
        TPM_RETURNCMD | TPM_NONOTIFY | TPM_RIGHTBUTTON | TPM_BOTTOMALIGN,
        pt.x,
        pt.y,
        0,
        hwnd_,
        nullptr);
    PostMessageW(hwnd_, WM_NULL, 0, 0);
    DestroyMenu(hmenu);

    switch (cmd) {
    case IDM_TRAY_OPEN_SETTINGS:
        PostMessageW(hwnd_, WM_APP_OPEN_SETTINGS, 0, 0);
        break;
    case IDM_TRAY_AUTOSTART:
        PostMessageW(hwnd_, WM_APP_TOGGLE_AUTOSTART, 0, 0);
        break;
    case IDM_TRAY_CAPTURE_FAST:
        PostMessageW(hwnd_, WM_APP_BEGIN_CAPTURE, 1, 1); // mode=1, from_tray=1
        break;
    case IDM_TRAY_CAPTURE_DRAW:
        PostMessageW(hwnd_, WM_APP_BEGIN_CAPTURE, 2, 1); // mode=2, from_tray=1
        break;
    case IDM_TRAY_EXIT:
        PostMessageW(hwnd_, WM_APP_EXIT, 0, 0);
        break;
    default:
        break;
    }
}

} // namespace app
