#!/bin/bash
# 継続検証を開始するスクリプト（重複起動防止）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCK_FILE="$WORK_DIR/.verification_running"

cd "$WORK_DIR"

# ログディレクトリ作成
mkdir -p logs

# 既に実行中か確認
if [ -f "$LOCK_FILE" ]; then
  # ロックファイルにPIDが記録されていれば、そのプロセスが生きているか確認
  if [ -s "$LOCK_FILE" ]; then
    OLD_PID=$(cat "$LOCK_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
      echo "継続検証は既に実行中です (PID: $OLD_PID)"
      exit 0
    else
      echo "古いロックファイルを削除します (PID: $OLD_PID は存在しません)"
      rm -f "$LOCK_FILE"
    fi
  else
    rm -f "$LOCK_FILE"
  fi
fi

# lock ファイル作成（自PIDを記録）
echo $$ > "$LOCK_FILE"

# 終了時にロックファイルを削除
trap 'rm -f "$LOCK_FILE"' EXIT

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
