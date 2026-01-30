#!/bin/bash

# ヤドン・エージェント 停止スクリプト

if tmux has-session -t yadon 2>/dev/null; then
    tmux kill-session -t yadon
    echo "yadon セッションを終了しました"
else
    echo "yadon セッションは存在しません"
fi
