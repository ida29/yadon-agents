#!/bin/bash
# 使い方: ./scripts/notify.sh <ペインID> "メッセージ"
TARGET_PANE=$1
MESSAGE=$2

tmux send-keys -t "$TARGET_PANE" "$MESSAGE"
tmux send-keys -t "$TARGET_PANE" Enter

sleep 2

# 入力欄を確認（最後の5行をチェック）
LAST_LINES=$(tmux capture-pane -t "$TARGET_PANE" -p | tail -5)

# 入力欄（❯ の後）に何か残っていたらEnterを再送信
if echo "$LAST_LINES" | grep -q '❯.*[^ ]'; then
  tmux send-keys -t "$TARGET_PANE" Enter
  sleep 1
  # もう一度確認、まだ残っていたらもう一回
  LAST_LINES=$(tmux capture-pane -t "$TARGET_PANE" -p | tail -5)
  if echo "$LAST_LINES" | grep -q '❯.*[^ ]'; then
    tmux send-keys -t "$TARGET_PANE" Enter
  fi
fi
