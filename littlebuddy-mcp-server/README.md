# littlebuddy-mcp-server

MCP + **常驻 BLE daemon**：Cursor / Claude Code 状态推到 M5 **little-buddy**，避免每次 MCP 调用重新扫描/连接。

## 架构

```
Cursor MCP (stdio)  ──Unix socket──►  littlebuddy-daemon (常驻)
                                         └─ BLE 长连接 M5
```

- **daemon**：启动时结束旧进程 → 按策略连接 M5 → 监听 `$LITTLEBUDDY_MCP_DIR/daemon.sock`
- **MCP**：经 socket 下发 `show`（fire-and-forget），立即返回 `{"ok":true,"queued":true}`，**不等待**屏上是否显示成功
- **协议**：JSON 一行，含 `msg` / `emoji` / `size` / `color` / `gap` / 自动生成的 `datetime`（见 `littlebuddy_mcp/protocol.py`）

## 安装

```bash
cd littlebuddy-mcp-server
pip install -e .
```

安装后命令：`littlebuddy-mcp`、`littlebuddy-daemon`、`littlebuddy-service`。

## 1. 常驻 daemon（默认自动，无需手动 start）

**Cursor 启动 MCP 时会自动**（`LITTLEBUDDY_AUTO_START` 非 `0` 时）：必要时结束旧 daemon → 启动子进程 → 连接 M5 → 监听 socket。  
第一次上屏可能多等几秒（BLE 连接），之后 MCP 只写 socket。

可选环境变量（写在 `mcp.json` 的 `env` 里）：

| 变量 | 默认 | 说明 |
|------|------|------|
| `LITTLEBUDDY_MCP_DIR` | `~/.littlebuddy-mcp` | socket、`daemon.pid`、`daemon.log`、`last_device` 目录；Cursor 建议设为项目内 `.littlebuddy-mcp` |
| `LITTLEBUDDY_AUTO_START` | `1` | `0` / `false` / `no` 关闭 MCP 自动拉起 |
| `LITTLEBUDDY_START_SCAN` | `0` | `1` / `true` / `yes` 时 **MCP 首次拉起 daemon** 带 `--scan`（强制扫描后再连） |

手动管理（调试用）：

```bash
littlebuddy-service start|stop|restart|status
littlebuddy-service start --scan              # 启动时强制扫描
littlebuddy-service start --address <BLE地址>  # 指定设备
littlebuddy-service restart --scan --address <BLE地址>
```

日志（均在 `$LITTLEBUDDY_MCP_DIR` 下）：

- `daemon.log` — daemon 主日志  
- `daemon.stdout` — 子进程标准输出  

未设置 `LITTLEBUDDY_MCP_DIR` 时，默认为 `~/.littlebuddy-mcp/`。

### BLE 选机策略（`littlebuddy_mcp/ble.py`）

daemon 连接时：

1. **`last_device` 存在且短时探测可连** → 用缓存地址  
2. **否则扫描** → 仅一台用该台；多台 little-buddy → **RSSI 最强**  
3. 启动参数 `--address` / `--scan` 见上（`--address` 与 `--scan` 组合时按地址过滤扫描）

`$LITTLEBUDDY_MCP_DIR/last_device` 与 `talk2littlebuddy/.last_device` **不是同一文件**。

## 2. Cursor MCP 配置

`little-buddy-kit/.cursor/mcp.json` 示例（路径按本机修改）：

```json
{
  "mcpServers": {
    "littlebuddy": {
      "command": "/path/to/bin/littlebuddy-mcp",
      "args": [],
      "env": {
        "LITTLEBUDDY_MCP_DIR": "/path/to/little-buddy-kit/.littlebuddy-mcp"
      }
    }
  }
}
```

首次连接困难时可加扫描：

```json
"env": {
  "LITTLEBUDDY_MCP_DIR": "/path/to/little-buddy-kit/.littlebuddy-mcp",
  "LITTLEBUDDY_START_SCAN": "1"
}
```

改完 `mcp.json` 后在 Cursor **Settings → MCP** 重载 littlebuddy。

## 3. MCP 工具

| 工具 | 说明 |
|------|------|
| `littlebuddy_show_status` | 预设状态（`thinking` / `tool` / `done` 等，见 `statuses.py`，约 70 条）；可选 `msg` 覆盖文案 |
| `littlebuddy_show` | 自定义 `msg` + 可选 `emoji` / `color` / `size`（默认 `size=4`） |
| `littlebuddy_list_statuses` | 列出预设（**不走** BLE / daemon） |

显示约束（`protocol.py`）：`msg` 最多 **7 个汉字**；`littlebuddy_show_status` 固定 `size=4`、`gap=6`。

换 BLE 设备请用 **`littlebuddy-service restart --address …`** 或 **`talk2bledaemon.py --reconnect`**，MCP 的 show 工具**不**带 `force_scan` / `address` 参数。

对话中可让 Agent 调用 `littlebuddy_show_status`，或由项目 **Cursor hooks**（`.cursor/hooks`）自动上屏（不经过 MCP 工具 schema）。

## 4. Socket 协议（daemon）

| `op` | MCP/客户端 | daemon 响应 |
|------|------------|-------------|
| `show` | 写一行 JSON | **无回包**（异步 `hub.show`） |
| `ping` | 请求 | `ok` + 连接状态 |
| `status` | 请求 | `ok` + 连接状态 |
| `reconnect` | 请求 | `ok` + `address` / `label` |
| `shutdown` | 请求 | `ok` 后退出 |

## 5. 与 talk2littlebuddy

- **独立进程与缓存**；日常 daemon 运行时请用 **`talk2bledaemon.py`** 测屏，勿与 `talk.py` 同时抢 BLE。  
- 详见仓库根目录 `install.md`。

## 6. 开机自启（macOS，可选）

本包**不**自动生成 LaunchAgent。若需登录自启，可自行编写 `~/Library/LaunchAgents/` plist，命令指向 `littlebuddy-daemon` 并设置 `LITTLEBUDDY_MCP_DIR`。

```bash
littlebuddy-service start   # 仅当前用户会话启动 daemon
```
