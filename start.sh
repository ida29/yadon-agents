#!/bin/bash

# ヤドン・エージェント 起動スクリプト
# 使用法: ./start.sh [作業ディレクトリ]
#   作業ディレクトリ省略時はカレントディレクトリで起動
#
# `yadon start` のシェルラッパー

set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")")" && pwd)"

# Python3の確認
if ! command -v python3 &> /dev/null; then
    echo -e "\033[0;31mエラー\033[0m Python3 が見つかりません"
    exit 1
fi

export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

WORK_DIR="${1:-$(pwd)}"
exec python3 -m yadon_agents.cli start "$WORK_DIR"
