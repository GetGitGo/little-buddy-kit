#pragma once

void audioBegin(void);

/** 收到有效 msg 时排队播放「叮咚」（在 loop 里执行，不阻塞 BLE） */
void audioRequestChime(void);

/** 在 loop 中调用 */
void audioPoll(void);
