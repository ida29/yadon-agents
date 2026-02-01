#!/bin/bash

# ヤドン・エージェント 停止スクリプト
# `yadon stop` のシェルラッパー

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

# CLI経由で停止
if python3 -c "import yadon_agents" 2>/dev/null; then
    python3 -m yadon_agents.cli stop
    exit 0
fi

# フォールバック: 直接停止
PID_DIR="$SCRIPT_DIR/.pids"

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

for YADON_NUM in 1 2 3 4; do
    stop_daemon "yadon-${YADON_NUM}"
done
stop_daemon "yadoran"

# フォールバック: プロセス名で残存プロセスを停止
for pattern in yadon_daemon.py yadoran_daemon.py yadon_pet.py yadoran_pet.py \
               yadon_agents.gui.yadon_pet yadon_agents.gui.yadoran_pet \
               yadon_agents.agent.worker yadon_agents.agent.manager; do
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        pkill -f "$pattern" 2>/dev/null || true
    fi
done

# ソケットのクリーンアップ
for SOCK in /tmp/yadon-agent-*.sock /tmp/yadon-pet-*.sock; do
    if [ -S "$SOCK" ] 2>/dev/null; then
        rm -f "$SOCK"
    fi
done

echo "停止完了"
