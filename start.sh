#!/bin/bash

# ヤドン・エージェント 起動スクリプト
# デーモン(ヤドラン + ヤドン1〜4) + ペット を起動する

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# PIDファイルディレクトリ
PID_DIR="$SCRIPT_DIR/.pids"
mkdir -p "$PID_DIR"

# ログディレクトリ
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

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

# Python3の確認
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}エラー${NC} Python3 が見つかりません"
    exit 1
fi

# 既存プロセスの停止
echo "既存プロセスを確認中..."
"$SCRIPT_DIR/stop.sh" 2>/dev/null || true
echo ""

# =============================================================
# 1. ヤドン1〜4 起動
#    PyQt6あり → ペット（エージェントソケット内蔵）
#    PyQt6なし → スタンドアロンデーモン
# =============================================================
HAS_PYQT6=false
if python3 -c "import PyQt6" 2>/dev/null; then
    HAS_PYQT6=true
fi

if $HAS_PYQT6; then
    echo -e "${CYAN}ヤドンペット+デーモンを起動中...${NC}"
    for YADON_NUM in 1 2 3 4; do
        python3 "$SCRIPT_DIR/pet/yadon_pet.py" \
            --number "$YADON_NUM" \
            >> "$LOG_DIR/yadon-${YADON_NUM}.log" 2>&1 &
        YADON_PID=$!
        echo "$YADON_PID" > "$PID_DIR/yadon-${YADON_NUM}.pid"
        echo "  ヤドン${YADON_NUM}: ペット+デーモン PID=$YADON_PID"
    done
else
    echo -e "${CYAN}ヤドンデーモンを起動中...${NC}"
    echo -e "${YELLOW}!${NC} PyQt6なし — デスクトップペットなしで起動"
    for YADON_NUM in 1 2 3 4; do
        python3 "$SCRIPT_DIR/daemons/yadon_daemon.py" --number "$YADON_NUM" \
            >> "$LOG_DIR/yadon-${YADON_NUM}.log" 2>&1 &
        YADON_PID=$!
        echo "$YADON_PID" > "$PID_DIR/yadon-${YADON_NUM}.pid"
        echo "  ヤドン${YADON_NUM}: デーモン PID=$YADON_PID"
    done
fi

# ヤドンのソケット起動を待つ
echo -n "  ソケット待機中..."
ALL_READY=false
for i in $(seq 1 30); do
    ALL_READY=true
    for YADON_NUM in 1 2 3 4; do
        if [ ! -S "/tmp/yadon-agent-yadon-${YADON_NUM}.sock" ]; then
            ALL_READY=false
            break
        fi
    done
    if $ALL_READY; then
        echo " OK"
        break
    fi
    sleep 0.5
done
if ! $ALL_READY; then
    echo ""
    echo -e "${YELLOW}!${NC} 一部のヤドンソケットが作成されませんでした"
fi

# =============================================================
# 2. ヤドラン起動
#    PyQt6あり → ペット（エージェントソケット内蔵）
#    PyQt6なし → スタンドアロンデーモン
# =============================================================
if $HAS_PYQT6; then
    echo -e "${CYAN}ヤドランペット+デーモンを起動中...${NC}"
    python3 "$SCRIPT_DIR/pet/yadoran_pet.py" \
        >> "$LOG_DIR/yadoran.log" 2>&1 &
    YADORAN_PID=$!
    echo "$YADORAN_PID" > "$PID_DIR/yadoran.pid"
    echo "  ヤドラン: ペット+デーモン PID=$YADORAN_PID"
else
    echo -e "${CYAN}ヤドランデーモンを起動中...${NC}"
    python3 "$SCRIPT_DIR/daemons/yadoran_daemon.py" \
        >> "$LOG_DIR/yadoran.log" 2>&1 &
    YADORAN_PID=$!
    echo "$YADORAN_PID" > "$PID_DIR/yadoran.pid"
    echo "  ヤドラン: デーモン PID=$YADORAN_PID"
fi

# ヤドランのソケット待機
echo -n "  ソケット待機中..."
for i in $(seq 1 30); do
    if [ -S "/tmp/yadon-agent-yadoran.sock" ]; then
        echo " OK"
        break
    fi
    sleep 0.5
done
if [ ! -S "/tmp/yadon-agent-yadoran.sock" ]; then
    echo ""
    echo -e "${YELLOW}!${NC} ヤドランのソケットが作成されませんでした"
fi

# =============================================================
# 完了
# =============================================================
echo ""
echo -e "${GREEN}OK${NC} 起動完了"
echo ""
echo "ヤドキングを起動するには、別ターミナルで:"
echo "  claude --model opus"
echo ""
echo "ヤドキングからタスクを送信:"
echo "  ./scripts/send_task.sh \"タスク内容\""
echo ""
echo "ステータス確認:"
echo "  ./scripts/check_status.sh"
echo ""
echo "停止:"
echo "  ./stop.sh"
