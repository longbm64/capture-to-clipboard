#pragma once
#include "common.h"

namespace app {

class GlobalHotkeyManager {
public:
    GlobalHotkeyManager(HWND notify_hwnd, bool prtsc_enabled);
    ~GlobalHotkeyManager();

    void Start();
    void Stop();
    void SetPrtScEnabled(bool enabled);
    bool IsPrtScEnabled() const { return prtsc_enabled_; }
    void HandleWmHotkey(WPARAM hotkey_id);

private:
    void TriggerMode(int mode);
    void RegisterPrtScHotkeys();
    void UnregisterPrtScHotkeys();

    HWND notify_hwnd_ = nullptr;
    bool running_ = false;
    bool prtsc_enabled_ = true;
    bool ctrl1_reg_ok_ = false;
    bool ctrl2_reg_ok_ = false;
    bool prtsc_reg_ok_ = false;
    ULONGLONG last_trigger_tick_ = 0;
};

} // namespace app
