#!/usr/bin/env python3
"""从 Twemoji (GitHub) 生成 40×40 RGB565 位图，写入 src/emoji_bitmaps.h"""

from __future__ import annotations

import re
import sys
import urllib.request
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow: pip install pillow")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "emoji_bitmaps.h"
TWEMOJI_BASE = (
    "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72"
)

W = H = 40
KEY = 0xF81F

# (name, codepoint hex without 0x, fe0f optional)
EMOJIS: list[tuple[str, str]] = [
    # 原有 10
    ("rocket", "1f680"),
    ("fire", "1f525"),
    ("check", "2705"),
    ("cross", "274c"),
    ("warn", "26a0"),
    ("computer", "1f4bb"),
    ("bug", "1f41b"),
    ("coffee", "2615"),
    ("thumbsup", "1f44d"),
    ("eyes", "1f440"),
    # 新增 20 — 程序员常用
    ("gear", "2699"),
    ("hammer", "1f528"),
    ("wrench", "1f527"),
    ("package", "1f4e6"),
    ("merge", "1f500"),
    ("branch", "1f33f"),
    ("lock", "1f512"),
    ("passkey", "1f511"),
    ("shield", "1f6e1"),
    ("zap", "26a1"),
    ("hourglass", "23f3"),
    ("stop", "1f6d1"),
    ("recycle", "267b"),
    ("memo", "1f4dd"),
    ("link", "1f517"),
    ("save", "1f4be"),
    ("robot", "1f916"),
    ("chartup", "1f4c8"),
    ("chartdown", "1f4c9"),
    ("target", "1f3af"),
    # 第二批 +20 — 程序员常用
    ("clipboard", "1f4cb"),
    ("bell", "1f514"),
    ("calendar", "1f4c5"),
    ("alarm", "23f0"),
    ("timer", "23f1"),
    ("inbox", "1f4e5"),
    ("outbox", "1f4e4"),
    ("email", "1f4e7"),
    ("phone", "1f4f1"),
    ("globe", "1f310"),
    ("cloud", "2601"),
    ("storage", "1f5c4"),
    ("testtube", "1f9ea"),
    ("microscope", "1f52c"),
    ("megaphone", "1f4e3"),
    ("wip", "1f6a7"),
    ("party", "1f389"),
    ("siren", "1f6a8"),
    ("sparkles", "2728"),
    ("search", "1f50d"),
    # Cursor / Claude Code 状态 +20
    ("brain", "1f9e0"),
    ("thought", "1f4ad"),
    ("bulb", "1f4a1"),
    ("wand", "1fa84"),
    ("plug", "1f50c"),
    ("pause", "23f8"),
    ("retry", "1f504"),
    ("blocked", "1f6ab"),
    ("pin", "1f4cc"),
    ("book", "1f4d6"),
    ("puzzle", "1f9e9"),
    ("crystal", "1f52e"),
    ("agent", "1f575"),
    ("stream", "1f4e1"),
    ("chat", "1f4ac"),
    ("notebook", "1f4d3"),
    ("trophy", "1f3c6"),
    ("broom", "1f9f9"),
    ("pencil", "270f"),
    ("scroll", "1f4dc"),
]


def rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def fetch_png(hex_cp: str) -> Image.Image:
    variants = [hex_cp, f"{hex_cp}-fe0f"]
    last_err: Exception | None = None
    for name in variants:
        url = f"{TWEMOJI_BASE}/{name}.png"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return Image.open(BytesIO(resp.read())).convert("RGBA")
        except Exception as e:
            last_err = e
    raise RuntimeError(f"无法下载 {hex_cp}: {last_err}")


def to_bitmap(img: Image.Image) -> list[int]:
    img = img.resize((W, H), Image.Resampling.LANCZOS)
    px = img.load()
    out: list[int] = []
    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            if a < 32:
                out.append(KEY)
            else:
                out.append(rgb565(r, g, b))
    return out


def fmt_array(name: str, data: list[int]) -> str:
    lines = [f"static const uint16_t kEmoji_{name}[{W * H}] PROGMEM = {{"]
    row: list[str] = []
    for i, v in enumerate(data):
        row.append(f"0x{v:04X}")
        if len(row) == 10:
            lines.append("  " + ", ".join(row) + ",")
            row = []
    if row:
        lines.append("  " + ", ".join(row) + ",")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("};")
    return "\n".join(lines)


def main() -> None:
    enum_parts = ["EMOJI_NONE = -1"]
    arrays: list[str] = []
    table: list[str] = []

    for i, (name, cp) in enumerate(EMOJIS):
        print(f"[{i+1}/{len(EMOJIS)}] {name} ({cp})…")
        img = fetch_png(cp)
        data = to_bitmap(img)
        arrays.append(fmt_array(name, data))
        enum_parts.append(f"EMOJI_{name.upper()}={i}")
        table.append(f'  {{"{name}", kEmoji_{name}}},')

    enum_line = ", ".join(enum_parts) + ", EMOJI_COUNT"

    body = f"""#pragma once
#include <Arduino.h>
#include <stdint.h>

#define EMOJI_W {W}
#define EMOJI_H {H}
#define EMOJI_DRAW_W EMOJI_W
#define EMOJI_DRAW_H EMOJI_H
#define EMOJI_KEY 0x{KEY:04X}

struct EmojiBmp {{ const char* name; const uint16_t* data; }};
enum EmojiId : int8_t {{ {enum_line} }};

int8_t emojiIdFromName(const char *name);
void emojiDraw(int x, int y, int8_t id);

"""
    body += "\n\n".join(arrays)
    body += "\n\nstatic const EmojiBmp kEmojiTable[] = {\n"
    body += "\n".join(table)
    body += "\n  {nullptr, nullptr}};\n"

    OUT.write_text(body, encoding="utf-8")
    print(f"Wrote {OUT} ({len(EMOJIS)} emojis, ~{len(EMOJIS)*W*H*2//1024} KiB bitmap)")


if __name__ == "__main__":
    main()
