#!/bin/bash
set -euo pipefail
# ヤドキングがヤドランにタスクを送信するスクリプト
#
# 使用法: send_task.sh <instruction> [project_dir]
#
# 引数:
#   instruction  - タスクの指示内容
#   project_dir  - 作業ディレクトリ (省略時: カレントディレクトリ)
#
# 例:
#   ./scripts/send_task.sh "READMEを更新してください"
#   ./scripts/send_task.sh "テストを実行してください" /Users/yida/work/some-project

INSTRUCTION="${1:-}"
PROJECT_DIR="${2:-}"

if [ -z "$INSTRUCTION" ]; then
    echo "使用法: send_task.sh <instruction> [project_dir]" >&2
    exit 1
fi

# デフォルトのproject_dir（カレントディレクトリ）
if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR="$(pwd)"
fi

# テーマ対応ソケットパス（YADON_SOCKET_PREFIX, YADON_MANAGER_ROLE で構築）
SOCKET_PREFIX="${YADON_SOCKET_PREFIX:-yadon}"
MANAGER_ROLE="${YADON_MANAGER_ROLE:-yadoran}"
SOCKET="/tmp/${SOCKET_PREFIX}-agent-${MANAGER_ROLE}.sock"

# ソケット存在チェック
if [ ! -S "$SOCKET" ]; then
    echo "エラー: マネージャーデーモンが起動していません ($SOCKET が見つかりません)" >&2
    exit 1
fi

# タスクID生成
TASK_ID="task-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 2)"

# JSONメッセージ作成（jqがあればjq、なければprintf）
if command -v jq &>/dev/null; then
    MESSAGE=$(jq -n \
        --arg type "task" \
        --arg id "$TASK_ID" \
        --arg from "yadoking" \
        --arg instruction "$INSTRUCTION" \
        --arg project_dir "$PROJECT_DIR" \
        '{type: $type, id: $id, from: $from, payload: {instruction: $instruction, project_dir: $project_dir}}')
else
    # jqがない場合のフォールバック（ダブルクォートをエスケープ）
    ESC_INST=$(printf '%s' "$INSTRUCTION" | sed 's/\\/\\\\/g; s/"/\\"/g')
    ESC_DIR=$(printf '%s' "$PROJECT_DIR" | sed 's/\\/\\\\/g; s/"/\\"/g')
    MESSAGE="{\"type\":\"task\",\"id\":\"${TASK_ID}\",\"from\":\"yadoking\",\"payload\":{\"instruction\":\"${ESC_INST}\",\"project_dir\":\"${ESC_DIR}\"}}"
fi

echo "タスク送信中... (ID: $TASK_ID)"
echo "指示: ${INSTRUCTION:0:80}..."
echo ""

# Python経由でUnixソケット通信（shutdown(SHUT_WR)が必要なため）
# メッセージはstdin経由で渡す（クォーティング問題を回避）
RESPONSE=$(echo "$MESSAGE" | python3 -c "
import socket, sys, json

sock_path = sys.argv[1]
message = sys.stdin.read()

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(600)  # 10分タイムアウト
try:
    sock.connect(sock_path)
    sock.sendall(message.encode('utf-8'))
    sock.shutdown(socket.SHUT_WR)
    chunks = []
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)
    print(b''.join(chunks).decode('utf-8'))
except Exception as e:
    print(json.dumps({'type': 'error', 'message': str(e)}))
    sys.exit(1)
finally:
    sock.close()
" "$SOCKET" 2>&1)

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "エラー: 通信に失敗しました" >&2
    echo "$RESPONSE" >&2
    exit 1
fi

# レスポンス表示
echo "--- レスポンス ---"
if command -v jq &>/dev/null; then
    echo "$RESPONSE" | jq .
else
    echo "$RESPONSE"
fi
