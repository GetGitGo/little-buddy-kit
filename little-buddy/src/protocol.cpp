#include "protocol.h"
#include "audio.h"
#include "display.h"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <M5Unified.h>
#include <string.h>

static constexpr uint8_t kMaxLines = 8;
static constexpr size_t kMsgBuf = 480;
static char msgBuf[kMsgBuf];

static uint16_t colorFromJson(JsonVariantConst v, uint16_t def) {
  if (v.isNull())
    return def;
  if (v.is<int>())
    return (uint16_t)v.as<int>();
  if (v.is<const char *>())
    return displayParseColor(v.as<const char *>(), def);
  return def;
}

static DisplayStyle styleFromDoc(JsonDocument &doc) {
  DisplayStyle st = {2, TFT_WHITE, TFT_BLACK, 6};
  if (!doc["size"].isNull())
    st.size = (uint8_t)doc["size"].as<int>();
  st.fg = colorFromJson(doc["color"], TFT_WHITE);
  st.bg = TFT_BLACK;
  if (!doc["gap"].isNull())
    st.gap = (uint8_t)doc["gap"].as<int>();
  return st;
}

static uint8_t splitMsg(const char *msg, const char *linePtrs[]) {
  strncpy(msgBuf, msg, kMsgBuf - 1);
  msgBuf[kMsgBuf - 1] = '\0';

  uint8_t n = 0;
  char *p = msgBuf;
  while (n < kMaxLines) {
    linePtrs[n++] = p;
    char *nl = strchr(p, '\n');
    if (!nl)
      break;
    *nl = '\0';
    p = nl + 1;
  }
  return n;
}

/** done 状态：英文 id 或 MCP 预设「任务圆满完成」→ 叮咚 */
static bool isDoneMsg(const char *msg) {
  if (!msg)
    return false;
  return strcmp(msg, "done") == 0 || strcmp(msg, "任务圆满完成") == 0;
}

bool protocolHandleLine(const char *line) {
  if (!line || line[0] != '{')
    return false;

  JsonDocument doc;
  if (deserializeJson(doc, line)) {
    Serial.println("[proto] json err");
    return false;
  }

  const char *msg = doc["msg"];
  if (!msg || !msg[0]) {
    Serial.println("[proto] missing msg");
    return false;
  }

  const char *linePtrs[kMaxLines];
  uint8_t n = splitMsg(msg, linePtrs);
  if (n == 0)
    return false;

  const char *emoji = doc["emoji"];
  const char *stamp = doc["datetime"];
  DisplayStyle st = styleFromDoc(doc);
  displayLines(linePtrs, n, st, emoji, stamp);
  audioRequestChime(isDoneMsg(msg) ? AUDIO_CHIME_DINGDONG : AUDIO_CHIME_BEEP);

  if (emoji && emoji[0])
    Serial.printf("[show] emoji=%s ", emoji);
  Serial.printf("size=%u gap=%u lines=%u", st.size, st.gap, n);
  if (stamp && stamp[0])
    Serial.printf(" datetime=%s", stamp);
  Serial.println();
  for (uint8_t i = 0; i < n; i++)
    Serial.printf("  %u: %s\n", i + 1, linePtrs[i]);
  return true;
}
