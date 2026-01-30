#!/bin/bash
TARGET_PANE=$1
MESSAGE=$2

# 入力欄をクリア（Ctrl+U で行削除）
tmux send-keys -t "$TARGET_PANE" C-u

sleep 0.5

# メッセージ送信
tmux send-keys -t "$TARGET_PANE" "$MESSAGE"
tmux send-keys -t "$TARGET_PANE" Enter

sleep 2

# 入力欄確認
LAST_LINES=$(tmux capture-pane -t "$TARGET_PANE" -p | tail -5)
if echo "$LAST_LINES" | grep -q '❯.*[^ ]'; then
  tmux send-keys -t "$TARGET_PANE" Enter
  sleep 1
  LAST_LINES=$(tmux capture-pane -t "$TARGET_PANE" -p | tail -5)
  if echo "$LAST_LINES" | grep -q '❯.*[^ ]'; then
    tmux send-keys -t "$TARGET_PANE" Enter
  fi
fi
