#pragma once
#include "common.h"

namespace app {

bool IsAutostartEnabled();
std::pair<bool, std::wstring> SetAutostartEnabled(bool enabled);
void SyncAutostartOnStartup();

bool IsPrtScEnabled();
std::pair<bool, std::wstring> SetPrtScEnabled(bool enabled);

} // namespace app
