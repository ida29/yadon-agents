#!/bin/bash
# エージェントのペインIDを取得するヘルパースクリプト
# 使用法: get_pane.sh <agent_name>
# 例:     get_pane.sh yadoran
#         get_pane.sh yadon1
#         get_pane.sh yadoking

AGENT_NAME=$1

if [ -z "$AGENT_NAME" ]; then
    echo "使用法: get_pane.sh <agent_name>" >&2
    echo "  agent_name: yadoking, yadoran, yadon1, yadon2, yadon3, yadon4" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ペイン設定ファイルを探す（panes-*.yaml を優先、なければ panes.yaml）
find_config() {
    local latest
    latest=$(ls -t "$WORK_DIR"/config/panes-*.yaml 2>/dev/null | head -1)
    if [ -n "$latest" ]; then
        echo "$latest"
        return
    fi
    if [ -f "$WORK_DIR/config/panes.yaml" ]; then
        echo "$WORK_DIR/config/panes.yaml"
        return
    fi
    echo ""
}

CONFIG_FILE=$(find_config)

if [ -z "$CONFIG_FILE" ] || [ ! -f "$CONFIG_FILE" ]; then
    echo "エラー: ペイン設定ファイルが見つかりません" >&2
    exit 1
fi

# YAML形式: agent_name: "%123" または agent_name: %123
PANE_ID=$(grep "^${AGENT_NAME}:" "$CONFIG_FILE" | sed "s/^${AGENT_NAME}:[[:space:]]*//" | tr -d '"' | tr -d "'")

if [ -z "$PANE_ID" ]; then
    echo "エラー: ${AGENT_NAME} のペインIDが見つかりません" >&2
    exit 1
fi

echo "$PANE_ID"
