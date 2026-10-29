cmake_minimum_required(VERSION 3.16)
project(CaptureToClipboard VERSION 2.0.0 LANGUAGES CXX RC)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options(/W3 /O2 /EHsc /utf-8)
endif()

set(SOURCES
    src/main.cpp
    src/i18n.cpp
    src/autostart.cpp
    src/platform_utils.cpp
    src/toast.cpp
    src/hotkeys.cpp
    src/tray.cpp
    src/overlay.cpp
    src/settings_window.cpp
    src/editor.cpp
    src/app.rc
)

add_executable(CaptureToClipboard WIN32 ${SOURCES})

target_include_directories(CaptureToClipboard PRIVATE src)

target_link_libraries(CaptureToClipboard PRIVATE
    user32
    gdi32
    gdiplus
    shell32
    advapi32
    comdlg32
    ole32
    shlwapi
)

set_target_properties(CaptureToClipboard PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/dist"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/dist"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_SOURCE_DIR}/dist"
)

add_custom_command(TARGET CaptureToClipboard POST_BUILD
    COMMAND powershell -NoProfile -ExecutionPolicy Bypass -File "${CMAKE_SOURCE_DIR}/sign_and_trust.ps1"
    COMMENT "Signing CaptureToClipboard.exe with Authenticode digital signature..."
)

