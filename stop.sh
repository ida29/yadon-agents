#!/bin/bash
set -euo pipefail

# ヤドン・エージェント 停止スクリプト
# GUIデーモン + CLI プロセスを pkill で停止し、ソケットをクリーンアップする

echo "停止中..."

# GUIデーモンプロセスを停止
pkill -f "yadon_agents.gui_daemon" 2>/dev/null || true

# CLIプロセスを停止
pkill -f "yadon_agents.cli start" 2>/dev/null || true

# ソケットのクリーンアップ
for SOCK in /tmp/yadon-agent-*.sock /tmp/yadon-pet-*.sock; do
    [ -S "$SOCK" ] && rm -f "$SOCK" || true
done

echo "停止完了"
