# Little Buddy

M5Stick S3 固件：Nordic **NUS** BLE + 黑底屏显 + 收到有效文案时短促提示音。

完整主机侧安装见仓库根目录 [`install.md`](../install.md)。

## 烧录

```bash
cd little-buddy
pio run -t upload
pio device monitor -b 115200   # 可选
```

异常或仍是旧程序：

```bash
pio run -t erase && pio run -t upload
```

环境：`platformio.ini` → `m5stack-sticks3`（ESP32-S3，`M5Unified` + `M5GFX` + `ArduinoJson`）。

## 上电与 BLE

| 状态 | 屏幕 |
|------|------|
| 等待连接 | 居中「等待连接 .oO.oO」（字号 3） |
| 已连接 | 「已连接」+ `link` emoji（`size=5`），随后可被业务 JSON 覆盖 |
| 断开 | 回到等待连接 |

- 蓝牙广播名：`Little-XXXX`（BT MAC 后两字节，见 `main.cpp`）
- 服务：NUS `6e400001-…`，RX 写 `6e400002-…`（主机下发 JSON 行）
- 广播 Manufacturer Data：`0xFFFF` + `LB01`（供主机识别，见 `ble_bridge.cpp`）
- 启动时清除 NVS 旧绑定，降低 macOS `CBError 14` 概率

## 应用层协议

一行一条 JSON（`\n` / `\r` 结束），必须以 `{` 开头且含非空 `msg`。

```json
{"msg":"部署成功","emoji":"rocket","size":4,"color":"green","gap":6,"datetime":"2026-5-17 10:06"}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `msg` | 是 | UTF-8；`\n` 最多拆 **8** 行；主机侧建议 ≤7 个汉字 |
| `emoji` | 否 | 英文名称 → 左侧 **40×40** Twemoji 位图 |
| `size` | 否 | `1`–`6`：1–4 用 efont；5–6 在 24 号字上放大（与 emoji 对齐）。省略时固件默认 `2`，并 **`pickMsgFontSize` 按屏宽/高度自动缩小** |
| `color` | 否 | 字符串：`green` / `yellow` / `red` / `blue` / `black` / `white`，或 `#RGB` / `#RRGGBB`；也可为 RGB565 整数。省略时字色 **白色** |
| `gap` | 否 | 多行行距（像素），默认 `6`，固件上限 `24` |
| `datetime` | 否 | 底行时间戳；贴底 **白色**小字（`pickStampFontSize`，最大约 size 5）。省略则不画 |

背景 **`bg` 固定黑色**，JSON 不支持改背景。

有效 `msg` 解析成功后播放提示音（`audio.cpp`）：默认短促「滴」；`msg` 为 `done` 或 `任务圆满完成` 时为「叮咚」。

## emoji（70 个）

`python talk.py --list-emoji`（在 `talk2littlebuddy/`）列出全部。  
含通用约 50 + Cursor/Agent 相关 20：`brain` `thought` `bulb` `wand` `plug` `pause` `retry` `blocked` `pin` `book` `puzzle` `crystal` `agent` `stream` `chat` `notebook` `trophy` `broom` `pencil` `scroll` 等（见 `emoji_bitmaps.h` / `kEmojiTable`）。

位图来源：[Twemoji](https://github.com/twitter/twemoji)。重新生成后需重烧：

```bash
pip install pillow
python tools/gen_emoji_bitmaps.py
pio run -t upload
```

## 主机测试

```bash
# daemon 未占用 BLE 时
cd ../talk2littlebuddy && python talk.py --msg "测试" --emoji brain --size 4

# daemon 已连接时（推荐）
export LITTLEBUDDY_MCP_DIR=/path/to/myesp/.littlebuddy-mcp
python talk2bledaemon.py --msg "测试" --emoji brain
```
