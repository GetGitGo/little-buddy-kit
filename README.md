# Little Buddy Kit

M5Stick S3 状态屏：BLE 固件 + 主机工具 + Cursor MCP/daemon，把 Agent 工作状态推到小屏上。

```
┌─────────────┐     BLE (单连接)      ┌──────────────┐
│  Mac / PC   │◄────────────────────►│ M5StickS3    │
│  daemon     │   NUS JSON 行协议     │ little-buddy │
└──────┬──────┘                       └──────────────┘
       │ Unix socket
       ├── Cursor hooks / MCP
       └── talk2bledaemon.py
```

## 仓库内容

| 目录 | 说明 |
|------|------|
| [`little-buddy/`](little-buddy/) | M5 固件（PlatformIO） |
| [`talk2littlebuddy/`](talk2littlebuddy/) | `talk.py`、`talk2bledaemon.py` 测试脚本 |
| [`littlebuddy-mcp-server/`](littlebuddy-mcp-server/) | MCP + 常驻 BLE daemon |
| [`install.md`](install.md) | **安装与使用（从这里开始）** |

## 快速开始

1. 烧录固件：`cd little-buddy && pio run -t upload`
2. 安装 MCP 包：`cd littlebuddy-mcp-server && pip install -e .`
3. 设置运行时目录并启动 daemon：

   ```bash
   export LITTLEBUDDY_MCP_DIR=/path/to/this-repo/.littlebuddy-mcp
   mkdir -p "$LITTLEBUDDY_MCP_DIR"
   littlebuddy-service start
   ```

4. 测试：`cd talk2littlebuddy && python talk2bledaemon.py --status thinking`

完整步骤、Cursor 配置、故障排查见 **[install.md](install.md)**。

## Cursor（可选）

1. 复制 [`.cursor/mcp.json.example`](.cursor/mcp.json.example) → `.cursor/mcp.json`，改 `command` 与 `LITTLEBUDDY_MCP_DIR`
2. 仓库已含 [`.cursor/hooks.json`](.cursor/hooks.json) 与 hook 脚本；需已 `pip install -e littlebuddy-mcp-server`
3. Cursor **Settings → MCP** 重载 `littlebuddy`

## 许可

- 代码：MIT（见 [LICENSE](LICENSE)）
- Emoji 位图：基于 [Twemoji](https://github.com/twitter/twemoji)，见 `little-buddy/README.md`
