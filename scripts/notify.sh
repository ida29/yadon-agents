#!/bin/bash
# エージェント間通知スクリプト
# 使用法: notify.sh <pane_id> <message>

TARGET_PANE=$1
MESSAGE=$2

# 引数チェック
if [ -z "$TARGET_PANE" ] || [ -z "$MESSAGE" ]; then
  echo "使用法: notify.sh <pane_id> <message>" >&2
  exit 1
fi

# ペインが存在するか確認
if ! tmux list-panes -a -F '#{pane_id}' 2>/dev/null | grep -q "^${TARGET_PANE}$"; then
  echo "エラー: ペイン ${TARGET_PANE} が存在しません" >&2
  exit 1
fi

# 入力欄をクリア（Ctrl+U で行削除）
tmux send-keys -t "$TARGET_PANE" C-u

sleep 0.5

# メッセージ送信
tmux send-keys -t "$TARGET_PANE" "$MESSAGE"
tmux send-keys -t "$TARGET_PANE" Enter

sleep 2

# 入力欄確認（プロンプト文字の検出 — 複数パターン対応）
LAST_LINES=$(tmux capture-pane -t "$TARGET_PANE" -p | tail -5)
if echo "$LAST_LINES" | grep -qE '(❯|>|\$|%).*[^ ]'; then
  tmux send-keys -t "$TARGET_PANE" Enter
  sleep 1
  LAST_LINES=$(tmux capture-pane -t "$TARGET_PANE" -p | tail -5)
  if echo "$LAST_LINES" | grep -qE '(❯|>|\$|%).*[^ ]'; then
    tmux send-keys -t "$TARGET_PANE" Enter
  fi
fi
