#!/bin/bash

# ヤドン・エージェント 停止スクリプト

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"

# デーモンの停止（PIDファイル経由）
stop_daemon() {
    local name="$1"
    local pid_file="$PID_DIR/${name}.pid"
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null
            for i in $(seq 1 10); do
                if ! kill -0 "$PID" 2>/dev/null; then
                    break
                fi
                sleep 0.5
            done
            if kill -0 "$PID" 2>/dev/null; then
                kill -9 "$PID" 2>/dev/null || true
            fi
            echo "  ${name}: 停止 (PID=$PID)"
        fi
        rm -f "$pid_file"
    fi
}

echo "停止中..."

# ヤドン1〜4停止
for YADON_NUM in 1 2 3 4; do
    stop_daemon "yadon-${YADON_NUM}"
done

# ヤドラン停止
stop_daemon "yadoran"

# フォールバック: プロセス名で残存プロセスを停止
if pgrep -f "yadon_daemon.py" > /dev/null 2>&1; then
    pkill -f "yadon_daemon.py" 2>/dev/null || true
    echo "  yadon_daemon.py 残存プロセスを停止"
fi
if pgrep -f "yadoran_daemon.py" > /dev/null 2>&1; then
    pkill -f "yadoran_daemon.py" 2>/dev/null || true
    echo "  yadoran_daemon.py 残存プロセスを停止"
fi
if pgrep -f "yadon_pet.py" > /dev/null 2>&1; then
    pkill -f "yadon_pet.py" 2>/dev/null || true
    echo "  yadon_pet.py 残存プロセスを停止"
fi
if pgrep -f "yadoran_pet.py" > /dev/null 2>&1; then
    pkill -f "yadoran_pet.py" 2>/dev/null || true
    echo "  yadoran_pet.py 残存プロセスを停止"
fi

# ソケットのクリーンアップ
for SOCK in /tmp/yadon-agent-*.sock /tmp/yadon-pet-*.sock; do
    if [ -S "$SOCK" ] 2>/dev/null; then
        rm -f "$SOCK"
    fi
done

echo "停止完了"
