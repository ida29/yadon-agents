#!/bin/bash

# ヤドン・エージェント 初回セットアップスクリプト
# ...ヤド...セットアップするよ...

set -e

echo "🐚 ヤドン・エージェント セットアップ開始..."
echo "   ...ゆっくりやっていくよ..."
echo ""

# カラー設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# OS判定
OS="$(uname -s)"

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 は既にインストールされています"
        return 0
    else
        echo -e "${YELLOW}!${NC} $1 が見つかりません"
        return 1
    fi
}

# 1. tmux のインストール確認
echo "📦 必要なツールを確認中..."
echo ""

if ! check_command tmux; then
    echo "  tmux をインストールします..."
    if [ "$OS" = "Darwin" ]; then
        if check_command brew; then
            brew install tmux
        else
            echo -e "${RED}✗${NC} Homebrew がインストールされていません"
            echo "  先に Homebrew をインストールしてください:"
            echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    elif [ "$OS" = "Linux" ]; then
        if check_command apt-get; then
            sudo apt-get update && sudo apt-get install -y tmux
        elif check_command yum; then
            sudo yum install -y tmux
        else
            echo -e "${RED}✗${NC} パッケージマネージャが見つかりません"
            exit 1
        fi
    fi
fi

# 2. Node.js のインストール確認
if ! check_command node; then
    echo "  Node.js をインストールします..."
    if [ "$OS" = "Darwin" ]; then
        brew install node
    elif [ "$OS" = "Linux" ]; then
        curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
fi

# 3. Claude Code CLI の確認
if ! check_command claude; then
    echo ""
    echo -e "${YELLOW}!${NC} Claude Code CLI が見つかりません"
    echo "  以下のコマンドでインストールしてください:"
    echo ""
    echo "  npm install -g @anthropic-ai/claude-code"
    echo ""
    echo "  インストール後、再度このスクリプトを実行してください"
    exit 1
fi

echo ""
echo "📁 ディレクトリ構造を確認中..."

# ディレクトリ作成（既に存在する場合はスキップ）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

dirs=(
    "config"
    "instructions"
    "queue/tasks"
    "queue/reports"
    "context"
    "memory"
    "templates"
    "status"
    "skills"
)

for dir in "${dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GREEN}✓${NC} $dir を作成しました"
    else
        echo -e "${GREEN}✓${NC} $dir は既に存在します"
    fi
done

# 4. エイリアス設定の提案
echo ""
echo "📝 便利なエイリアスを設定しますか？"
echo ""
echo "  以下の行を ~/.bashrc または ~/.zshrc に追加することをおすすめします:"
echo ""
echo "  # ヤドン・エージェント"
echo "  alias yadon='cd $SCRIPT_DIR && ./start.sh'"
echo "  alias yadoking='tmux attach-session -t yadoking'"
echo "  alias yadon-status='tmux attach-session -t multiagent'"
echo ""

# 5. 完了メッセージ
echo ""
echo -e "${GREEN}✓${NC} セットアップ完了！"
echo ""
echo "🐚 次のステップ:"
echo "   1. ./start.sh を実行してエージェントを起動"
echo "   2. yadoking セッションに接続して指示を出す"
echo ""
echo "   ...ヤド...準備できた..."
