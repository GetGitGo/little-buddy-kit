#include "audio.h"
#include <Arduino.h>
#include <M5Unified.h>

static volatile bool s_chimePending = false;
static volatile AudioChime s_chimeKind = AUDIO_CHIME_BEEP;

void audioBegin(void) {
  M5.Speaker.begin();
  M5.Speaker.setVolume(96);
}

void audioRequestChime(AudioChime kind) {
  s_chimeKind = kind;
  s_chimePending = true;
}

void audioPoll(void) {
  if (!s_chimePending)
    return;
  s_chimePending = false;

  if (!M5.Speaker.isEnabled())
    return;

  constexpr int kCh = 0;
  auto waitMs = [](uint32_t ms) {
    const uint32_t until = millis() + ms;
    while ((int32_t)(until - millis()) > 0) {
      M5.update();
      delay(2);
    }
  };

  const AudioChime kind = s_chimeKind;
  if (kind == AUDIO_CHIME_DINGDONG) {
    M5.Speaker.tone(880.0f, 120, kCh, true);
    waitMs(130);
    M5.Speaker.tone(659.25f, 140, kCh, true);
    waitMs(150);
    return;
  }

  /* 单音短促「滴」 */
  M5.Speaker.tone(1200.0f, 70, kCh, true);
  waitMs(80);
}
