"""プロセス管理 — PID追跡・バックグラウンドプロセス起動/停止"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from yadon_agents import PROJECT_ROOT
from yadon_agents.config.agent import PROCESS_STOP_INTERVAL, PROCESS_STOP_RETRIES

__all__ = [
    "pid_dir",
    "log_dir",
    "save_pid",
    "read_pid",
    "start_background",
    "stop_daemons",
]


def pid_dir() -> Path:
    """PIDファイルディレクトリを返す（なければ作成）。"""
    d = PROJECT_ROOT / ".pids"
    d.mkdir(exist_ok=True)
    return d


def log_dir() -> Path:
    """ログファイルディレクトリを返す（なければ作成）。"""
    d = PROJECT_ROOT / "logs"
    d.mkdir(exist_ok=True)
    return d


def save_pid(name: str, pid: int) -> None:
    """PIDファイルに書き込む。"""
    (pid_dir() / f"{name}.pid").write_text(str(pid))


def read_pid(name: str) -> int | None:
    """PIDファイルを読み、プロセスが生存していればPIDを返す。"""
    pid_file = pid_dir() / f"{name}.pid"
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
    except ValueError:
        pid_file.unlink(missing_ok=True)
        return None
    try:
        os.kill(pid, 0)
        return pid
    except OSError:
        pid_file.unlink(missing_ok=True)
        return None


def _ensure_pythonpath() -> dict[str, str]:
    """PYTHONPATHにsrc/を含む環境変数を返す。"""
    env = os.environ.copy()
    src_dir = str(PROJECT_ROOT / "src")
    current = env.get("PYTHONPATH", "")
    if src_dir not in current:
        env["PYTHONPATH"] = f"{src_dir}:{current}" if current else src_dir
    return env


def start_background(cmd: list[str], log_path: Path) -> int:
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


def stop_daemons(names: list[str]) -> None:
    """全デーモンにSIGTERMを送信し、並列に終了を待つ。"""
    # 生存中のプロセスを収集 & 一斉にSIGTERM送信
    targets: list[tuple[str, int]] = []
    for name in names:
        pid = read_pid(name)
        if pid is not None:
            os.kill(pid, signal.SIGTERM)
            targets.append((name, pid))

    if not targets:
        return

    # 全プロセスの終了を待つ（最大 PROCESS_STOP_RETRIES * PROCESS_STOP_INTERVAL 秒）
    remaining = list(targets)
    for _ in range(PROCESS_STOP_RETRIES):
        if not remaining:
            break
        time.sleep(PROCESS_STOP_INTERVAL)
        still_alive = []
        for name, pid in remaining:
            try:
                os.kill(pid, 0)
                still_alive.append((name, pid))
            except OSError:
                print(f"  {name}: 停止 (PID={pid})")
                (pid_dir() / f"{name}.pid").unlink(missing_ok=True)
        remaining = still_alive

    # タイムアウト — 残存プロセスをSIGKILL
    for name, pid in remaining:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        print(f"  {name}: 強制停止 (PID={pid})")
        (pid_dir() / f"{name}.pid").unlink(missing_ok=True)
