#!/bin/bash
# 役割別ツール制御フック
# AGENT_ROLE 環境変数でエージェントを識別し、役割に応じてツール実行をブロックする
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

# AGENT_ROLE が未設定なら許可（通常のClaude Code使用）
if [ -z "$AGENT_ROLE" ]; then
    exit 0
fi

# ヤドン → 全て許可
if [ "$AGENT_ROLE" = "yadon" ]; then
    exit 0
fi

# --- ヤドキング ---
if [ "$AGENT_ROLE" = "yadoking" ]; then
    # Edit / Write / NotebookEdit → 全てブロック
    if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "NotebookEdit" ]; then
        echo "【ブロック】ヤドキングはファイルを編集できません。ヤドランに指示を委譲してください。" >&2
        exit 2
    fi

    # Bash → git書込系・ファイル操作系をブロック
    if [ "$TOOL_NAME" = "Bash" ]; then
        COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // empty')

        # git 書き込み系コマンド
        if echo "$COMMAND" | grep -qE '\bgit\s+(add|commit|push|reset|rebase|checkout|restore|clean|rm|mv|merge|cherry-pick|stash)\b'; then
            echo "【ブロック】ヤドキングはgit書き込みコマンドを実行できません。ヤドランに指示を委譲してください。" >&2
            exit 2
        fi

        # ファイル操作コマンド
        if echo "$COMMAND" | grep -qE '\b(mkdir|touch|cp|mv|rm|chmod|chown)\b'; then
            echo "【ブロック】ヤドキングはファイル操作コマンドを実行できません。ヤドランに指示を委譲してください。" >&2
            exit 2
        fi

        # リダイレクト（> または >>）
        if echo "$COMMAND" | grep -qE '>>?'; then
            echo "【ブロック】ヤドキングはリダイレクトを使用できません。ヤドランに指示を委譲してください。" >&2
            exit 2
        fi

        # sed -i（インプレース編集）
        if echo "$COMMAND" | grep -qE '\bsed\s+(-[a-zA-Z]*i|--in-place)'; then
            echo "【ブロック】ヤドキングはsedインプレース編集を実行できません。ヤドランに指示を委譲してください。" >&2
            exit 2
        fi

        # パッケージ管理
        if echo "$COMMAND" | grep -qE '\b(npm|yarn|pnpm)\s+(install|uninstall|add|remove)\b'; then
            echo "【ブロック】ヤドキングはパッケージ管理コマンドを実行できません。ヤドランに指示を委譲してください。" >&2
            exit 2
        fi

        # それ以外のBash（読み取り系）は許可
        exit 0
    fi

    # その他のツールは許可
    exit 0
fi

# --- ヤドラン ---
if [ "$AGENT_ROLE" = "yadoran" ]; then
    # Edit / Write / NotebookEdit → dashboard.md のみ許可
    if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "NotebookEdit" ]; then
        FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // empty')

        if echo "$FILE_PATH" | grep -qE '(^|/)docs/dashboard\.md$'; then
            exit 0
        fi

        echo "【ブロック】ヤドランは docs/dashboard.md 以外のファイルを編集できません。ヤドンに作業を委譲してください。" >&2
        exit 2
    fi

    # Bash → git書込系のみブロック
    if [ "$TOOL_NAME" = "Bash" ]; then
        COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // empty')

        # git 書き込み系コマンド
        if echo "$COMMAND" | grep -qE '\bgit\s+(add|commit|push|reset|rebase|checkout|restore|clean|rm|mv|merge|cherry-pick|stash)\b'; then
            echo "【ブロック】ヤドランはgit書き込みコマンドを実行できません。ヤドンに作業を委譲してください。" >&2
            exit 2
        fi

        # それ以外のBash（tmux send-keys等）は許可
        exit 0
    fi

    # その他のツールは許可
    exit 0
fi

# 未知のロール → 許可
exit 0
