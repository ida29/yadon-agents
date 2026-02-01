#!/bin/bash
# 1プロセスを停止 → ソケット削除のみ
pkill -f "yadon_agents.cli start" 2>/dev/null || true
for SOCK in /tmp/yadon-agent-*.sock /tmp/yadon-pet-*.sock; do
    [ -S "$SOCK" ] && rm -f "$SOCK" || true
done
