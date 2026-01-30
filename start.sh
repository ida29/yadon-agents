#!/bin/bash

# ヤドン・エージェント 起動スクリプト
# ...ヤド...起動するよ...

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# カラー設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}ヤドン・エージェント 起動中...${NC}"
echo "   困ったなぁ...でもやるか..."
echo ""

# Claude Code CLI の確認
if ! command -v claude &> /dev/null; then
    echo -e "${RED}✗${NC} Claude Code CLI が見つかりません"
    echo "  npm install -g @anthropic-ai/claude-code でインストールしてください"
    exit 1
fi

# 既存セッションの確認と終了
if tmux has-session -t yadon 2>/dev/null; then
    echo -e "${YELLOW}!${NC} 既存の yadon セッションを終了します..."
    tmux kill-session -t yadon
fi

echo "セッションを作成中..."
echo ""

# yadon セッション作成（全員を1つのセッションに）
tmux new-session -d -s yadon -c "$SCRIPT_DIR"

# ウィンドウ名を設定
tmux rename-window -t yadon "ヤドン・エージェント"

# Claudeの起動を待つ関数
wait_for_claude() {
    local pane=$1
    local max_wait=60
    local count=0
    while [ $count -lt $max_wait ]; do
        # Claude Code特有の表示を検出
        if tmux capture-pane -t "$pane" -p | grep -qE "(^>|Tips for|Claude Code)"; then
            sleep 1
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    echo "Warning: Claude may not be ready in pane $pane"
}

# 全ペインを先に作成
echo "ペインを作成中..."
for i in {1..9}; do
    tmux split-window -t yadon -c "$SCRIPT_DIR"
done
tmux select-layout -t yadon tiled

# 全ペインでClaudeを起動（並列）
echo "Claudeを起動中..."
for i in {0..9}; do
    tmux send-keys -t yadon:0.${i} "claude" Enter
done

# 全Claudeの起動を待つ
echo "起動を待機中..."
for i in {0..9}; do
    wait_for_claude "yadon:0.${i}"
    echo "  ペイン${i} 準備完了"
done

# 各ペインに指示を送信
echo -e "${GREEN}ヤドキング${NC} に指示..."
tmux send-keys -t yadon:0.0 "instructions/yadoking.md を読んで、ヤドキングとして振る舞ってください" Enter

echo -e "${GREEN}ヤドラン${NC} に指示..."
tmux send-keys -t yadon:0.1 "instructions/yadoran.md を読んで、ヤドランとして振る舞ってください" Enter

echo -e "${GREEN}ヤドン x8${NC} に指示..."
for i in {1..7}; do
    pane_num=$((i + 1))
    tmux send-keys -t yadon:0.${pane_num} "instructions/yadon.md を読んで、ヤドン${i}として振る舞ってください。あなたの番号は${i}です。" Enter
done

# ヤドン8はぽこあポケモン風ヤドン
tmux send-keys -t yadon:0.9 "instructions/yadon_pokoa.md を読んで、ヤドン8として振る舞ってください。あなたの番号は8です。" Enter

# ヤドキングのペインを選択状態に
tmux select-pane -t yadon:0.0

echo ""
echo -e "${GREEN}OK${NC} 起動完了"
echo ""
echo "レイアウト:"
echo ""
echo "   ┌─────────┬─────────┬─────────┐"
echo "   │ヤドキング│ ヤドラン │  ヤドン1 │"
echo "   ├─────────┼─────────┼─────────┤"
echo "   │ ヤドン2 │ ヤドン3 │  ヤドン4 │"
echo "   ├─────────┼─────────┼─────────┤"
echo "   │ ヤドン5 │ ヤドン6 │  ヤドン7 │"
echo "   ├─────────┴─────────┴─────────┤"
echo "   │      ヤドン8(pokoa)          │"
echo "   └─────────────────────────────┘"
echo ""
echo "操作方法:"
echo ""
echo "   Ctrl+b d      : デタッチ（バックグラウンドに戻す）"
echo "   Ctrl+b 矢印   : ペイン移動"
echo "   Ctrl+b z      : ペインをズーム（もう一度で戻る）"
echo "   Ctrl+b q      : ペイン番号を表示"
echo ""
echo "接続しますか？ [Y/n]"
read -r response

if [[ "$response" =~ ^[Nn]$ ]]; then
    echo ""
    echo "   ...ヤド...じゃあ待ってる..."
    echo "   tmux attach-session -t yadon で接続できます"
else
    tmux attach-session -t yadon
fi
