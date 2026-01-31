#!/bin/bash
# Token使用量を監視するスクリプト

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TOKEN_LOG="$WORK_DIR/logs/token_usage.log"
mkdir -p "$(dirname "$TOKEN_LOG")"

# 現在のタイムスタンプとtoken使用量を記録
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ログに記録
echo "[$TIMESTAMP] Session started" >> "$TOKEN_LOG"

# 使用量が多い場合のチェック
if [ -f "$TOKEN_LOG" ]; then
  LINE_COUNT=$(wc -l < "$TOKEN_LOG")
  if [ "$LINE_COUNT" -gt 100 ]; then
    echo "[$TIMESTAMP] WARNING: Token log growing (lines: $LINE_COUNT)"
  fi
fi
