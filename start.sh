#!/bin/bash

# ヤドン・エージェント 起動スクリプト

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
    echo -e "${RED}エラー${NC} Claude Code CLI が見つかりません"
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

# Claudeの起動を待つ関数
wait_for_claude() {
    local target=$1
    local max_wait=60
    local count=0
    while [ $count -lt $max_wait ]; do
        # Claude Codeのステータスバー（Opus）を検出
        if tmux capture-pane -t "$target" -p 2>/dev/null | grep -q "Opus"; then
            sleep 3  # 入力プロンプトが表示されるまで少し待つ
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    echo -e "${YELLOW}Warning${NC}: Claude may not be ready in $target"
}

# エージェント設定
declare -a AGENTS=(
    "ヤドキング:instructions/yadoking.md を読んで、ヤドキングとして振る舞ってください"
    "ヤドラン:instructions/yadoran.md を読んで、ヤドランとして振る舞ってください"
    "ヤドン1:instructions/yadon.md を読んで、ヤドン1として振る舞ってください。あなたの番号は1です。"
    "ヤドン2:instructions/yadon.md を読んで、ヤドン2として振る舞ってください。あなたの番号は2です。"
    "ヤドン3:instructions/yadon.md を読んで、ヤドン3として振る舞ってください。あなたの番号は3です。"
    "ヤドン4:instructions/yadon.md を読んで、ヤドン4として振る舞ってください。あなたの番号は4です。"
    "ヤドン5:instructions/yadon.md を読んで、ヤドン5として振る舞ってください。あなたの番号は5です。"
    "ヤドン6:instructions/yadon.md を読んで、ヤドン6として振る舞ってください。あなたの番号は6です。"
    "ヤドン7:instructions/yadon.md を読んで、ヤドン7として振る舞ってください。あなたの番号は7です。"
    "ヤドン8:instructions/yadon_pokoa.md を読んで、ヤドン8として振る舞ってください。あなたの番号は8です。"
)

# 各エージェント用のウィンドウを作成
for i in "${!AGENTS[@]}"; do
    IFS=':' read -r name instruction <<< "${AGENTS[$i]}"

    if [ $i -eq 0 ]; then
        # 最初のエージェント: セッション作成
        tmux new-session -d -s yadon -n "$name" -x 200 -y 50 -c "$SCRIPT_DIR"
    else
        # 2番目以降: ウィンドウ追加
        tmux new-window -t yadon -n "$name" -c "$SCRIPT_DIR"
    fi
done

# 全ウィンドウでClaudeを起動
echo "Claudeを起動中..."
for i in "${!AGENTS[@]}"; do
    IFS=':' read -r name instruction <<< "${AGENTS[$i]}"
    tmux send-keys -t "yadon:$name" "claude" Enter
done

# 全Claudeの起動を待機
echo "起動を待機中..."
for i in "${!AGENTS[@]}"; do
    IFS=':' read -r name instruction <<< "${AGENTS[$i]}"
    echo -n "  $name..."
    wait_for_claude "yadon:$name"
    echo " OK"
done

# 各ウィンドウに指示を送信
echo "指示を送信中..."
for i in "${!AGENTS[@]}"; do
    IFS=':' read -r name instruction <<< "${AGENTS[$i]}"
    tmux send-keys -t "yadon:$name" "$instruction"
    sleep 0.5
    tmux send-keys -t "yadon:$name" Enter
    echo "  $name に指示を送信"
    sleep 0.5
done

# ヤドキングのウィンドウを選択
tmux select-window -t "yadon:ヤドキング"

echo ""
echo -e "${GREEN}OK${NC} 起動完了"
echo ""
echo "ウィンドウ一覧:"
echo "  0: ヤドキング"
echo "  1: ヤドラン"
echo "  2-9: ヤドン1-8 (ヤドン8はpokoa風)"
echo ""
echo "操作方法:"
echo ""
echo "   Ctrl+b d       : デタッチ（バックグラウンドに戻す）"
echo "   Ctrl+b n/p     : 次/前のウィンドウ"
echo "   Ctrl+b 0-9     : ウィンドウ番号で移動"
echo "   Ctrl+b w       : ウィンドウ一覧"
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
