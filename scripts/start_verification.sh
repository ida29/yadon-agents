#!/bin/bash
# 継続検証を開始するスクリプト（重複起動防止）

WORK_DIR="/Users/yuto.ida/work/yadon-agent"
LOCK_FILE="$WORK_DIR/.verification_running"

cd "$WORK_DIR"

# ログディレクトリ作成
mkdir -p logs

# 既に実行中か確認
if [ -f "$LOCK_FILE" ]; then
  echo "継続検証は既に実行中です"
  exit 0
fi

# lock ファイル作成
touch "$LOCK_FILE"

# auto_runner.sh をバックグラウンドで実行
bash scripts/auto_runner.sh > logs/auto_runner.log 2>&1 &
AUTO_PID=$!

# token_monitor.sh をバックグラウンドで実行
bash scripts/token_monitor.sh > logs/token_monitor.log 2>&1 &
TOKEN_PID=$!

echo "継続検証開始"
echo "auto_runner.sh PID: $AUTO_PID"
echo "token_monitor.sh PID: $TOKEN_PID"

# プロセス監視（終了したら lock ファイル削除）
wait $AUTO_PID $TOKEN_PID
rm -f "$LOCK_FILE"
