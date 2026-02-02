#!/bin/bash

# ヤドン・エージェント 起動スクリプト
# 使用法: ./start.sh [作業ディレクトリ]
#   作業ディレクトリ省略時はカレントディレクトリで起動
#
# `yadon start` のシェルラッパー

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")")" && pwd)"

# uvのチェック
if ! command -v uv &> /dev/null; then
    echo -e "\033[0;31mエラー\033[0m uv が見つかりません"
    echo "インストールしてください: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# uv環境で実行
cd "$SCRIPT_DIR"
WORK_DIR="${1:-$(pwd)}"
exec uv run yadon start "$WORK_DIR"
