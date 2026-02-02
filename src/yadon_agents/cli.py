#!/usr/bin/env python3
"""yadon CLI -- マルチエージェント起動/停止

使用法:
    yadon start [work_dir]  -- 全エージェント起動
    yadon stop              -- 全エージェント停止
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from yadon_agents import PROJECT_ROOT
from yadon_agents.config.agent import (
    SOCKET_WAIT_INTERVAL,
    SOCKET_WAIT_TIMEOUT,
    get_yadon_count,
    get_yadon_variant,
)
from yadon_agents.infra.process import log_dir
from yadon_agents.themes import get_theme

logger = logging.getLogger(__name__)


def _wait_sockets(names: list[str], prefix: str = "yadon", timeout: int = SOCKET_WAIT_TIMEOUT) -> bool:
    """ソケットファイルの作成を待つ。"""
    from yadon_agents.infra.protocol import agent_socket_path
    iterations = int(timeout / SOCKET_WAIT_INTERVAL)
    for _ in range(iterations):
        if all(Path(agent_socket_path(n, prefix=prefix)).exists() for n in names):
            return True
        time.sleep(SOCKET_WAIT_INTERVAL)
    return False


def _cleanup_sockets(prefix: str = "yadon") -> None:
    """ソケットファイルを削除する。"""
    tmp = Path("/tmp")
    for pattern in [f"{prefix}-agent-*.sock", f"{prefix}-pet-*.sock"]:
        for sock in tmp.glob(pattern):
            try:
                sock.unlink()
            except OSError:
                pass


def cmd_start(work_dir: str) -> None:
    """全エージェントを1プロセスで起動"""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer, Qt
    from PyQt6.QtGui import QCursor

    from yadon_agents.agent.manager import YadoranManager
    from yadon_agents.agent.worker import YadonWorker
    from yadon_agents.config.ui import WINDOW_WIDTH, WINDOW_HEIGHT
    from yadon_agents.gui.agent_thread import AgentThread
    from yadon_agents.gui.yadon_pet import YadonPet
    from yadon_agents.gui.yadoran_pet import YadoranPet
    from yadon_agents.infra.protocol import pet_socket_path

    theme = get_theme()
    yadon_count = get_yadon_count()
    coordinator_role = theme.agent_role_coordinator
    prefix = theme.socket_prefix

    print()
    print(f"\033[0;36m{theme.display_name} 起動中...\033[0m")
    print("   困ったなぁ...でもやるか...")
    print(f"   {theme.role_names.worker}数: {yadon_count}")
    print()

    # 既存プロセスの停止
    print("既存プロセスを確認中...")
    cmd_stop()
    print()

    # ログディレクトリ確保
    log_dir()

    # --- QApplication 作成 ---
    app = QApplication(sys.argv)

    # macOS: Pythonシグナル処理のためのタイマー
    sig_timer = QTimer()
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start(500)

    screen_obj = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
    screen = screen_obj.geometry()
    margin = 20
    spacing = 10

    # --- ワーカー 1-N 構築 ---
    print(f"\033[0;36m{theme.role_names.worker}を起動中...\033[0m")
    pets: list[YadonPet | YadoranPet] = []

    for n in range(1, yadon_count + 1):
        worker = YadonWorker(n, str(PROJECT_ROOT))
        agent_thread = AgentThread(worker)
        variant = get_yadon_variant(n)

        pet = YadonPet(
            yadon_number=n,
            agent_thread=agent_thread,
            pet_sock_path=pet_socket_path(str(n), prefix=prefix),
            variant=variant,
        )

        x_pos = screen.width() - margin - (WINDOW_WIDTH + spacing) * n
        y_pos = screen.height() - margin - WINDOW_HEIGHT
        pet.move(x_pos, y_pos)
        pets.append(pet)
        print(f"  {theme.role_names.worker}{n}: 起動")

    # ソケット待機
    worker_role = theme.agent_role_worker
    worker_names = [f"{worker_role}-{n}" for n in range(1, yadon_count + 1)]
    print("  ソケット待機中...", end="", flush=True)
    if _wait_sockets(worker_names, prefix=prefix):
        print(" OK")
    else:
        print()
        print(f"\033[1;33m!\033[0m 一部の{theme.role_names.worker}ソケットが作成されませんでした")

    # --- マネージャー構築 ---
    print(f"\033[0;36m{theme.role_names.manager}を起動中...\033[0m")
    manager = YadoranManager(str(PROJECT_ROOT))
    manager_agent_thread = AgentThread(manager)

    manager_pet = YadoranPet(
        agent_thread=manager_agent_thread,
        pet_sock_path=pet_socket_path(theme.agent_role_manager, prefix=prefix),
    )

    x_pos = screen.width() - margin - (WINDOW_WIDTH + spacing) * (yadon_count + 1)
    y_pos = screen.height() - margin - WINDOW_HEIGHT
    manager_pet.move(x_pos, y_pos)
    pets.append(manager_pet)
    print(f"  {theme.role_names.manager}: 起動")

    manager_role = theme.agent_role_manager
    print("  ソケット待機中...", end="", flush=True)
    if _wait_sockets([manager_role], prefix=prefix):
        print(" OK")
    else:
        print()
        print(f"\033[1;33m!\033[0m {theme.role_names.manager}のソケットが作成されませんでした")

    # --- コーディネーター起動準備 ---
    print()
    print(f"\033[0;32mOK\033[0m {theme.role_names.manager}+{theme.role_names.worker}起動完了")
    print()
    print(f"{theme.role_names.coordinator}（claude --model opus）を起動します...")
    print()

    # 指示書読み込み
    instructions_path = PROJECT_ROOT / theme.instructions_coordinator
    if instructions_path.exists():
        system_prompt = instructions_path.read_text()
    else:
        system_prompt = f"あなたは{theme.role_names.coordinator}です。"

    system_prompt += f"""

---
【システム情報】
- 作業ディレクトリ: {work_dir}
- send_task.sh: {PROJECT_ROOT}/scripts/send_task.sh
- check_status.sh: {PROJECT_ROOT}/scripts/check_status.sh
- restart_daemons.sh: {PROJECT_ROOT}/scripts/restart_daemons.sh
- stop.sh: {PROJECT_ROOT}/stop.sh
- スクリプトは上記の絶対パスで実行すること（./scripts/ は使わない）"""

    env = os.environ.copy()
    env["AGENT_ROLE"] = coordinator_role
    env["AGENT_ROLE_LEVEL"] = "coordinator"

    exit_code = 0

    def _run_coordinator() -> None:
        nonlocal exit_code
        try:
            result = subprocess.run(
                [
                    "claude", "--model", "opus",
                    "--dangerously-skip-permissions",
                    "--append-system-prompt", system_prompt,
                ],
                cwd=work_dir,
                env=env,
            )
            exit_code = result.returncode
        except KeyboardInterrupt:
            exit_code = 0
        finally:
            # コーディネーター終了 → Qtイベントループを終了
            QApplication.quit()

    coordinator_thread = threading.Thread(target=_run_coordinator, daemon=True)
    coordinator_thread.start()

    def _sigterm_handler(signum, frame):
        QApplication.quit()

    signal.signal(signal.SIGTERM, _sigterm_handler)

    # --- ウェルカムメッセージ（イベントループ開始後に表示） ---
    def _show_welcome():
        for pet in pets:
            if isinstance(pet, YadoranPet):
                pet.show_bubble(random.choice(theme.manager_welcome_messages), 'normal')
            else:
                pet.show_bubble(random.choice(theme.welcome_messages), 'normal')

    QTimer.singleShot(0, _show_welcome)

    # --- Qtイベントループ（ブロック） ---
    try:
        app.exec()
    except KeyboardInterrupt:
        pass

    # --- 終了処理 ---
    print()
    print(f"{theme.role_names.coordinator}終了 -- ペットを停止中...")

    for pet in reversed(pets):
        pet.close()

    _cleanup_sockets(prefix=prefix)
    print("停止完了")

    sys.exit(exit_code)


def cmd_stop() -> None:
    """全エージェント停止"""
    theme = get_theme()
    print("停止中...")

    # プロセス名で残存プロセスを停止
    for pattern in ["yadon_agents.cli start"]:
        try:
            subprocess.run(
                ["pkill", "-f", pattern],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass

    _cleanup_sockets(prefix=theme.socket_prefix)
    print("停止完了")


def main() -> None:
    theme = get_theme()
    parser = argparse.ArgumentParser(description=f"{theme.display_name} CLI")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="全エージェント起動")
    start_parser.add_argument("work_dir", nargs="?", default=str(Path.cwd()), help="作業ディレクトリ")

    subparsers.add_parser("stop", help="全エージェント停止")

    args = parser.parse_args()

    # デフォルトコマンドは start
    if args.command is None:
        args.command = "start"
        args.work_dir = str(Path.cwd())

    if args.command == "start":
        work_dir = str(Path(args.work_dir).resolve())
        cmd_start(work_dir)
    elif args.command == "stop":
        cmd_stop()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
