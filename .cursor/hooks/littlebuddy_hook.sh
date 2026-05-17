#!/bin/bash
# Cursor hook：立即退出；屏显在后台进程完成（不阻塞 Agent）
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export LITTLEBUDDY_MCP_DIR="${LITTLEBUDDY_MCP_DIR:-$ROOT/.littlebuddy-mcp}"
PY="${LITTLEBUDDY_PYTHON:-python3}"
mkdir -p "$LITTLEBUDDY_MCP_DIR"

TMP="$(mktemp "${LITTLEBUDDY_MCP_DIR}/hook.XXXXXX")"
cat >"$TMP" 2>/dev/null || : >"$TMP"

nohup "$PY" "$ROOT/.cursor/hooks/littlebuddy_hook.py" "$@" <"$TMP" \
  >>"${LITTLEBUDDY_MCP_DIR}/hook.log" 2>&1 &
rm -f "$TMP"
exit 0
