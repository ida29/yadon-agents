#!/bin/bash
# Token使用量を監視して、使いすぎを防ぐスクリプト

WORK_DIR="/Users/yuto.ida/work/yadon-agent"
TOKEN_LOG="$WORK_DIR/logs/token_usage.log"
mkdir -p "$(dirname "$TOKEN_LOG")"

# トークン使用量の閾値（超えたら待機）
TOKEN_THRESHOLD_PERCENT=80

# 定期的に使用量をチェック
while true; do
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
  
  # ダミー実装：実際にはAPI レスポンスヘッダーから取得すべき
  # 現在は10秒ごとにログに記録するだけ
  echo "[$TIMESTAMP] Token monitor running" >> "$TOKEN_LOG"
  
  # ログ行数で簡易的に使用量を推定
  if [ -f "$TOKEN_LOG" ]; then
    LINE_COUNT=$(wc -l < "$TOKEN_LOG")
    
    # 500行を超えたら警告
    if [ "$LINE_COUNT" -gt 500 ]; then
      echo "[$TIMESTAMP] WARNING: High token usage detected ($LINE_COUNT log entries)"
      echo "[$TIMESTAMP] Recommend: Wait before next operation" >> "$TOKEN_LOG"
    fi
  fi
  
  sleep 30
done
