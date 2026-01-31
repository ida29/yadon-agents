#!/bin/bash
# auto_runner.sh - 自動タスク処理スクリプト
# 10秒ごとにdashboard.mdをチェックして新しいタスクがあれば通知

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DASHBOARD_FILE="$WORK_DIR/docs/dashboard.md"
LAST_TASK_COUNT=0

# ペイン設定ファイルを探す（panes-*.yaml を優先、なければ panes.yaml）
find_panes_config() {
  # start.sh が生成する panes-$PROJECT_NAME.yaml を探す
  local latest
  latest=$(ls -t "$WORK_DIR"/config/panes-*.yaml 2>/dev/null | head -1)
  if [ -n "$latest" ]; then
    echo "$latest"
    return
  fi
  # フォールバック: panes.yaml
  if [ -f "$WORK_DIR/config/panes.yaml" ]; then
    echo "$WORK_DIR/config/panes.yaml"
    return
  fi
  echo ""
}

# ヤドランのペインIDを取得
get_yadoran_pane() {
  local config_file
  config_file=$(find_panes_config)
  if [ -z "$config_file" ] || [ ! -f "$config_file" ]; then
    echo ""
    return
  fi
  # YAML形式: yadoran: "%123" または yadoran: %123
  grep '^yadoran:' "$config_file" | sed 's/^yadoran:[[:space:]]*//' | tr -d '"' | tr -d "'"
}

# dashboard.mdから進行中タスクのセクション内のタスク数を取得
get_task_count() {
  if [ ! -f "$DASHBOARD_FILE" ]; then
    echo "0"
    return
  fi
  # 進行中タスクセクションの内容を取得（次のセクションまで）
  local count
  count=$(sed -n '/進行中タスク/,/完了タスク/p' "$DASHBOARD_FILE" | \
    grep -c "^- \*\*" 2>/dev/null || true)
  echo "${count:-0}"
}

echo "...自動タスク処理スクリプト開始やぁん..."

while true; do
  sleep 10

  # dashboard.mdが存在するか確認
  if [ ! -f "$DASHBOARD_FILE" ]; then
    continue
  fi

  # 現在のタスク数を取得
  CURRENT_TASK_COUNT=$(get_task_count)

  # 新しいタスクがあるかチェック
  if [ "$CURRENT_TASK_COUNT" -gt "$LAST_TASK_COUNT" ] 2>/dev/null; then
    YADORAN_PANE=$(get_yadoran_pane)

    if [ -z "$YADORAN_PANE" ]; then
      echo "...ヤドランのペインIDが見つからないやぁん..."
      continue
    fi

    # ペインが存在するか確認
    if ! tmux has-session -t "${YADORAN_PANE}" 2>/dev/null && \
       ! tmux list-panes -a -F '#{pane_id}' 2>/dev/null | grep -q "^${YADORAN_PANE}$"; then
      echo "...ヤドランのペイン ${YADORAN_PANE} が存在しないやぁん..."
      continue
    fi

    # ヤドランに新しいタスクを通知
    tmux send-keys -t "$YADORAN_PANE" "【自動検出】新しいタスクを検出しました。dashboard.mdを確認してください。" && \
      tmux send-keys -t "$YADORAN_PANE" Enter

    echo "...新しいタスク $CURRENT_TASK_COUNT 件を検出してヤドランに通知したやぁん..."

    # タスク数を更新
    LAST_TASK_COUNT=$CURRENT_TASK_COUNT
  fi
done
