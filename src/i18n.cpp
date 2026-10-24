#include "i18n.h"
#include "platform_utils.h"

namespace app {

namespace {

std::wstring g_current_lang;

std::filesystem::path GetSettingsFilePath() {
    return GetWritableDataDir() / L"settings.json";
}

std::string ReadFileBytes(const std::filesystem::path& path) {
    std::ifstream ifs(path, std::ios::binary);
    if (!ifs) return "";
    std::ostringstream oss;
    oss << ifs.rdbuf();
    return oss.str();
}

bool WriteFileBytes(const std::filesystem::path& path, const std::string& content) {
    std::error_code ec;
    std::filesystem::create_directories(path.parent_path(), ec);
    std::ofstream ofs(path, std::ios::binary | std::ios::trunc);
    if (!ofs) return false;
    ofs.write(content.data(), static_cast<std::streamsize>(content.size()));
    return ofs.good();
}

// Lightweight JSON key parser for settings.json
bool ExtractJsonBool(const std::string& json, const std::string& key, bool default_val, bool* found_out = nullptr) {
    std::string pattern = "\"" + key + "\"";
    auto pos = json.find(pattern);
    if (pos == std::string::npos) {
        if (found_out) *found_out = false;
        return default_val;
    }
    auto colon = json.find(':', pos + pattern.size());
    if (colon == std::string::npos) {
        if (found_out) *found_out = false;
        return default_val;
    }
    if (found_out) *found_out = true;
    auto val_start = json.find_first_not_of(" \t\r\n", colon + 1);
    if (val_start == std::string::npos) return default_val;
    if (json.compare(val_start, 4, "true") == 0) return true;
    if (json.compare(val_start, 5, "false") == 0) return false;
    return default_val;
}

std::string ExtractJsonString(const std::string& json, const std::string& key, const std::string& default_val) {
    std::string pattern = "\"" + key + "\"";
    auto pos = json.find(pattern);
    if (pos == std::string::npos) return default_val;
    auto colon = json.find(':', pos + pattern.size());
    if (colon == std::string::npos) return default_val;
    auto q1 = json.find('"', colon + 1);
    if (q1 == std::string::npos) return default_val;
    auto q2 = json.find('"', q1 + 1);
    if (q2 == std::string::npos) return default_val;
    return json.substr(q1 + 1, q2 - q1 - 1);
}

const std::unordered_map<std::wstring, std::wstring>& GetViMap() {
    static const std::unordered_map<std::wstring, std::wstring> m = {
        {L"app_title", L"Capture To Clipboard v2.0.0"},
        {L"tray_tooltip", L"Capture To Clipboard v2.0.0 \u2014 Nh\u1EA5n \u0111\u1EC3 m\u1EDF C\u00E0i \u0111\u1EB7t & H\u01B0\u1EDBng d\u1EABn"},
        {L"tray_open_settings", L"B\u1EA3ng h\u01B0\u1EDBng d\u1EABn & C\u00E0i \u0111\u1EB7t"},
        {L"tray_autostart", L"Kh\u1EDFi \u0111\u1ED9ng c\u00F9ng m\u00E1y t\u00EDnh"},
        {L"tray_capture_fast", L"Ch\u1EE5p nhanh (Ctrl + 1)"},
        {L"tray_capture_draw", L"Ch\u1EE5p & Ghi ch\u00FA (Ctrl + 2)"},
        {L"tray_exit", L"\u0110\u00F3ng \u1EE9ng d\u1EE5ng"},

        {L"toast_ready", L"Capture To Clipboard \u0111\u00E3 s\u1EB5n s\u00E0ng  \u2022  Ctrl+1 / PrtSc: Ch\u1EE5p nhanh  |  Ctrl+2: Ch\u1EE5p & Ghi ch\u00FA"},
        {L"toast_minimized_tray", L"Capture To Clipboard \u0111\u00E3 thu xu\u1ED1ng khay h\u1EC7 th\u1ED1ng (System Tray)."},
        {L"toast_autostart_on", L"\u0110\u00E3 b\u1EADt kh\u1EDFi \u0111\u1ED9ng c\u00F9ng m\u00E1y t\u00EDnh."},
        {L"toast_autostart_off", L"\u0110\u00E3 t\u1EAFt kh\u1EDFi \u0111\u1ED9ng c\u00F9ng m\u00E1y t\u00EDnh."},
        {L"toast_prtsc_on", L"\u0110\u00E3 b\u1EADt ch\u1EE5p nhanh b\u1EB1ng ph\u00EDm PrtSc."},
        {L"toast_prtsc_off", L"\u0110\u00E3 t\u1EAFt ch\u1EE5p nhanh b\u1EB1ng ph\u00EDm PrtSc."},
        {L"toast_capture_err", L"Kh\u00F4ng th\u1EC3 ch\u1EE5p m\u00E0n h\u00ECnh: {err}"},
        {L"toast_copied_fast", L"\u0110\u00E3 sao ch\u00E9p \u1EA3nh s\u1EAFc n\u00E9t ({w}\u00D7{h} px) v\u00E0o b\u1ED9 nh\u1EDB t\u1EA1m!"},
        {L"toast_copied_draw", L"\u0110\u00E3 sao ch\u00E9p \u1EA3nh ghi ch\u00FA ({w}\u00D7{h} px) v\u00E0o b\u1ED9 nh\u1EDB t\u1EA1m!"},

        {L"settings_autostart_title", L"Kh\u1EDFi \u0111\u1ED9ng c\u00F9ng m\u00E1y t\u00EDnh"},
        {L"settings_prtsc_title", L"B\u1EA5m ph\u00EDm PrtSc \u0111\u1EC3 ch\u1EE5p nhanh (t\u01B0\u01A1ng t\u1EF1 Ctrl + 1)"},
        {L"settings_lang_title", L"Ng\u00F4n ng\u1EEF hi\u1EC3n th\u1ECB (Language)"},
        {L"status_enabled", L"\u2713 \u0110ang b\u1EADt"},
        {L"status_disabled", L"\u0110ang t\u1EAFt"},
        {L"guide_section_title", L"PH\u00CDM T\u1EAET & H\u01AF\u1EDANG D\u1EAAN NHANH"},
        {L"table_col_shortcut", L"PH\u00CDM T\u1EAET"},
        {L"table_col_function", L"CH\u1EE8C N\u0102NG"},
        {L"table_col_desc", L"M\u00D4 T\u1EA2 THAO T\u00C1C"},
        {L"footer_version", L"Phi\u00EAn b\u1EA3n v2.0.0"},
        {L"footer_developer", L"\u0110\u01B0\u1EE3c ph\u00E1t tri\u1EC3n b\u1EDFi KAHUB PLATFORM"},

        {L"overlay_ctrl1_title", L"\u26A1 Ctrl + 1 : K\u00E9o ch\u1ECDn v\u00F9ng \u0111\u1EC3 sao ch\u00E9p \u1EA3nh ngay"},
        {L"overlay_ctrl2_title", L"\xD83C\xDFA8 Ctrl + 2 : K\u00E9o ch\u1ECDn v\u00F9ng \u0111\u1EC3 th\u00EAm ghi ch\u00FA"},
        {L"overlay_banner_hint", L"K\u00E9o chu\u1ED9t ch\u1ECDn v\u00F9ng   \u2022   ESC ho\u1EB7c Chu\u1ED9t ph\u1EA3i \u0111\u1EC3 h\u1EE7y"},

        {L"editor_undo", L"Ho\u00E0n t\u00E1c"},
        {L"editor_redo", L"L\u00E0m l\u1EA1i"},
        {L"editor_clear", L"X\u00F3a h\u1EBFt"},
        {L"editor_color_label", L"M\u00E0u s\u1EAFc:"},
        {L"editor_custom_color", L"M\u00E0u kh\u00E1c"},
        {L"editor_custom_color_title", L"Ch\u1ECDn m\u00E0u n\u00E9t v\u1EBD"},
        {L"editor_size_label", L"\u0110\u1ED9 d\u00E0y:"},
        {L"editor_copy_btn", L"Sao ch\u00E9p (Ctrl+C)"},
        {L"editor_save_btn", L"L\u01B0u \u1EA3nh (Ctrl+S)"},
        {L"editor_close_btn", L"\u0110\u00F3ng (ESC)"},
        {L"editor_save_dialog_title", L"L\u01B0u \u1EA3nh ch\u1EE5p m\u00E0n h\u00ECnh ch\u1EA5t l\u01B0\u1EE3ng cao"},
        {L"editor_status_bar", L"K\u00EDch th\u01B0\u1EDBc: {w}\u00D7{h} px   \u2022   K\u00E9o gi\u1EEF chu\u1ED9t v\u00E0o n\u00E9t \u0111\u00E3 v\u1EBD \u0111\u1EC3 di chuy\u1EC3n v\u1ECB tr\u00ED   \u2022   Delete: X\u00F3a n\u00E9t ch\u1ECDn   |   Ctrl+C: Sao ch\u00E9p \u1EA3nh"}
    };
    return m;
}

const std::unordered_map<std::wstring, std::wstring>& GetEnMap() {
    static const std::unordered_map<std::wstring, std::wstring> m = {
        {L"app_title", L"Capture To Clipboard v2.0.0"},
        {L"tray_tooltip", L"Capture To Clipboard v2.0.0 \u2014 Click to open Settings & Guide"},
        {L"tray_open_settings", L"Settings & Shortcut Guide"},
        {L"tray_autostart", L"Launch at system startup"},
        {L"tray_capture_fast", L"Quick Capture (Ctrl + 1)"},
        {L"tray_capture_draw", L"Capture & Annotate (Ctrl + 2)"},
        {L"tray_exit", L"Quit Application"},

        {L"toast_ready", L"Capture To Clipboard is ready  \u2022  Ctrl+1 / PrtSc: Quick Capture  |  Ctrl+2: Capture & Annotate"},
        {L"toast_minimized_tray", L"Capture To Clipboard minimized to the System Tray."},
        {L"toast_autostart_on", L"Enabled launch at system startup."},
        {L"toast_autostart_off", L"Disabled launch at system startup."},
        {L"toast_prtsc_on", L"Enabled instant capture with PrtSc key."},
        {L"toast_prtsc_off", L"Disabled instant capture with PrtSc key."},
        {L"toast_capture_err", L"Failed to capture screen: {err}"},
        {L"toast_copied_fast", L"Copied HD screenshot ({w}\u00D7{h} px) to Clipboard!"},
        {L"toast_copied_draw", L"Copied annotated image ({w}\u00D7{h} px) to Clipboard!"},

        {L"settings_autostart_title", L"Launch at system startup"},
        {L"settings_prtsc_title", L"Press PrtSc for instant capture (same as Ctrl + 1)"},
        {L"settings_lang_title", L"Display Language (Ng\u00F4n ng\u1EEF)"},
        {L"status_enabled", L"\u2713 Enabled"},
        {L"status_disabled", L"Disabled"},
        {L"guide_section_title", L"KEYBOARD SHORTCUTS & QUICK GUIDE"},
        {L"table_col_shortcut", L"SHORTCUT"},
        {L"table_col_function", L"FUNCTION"},
        {L"table_col_desc", L"ACTION DESCRIPTION"},
        {L"footer_version", L"Version v2.0.0"},
        {L"footer_developer", L"Developed by KAHUB PLATFORM"},

        {L"overlay_ctrl1_title", L"\u26A1 Ctrl + 1 : Drag to select region & copy immediately"},
        {L"overlay_ctrl2_title", L"\xD83C\xDFA8 Ctrl + 2 : Drag to select region & annotate"},
        {L"overlay_banner_hint", L"Drag to select region   \u2022   ESC or Right-click to cancel"},

        {L"editor_undo", L"Undo"},
        {L"editor_redo", L"Redo"},
        {L"editor_clear", L"Clear All"},
        {L"editor_color_label", L"Color:"},
        {L"editor_custom_color", L"Custom"},
        {L"editor_custom_color_title", L"Choose stroke color"},
        {L"editor_size_label", L"Thickness:"},
        {L"editor_copy_btn", L"Copy (Ctrl+C)"},
        {L"editor_save_btn", L"Save (Ctrl+S)"},
        {L"editor_close_btn", L"Close (ESC)"},
        {L"editor_save_dialog_title", L"Save High-Quality Screenshot"},
        {L"editor_status_bar", L"Resolution: {w}\u00D7{h} px   \u2022   Drag any drawn shape to move or resize   \u2022   Delete: Remove selected   |   Ctrl+C: Copy to Clipboard"}
    };
    return m;
}

} // namespace

AppSettings LoadAppSettings() {
    AppSettings s;
    std::string raw = ReadFileBytes(GetSettingsFilePath());
    if (raw.empty()) {
        return s;
    }
    std::string lang = ExtractJsonString(raw, "language", "vi");
    s.language = (lang == "en") ? L"en" : L"vi";
    s.autostart_enabled = ExtractJsonBool(raw, "autostart_enabled", true, &s.has_autostart_key);
    s.prtsc_enabled = ExtractJsonBool(raw, "prtsc_enabled", true);
    return s;
}

bool SaveAppSettings(const AppSettings& s) {
    std::ostringstream oss;
    oss << "{\n"
        << "  \"autostart_enabled\": " << (s.autostart_enabled ? "true" : "false") << ",\n"
        << "  \"prtsc_enabled\": " << (s.prtsc_enabled ? "true" : "false") << ",\n"
        << "  \"language\": \"" << (s.language == L"en" ? "en" : "vi") << "\"\n"
        << "}\n";
    return WriteFileBytes(GetSettingsFilePath(), oss.str());
}

std::wstring GetLanguage() {
    if (g_current_lang == L"vi" || g_current_lang == L"en") {
        return g_current_lang;
    }
    AppSettings s = LoadAppSettings();
    g_current_lang = s.language;
    return g_current_lang;
}

std::pair<bool, std::wstring> SetLanguage(const std::wstring& lang) {
    std::wstring norm = (lang == L"en") ? L"en" : L"vi";
    g_current_lang = norm;
    AppSettings s = LoadAppSettings();
    s.language = norm;
    bool ok = SaveAppSettings(s);
    std::wstring msg = (norm == L"en")
        ? L"Switched language to English."
        : L"\u0110\u00E3 chuy\u1EC3n ng\u00F4n ng\u1EEF sang Ti\u1EBFng Vi\u1EC7t.";
    return {ok, msg};
}

std::wstring Tr(const std::wstring& key) {
    const auto& primary = (GetLanguage() == L"en") ? GetEnMap() : GetViMap();
    auto it = primary.find(key);
    if (it != primary.end()) return it->second;
    const auto& fallback = GetViMap();
    auto it2 = fallback.find(key);
    if (it2 != fallback.end()) return it2->second;
    return key;
}

std::wstring TrFmtInt2(const std::wstring& key, int w, int h) {
    std::wstring s = Tr(key);
    auto replace_token = [&](const std::wstring& token, const std::wstring& val) {
        size_t pos = 0;
        while ((pos = s.find(token, pos)) != std::wstring::npos) {
            s.replace(pos, token.size(), val);
            pos += val.size();
        }
    };
    replace_token(L"{w}", std::to_wstring(w));
    replace_token(L"{h}", std::to_wstring(h));
    return s;
}

std::wstring TrFmtErr(const std::wstring& key, const std::wstring& err) {
    std::wstring s = Tr(key);
    size_t pos = s.find(L"{err}");
    if (pos != std::wstring::npos) {
        s.replace(pos, 5, err);
    }
    return s;
}

const std::vector<ShortcutGuideRow>& GetShortcutsGuide() {
    static const std::vector<ShortcutGuideRow> vi_rows = {
        {L"Ctrl + 1 / PrtSc", L"#0284c7", L"#e0f2fe", L"Ch\u1EE5p & Sao ch\u00E9p ngay", L"K\u00E9o ch\u1ECDn v\u00F9ng m\u00E0n h\u00ECnh \u0111\u1EC3 l\u01B0u ngay \u1EA3nh n\u00E9t cao v\u00E0o b\u1ED9 nh\u1EDB t\u1EA1m (nh\u1EA5n Ctrl + V \u0111\u1EC3 d\u00E1n)."},
        {L"Ctrl + 2", L"#7c3aed", L"#f3e8ff", L"Ch\u1EE5p & Ghi ch\u00FA tr\u00EAn \u1EA3nh", L"K\u00E9o ch\u1ECDn v\u00F9ng m\u00E0n h\u00ECnh v\u00E0 m\u1EDF b\u1EA3ng v\u1EBD M\u0169i t\u00EAn, Khung, Ch\u1EEF, B\u00FAt d\u1EA1 quang, L\u00E0m m\u1EDD..."},
        {L"K\u00E9o gi\u1EEF chu\u1ED9t", L"#d97706", L"#fef3c7", L"Di chuy\u1EC3n n\u00E9t \u0111\u00E3 v\u1EBD", L"Nh\u1EA5n gi\u1EEF v\u00E0o m\u0169i t\u00EAn, ch\u1EEF ho\u1EB7c khung \u0111\u00E3 v\u1EBD \u0111\u1EC3 d\u1EDDi v\u1ECB tr\u00ED ho\u1EB7c ch\u1EC9nh l\u1EA1i h\u01B0\u1EDBng."},
        {L"Nh\u1EA5p \u0111\u00FAp chu\u1ED9t", L"#db2777", L"#fce7f3", L"S\u1EEDa n\u1ED9i dung ch\u1EEF", L"Nh\u1EA5p \u0111\u00FAp chu\u1ED9t tr\u00E1i v\u00E0o ch\u1EEF \u0111\u00E3 th\u00EAm tr\u00EAn \u1EA3nh \u0111\u1EC3 ch\u1EC9nh s\u1EEDa l\u1EA1i n\u1ED9i dung."},
        {L"Ctrl + C", L"#059669", L"#d1fae5", L"Ho\u00E0n t\u1EA5t & Sao ch\u00E9p", L"Sao ch\u00E9p \u1EA3nh \u0111\u00E3 ghi ch\u00FA v\u00E0o b\u1ED9 nh\u1EDB t\u1EA1m v\u00E0 \u0111\u00F3ng c\u1EEDa s\u1ED5 v\u1EBD."},
        {L"Ctrl + S", L"#0369a1", L"#e0f2fe", L"L\u01B0u th\u00E0nh file \u1EA3nh", L"L\u01B0u \u1EA3nh v\u1EC1 m\u00E1y t\u00EDnh v\u1EDBi \u0111\u1ECBnh d\u1EA1ng PNG, JPG ho\u1EB7c WebP ch\u1EA5t l\u01B0\u1EE3ng cao."},
        {L"Ctrl + Z / Delete", L"#475569", L"#e2e8f0", L"Ho\u00E0n t\u00E1c / X\u00F3a n\u00E9t v\u1EBD", L"Nh\u1EA5n Ctrl + Z \u0111\u1EC3 quay l\u1EA1i b\u01B0\u1EDBc tr\u01B0\u1EDBc, ho\u1EB7c nh\u1EA5n Delete \u0111\u1EC3 x\u00F3a n\u00E9t \u0111ang ch\u1ECDn."},
        {L"ESC / Chu\u1ED9t ph\u1EA3i", L"#dc2626", L"#fee2e2", L"H\u1EE7y thao t\u00E1c", L"Tho\u00E1t nhanh m\u00E0n h\u00ECnh ch\u1ECDn v\u00F9ng ch\u1EE5p ho\u1EB7c \u0111\u00F3ng c\u1EEDa s\u1ED5 hi\u1EC7n t\u1EA1i."}
    };

    static const std::vector<ShortcutGuideRow> en_rows = {
        {L"Ctrl + 1 / PrtSc", L"#0284c7", L"#e0f2fe", L"Instant Capture & Copy", L"Drag to select a screen region and immediately copy HD image to Clipboard (Ctrl + V to paste)."},
        {L"Ctrl + 2", L"#7c3aed", L"#f3e8ff", L"Capture & Annotate", L"Drag to select a region and open the editor with Arrow, Rectangle, Text, Highlighter, Blur..."},
        {L"Click & Drag", L"#d97706", L"#fef3c7", L"Move / Resize Shapes", L"Click and drag any drawn arrow, text, or box to reposition or adjust its control handles."},
        {L"Double-Click", L"#db2777", L"#fce7f3", L"Edit Text Content", L"Double-click on any added text annotation on the canvas to edit its content."},
        {L"Ctrl + C", L"#059669", L"#d1fae5", L"Finish & Copy Image", L"Copy the annotated image to the Clipboard and close the editor window."},
        {L"Ctrl + S", L"#0369a1", L"#e0f2fe", L"Save Image to File", L"Export the annotated screenshot as high-resolution PNG, JPG, or WebP."},
        {L"Ctrl + Z / Delete", L"#475569", L"#e2e8f0", L"Undo / Delete Shape", L"Press Ctrl + Z to undo the previous step, or press Delete to remove the selected shape."},
        {L"ESC / Right-Click", L"#dc2626", L"#fee2e2", L"Cancel Action", L"Quickly exit the region selection overlay or close the current window."}
    };

    return (GetLanguage() == L"en") ? en_rows : vi_rows;
}

const std::vector<EditorToolDef>& GetEditorTools() {
    static const std::vector<EditorToolDef> vi_tools = {
        {L"arrow", L"M\u0169i t\u00EAn"},
        {L"pen", L"B\u00FAt v\u1EBD"},
        {L"highlighter", L"D\u1EA1 quang"},
        {L"rect", L"Khung"},
        {L"ellipse", L"Elip"},
        {L"line", L"\u0110\u01B0\u1EDDng th\u1EB3ng"},
        {L"text", L"Ch\u00E8n ch\u1EEF"},
        {L"pixelate", L"L\u00E0m m\u1EDD"}
    };
    static const std::vector<EditorToolDef> en_tools = {
        {L"arrow", L"Arrow"},
        {L"pen", L"Pen"},
        {L"highlighter", L"Highlight"},
        {L"rect", L"Box"},
        {L"ellipse", L"Ellipse"},
        {L"line", L"Line"},
        {L"text", L"Text"},
        {L"pixelate", L"Blur"}
    };
    return (GetLanguage() == L"en") ? en_tools : vi_tools;
}

const std::vector<EditorSizeDef>& GetEditorSizes() {
    static const std::vector<EditorSizeDef> vi_sizes = {
        {3, L"Nh\u1ECF", 3},
        {5, L"V\u1EEBa", 5},
        {9, L"L\u1EDBn", 7},
        {14, L"R\u1EA5t l\u1EDBn", 9}
    };
    static const std::vector<EditorSizeDef> en_sizes = {
        {3, L"Small", 3},
        {5, L"Medium", 5},
        {9, L"Large", 7},
        {14, L"X-Large", 9}
    };
    return (GetLanguage() == L"en") ? en_sizes : vi_sizes;
}

} // namespace app
