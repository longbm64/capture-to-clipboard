#include "hotkeys.h"

namespace app {

GlobalHotkeyManager::GlobalHotkeyManager(HWND notify_hwnd, bool prtsc_enabled)
    : notify_hwnd_(notify_hwnd), prtsc_enabled_(prtsc_enabled) {}

GlobalHotkeyManager::~GlobalHotkeyManager() {
    Stop();
}

void GlobalHotkeyManager::Start() {
    if (running_) return;
    running_ = true;

    ctrl1_reg_ok_ = RegisterHotKey(notify_hwnd_, 1, MOD_CONTROL | MOD_NOREPEAT, 0x31) != FALSE;
    ctrl2_reg_ok_ = RegisterHotKey(notify_hwnd_, 2, MOD_CONTROL | MOD_NOREPEAT, 0x32) != FALSE;
    RegisterHotKey(notify_hwnd_, 3, MOD_CONTROL | MOD_NOREPEAT, VK_NUMPAD1);
    RegisterHotKey(notify_hwnd_, 4, MOD_CONTROL | MOD_NOREPEAT, VK_NUMPAD2);
    RegisterHotKey(notify_hwnd_, 7, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x31);
    RegisterHotKey(notify_hwnd_, 8, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x32);

    if (prtsc_enabled_) {
        RegisterPrtScHotkeys();
    }
}

void GlobalHotkeyManager::Stop() {
    if (!running_) return;
    running_ = false;

    if (notify_hwnd_) {
        for (int id = 1; id <= 8; ++id) {
            UnregisterHotKey(notify_hwnd_, id);
        }
    }
    ctrl1_reg_ok_ = false;
    ctrl2_reg_ok_ = false;
    prtsc_reg_ok_ = false;
}

void GlobalHotkeyManager::SetPrtScEnabled(bool enabled) {
    prtsc_enabled_ = enabled;
    if (!running_) return;
    if (enabled && !prtsc_reg_ok_) {
        RegisterPrtScHotkeys();
    } else if (!enabled && prtsc_reg_ok_) {
        UnregisterPrtScHotkeys();
    }
}

void GlobalHotkeyManager::RegisterPrtScHotkeys() {
    if (!notify_hwnd_) return;
    bool ok1 = RegisterHotKey(notify_hwnd_, 5, MOD_NOREPEAT, VK_SNAPSHOT) != FALSE;
    bool ok2 = RegisterHotKey(notify_hwnd_, 6, 0, VK_SNAPSHOT) != FALSE;
    prtsc_reg_ok_ = ok1 || ok2;
}

void GlobalHotkeyManager::UnregisterPrtScHotkeys() {
    if (!notify_hwnd_) return;
    UnregisterHotKey(notify_hwnd_, 5);
    UnregisterHotKey(notify_hwnd_, 6);
    prtsc_reg_ok_ = false;
}

void GlobalHotkeyManager::HandleWmHotkey(WPARAM hotkey_id) {
    if (!running_) return;
    int id = static_cast<int>(hotkey_id);
    if (id == 1 || id == 3 || id == 7) {
        TriggerMode(1);
    } else if ((id == 5 || id == 6) && prtsc_enabled_) {
        TriggerMode(1);
    } else if (id == 2 || id == 4 || id == 8) {
        TriggerMode(2);
    }
}

void GlobalHotkeyManager::TriggerMode(int mode) {
    ULONGLONG now = GetTickCount64();
    if (now - last_trigger_tick_ < 300) {
        return;
    }
    last_trigger_tick_ = now;
    if (notify_hwnd_) {
        PostMessageW(notify_hwnd_, WM_APP_BEGIN_CAPTURE, static_cast<WPARAM>(mode), 0);
    }
}

} // namespace app
