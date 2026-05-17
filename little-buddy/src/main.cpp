#include "audio.h"
#include "ble_bridge.h"
#include "display.h"
#include "protocol.h"
#include <Arduino.h>
#include <M5Unified.h>
#include <esp_mac.h>

static char btName[16] = "Little";

static void startBle(void) {
  uint8_t mac[6] = {0};
  esp_read_mac(mac, ESP_MAC_BT);
  snprintf(btName, sizeof(btName), "Little-%02X%02X", mac[4], mac[5]);
  bleInit(btName);
}

static void pollBleLines(void) {
  static char line[512];
  static uint16_t len = 0;

  while (bleAvailable()) {
    int c = bleRead();
    if (c < 0)
      break;
    if (c == '\n' || c == '\r') {
      if (len > 0) {
        line[len] = '\0';
        protocolHandleLine(line);
        len = 0;
      }
      continue;
    }
    if (len < sizeof(line) - 1)
      line[len++] = (char)c;
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== Little Buddy ===");

  displayBegin();
  audioBegin();
  startBle();
}

void loop() {
  static bool wasConnected = false;
  const bool now = bleConnected();

  if (now && !wasConnected) {
    const char *one[] = {"已连接"};
    displayLines(one, 1, {5, TFT_GREEN, TFT_BLACK, 0}, "link");
  }
  if (!now && wasConnected)
    displayWaiting();

  wasConnected = now;
  pollBleLines();
  audioPoll();
  M5.update();
  delay(5);
}
