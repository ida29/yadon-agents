#!/usr/bin/env python3
"""yadon CLI -- マルチエージェント起動/停止

使用法:
    yadon start [work_dir]  -- 全エージェント起動
    yadon stop              -- 全エージェント停止
"""

from __future__ import annotations

import argparse
import os
import signal
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
from yadon_agents.infra.process import (
    log_dir,
    save_pid,
    start_background,
    stop_daemons,
)
from yadon_agents.themes import get_theme


def _has_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


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
    """全エージェント起動"""
    theme = get_theme()
    yadon_count = get_yadon_count()
    worker_role = theme.agent_role_worker
    manager_role = theme.agent_role_manager
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

    use_gui = _has_pyqt6()
    logs = log_dir()

    # --- ワーカー 1-N 起動 ---
    if use_gui:
        print(f"\033[0;36m{theme.role_names.worker}ペット+デーモンを起動中...\033[0m")
        for n in range(1, yadon_count + 1):
            cmd = [sys.executable, "-m", "yadon_agents.gui.yadon_pet", "--number", str(n)]
            pid = start_background(cmd, logs / f"{worker_role}-{n}.log")
            save_pid(f"{worker_role}-{n}", pid)
            print(f"  {theme.role_names.worker}{n}: ペット+デーモン PID={pid}")
    else:
        print(f"\033[0;36m{theme.role_names.worker}デーモンを起動中...\033[0m")
        print("\033[1;33m!\033[0m PyQt6なし -- デスクトップペットなしで起動")
        for n in range(1, yadon_count + 1):
            cmd = [sys.executable, "-m", "yadon_agents.agent.worker", "--number", str(n)]
            pid = start_background(cmd, logs / f"{worker_role}-{n}.log")
            save_pid(f"{worker_role}-{n}", pid)
            print(f"  {theme.role_names.worker}{n}: デーモン PID={pid}")

    # ソケット待機
    worker_names = [f"{worker_role}-{n}" for n in range(1, yadon_count + 1)]
    print("  ソケット待機中...", end="", flush=True)
    if _wait_sockets(worker_names, prefix=prefix):
        print(" OK")
    else:
        print()
        print(f"\033[1;33m!\033[0m 一部の{theme.role_names.worker}ソケットが作成されませんでした")

    # --- マネージャー起動 ---
    if use_gui:
        print(f"\033[0;36m{theme.role_names.manager}ペット+デーモンを起動中...\033[0m")
        cmd = [sys.executable, "-m", "yadon_agents.gui.yadoran_pet"]
        pid = start_background(cmd, logs / f"{manager_role}.log")
        save_pid(manager_role, pid)
        print(f"  {theme.role_names.manager}: ペット+デーモン PID={pid}")
    else:
        print(f"\033[0;36m{theme.role_names.manager}デーモンを起動中...\033[0m")
        cmd = [sys.executable, "-m", "yadon_agents.agent.manager"]
        pid = start_background(cmd, logs / f"{manager_role}.log")
        save_pid(manager_role, pid)
        print(f"  {theme.role_names.manager}: デーモン PID={pid}")

    print("  ソケット待機中...", end="", flush=True)
    if _wait_sockets([manager_role], prefix=prefix):
        print(" OK")
    else:
        print()
        print(f"\033[1;33m!\033[0m {theme.role_names.manager}のソケットが作成されませんでした")

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

    def _sigterm_handler(signum, frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _sigterm_handler)

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
    except SystemExit:
        exit_code = 0
    finally:
        print()
        print(f"{theme.role_names.coordinator}終了 -- デーモン+ペットを停止中...")
        cmd_stop()

    sys.exit(exit_code)


def cmd_stop() -> None:
    """全エージェント停止"""
    theme = get_theme()
    print("停止中...")

    yadon_count = get_yadon_count()
    worker_role = theme.agent_role_worker
    manager_role = theme.agent_role_manager
    all_names = [f"{worker_role}-{n}" for n in range(1, yadon_count + 1)] + [manager_role]
    stop_daemons(all_names)

    # フォールバック: プロセス名で残存プロセスを停止
    for pattern in ["yadon_pet", "yadoran_pet", "yadon_daemon", "yadoran_daemon",
                    "yadon_agents.gui.yadon_pet", "yadon_agents.gui.yadoran_pet",
                    "yadon_agents.agent.worker", "yadon_agents.agent.manager"]:
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
