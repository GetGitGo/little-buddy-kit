# Little Buddy 安装与使用

M5StickS3 状态屏：**固件**（little-buddy）+ **主机工具**（talk2littlebuddy、littlebuddy-mcp-server）。  
推荐日常路径：**daemon 持有一条 BLE 连接**，Cursor hook / MCP / `talk2bledaemon.py` 经 Unix socket 发显示；仅调试时再用 `talk.py` 直连。

```
┌─────────────┐     BLE (单连接)      ┌──────────────┐
│  Mac / PC   │◄────────────────────►│ M5StickS3    │
│  daemon     │   NUS JSON 行协议     │ little-buddy │
└──────┬──────┘                       └──────────────┘
       │ Unix socket
       ├── Cursor hooks (自动状态)
       ├── MCP littlebuddy-mcp
       └── talk2bledaemon.py (手动测试)
```

---

## 前置条件

| 项目 | 说明 |
|------|------|
| 硬件 | M5StickS3（已刷 little-buddy 固件） |
| 电脑蓝牙 | 已开启；Windows 需允许 Python 使用蓝牙 |
| Python | 3.10+（建议 pyenv / 系统 Python 一致） |
| 烧录（仅改固件时） | [PlatformIO](https://platformio.org/)（`pio` 命令可用） |

---

## 1. little-buddy（固件烧录与屏显协议）

### 1.1 烧录

```bash
cd little-buddy
pio run -t upload
```

串口监视（可选）：

```bash
pio device monitor -b 115200
```

若异常或仍是旧程序，可全片擦除后重烧：

```bash
pio run -t erase && pio run -t upload
```

### 1.2 上电表现

| 状态 | 屏幕 |
|------|------|
| 等待连接 | 居中「等待连接 .oO.oO」 |
| BLE 已连接 | 「已连接」+ `link` emoji（随后可被业务文案覆盖） |
| 收到 JSON | 主文案 + 可选 emoji + 底行时间 |

蓝牙名形如 `Little-XXXX`（MAC 后两字节）。

### 1.3 主机下发的 JSON（一行一条）

```json
{"msg":"正在调用工具","emoji":"plug","size":4,"color":"green","gap":6,"datetime":"2026-5-17 10:06"}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `msg` | 是 | UTF-8；`\n` 可多行；主机侧建议 ≤7 个汉字 |
| `emoji` | 否 | 70 个英文名，左侧 40×40 位图（见 `talk.py --list-emoji`） |
| `size` | 否 | `1`–`6`；MCP/hook 默认 `4`，固件会按屏宽自动缩小 |
| `color` | 否 | `green` / `yellow` / `red`（字色；底固定黑） |
| `gap` | 否 | 行距像素，默认 `6` |
| `datetime` | 否 | 本地时间；省略时主机常自动补；屏上贴底白字 |

收到有效 `msg` 时播放提示音：默认「滴」；`msg` 为 `done` 或 `任务圆满完成` 时为「叮咚」。

### 1.4 修改 emoji 位图后重烧

```bash
pip install pillow
python tools/gen_emoji_bitmaps.py
pio run -t upload
```

---

## 2. talk2littlebuddy（主机 Python 工具）

目录：`talk2littlebuddy/`。与 MCP **相互独立**的 BLE 缓存（`.last_device`），与 daemon 的 `.littlebuddy-mcp/last_device` 不是同一路径。

### 2.1 安装依赖

```bash
cd talk2littlebuddy
pip install -r requirements.txt
```

使用 `talk2bledaemon.py` 时还需安装 MCP 包（见第 3 节）：

```bash
cd ../littlebuddy-mcp-server
pip install -e .
```

### 2.2 talk.py — 直连 BLE

**daemon 未运行时**用；若 daemon 已连接 M5，直连常会 `Device was not found`（从机通常只接受一条 Central 连接）。

```bash
python scan.py                    # 扫描
python talk.py --scan             # 演示轮播（强制扫描）
python talk.py --msg "测试文案" --emoji brain --color green --size 4
python talk.py --list-emoji
```

首次成功会在本目录生成 `.last_device`，之后默认**探测缓存可连则用缓存**，否则扫描；多台 little-buddy 时选 **RSSI 最强**（与 daemon 策略一致，见 `little_ble.py`）。

配对失败（含 macOS `CBError 14`）：系统蓝牙里**忽略/删除**该设备 → M5 重新上电 → 再试。

### 2.3 talk2bledaemon.py — 经 daemon（推荐自测）

**daemon 运行中**时使用，与 Cursor 共用同一条 BLE，不抢连接。

```bash
export LITTLEBUDDY_MCP_DIR=/path/to/little-buddy-kit/.littlebuddy-mcp   # 与 mcp.json 一致
littlebuddy-service start   # 若未运行

cd talk2littlebuddy
python talk2bledaemon.py --msg "一二三四五六七" --emoji brain
python talk2bledaemon.py --status thinking
python talk2bledaemon.py --demo
python talk2bledaemon.py --ping
python talk2bledaemon.py --list-statuses
python talk2bledaemon.py --reconnect
python talk2bledaemon.py --reconnect --scan
python talk2bledaemon.py --reconnect --address <MAC>
```

### 2.4 选型对照

| 脚本 | 连接方式 | daemon 开着时 |
|------|----------|----------------|
| `talk.py` | 本进程直连 BLE | 通常不可用 |
| `talk2bledaemon.py` | Unix socket → daemon | 可用 |

---

## 3. littlebuddy-mcp-server（MCP + 常驻 daemon）

目录：`littlebuddy-mcp-server/`。

### 3.1 安装

```bash
cd littlebuddy-mcp-server
pip install -e .
```

安装后可用命令：

| 命令 | 作用 |
|------|------|
| `littlebuddy-mcp` | Cursor MCP（stdio） |
| `littlebuddy-daemon` | BLE 守护进程（一般由 service/MCP 拉起） |
| `littlebuddy-service` | `start` / `stop` / `restart` / `status` |

### 3.2 运行时目录

通过环境变量 **`LITTLEBUDDY_MCP_DIR`** 指定（建议在项目内固定路径）：

```
$LITTLEBUDDY_MCP_DIR/
  daemon.sock      # Unix socket（JSON 行协议，非 HTTP）
  daemon.pid
  daemon.log       # daemon 主日志
  daemon.stdout    # 子进程标准输出
  last_device      # daemon 用的 BLE 缓存
  hook.log         # Cursor hook 调试日志（若启用 hooks）
```

示例（`little-buddy-kit` 仓库）：

```bash
export LITTLEBUDDY_MCP_DIR=/Users/you/little-buddy-kit/.littlebuddy-mcp
mkdir -p "$LITTLEBUDDY_MCP_DIR"
```

### 3.3 手动管理 daemon

```bash
littlebuddy-service start                    # 结束旧进程 → 连 M5 → 监听 socket
littlebuddy-service start --scan             # 启动时强制 BLE 扫描
littlebuddy-service start --address <MAC>    # 指定设备地址
littlebuddy-service status
littlebuddy-service restart                  # 改 daemon 代码或协议后常用
littlebuddy-service restart --scan --address <MAC>
littlebuddy-service stop
tail -f "$LITTLEBUDDY_MCP_DIR/daemon.log"
```

**BLE 选机**（`littlebuddy_mcp/ble.py`，与 `talk2littlebuddy/little_ble.py` 同策略）：

1. `last_device` 存在且短时探测可连 → 用缓存  
2. 否则扫描 → 仅一台用该台；多台 → **RSSI 最强**  
3. `--address` / `--scan` 见上表  

首次找不到设备：在 `mcp.json` 设 `LITTLEBUDDY_START_SCAN=1`，或 `littlebuddy-service start --scan`。

### 3.4 Cursor MCP 配置

编辑 `little-buddy-kit/.cursor/mcp.json`（路径按本机 Python 修改）：

```json
{
  "mcpServers": {
    "littlebuddy": {
      "command": "/path/to/python3.10/bin/littlebuddy-mcp",
      "args": [],
      "env": {
        "LITTLEBUDDY_MCP_DIR": "/path/to/little-buddy-kit/.littlebuddy-mcp"
      }
    }
  }
}
```

| 环境变量 | 默认 | 说明 |
|----------|------|------|
| `LITTLEBUDDY_MCP_DIR` | `~/.littlebuddy-mcp` | socket / 日志目录 |
| `LITTLEBUDDY_AUTO_START` | `1` | MCP 启动时后台拉起 daemon |
| `LITTLEBUDDY_START_SCAN` | `0` | `1` / `true` / `yes` = **MCP 首次拉起 daemon** 时带 `--scan` |

首次连接困难时可在 `env` 中加 `"LITTLEBUDDY_START_SCAN": "1"`。

改完 `mcp.json` 后在 Cursor **Settings → MCP** 重载 littlebuddy。

### 3.5 MCP 工具

| 工具 | 说明 |
|------|------|
| `littlebuddy_show_status` | 预设状态（约 **70** 条，`statuses.py`）；可选 `msg` 覆盖；固定 `size=4`、`gap=6` |
| `littlebuddy_show` | 自定义 `msg` + 可选 `emoji` / `color` / `size`（默认 `size=4`） |
| `littlebuddy_list_statuses` | 列出预设（**不走** BLE / daemon） |

**fire-and-forget**：MCP 写 socket 即返回 `{"ok":true,"queued":true}`，**不等待**屏上是否显示成功。daemon 对 `op=show` **无回包**（异步 BLE 发送）。

约束（`protocol.py`）：`msg` 最多 **7 个汉字**；`gap` / `datetime` 由 daemon 侧 `make_payload` 补全（默认 `gap=6`、自动本地时间）。

换 BLE 设备：**不要**指望 MCP show 工具传地址；用 `littlebuddy-service restart --address <MAC>` 或 `talk2bledaemon.py --reconnect`。

### 3.5.1 Socket 协议（daemon）

| `op` | 说明 |
|------|------|
| `show` | 一行 JSON（含 `msg` 等）；**无响应** |
| `ping` / `status` | 查询连接状态 |
| `reconnect` | 重连 BLE（可选 `force_scan` / `address`） |
| `shutdown` | 退出 daemon |

详见 `littlebuddy-mcp-server/README.md`。

### 3.6 Cursor Hooks（自动上屏）

已配置在 `little-buddy-kit/.cursor/hooks.json`：提交提示、工具调用、编辑文件、`stop` 等事件 → 对应预设状态。  
Hook 脚本：`.cursor/hooks/littlebuddy_hook.sh`（后台进程，不阻塞 Agent）。

要求：**daemon 在跑**且 `LITTLEBUDDY_MCP_DIR` 与 MCP 一致（未设置时 hook 默认用 `little-buddy-kit/.littlebuddy-mcp`）。

Hook 调试日志：`$LITTLEBUDDY_MCP_DIR/hook.log`。

### 3.7 改 Python 代码后

```bash
cd littlebuddy-mcp-server && pip install -e .
littlebuddy-service restart
# MCP：Cursor 里开关一次 littlebuddy
```

改固件后只需 `pio run -t upload`，**不必**为固件重启 daemon（除非协议字段变了且 daemon 需适配）。

---

## 4. 推荐工作流

1. 烧录最新 **little-buddy** 固件。  
2. `pip install -e littlebuddy-mcp-server`，配置 **mcp.json** + `LITTLEBUDDY_MCP_DIR`。  
3. `littlebuddy-service start`（或由 Cursor 打开 MCP 自动拉起）。  
4. 用 **`talk2bledaemon.py`** 验证 7 字、emoji、时间行。  
5. 日常用 **Cursor**；需要绕过 daemon 调试 BLE 时再 `littlebuddy-service stop` + **`talk.py`**。

---

## 5. 常见问题

**Q: talk.py 报 Device was not found，但 MCP 正常？**  
A: daemon 已占用 BLE。用 `talk2bledaemon.py` 或先 `littlebuddy-service stop`。

**Q: MCP / hook 无反应？**  
A: 检查 `daemon.sock` 是否存在、`littlebuddy-service status`、MCP 是否重载、`$LITTLEBUDDY_MCP_DIR/hook.log` 是否有报错。MCP 成功只表示 `queued`，屏无变化可查 `daemon.log` / BLE 是否仍连接。

**Q: 屏上仍是旧文案/无时间行？**  
A: 确认固件已烧录最新；主机 JSON 需带 `datetime`（当前 MCP/talk 默认会带）。

**Q: Windows 配对失败？**  
A: 设置 → 蓝牙 → 删除设备 → 重新上电 M5 → `python talk.py --scan` 或 daemon `--scan`。

---

## 6. 仓库目录

| 目录 | 内容 |
|------|------|
| `little-buddy/` | M5 固件（PlatformIO） |
| `talk2littlebuddy/` | `talk.py`、`talk2bledaemon.py`、`scan.py` |
| `littlebuddy-mcp-server/` | MCP、daemon、协议与预设（细节见该目录 `README.md`） |
| `.littlebuddy-mcp/` | 运行时 socket/日志（可 gitignore） |
| `.cursor/mcp.json`、`hooks.json` | Cursor 集成 |
