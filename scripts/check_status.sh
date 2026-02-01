#!/bin/bash
set -euo pipefail
# エージェントのステータスを照会するスクリプト
#
# 使用法: check_status.sh [agent_name]
#
# 引数:
#   agent_name - "yadoran", "yadon-1", "yadon-2", "yadon-3", "yadon-4", "all" (省略時: all)
#
# 例:
#   ./scripts/check_status.sh           # 全エージェント
#   ./scripts/check_status.sh yadoran   # ヤドランのみ
#   ./scripts/check_status.sh yadon-1   # ヤドン1のみ

YADON_COUNT="${YADON_COUNT:-4}"
SOCKET_PREFIX="${YADON_SOCKET_PREFIX:-yadon}"
MANAGER_ROLE="${YADON_MANAGER_ROLE:-yadoran}"
WORKER_ROLE="${YADON_WORKER_ROLE:-yadon}"
TARGET="${1:-all}"

query_agent() {
    local name="$1"
    local sock="/tmp/${SOCKET_PREFIX}-agent-${name}.sock"

    if [ ! -S "$sock" ]; then
        echo "  ${name}: 停止中 (ソケットなし)"
        return
    fi

    RESPONSE=$(python3 -c "
import socket, json, sys, os

sock_path = sys.argv[1]
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(5)
try:
    sock.connect(sock_path)
    msg = json.dumps({'type': 'status', 'from': 'check_status'})
    sock.sendall(msg.encode('utf-8'))
    sock.shutdown(socket.SHUT_WR)
    chunks = []
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)
    data = json.loads(b''.join(chunks).decode('utf-8'))
    state = data.get('state', '不明')
    task = data.get('current_task', '-')
    workers = data.get('workers', None)
    queue = data.get('queue_size', None)
    parts = [f'{state}']
    if task and task != '-' and state == 'busy':
        parts.append(f'タスク: {task}')
    if workers is not None:
        parts.append(f'ワーカー: {workers}')
    if queue is not None:
        parts.append(f'キュー: {queue}')
    print(', '.join(parts))
except socket.timeout:
    print('タイムアウト (ビジー?)')
except Exception as e:
    print(f'エラー: {e}')
finally:
    sock.close()
" "$sock" 2>&1)

    echo "  ${name}: ${RESPONSE}"
}

echo "=== エージェント ステータス ==="
echo ""

if [ "$TARGET" = "all" ]; then
    query_agent "$MANAGER_ROLE"
    for i in $(seq 1 "$YADON_COUNT"); do
        query_agent "${WORKER_ROLE}-${i}"
    done
else
    query_agent "$TARGET"
fi

echo ""
