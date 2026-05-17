#pragma once

#include <stddef.h>
#include <stdint.h>

// Nordic UART Service (same transport as claude-desktop-buddy)
void bleInit(const char *deviceName);
bool bleConnected();
size_t bleAvailable();
int bleRead();
