"""little-buddy 设备 emoji 与 MCP 状态预设（与固件 emoji_bitmaps / talk2littlebuddy 一致）。"""

from __future__ import annotations

COLOR_GREEN = "green"
COLOR_YELLOW = "yellow"
COLOR_RED = "red"
LEVEL_COLORS: tuple[str, ...] = (COLOR_GREEN, COLOR_YELLOW, COLOR_RED)

MAX_MSG_CJK = 7

# M5StickS3 固件 Twemoji 40×40 位图名称（70 个，顺序同 talk2littlebuddy/talk.py）
DEVICE_EMOJI_NAMES: tuple[str, ...] = (
    "rocket",
    "fire",
    "check",
    "cross",
    "warn",
    "computer",
    "bug",
    "coffee",
    "thumbsup",
    "eyes",
    "gear",
    "hammer",
    "wrench",
    "package",
    "merge",
    "branch",
    "lock",
    "passkey",
    "shield",
    "zap",
    "hourglass",
    "stop",
    "recycle",
    "memo",
    "link",
    "save",
    "robot",
    "chartup",
    "chartdown",
    "target",
    "clipboard",
    "bell",
    "calendar",
    "alarm",
    "timer",
    "inbox",
    "outbox",
    "email",
    "phone",
    "globe",
    "cloud",
    "storage",
    "testtube",
    "microscope",
    "megaphone",
    "wip",
    "party",
    "siren",
    "sparkles",
    "search",
    "brain",
    "thought",
    "bulb",
    "wand",
    "plug",
    "pause",
    "retry",
    "blocked",
    "pin",
    "book",
    "puzzle",
    "crystal",
    "agent",
    "stream",
    "chat",
    "notebook",
    "trophy",
    "broom",
    "pencil",
    "scroll",
)

# littlebuddy_show 的 emoji 枚举；与 DEVICE_EMOJI_NAMES 相同
CURSOR_EMOJI_NAMES: tuple[str, ...] = DEVICE_EMOJI_NAMES

# 通用开发场景（50）+ Cursor/Agent 状态（20）；msg 最多 MAX_MSG_CJK 个汉字
_GENERAL_STATUS_PRESETS: dict[str, tuple[str, str, str]] = {
    "deploy": ("正在发布上线", "rocket", COLOR_GREEN),
    "perf_boost": ("性能拉满中", "fire", COLOR_YELLOW),
    "test_pass": ("测试已通过", "check", COLOR_GREEN),
    "build_fail": ("编译失败了", "cross", COLOR_RED),
    "disk_warn": ("磁盘快满了", "warn", COLOR_YELLOW),
    "building": ("正在构建中", "computer", COLOR_GREEN),
    "runtime_bug": ("程序出错了", "bug", COLOR_RED),
    "coffee_break": ("休息一下吧", "coffee", COLOR_GREEN),
    "thumbs_up": ("给你点个赞", "thumbsup", COLOR_GREEN),
    "code_review": ("请审核代码", "eyes", COLOR_YELLOW),
    "configuring": ("正在配置中", "gear", COLOR_GREEN),
    "hotfix": ("紧急修复中", "hammer", COLOR_YELLOW),
    "debugging": ("正在调试中", "wrench", COLOR_YELLOW),
    "packaged": ("构建完成了", "package", COLOR_GREEN),
    "merged": ("合并成功了", "merge", COLOR_GREEN),
    "new_branch": ("新建分支了", "branch", COLOR_GREEN),
    "repo_locked": ("仓库已锁定", "lock", COLOR_YELLOW),
    "passkey_ok": ("密钥已就绪", "passkey", COLOR_GREEN),
    "secured": ("安全防护中", "shield", COLOR_GREEN),
    "perf_zap": ("性能爆表了", "zap", COLOR_YELLOW),
    "waiting": ("排队等待中", "hourglass", COLOR_YELLOW),
    "task_stop": ("任务已停止", "stop", COLOR_RED),
    "redeploy": ("重新部署中", "recycle", COLOR_YELLOW),
    "docs_update": ("正在更新文档", "memo", COLOR_GREEN),
    "link_ok": ("链路正常了", "link", COLOR_GREEN),
    "saved": ("数据已落盘", "save", COLOR_GREEN),
    "auto_run": ("自动执行中", "robot", COLOR_GREEN),
    "metrics_up": ("指标上涨了", "chartup", COLOR_GREEN),
    "metrics_down": ("指标下跌了", "chartdown", COLOR_RED),
    "goal_met": ("目标已达成", "target", COLOR_GREEN),
    "copied": ("已复制好了", "clipboard", COLOR_GREEN),
    "notify": ("有新通知了", "bell", COLOR_YELLOW),
    "calendar_full": ("日程已满了", "calendar", COLOR_YELLOW),
    "alarm_soon": ("快到点了哦", "alarm", COLOR_YELLOW),
    "timed_out": ("请求超时了", "timer", COLOR_RED),
    "inbox": ("收到新消息", "inbox", COLOR_GREEN),
    "outbox": ("消息已发出", "outbox", COLOR_GREEN),
    "email_unread": ("有未读邮件", "email", COLOR_YELLOW),
    "phone_ring": ("电话找你了", "phone", COLOR_YELLOW),
    "global_ok": ("全网已可达", "globe", COLOR_GREEN),
    "cloud_sync": ("同步云端中", "cloud", COLOR_GREEN),
    "storage_ok": ("写入存储中", "storage", COLOR_GREEN),
    "unit_test": ("单元测试中", "testtube", COLOR_GREEN),
    "investigate": ("深入排查中", "microscope", COLOR_YELLOW),
    "broadcast": ("全员通知中", "megaphone", COLOR_YELLOW),
    "maintenance": ("维护进行中", "wip", COLOR_YELLOW),
    "celebrate": ("版本庆祝中", "party", COLOR_GREEN),
    "alert_critical": ("严重告警了", "siren", COLOR_RED),
    "feature_highlight": ("亮点新功能", "sparkles", COLOR_GREEN),
    "search_done": ("检索完成了", "search", COLOR_GREEN),
}

_AGENT_STATUS_PRESETS: dict[str, tuple[str, str, str]] = {
    "thinking": ("正在思考中", "brain", COLOR_YELLOW),
    "reasoning": ("深度推理中", "thought", COLOR_YELLOW),
    "idea": ("突然想到了", "bulb", COLOR_GREEN),
    "autofix": ("一键修好中", "wand", COLOR_GREEN),
    "tool": ("正在调用工具", "plug", COLOR_GREEN),
    "pause": ("请稍等一下", "pause", COLOR_YELLOW),
    "retry": ("正在重试中", "retry", COLOR_YELLOW),
    "cancelled": ("操作已取消", "blocked", COLOR_RED),
    "context_pin": ("已钉住上文", "pin", COLOR_YELLOW),
    "read_docs": ("正在查阅资料", "book", COLOR_GREEN),
    "decompose": ("正在拆解问题", "puzzle", COLOR_YELLOW),
    "plan": ("正在制定计划", "crystal", COLOR_GREEN),
    "agent": ("代理执行中", "agent", COLOR_GREEN),
    "streaming": ("流式输出中", "stream", COLOR_GREEN),
    "chatting": ("继续对话中", "chat", COLOR_GREEN),
    "session": ("记录会话中", "notebook", COLOR_GREEN),
    "done": ("任务圆满完成", "trophy", COLOR_GREEN),
    "format": ("正在整理代码", "broom", COLOR_GREEN),
    "generating": ("正在生成代码", "pencil", COLOR_GREEN),
    "applying": ("正在应用修改", "scroll", COLOR_GREEN),
}

CURSOR_STATUS_PRESETS: dict[str, tuple[str, str, str]] = {
    **_GENERAL_STATUS_PRESETS,
    **_AGENT_STATUS_PRESETS,
}


def _cjk_len(msg: str) -> int:
    return sum(1 for c in msg if "\u4e00" <= c <= "\u9fff")


for _sid, (_msg, _emoji, _color) in CURSOR_STATUS_PRESETS.items():
    n = _cjk_len(_msg)
    if n > MAX_MSG_CJK:
        raise ValueError(f"预设 {_sid!r} msg 超过 {MAX_MSG_CJK} 字: {_msg!r} ({n})")
