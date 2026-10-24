#pragma once
#include "common.h"

namespace app {

class SystemTrayController {
public:
    explicit SystemTrayController(HWND hwnd);
    ~SystemTrayController();

    void Start();
    void Stop();
    void RefreshMenu();
    void EnsureVisible();
    void HandleTrayMessage(WPARAM wparam, LPARAM lparam);

private:
    void ShowContextMenu();
    void PopulateNotifyData(NOTIFYICONDATAW& nid);

    HWND hwnd_ = nullptr;
    HICON hicon_ = nullptr;
    bool added_ = false;
};

} // namespace app
