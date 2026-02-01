#!/bin/bash
# エージェント再起動スクリプト
#
# 停止して再起動する。
#
# 使用法: restart_daemons.sh [作業ディレクトリ]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

"$ROOT_DIR/stop.sh"
exec "$ROOT_DIR/start.sh" "$@"
