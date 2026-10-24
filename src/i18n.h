#pragma once
#include "common.h"

namespace app {

constexpr const wchar_t* APP_NAME_W = L"Capture To Clipboard";
constexpr const wchar_t* APP_VERSION_W = L"2.0.0";
constexpr const wchar_t* APP_TITLE_WITH_VERSION_W = L"Capture To Clipboard v2.0.0";

struct ShortcutGuideRow {
    std::wstring key_text;
    std::wstring key_fg;
    std::wstring key_bg;
    std::wstring action_title;
    std::wstring desc_text;
};

struct EditorToolDef {
    std::wstring id;
    std::wstring label;
};

struct EditorSizeDef {
    int size_val;
    std::wstring label;
    int dot_radius_pt;
};

struct AppSettings {
    std::wstring language = L"vi";
    bool autostart_enabled = true;
    bool prtsc_enabled = true;
    bool has_autostart_key = false;
};

AppSettings LoadAppSettings();
bool SaveAppSettings(const AppSettings& settings);

std::wstring GetLanguage();
std::pair<bool, std::wstring> SetLanguage(const std::wstring& lang);

std::wstring Tr(const std::wstring& key);
std::wstring TrFmtInt2(const std::wstring& key, int w, int h);
std::wstring TrFmtErr(const std::wstring& key, const std::wstring& err);

const std::vector<ShortcutGuideRow>& GetShortcutsGuide();
const std::vector<EditorToolDef>& GetEditorTools();
const std::vector<EditorSizeDef>& GetEditorSizes();

} // namespace app
