#!/bin/bash
# auto_runner.sh - 自動タスク処理スクリプト
# 10秒ごとにdashboard.mdをチェックして新しいタスクがあれば通知

WORK_DIR="/Users/yuto.ida/work/yadon-agent"
DASHBOARD_FILE="$WORK_DIR/docs/dashboard.md"
CONFIG_FILE="$WORK_DIR/config/panes.yaml"
LAST_TASK_COUNT=0

# ヤドランのペインIDを取得
get_yadoran_pane() {
  grep yadoran "$CONFIG_FILE" | cut -d'"' -f2
}

# dashboard.mdから進行中タスクのセクション内のタスク数を取得
get_task_count() {
  if [ ! -f "$DASHBOARD_FILE" ]; then
    echo "0"
    return
  fi
  # 進行中タスクセクションの内容を取得（次のセクションまで）
  sed -n '/## 🔄 進行中タスク/,/## ✅ 完了タスク/p' "$DASHBOARD_FILE" | \
    grep -c "^- \*\*" || echo "0"
}

echo "...自動タスク処理スクリプト開始やぁん..."

while true; do
  sleep 10

  # dashboard.mdが存在するか確認
  if [ ! -f "$DASHBOARD_FILE" ]; then
    echo "...dashboard.md が見つからないやぁん...待機中..."
    continue
  fi

  # 現在のタスク数を取得
  CURRENT_TASK_COUNT=$(get_task_count)

  # 新しいタスクがあるかチェック
  if [ "$CURRENT_TASK_COUNT" -gt "$LAST_TASK_COUNT" ]; then
    YADORAN_PANE=$(get_yadoran_pane)

    if [ -z "$YADORAN_PANE" ]; then
      echo "...ヤドランのペインIDが見つからないやぁん..."
      continue
    fi

    # ヤドランに新しいタスクを通知
    tmux send-keys -t "$YADORAN_PANE" "【自動検出】新しいタスクを検出しました。dashboard.mdを確認してください。" && tmux send-keys -t "$YADORAN_PANE" Enter

    echo "...新しいタスク $CURRENT_TASK_COUNT 件を検出してヤドランに通知したやぁん..."

    # タスク数を更新
    LAST_TASK_COUNT=$CURRENT_TASK_COUNT
  fi

  # rate limit チェック（監視中）
  # 10秒待機で自然にレート制限されている
done
