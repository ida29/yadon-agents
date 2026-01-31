#!/bin/bash

# ヤドン・エージェント 起動スクリプト

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# プロジェクトディレクトリの決定（引数があればそれを使用、なければ現在のディレクトリ）
if [ -n "$1" ]; then
    PROJECT_DIR="$(cd "$1" && pwd)"
else
    PROJECT_DIR="$(pwd)"
fi

# プロジェクト名の取得（ディレクトリのbasename）
PROJECT_NAME="$(basename "$PROJECT_DIR")"

# セッション名の生成
SESSION_NAME="yadon-$PROJECT_NAME"

# panes.yaml のパス
PANES_YAML="$SCRIPT_DIR/config/panes-$PROJECT_NAME.yaml"

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
echo -e "${CYAN}プロジェクト:${NC} $PROJECT_NAME"
echo -e "${CYAN}セッション名:${NC} $SESSION_NAME"
echo -e "${CYAN}作業ディレクトリ:${NC} $PROJECT_DIR"
echo ""

# Claude Code CLI の確認
if ! command -v claude &> /dev/null; then
    echo -e "${RED}エラー${NC} Claude Code CLI が見つかりません"
    echo "  npm install -g @anthropic-ai/claude-code でインストールしてください"
    exit 1
fi

# 既存セッションの確認と終了
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo -e "${YELLOW}!${NC} 既存の $SESSION_NAME セッションを終了します..."
    tmux kill-session -t "$SESSION_NAME"
fi

echo "セッションを作成中..."
echo ""

# Claudeの起動を待つ関数
wait_for_claude() {
    local target=$1
    local max_wait=60
    local count=0
    while [ $count -lt $max_wait ]; do
        # Claude Codeのステータスバーを検出（モデル名）
        if tmux capture-pane -t "$target" -p 2>/dev/null | grep -qE "(Opus|Sonnet|Haiku)"; then
            sleep 1
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    return 1
}

# エージェント設定（名前:モデル:指示）
# ヤドキング: opus（戦略立案）
# ヤドラン: sonnet（タスク分解・管理）
# ヤドン: haiku（実作業）
declare -a AGENTS=(
    "ヤドキング:opus:instructions/yadoking.md を読んで、ヤドキングとして振る舞ってください"
    "ヤドラン:sonnet:instructions/yadoran.md を読んで、ヤドランとして振る舞ってください"
    "ヤドン1:haiku:instructions/yadon.md を読んで、ヤドン1として振る舞ってください。あなたの番号は1です。"
    "ヤドン2:haiku:instructions/yadon.md を読んで、ヤドン2として振る舞ってください。あなたの番号は2です。"
    "ヤドン3:haiku:instructions/yadon.md を読んで、ヤドン3として振る舞ってください。あなたの番号は3です。"
    "ヤドン4:haiku:instructions/yadon_pokoa.md を読んで、ヤドン4として振る舞ってください。あなたの番号は4です。"
)

# セッション作成（大きめのサイズ）
tmux new-session -d -s "$SESSION_NAME" -x 400 -y 100 -c "$PROJECT_DIR"

# レイアウト作成
# ┌───────────┬───────────┐
# │ ヤドキング │  ヤドラン  │  (各1/4 = 50%幅)
# ├─────┬─────┼─────┬─────┤
# │ Y1  │ Y2  │ Y3  │ Y4  │  (各1/8 = 25%幅)
# └─────┴─────┴─────┴─────┘

echo "ペインを作成中..."

# レイアウト:
# ┌───────────┬───────────┐
# │ ヤドキング │  ヤドラン  │  (各1/4 高さ)
# ├───────────┼───────────┤
# │  ヤドン1   │  ヤドン3   │  (各1/8 高さ)
# ├───────────┼───────────┤
# │  ヤドン2   │  ヤドン4   │  (各1/8 高さ)
# └───────────┴───────────┘

# まず左右に分割（50:50）
tmux split-window -h -t yadon -c "$PROJECT_DIR" -p 50

# 左側（ペイン0）を縦に3分割
# ヤドキング(50%) | ヤドン1(25%) | ヤドン2(25%)
PANE_LEFT=$(tmux list-panes -t "$SESSION_NAME" -F '#{pane_id}' | head -1)
PANE_RIGHT=$(tmux list-panes -t "$SESSION_NAME" -F '#{pane_id}' | tail -1)

# 左側: 下半分を分割
tmux split-window -v -t "$PANE_LEFT" -c "$PROJECT_DIR" -p 50
PANE_LEFT_BOTTOM=$(tmux list-panes -t "$SESSION_NAME" -F '#{pane_id}' | sed -n '2p')
# 左下をさらに分割
tmux split-window -v -t "$PANE_LEFT_BOTTOM" -c "$PROJECT_DIR" -p 50

# 右側: 下半分を分割
tmux split-window -v -t "$PANE_RIGHT" -c "$PROJECT_DIR" -p 50
PANE_RIGHT_BOTTOM=$(tmux list-panes -t "$SESSION_NAME" -F '#{pane_id}' | tail -1)
# 右下をさらに分割
tmux split-window -v -t "$PANE_RIGHT_BOTTOM" -c "$PROJECT_DIR" -p 50

# ペインを作成順に記録
# 最初のペインはヤドキング
ALL_PANES=($(tmux list-panes -t "$SESSION_NAME" -F '#{pane_id}'))
YADOKING_PANE="${ALL_PANES[0]}"

# 右分割で作成したのがヤドラン
YADORAN_PANE="$PANE_RIGHT"

# 左側を縦分割したペインがヤドン1
YADON1_PANE="$PANE_LEFT_BOTTOM"

# 左下をさらに分割したのがヤドン2
# （この時点で tail -1 で取得）
YADON2_PANE=$(tmux list-panes -t "$SESSION_NAME" -F '#{pane_id}' | sed -n '4p')

# 右側を縦分割したペインがヤドン3
YADON3_PANE=$(tmux list-panes -t "$SESSION_NAME" -F '#{pane_id}' | sed -n '3p')

# 右下をさらに分割したのがヤドン4
YADON4_PANE=$(tmux list-panes -t "$SESSION_NAME" -F '#{pane_id}' | sed -n '6p')

# 視覚的レイアウト:
# ┌───────────┬───────────┐
# │ [0]ヤドキング │ [1]ヤドラン │
# ├───────────┼───────────┤
# │ [2]ヤドン1  │ [3]ヤドン3 │
# ├───────────┼───────────┤
# │ [4]ヤドン2  │ [5]ヤドン4 │
# └───────────┴───────────┘
PANE_IDS=(
    "$YADOKING_PANE"
    "$YADORAN_PANE"
    "$YADON1_PANE"
    "$YADON2_PANE"
    "$YADON3_PANE"
    "$YADON4_PANE"
)

# ペインIDを設定ファイルに保存（エージェント間通信用）
cat > "$PANES_YAML" << EOF
# 自動生成: エージェントのペインID
# start.sh によって起動時に更新される
yadoking: "${PANE_IDS[0]}"
yadoran: "${PANE_IDS[1]}"
yadon1: "${PANE_IDS[2]}"
yadon2: "${PANE_IDS[3]}"
yadon3: "${PANE_IDS[4]}"
yadon4: "${PANE_IDS[5]}"
EOF
echo "ペインID設定を保存: $PANES_YAML"

# 各ペインにタイトルを設定（名前とモデル）
TITLES=("ヤドキング(opus)" "ヤドラン(sonnet)" "ヤドン1(haiku)" "ヤドン2(haiku)" "ヤドン3(haiku)" "ヤドン4(haiku)")
for i in {0..5}; do
    tmux select-pane -t "${PANE_IDS[$i]}" -T "${TITLES[$i]}"
done

# ペインタイトルを表示する設定
tmux set-option -t "$SESSION_NAME" pane-border-status top
tmux set-option -t "$SESSION_NAME" pane-border-format " #{pane_index}: #{pane_title} "

# 全ペインでClaudeを起動（並列、許可確認スキップ、モデル指定）
echo "Claudeを起動中（並列）..."
for i in {0..5}; do
    IFS=':' read -r name model instruction <<< "${AGENTS[$i]}"
    tmux send-keys -t "${PANE_IDS[$i]}" "claude --dangerously-skip-permissions --model $model" Enter
done

# 全Claudeの起動を並列で待機
echo -n "起動を待機中..."
for i in {0..5}; do
    wait_for_claude "${PANE_IDS[$i]}" &
done
wait
echo " OK"

# 各ペインに指示を送信（並列）
echo "指示を送信中..."
for i in {0..5}; do
    IFS=':' read -r name model instruction <<< "${AGENTS[$i]}"
    tmux send-keys -t "${PANE_IDS[$i]}" "$instruction"
    tmux send-keys -t "${PANE_IDS[$i]}" Enter
done
echo "完了"

# 最初のペイン（ヤドキング）を選択
tmux select-pane -t "${PANE_IDS[0]}"

echo ""
echo -e "${GREEN}OK${NC} 起動完了"
echo ""
echo "レイアウト:"
echo "  ┌───────────┬───────────┐"
echo "  │ ヤドキング │  ヤドラン  │"
echo "  ├───────────┼───────────┤"
echo "  │  ヤドン1   │  ヤドン3   │"
echo "  ├───────────┼───────────┤"
echo "  │  ヤドン2   │  ヤドン4   │"
echo "  └───────────┴───────────┘"
echo ""
echo "操作方法:"
echo ""
echo "   Ctrl+b d       : デタッチ（バックグラウンドに戻す）"
echo "   Ctrl+b 矢印    : ペイン移動"
echo "   Ctrl+b q       : ペイン番号を表示"
echo "   Ctrl+b z       : ペインをズーム（もう一度で戻る）"
echo ""
echo "接続しますか？ [Y/n]"
read -r response

if [[ "$response" =~ ^[Nn]$ ]]; then
    echo ""
    echo "   ...ヤド...じゃあ待ってる..."
    echo "   tmux attach-session -t $SESSION_NAME で接続できます"
else
    tmux attach-session -t "$SESSION_NAME"
fi
