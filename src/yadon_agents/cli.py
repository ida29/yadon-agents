#!/usr/bin/env python3
"""yadon CLI — マルチエージェント起動/停止

使用法:
    yadon start [work_dir]  — 全エージェント起動
    yadon stop              — 全エージェント停止
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from yadon_agents.domain.types import YADON_COUNT

# プロジェクトルート（src/yadon_agents/cli.py → 3階層上）
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _pid_dir() -> Path:
    d = PROJECT_ROOT / ".pids"
    d.mkdir(exist_ok=True)
    return d


def _log_dir() -> Path:
    d = PROJECT_ROOT / "logs"
    d.mkdir(exist_ok=True)
    return d


def _has_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def _ensure_pythonpath() -> dict:
    """PYTHONPATHにsrc/を含む環境変数を返す。"""
    env = os.environ.copy()
    src_dir = str(PROJECT_ROOT / "src")
    current = env.get("PYTHONPATH", "")
    if src_dir not in current:
        env["PYTHONPATH"] = f"{src_dir}:{current}" if current else src_dir
    return env


def _start_process(cmd: list[str], log_path: Path) -> int:
    """バックグラウンドプロセスを起動し、PIDを返す。"""
    with open(log_path, "a") as log_f:
        proc = subprocess.Popen(
            cmd,
            stdout=log_f,
            stderr=log_f,
            start_new_session=True,
            env=_ensure_pythonpath(),
        )
    return proc.pid


def _save_pid(name: str, pid: int) -> None:
    (_pid_dir() / f"{name}.pid").write_text(str(pid))


def _stop_daemon(name: str) -> None:
    pid_file = _pid_dir() / f"{name}.pid"
    if not pid_file.exists():
        return
    pid = int(pid_file.read_text().strip())
    try:
        os.kill(pid, 0)  # 生存確認
    except OSError:
        pid_file.unlink(missing_ok=True)
        return

    os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        time.sleep(0.5)
        try:
            os.kill(pid, 0)
        except OSError:
            break
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

    print(f"  {name}: 停止 (PID={pid})")
    pid_file.unlink(missing_ok=True)


def _wait_sockets(names: list[str], timeout: int = 15) -> bool:
    """ソケットファイルの作成を待つ。"""
    from yadon_agents.infra.protocol import agent_socket_path
    for _ in range(timeout * 2):
        if all(os.path.exists(agent_socket_path(n)) for n in names):
            return True
        time.sleep(0.5)
    return False


def _cleanup_sockets() -> None:
    """ソケットファイルを削除する。"""
    import glob
    for pattern in ["/tmp/yadon-agent-*.sock", "/tmp/yadon-pet-*.sock"]:
        for sock in glob.glob(pattern):
            try:
                os.unlink(sock)
            except OSError:
                pass


def cmd_start(work_dir: str) -> None:
    """全エージェント起動"""
    print()
    print("\033[0;36mヤドン・エージェント 起動中...\033[0m")
    print("   困ったなぁ...でもやるか...")
    print()

    # 既存プロセスの停止
    print("既存プロセスを確認中...")
    cmd_stop()
    print()

    use_gui = _has_pyqt6()
    log_dir = _log_dir()

    # --- ヤドン 1-4 起動 ---
    if use_gui:
        print("\033[0;36mヤドンペット+デーモンを起動中...\033[0m")
        for n in range(1, YADON_COUNT + 1):
            cmd = [sys.executable, "-m", "yadon_agents.gui.yadon_pet", "--number", str(n)]
            pid = _start_process(cmd, log_dir / f"yadon-{n}.log")
            _save_pid(f"yadon-{n}", pid)
            print(f"  ヤドン{n}: ペット+デーモン PID={pid}")
    else:
        print("\033[0;36mヤドンデーモンを起動中...\033[0m")
        print("\033[1;33m!\033[0m PyQt6なし — デスクトップペットなしで起動")
        for n in range(1, YADON_COUNT + 1):
            cmd = [sys.executable, "-m", "yadon_agents.agent.worker", "--number", str(n)]
            pid = _start_process(cmd, log_dir / f"yadon-{n}.log")
            _save_pid(f"yadon-{n}", pid)
            print(f"  ヤドン{n}: デーモン PID={pid}")

    # ソケット待機
    yadon_names = [f"yadon-{n}" for n in range(1, YADON_COUNT + 1)]
    print("  ソケット待機中...", end="", flush=True)
    if _wait_sockets(yadon_names):
        print(" OK")
    else:
        print()
        print("\033[1;33m!\033[0m 一部のヤドンソケットが作成されませんでした")

    # --- ヤドラン起動 ---
    if use_gui:
        print("\033[0;36mヤドランペット+デーモンを起動中...\033[0m")
        cmd = [sys.executable, "-m", "yadon_agents.gui.yadoran_pet"]
        pid = _start_process(cmd, log_dir / "yadoran.log")
        _save_pid("yadoran", pid)
        print(f"  ヤドラン: ペット+デーモン PID={pid}")
    else:
        print("\033[0;36mヤドランデーモンを起動中...\033[0m")
        cmd = [sys.executable, "-m", "yadon_agents.agent.manager"]
        pid = _start_process(cmd, log_dir / "yadoran.log")
        _save_pid("yadoran", pid)
        print(f"  ヤドラン: デーモン PID={pid}")

    print("  ソケット待機中...", end="", flush=True)
    if _wait_sockets(["yadoran"]):
        print(" OK")
    else:
        print()
        print("\033[1;33m!\033[0m ヤドランのソケットが作成されませんでした")

    # --- ヤドキング起動 ---
    print()
    print("\033[0;32mOK\033[0m ヤドラン+ヤドン起動完了")
    print()
    print("ヤドキング（claude --model opus）を起動します...")
    print()

    # 指示書読み込み
    instructions_path = PROJECT_ROOT / "instructions" / "yadoking.md"
    if instructions_path.exists():
        system_prompt = instructions_path.read_text()
    else:
        system_prompt = "あなたはヤドキングです。"

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
    env["AGENT_ROLE"] = "yadoking"

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
        print()
        print("ヤドキング終了 — デーモン+ペットを停止中...")
        cmd_stop()

    sys.exit(exit_code)


def cmd_stop() -> None:
    """全エージェント停止"""
    print("停止中...")

    for n in range(1, YADON_COUNT + 1):
        _stop_daemon(f"yadon-{n}")
    _stop_daemon("yadoran")

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

    _cleanup_sockets()
    print("停止完了")


def main() -> None:
    parser = argparse.ArgumentParser(description="ヤドン・エージェント CLI")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="全エージェント起動")
    start_parser.add_argument("work_dir", nargs="?", default=os.getcwd(), help="作業ディレクトリ")

    subparsers.add_parser("stop", help="全エージェント停止")

    args = parser.parse_args()

    if args.command == "start":
        work_dir = os.path.abspath(args.work_dir)
        cmd_start(work_dir)
    elif args.command == "stop":
        cmd_stop()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
