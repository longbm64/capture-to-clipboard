#include "autostart.h"
#include "i18n.h"
#include "platform_utils.h"

namespace app {

namespace {

constexpr const wchar_t* kAppRunName = L"CaptureToClipboard";
constexpr const wchar_t* kLegacyRunName = L"ChupManHinh";
constexpr const wchar_t* kRunRegSubKey = L"Software\\Microsoft\\Windows\\CurrentVersion\\Run";
constexpr const wchar_t* kStartupApprovedSubKey = L"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\StartupApproved\\Run";

std::wstring GetWindowsLaunchCommand() {
    wchar_t exe_buf[MAX_PATH] = {0};
    GetModuleFileNameW(nullptr, exe_buf, MAX_PATH);
    std::filesystem::path current_exe(exe_buf);

    std::filesystem::path dist_exe = current_exe.parent_path() / L"dist" / L"CaptureToClipboard.exe";
    std::error_code ec;
    if (std::filesystem::exists(dist_exe, ec)) {
        return L"\"" + dist_exe.wstring() + L"\" --minimized";
    }
    return L"\"" + current_exe.wstring() + L"\" --minimized";
}

std::filesystem::path ExtractExeFromCommand(const std::wstring& cmd) {
    size_t first = cmd.find_first_not_of(L" \t\r\n");
    if (first == std::wstring::npos) return {};
    if (cmd[first] == L'"') {
        size_t end_q = cmd.find(L'"', first + 1);
        if (end_q != std::wstring::npos && end_q > first + 1) {
            return std::filesystem::path(cmd.substr(first + 1, end_q - first - 1));
        }
    }
    size_t space = cmd.find_first_of(L" \t", first);
    if (space != std::wstring::npos) {
        return std::filesystem::path(cmd.substr(first, space - first));
    }
    return std::filesystem::path(cmd.substr(first));
}

bool IsWindowsStartupApproved() {
    HKEY hkey = nullptr;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, kStartupApprovedSubKey, 0, KEY_READ, &hkey) != ERROR_SUCCESS) {
        return true;
    }
    BYTE buf[64] = {0};
    DWORD buf_sz = sizeof(buf);
    DWORD type = 0;
    LSTATUS st = RegQueryValueExW(hkey, kAppRunName, nullptr, &type, buf, &buf_sz);
    RegCloseKey(hkey);
    if (st == ERROR_SUCCESS && buf_sz > 0) {
        // Odd first byte (1, 3, etc.) means disabled by Task Manager
        if (buf[0] == 1 || buf[0] == 3) {
            return false;
        }
    }
    return true;
}

void SetWindowsStartupApproved(bool enabled) {
    HKEY hkey = nullptr;
    if (RegCreateKeyExW(HKEY_CURRENT_USER, kStartupApprovedSubKey, 0, nullptr, 0, KEY_SET_VALUE, nullptr, &hkey, nullptr) != ERROR_SUCCESS) {
        return;
    }
    RegDeleteValueW(hkey, kLegacyRunName);
    if (enabled) {
        const BYTE enabled_bytes[12] = {0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
        RegSetValueExW(hkey, kAppRunName, 0, REG_BINARY, enabled_bytes, sizeof(enabled_bytes));
    } else {
        RegDeleteValueW(hkey, kAppRunName);
    }
    RegCloseKey(hkey);
}

} // namespace

bool IsAutostartEnabled() {
    if (!IsWindowsStartupApproved()) {
        return false;
    }
    HKEY hkey = nullptr;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, kRunRegSubKey, 0, KEY_READ, &hkey) != ERROR_SUCCESS) {
        return false;
    }
    wchar_t val[1024] = {0};
    DWORD val_bytes = sizeof(val);
    DWORD type = 0;
    LSTATUS st = RegQueryValueExW(hkey, kAppRunName, nullptr, &type, reinterpret_cast<LPBYTE>(val), &val_bytes);
    RegCloseKey(hkey);
    if (st != ERROR_SUCCESS || (type != REG_SZ && type != REG_EXPAND_SZ)) {
        return false;
    }
    std::wstring cmd(val);
    if (cmd.empty()) return false;
    std::filesystem::path exe_p = ExtractExeFromCommand(cmd);
    std::error_code ec;
    return !exe_p.empty() && std::filesystem::exists(exe_p, ec);
}

std::pair<bool, std::wstring> SetAutostartEnabled(bool enabled) {
    AppSettings settings = LoadAppSettings();
    settings.autostart_enabled = enabled;
    SaveAppSettings(settings);

    HKEY hkey = nullptr;
    if (RegCreateKeyExW(HKEY_CURRENT_USER, kRunRegSubKey, 0, nullptr, 0, KEY_SET_VALUE, nullptr, &hkey, nullptr) != ERROR_SUCCESS) {
        return {false, L"Autostart registry error"};
    }
    RegDeleteValueW(hkey, kLegacyRunName);

    if (enabled) {
        std::wstring cmd = GetWindowsLaunchCommand();
        DWORD byte_len = static_cast<DWORD>((cmd.size() + 1) * sizeof(wchar_t));
        LSTATUS st = RegSetValueExW(hkey, kAppRunName, 0, REG_SZ, reinterpret_cast<const BYTE*>(cmd.c_str()), byte_len);
        RegCloseKey(hkey);
        if (st != ERROR_SUCCESS) {
            return {false, L"Failed to write Run registry value"};
        }
        SetWindowsStartupApproved(true);
        return {true, Tr(L"toast_autostart_on")};
    } else {
        RegDeleteValueW(hkey, kAppRunName);
        RegCloseKey(hkey);
        SetWindowsStartupApproved(false);
        return {true, Tr(L"toast_autostart_off")};
    }
}

void SyncAutostartOnStartup() {
    AppSettings settings = LoadAppSettings();
    bool want_enabled = settings.has_autostart_key ? settings.autostart_enabled : true;
    if (want_enabled) {
        SetAutostartEnabled(true);
    }
}

bool IsPrtScEnabled() {
    AppSettings settings = LoadAppSettings();
    return settings.prtsc_enabled;
}

std::pair<bool, std::wstring> SetPrtScEnabled(bool enabled) {
    AppSettings settings = LoadAppSettings();
    settings.prtsc_enabled = enabled;
    if (SaveAppSettings(settings)) {
        return {true, enabled ? Tr(L"toast_prtsc_on") : Tr(L"toast_prtsc_off")};
    }
    return {false, L"Failed to save PrtSc setting"};
}

} // namespace app
