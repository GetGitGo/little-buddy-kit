# talk2littlebuddy

通过 BLE 向 **little-buddy** 固件发显示数据。`talk.py` / `scan.py` / `little_ble.py` 为纯 Python，**Windows / macOS / Linux 用法相同**（依赖 [bleak](https://github.com/hbldh/bleak) 调用本机蓝牙）。

## 环境

- Python 3.10+
- 电脑自带蓝牙，系统已打开蓝牙
- Windows：建议 Windows 10/11，需允许 Python 使用蓝牙

```bash
cd talk2littlebuddy
pip install -r requirements.txt
```

## 用法（各平台相同）

```bash
python scan.py              # 扫描设备
python talk.py              # 演示（默认 size=6，直连缓存地址）
python talk.py --scan       # 强制重新扫描
python talk.py --msg "上线" --emoji rocket --color green
python talk.py --list-emoji
```

首次成功连接后会在本目录生成 `.last_device`（记录地址），下次默认**不扫描、直接连**。

## 与 macOS 的差异（仅系统层）

| 项目 | 说明 |
|------|------|
| Python 代码 | 无区别 |
| 设备地址 | Windows 也可能显示为 UUID 字符串，bleak 均支持 |
| 配对失败 | 到系统蓝牙设置里**删除/忽略**该设备后重试 |
| 缓存文件 | `.last_device` 在 `talk2littlebuddy` 目录下，路径由 `pathlib` 处理 |

Windows 删除配对：**设置 → 蓝牙和其他设备 → 设备 → 删除设备**。

## 协议摘要

```json
{"msg":"文案","emoji":"rocket","size":6,"color":"green","gap":6}
```

`color` 仅 `green` / `yellow` / `red`。无 `bg`（屏固定黑底）。

**70 个 emoji**（Twemoji 位图，含 Cursor/Claude Code 状态）。`python talk.py --list-emoji` 列出全部；默认演示轮播约 2 分钟。
