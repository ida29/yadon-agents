#!/bin/bash
# デーモン（ヤドラン + ヤドン1〜4）の再起動スクリプト
#
# ヤドキング実行中にデーモンだけ再起動したいときに使う。
# stop.sh → デーモン起動 の順で実行する。
#
# 使用法: restart_daemons.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

PID_DIR="$ROOT_DIR/.pids"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}デーモン再起動中...${NC}"

# 既存デーモンを停止
"$ROOT_DIR/stop.sh" 2>/dev/null || true
echo ""

# PyQt6チェック
HAS_PYQT6=false
if python3 -c "import PyQt6" 2>/dev/null; then
    HAS_PYQT6=true
fi

# ヤドン1〜4起動
if $HAS_PYQT6; then
    echo -e "${CYAN}ヤドンペット+デーモンを起動中...${NC}"
    for YADON_NUM in 1 2 3 4; do
        python3 -m yadon_agents.gui.yadon_pet \
            --number "$YADON_NUM" \
            >> "$LOG_DIR/yadon-${YADON_NUM}.log" 2>&1 &
        YADON_PID=$!
        echo "$YADON_PID" > "$PID_DIR/yadon-${YADON_NUM}.pid"
        echo "  ヤドン${YADON_NUM}: PID=$YADON_PID"
    done
else
    echo -e "${CYAN}ヤドンデーモンを起動中...${NC}"
    for YADON_NUM in 1 2 3 4; do
        python3 -m yadon_agents.agent.worker --number "$YADON_NUM" \
            >> "$LOG_DIR/yadon-${YADON_NUM}.log" 2>&1 &
        YADON_PID=$!
        echo "$YADON_PID" > "$PID_DIR/yadon-${YADON_NUM}.pid"
        echo "  ヤドン${YADON_NUM}: PID=$YADON_PID"
    done
fi

# ヤドンソケット待機
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

# ヤドラン起動
if $HAS_PYQT6; then
    echo -e "${CYAN}ヤドランペット+デーモンを起動中...${NC}"
    python3 -m yadon_agents.gui.yadoran_pet \
        >> "$LOG_DIR/yadoran.log" 2>&1 &
    YADORAN_PID=$!
    echo "$YADORAN_PID" > "$PID_DIR/yadoran.pid"
    echo "  ヤドラン: PID=$YADORAN_PID"
else
    echo -e "${CYAN}ヤドランデーモンを起動中...${NC}"
    python3 -m yadon_agents.agent.manager \
        >> "$LOG_DIR/yadoran.log" 2>&1 &
    YADORAN_PID=$!
    echo "$YADORAN_PID" > "$PID_DIR/yadoran.pid"
    echo "  ヤドラン: PID=$YADORAN_PID"
fi

# ヤドランソケット待機
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

echo ""
echo -e "${GREEN}OK${NC} デーモン再起動完了"
