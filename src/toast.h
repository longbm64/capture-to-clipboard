#pragma once
#include "common.h"

namespace app {

class ToastNotification {
public:
    static void Show(const std::wstring& message, bool success = true, int duration_ms = 2000);
    static void Dismiss();
    static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam);
};

} // namespace app
