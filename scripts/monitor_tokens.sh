#!/bin/bash
# Token使用量を監視するスクリプト

TOKEN_LOG="/Users/yuto.ida/work/yadon-agent/logs/token_usage.log"
mkdir -p "$(dirname "$TOKEN_LOG")"

# 現在のタイムスタンプとtoken使用量を記録
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
USAGE=$(echo "トークン監視開始" 2>&1)

# ログに記録
echo "[$TIMESTAMP] Session started" >> "$TOKEN_LOG"

# 使用量が多い場合のチェック
if [ -f "$TOKEN_LOG" ]; then
  LINE_COUNT=$(wc -l < "$TOKEN_LOG")
  if [ "$LINE_COUNT" -gt 100 ]; then
    echo "[$TIMESTAMP] WARNING: Token log growing (lines: $LINE_COUNT)"
  fi
fi
