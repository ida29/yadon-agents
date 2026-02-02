#!/bin/bash
# GUIデーモン分離後の停止スクリプト
# コーディネーター（cli start）とGUIデーモンの両方を停止

pkill -f "yadon_agents.gui_daemon" 2>/dev/null || true
pkill -f "yadon_agents.cli start" 2>/dev/null || true

# ソケットファイルをクリーンアップ
for SOCK in /tmp/yadon-agent-*.sock /tmp/yadon-pet-*.sock; do
    [ -S "$SOCK" ] && rm -f "$SOCK" || true
done
