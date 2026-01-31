#!/bin/bash

# ヤドン・エージェント 停止スクリプト

# yadon- で始まるセッションを全て検出して停止
SESSIONS=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep '^yadon-' || true)

if [ -z "$SESSIONS" ]; then
    # 後方互換: 旧名 "yadon" セッションも確認
    if tmux has-session -t yadon 2>/dev/null; then
        tmux kill-session -t yadon
        echo "yadon セッションを終了しました"
    else
        echo "yadon セッションは存在しません"
    fi
else
    for SESSION in $SESSIONS; do
        tmux kill-session -t "$SESSION"
        echo "$SESSION セッションを終了しました"
    done
fi

# ロックファイルのクリーンアップ
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_FILE="$SCRIPT_DIR/.verification_running"
if [ -f "$LOCK_FILE" ]; then
    rm -f "$LOCK_FILE"
    echo "ロックファイルを削除しました"
fi
