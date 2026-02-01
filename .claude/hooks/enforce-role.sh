#!/bin/bash
set -uo pipefail
# 役割別ツール制御フック
# AGENT_ROLE_LEVEL (coordinator/manager/worker) または AGENT_ROLE で判定
#
# exit 0 = 許可
# exit 2 = ブロック（stderrにメッセージ）

# jq が利用可能か確認（なければ許可してフェイルオープン）
if ! command -v jq &>/dev/null; then
    echo "警告: jq が見つかりません。役割制御をスキップします。" >&2
    exit 0
fi

# stdin から JSON を読み取る
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // empty')

# ロールレベル判定: AGENT_ROLE_LEVEL を優先、なければ AGENT_ROLE からフォールバック
ROLE_LEVEL="${AGENT_ROLE_LEVEL:-}"
if [ -z "$ROLE_LEVEL" ]; then
    AGENT_ROLE="${AGENT_ROLE:-}"
    if [ -z "$AGENT_ROLE" ]; then
        # どちらも未設定なら許可（通常のClaude Code使用）
        exit 0
    fi
    # 既存 AGENT_ROLE 値からレベルを推定
    case "$AGENT_ROLE" in
        yadoking)  ROLE_LEVEL="coordinator" ;;
        yadoran)   ROLE_LEVEL="manager" ;;
        yadon)     ROLE_LEVEL="worker" ;;
        *)         exit 0 ;;  # 未知のロール -> 許可
    esac
fi

# --- worker: 全て許可 ---
if [ "$ROLE_LEVEL" = "worker" ]; then
    exit 0
fi

# --- coordinator: 編集・書き込み系をブロック ---
if [ "$ROLE_LEVEL" = "coordinator" ]; then
    if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "NotebookEdit" ]; then
        echo "【ブロック】coordinatorはファイルを編集できません。managerに指示を委譲してください。" >&2
        exit 2
    fi

    if [ "$TOOL_NAME" = "Bash" ]; then
        COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // empty')

        if echo "$COMMAND" | grep -qE '\bgit\s+(add|commit|push|reset|rebase|checkout|restore|clean|rm|mv|merge|cherry-pick|stash)\b'; then
            echo "【ブロック】coordinatorはgit書き込みコマンドを実行できません。managerに指示を委譲してください。" >&2
            exit 2
        fi

        if echo "$COMMAND" | grep -qE '\b(mkdir|touch|cp|mv|rm|chmod|chown)\b'; then
            echo "【ブロック】coordinatorはファイル操作コマンドを実行できません。managerに指示を委譲してください。" >&2
            exit 2
        fi

        if echo "$COMMAND" | grep -qE '>>?'; then
            echo "【ブロック】coordinatorはリダイレクトを使用できません。managerに指示を委譲してください。" >&2
            exit 2
        fi

        if echo "$COMMAND" | grep -qE '\bsed\s+(-[a-zA-Z]*i|--in-place)'; then
            echo "【ブロック】coordinatorはsedインプレース編集を実行できません。managerに指示を委譲してください。" >&2
            exit 2
        fi

        if echo "$COMMAND" | grep -qE '\b(npm|yarn|pnpm)\s+(install|uninstall|add|remove)\b'; then
            echo "【ブロック】coordinatorはパッケージ管理コマンドを実行できません。managerに指示を委譲してください。" >&2
            exit 2
        fi

        exit 0
    fi

    exit 0
fi

# --- manager: 編集ブロック、git書き込みブロック ---
if [ "$ROLE_LEVEL" = "manager" ]; then
    if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "NotebookEdit" ]; then
        echo "【ブロック】managerはファイルを編集できません。workerに作業を委譲してください。" >&2
        exit 2
    fi

    if [ "$TOOL_NAME" = "Bash" ]; then
        COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // empty')

        if echo "$COMMAND" | grep -qE '\bgit\s+(add|commit|push|reset|rebase|checkout|restore|clean|rm|mv|merge|cherry-pick|stash)\b'; then
            echo "【ブロック】managerはgit書き込みコマンドを実行できません。workerに作業を委譲してください。" >&2
            exit 2
        fi

        exit 0
    fi

    exit 0
fi

# 未知のレベル -> 許可
exit 0
