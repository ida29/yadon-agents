#!/bin/bash
# 使い方: ./scripts/notify.sh <ペインID> "メッセージ"
TARGET_PANE=$1
MESSAGE=$2

tmux send-keys -t "$TARGET_PANE" "$MESSAGE"
tmux send-keys -t "$TARGET_PANE" Enter

sleep 2
# 入力欄に残っていたら再送信
REMAINING=$(tmux capture-pane -t "$TARGET_PANE" -p | tail -1)
if [[ "$REMAINING" == *"$MESSAGE"* ]]; then
  tmux send-keys -t "$TARGET_PANE" Enter
fi
