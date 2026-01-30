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

# ペイン0: ヤドキング（左上・大きめ）
echo -e "${GREEN}ヤドキング${NC} を配置..."
tmux send-keys -t yadon "claude" Enter
sleep 3
tmux send-keys -t yadon "instructions/yadoking.md を読んで、ヤドキングとして振る舞ってください" Enter

sleep 2

# ペイン1: ヤドラン（右側）
echo -e "${GREEN}ヤドラン${NC} を配置..."
tmux split-window -h -t yadon -c "$SCRIPT_DIR"
tmux send-keys -t yadon "claude" Enter
sleep 3
tmux send-keys -t yadon "instructions/yadoran.md を読んで、ヤドランとして振る舞ってください" Enter

sleep 2

# ペイン2-9: ヤドン×8（下部に並べる）
echo -e "${GREEN}ヤドン x8${NC} を配置..."
for i in {1..8}; do
    tmux split-window -v -t yadon -c "$SCRIPT_DIR"
    tmux send-keys -t yadon "claude" Enter
    sleep 3
    tmux send-keys -t yadon "instructions/yadon.md を読んで、ヤドン${i}として振る舞ってください。あなたの番号は${i}です。" Enter
    sleep 2
done

# レイアウト調整: tiledで均等配置
tmux select-layout -t yadon tiled

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
echo "   │          ヤドン8             │"
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
