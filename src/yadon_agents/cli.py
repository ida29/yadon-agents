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
import subprocess
import sys
import time
from pathlib import Path

from yadon_agents import PROJECT_ROOT
from yadon_agents.config.agent import (
    SOCKET_WAIT_INTERVAL,
    SOCKET_WAIT_TIMEOUT,
    get_yadon_count,
)
from yadon_agents.config.llm import get_backend_name
from yadon_agents.infra.claude_runner import SubprocessClaudeRunner
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
    """全エージェント起動（GUIは別プロセス）"""
    from yadon_agents.ascii_art import show_yadon_ascii

    theme = get_theme()
    yadon_count = get_yadon_count()
    coordinator_role = theme.agent_role_coordinator
    prefix = theme.socket_prefix

    # ヤドンのドット絵を表示
    show_yadon_ascii()

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

    # GUIデーモンを別プロセスで起動
    print(f"\033[0;36mGUIデーモンを起動中...\033[0m")
    log_file = open(log_dir() / "gui_daemon.log", "a")
    try:
        gui_process = subprocess.Popen(
            [sys.executable, "-m", "yadon_agents.gui_daemon"],
            stdout=subprocess.DEVNULL,
            stderr=log_file,
            start_new_session=True,  # 完全に独立したプロセスグループ
        )
        print(f"  GUI PID: {gui_process.pid}")

        # ソケット待機
        worker_role = theme.agent_role_worker
        manager_role = theme.agent_role_manager
        worker_names = [f"{worker_role}-{n}" for n in range(1, yadon_count + 1)]
        all_agents = worker_names + [manager_role]

        print(f"\033[0;36mエージェントソケット待機中...\033[0m", end="", flush=True)
        if _wait_sockets(all_agents, prefix=prefix):
            print(" OK")
        else:
            print()
            print(f"\033[1;33m!\033[0m 一部のエージェントソケットが作成されませんでした")

        # --- コーディネーター起動 ---
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

        # コーディネーター起動（ブロッキング）
        try:
            runner = SubprocessClaudeRunner()
            cmd = runner.build_interactive_command(model_tier="coordinator")
            cmd.extend(["--append-system-prompt", system_prompt])

            # Claude専用フラグを追加
            if get_backend_name() == "claude":
                cmd.append("--dangerously-skip-permissions")

            result = subprocess.run(
                cmd,
                cwd=work_dir,
                env=env,
            )
            exit_code = result.returncode
        except KeyboardInterrupt:
            exit_code = 0

        # --- 終了処理 ---
        print()
        print(f"{theme.role_names.coordinator}終了 -- GUIデーモンを停止中...")

        # GUIプロセスを停止
        try:
            gui_process.terminate()
            gui_process.wait(timeout=5)
        except Exception:
            try:
                gui_process.kill()
            except Exception:
                pass
        _cleanup_sockets(prefix=prefix)
        print("停止完了")
    finally:
        log_file.close()

    sys.exit(exit_code)


def cmd_stop() -> None:
    """全エージェント停止"""
    theme = get_theme()
    print("停止中...")

    # プロセス名で残存プロセスを停止
    for pattern in ["yadon_agents.cli start", "yadon_agents.gui_daemon"]:
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
