#pragma once

#include <stdint.h>

enum AudioChime : uint8_t {
  AUDIO_CHIME_BEEP = 0,     /* 短促「滴」 */
  AUDIO_CHIME_DINGDONG = 1, /* 「叮咚」 */
};

void audioBegin(void);

/** 收到有效 msg 时排队播放（在 loop 里执行，不阻塞 BLE） */
void audioRequestChime(AudioChime kind);

void audioPoll(void);
