#!/usr/bin/env python3
"""yadon CLI -- マルチエージェント起動/停止

使用法:
    yadon start [work_dir]  -- 全エージェント起動
    yadon stop              -- 全エージェント停止
"""

from __future__ import annotations

import argparse
import importlib.resources
import json
import logging
import os
import socket
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
from yadon_agents.infra.protocol import (
    agent_socket_path,
    pet_socket_path,
    send_message,
)
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


def cmd_start(work_dir: str, multi_llm: bool = False) -> None:
    """全エージェント起動（GUIは別プロセス）"""
    from yadon_agents.ascii_art import show_yadon_ascii

    theme = get_theme()
    yadon_count = get_yadon_count()
    coordinator_role = theme.agent_role_coordinator
    prefix = theme.socket_prefix

    # ワーカーバックエンド環境変数の処理
    backend_rotation = ['copilot', 'gemini', 'claude-opus', 'opencode']
    if multi_llm:
        # マルチLLMモード: ローテーションで環境変数を設定
        # ただし、既に YADON_N_BACKEND が設定されている場合はスキップ
        for i in range(1, yadon_count + 1):
            env_var = f'YADON_{i}_BACKEND'
            if env_var not in os.environ:  # 既に設定されている場合はスキップ
                backend = backend_rotation[(i - 1) % len(backend_rotation)]
                os.environ[env_var] = backend
    else:
        # 通常モード: YADON_N_BACKEND 環境変数をクリア（親シェルの残留値を無効化）
        for i in range(1, yadon_count + 1):
            env_var = f'YADON_{i}_BACKEND'
            if env_var in os.environ:
                del os.environ[env_var]

    # ヤドンのドット絵を表示
    show_yadon_ascii()

    print(f"\033[0;36m{theme.display_name} 起動中...\033[0m")
    print("   困ったなぁ...でもやるか...")
    print(f"   {theme.role_names.worker}数: {yadon_count}")
    if multi_llm:
        print(f"   \033[0;35m【マルチLLMモード有効】\033[0m")
        for i in range(1, yadon_count + 1):
            env_var = f'YADON_{i}_BACKEND'
            # 既に設定されている場合はそれを使用、未設定の場合はローテーション割り当て
            backend = os.environ.get(env_var) or backend_rotation[(i - 1) % len(backend_rotation)]
            print(f"     {theme.role_names.worker}{i}: {backend}")
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
            env=os.environ.copy(),
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
        try:
            files = importlib.resources.files("yadon_agents.instructions")
            instruction_file = files / theme.instructions_coordinator
            system_prompt = instruction_file.read_text(encoding="utf-8")
        except (FileNotFoundError, TypeError):
            system_prompt = f"あなたは{theme.role_names.coordinator}です。"

        system_prompt += f"""

---
【システム情報】
- 作業ディレクトリ: {work_dir}
- タスク送信: yadon _send "タスク内容"
- ステータス確認: yadon _status
- デーモン再起動: yadon _restart
- 全エージェント停止: yadon stop"""

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


def cmd_status(agent_name: str | None = None) -> None:
    """エージェントのステータスを確認"""
    theme = get_theme()
    manager_name = theme.agent_role_manager
    worker_role = theme.agent_role_worker
    prefix = theme.socket_prefix
    yadon_count = get_yadon_count()

    # agent_name が指定された場合、その1つだけをチェック
    if agent_name:
        sock_path = agent_socket_path(agent_name, prefix=prefix)
        agents_to_check = [agent_name]
    else:
        # 全エージェント（マネージャー + ワーカー）をチェック
        agents_to_check = [manager_name] + [f"{worker_role}-{n}" for n in range(1, yadon_count + 1)]
        sock_path = agent_socket_path(manager_name, prefix=prefix)

    message = {"type": "status"}

    try:
        print(f"ステータス確認中 ({', '.join(agents_to_check)})...", end="", flush=True)
        response = send_message(sock_path, message, timeout=5)
        print(" OK")
        print()

        # マネージャーのステータスを表示
        print(f"{theme.role_names.manager}:")
        print(f"  状態: {response.get('state', 'unknown')}")
        if response.get("current_task"):
            print(f"  現在のタスク: {response['current_task']}")

        # ワーカーのステータスを表示
        workers = response.get("workers", {})
        if workers:
            print(f"\n{theme.role_names.worker}:")
            for worker_id, status in sorted(workers.items()):
                print(f"  {worker_id}: {status}")
    except socket.timeout:
        print()
        print(f"\033[1;31mタイムアウト\033[0m: ステータス確認がタイムアウトしました")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"\033[1;31mエラー\033[0m: {e}")
        sys.exit(1)


def cmd_restart(work_dir: str, multi_llm: bool = False) -> None:
    """デーモンを停止してから起動"""
    print("デーモン再起動...")
    print()
    cmd_stop()
    print()
    cmd_start(work_dir, multi_llm=multi_llm)


def cmd_say(number: int, message: str, bubble_type: str = "info", duration_ms: int = 5000) -> None:
    """ペットに吹き出しメッセージを送信"""
    theme = get_theme()
    prefix = theme.socket_prefix
    sock_path = pet_socket_path(str(number), prefix=prefix)

    if not Path(sock_path).exists():
        print(f"\033[1;33m警告\033[0m: ペットソケットが見つかりません ({sock_path})")
        print("ペットが起動していないか、番号が間違っている可能性があります")
        sys.exit(1)

    payload = {
        "text": message,
        "type": bubble_type,
        "duration": duration_ms,
    }

    try:
        print(f"吹き出し送信中 ({theme.role_names.worker}{number}へ)...", end="", flush=True)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(sock_path)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sock.sendall(data)
        sock.close()
        print(" OK")
    except socket.timeout:
        print()
        print(f"\033[1;31mタイムアウト\033[0m: ペットからの応答がありません")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"\033[1;31mエラー\033[0m: {e}")
        sys.exit(1)


def cmd_internal_send(instruction: str, project_dir: str | None = None) -> None:
    """【内部用】タスク送信 (JSON形式出力)

    cmd_send() の JSON出力バージョン。
    エージェント間通信で結果をJSON形式で返す際に使用。
    """
    theme = get_theme()
    manager_name = theme.agent_role_manager
    prefix = theme.socket_prefix
    sock_path = agent_socket_path(manager_name, prefix=prefix)

    result = {"success": False, "message": "", "data": None}

    if not Path(sock_path).exists():
        result["message"] = f"{manager_name}ソケットが見つかりません ({sock_path})"
        print(json.dumps(result, ensure_ascii=False))
        return

    message = {
        "type": "task",
        "payload": {
            "instruction": instruction,
        }
    }
    if project_dir:
        message["payload"]["project_dir"] = project_dir

    try:
        response = send_message(sock_path, message, timeout=600)
        result["success"] = response.get("status") == "success"
        result["data"] = response
        print(json.dumps(result, ensure_ascii=False))
    except socket.timeout:
        result["message"] = f"{manager_name}からの応答がありません（タイムアウト）"
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        result["message"] = str(e)
        print(json.dumps(result, ensure_ascii=False))


def cmd_internal_status(agent_name: str | None = None) -> None:
    """【内部用】ステータス確認 (JSON形式出力)

    cmd_status() の JSON出力バージョン。
    エージェント間通信で結果をJSON形式で返す際に使用。
    """
    theme = get_theme()
    manager_name = theme.agent_role_manager
    worker_role = theme.agent_role_worker
    prefix = theme.socket_prefix
    yadon_count = get_yadon_count()

    result = {"success": False, "message": "", "data": None}

    if agent_name:
        sock_path = agent_socket_path(agent_name, prefix=prefix)
        agents_to_check = [agent_name]
    else:
        agents_to_check = [manager_name] + [f"{worker_role}-{n}" for n in range(1, yadon_count + 1)]
        sock_path = agent_socket_path(manager_name, prefix=prefix)

    message = {"type": "status"}

    try:
        response = send_message(sock_path, message, timeout=5)
        result["success"] = True
        result["data"] = response
        print(json.dumps(result, ensure_ascii=False))
    except socket.timeout:
        result["message"] = "ステータス確認がタイムアウトしました"
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        result["message"] = str(e)
        print(json.dumps(result, ensure_ascii=False))


def cmd_internal_restart() -> None:
    """【内部用】デーモン再起動

    パイプラインの内部処理用。
    再起動完了メッセージを出力。
    """
    cmd_stop()
    time.sleep(1)
    cmd_start(str(Path.cwd()), multi_llm=False)
    print("再起動が完了しました")


def cmd_internal_say(number: int, message: str, bubble_type: str = "info", duration_ms: int = 5000) -> None:
    """【内部用】ペット吹き出し表示

    ペット番号に吹き出しメッセージを送信。
    """
    theme = get_theme()
    prefix = theme.socket_prefix
    sock_path = pet_socket_path(str(number), prefix=prefix)

    if not Path(sock_path).exists():
        # ペット未起動時は静かに終了
        return

    payload = {
        "text": message,
        "type": bubble_type,
        "duration": duration_ms,
    }

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(sock_path)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sock.sendall(data)
        sock.close()
    except (socket.timeout, FileNotFoundError, ConnectionRefusedError):
        # ペット未起動時は静かに終了
        pass
    except Exception:
        pass


def main() -> None:
    theme = get_theme()
    parser = argparse.ArgumentParser(description=f"{theme.display_name} CLI")
    parser.add_argument("--multi-llm", action="store_true", help="マルチLLMモード有効（各ワーカーに異なるバックエンドを自動割り当て）")
    subparsers = parser.add_subparsers(dest="command")

    # start コマンド
    start_parser = subparsers.add_parser("start", help="全エージェント起動")
    start_parser.add_argument("work_dir", nargs="?", default=str(Path.cwd()), help="作業ディレクトリ")
    start_parser.add_argument("--multi-llm", action="store_true", help="マルチLLMモード有効（各ワーカーに異なるバックエンドを自動割り当て）")

    # stop コマンド
    subparsers.add_parser("stop", help="全エージェント停止")

    # status コマンド
    status_parser = subparsers.add_parser("status", help="ステータス確認")
    status_parser.add_argument("agent_name", nargs="?", help="エージェント名（未指定時は全エージェント）")

    # restart コマンド
    restart_parser = subparsers.add_parser("restart", help="デーモン再起動")
    restart_parser.add_argument("work_dir", nargs="?", default=str(Path.cwd()), help="作業ディレクトリ")
    restart_parser.add_argument("--multi-llm", action="store_true", help="マルチLLMモード有効")

    # say コマンド
    say_parser = subparsers.add_parser("say", help="ペット吹き出し表示")
    say_parser.add_argument("number", type=int, help="ペット番号（1-N）")
    say_parser.add_argument("message", help="吹き出しメッセージ")
    say_parser.add_argument("--type", default="info", help="吹き出しタイプ（デフォルト: info）")
    say_parser.add_argument("--duration", type=int, default=5000, help="表示時間（ミリ秒、デフォルト: 5000）")

    # 【内部用】_send コマンド
    _send_parser = subparsers.add_parser("_send", help="【内部用】タスク送信 (JSON出力)")
    _send_parser.add_argument("instruction", help="実行するタスク指示")
    _send_parser.add_argument("--project-dir", help="作業ディレクトリ（オプション）")

    # 【内部用】_status コマンド
    _status_parser = subparsers.add_parser("_status", help="【内部用】ステータス確認 (JSON出力)")
    _status_parser.add_argument("agent_name", nargs="?", help="エージェント名（未指定時は全エージェント）")

    # 【内部用】_restart コマンド
    subparsers.add_parser("_restart", help="【内部用】デーモン再起動")

    # 【内部用】_say コマンド
    _say_parser = subparsers.add_parser("_say", help="【内部用】ペット吹き出し表示")
    _say_parser.add_argument("number", type=int, help="ペット番号（1-N）")
    _say_parser.add_argument("message", help="吹き出しメッセージ")
    _say_parser.add_argument("--type", default="info", help="吹き出しタイプ（デフォルト: info）")
    _say_parser.add_argument("--duration", type=int, default=5000, help="表示時間（ミリ秒、デフォルト: 5000）")

    args = parser.parse_args()

    # デフォルトコマンドは start（yadon だけで起動可能）
    if args.command is None:
        work_dir = str(Path.cwd())
        multi_llm = getattr(args, 'multi_llm', False)
        cmd_start(work_dir, multi_llm=multi_llm)
        return

    if args.command == "start":
        work_dir = str(Path(args.work_dir).resolve())
        # start サブコマンドの --multi-llm またはグローバルの --multi-llm
        multi_llm = getattr(args, 'multi_llm', False)
        cmd_start(work_dir, multi_llm=multi_llm)
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "status":
        cmd_status(agent_name=args.agent_name)
    elif args.command == "restart":
        work_dir = str(Path(args.work_dir).resolve())
        multi_llm = getattr(args, 'multi_llm', False)
        cmd_restart(work_dir, multi_llm=multi_llm)
    elif args.command == "say":
        cmd_say(args.number, args.message, bubble_type=args.type, duration_ms=args.duration)
    elif args.command == "_send":
        cmd_internal_send(args.instruction, project_dir=args.project_dir)
    elif args.command == "_status":
        cmd_internal_status(agent_name=args.agent_name)
    elif args.command == "_restart":
        cmd_internal_restart()
    elif args.command == "_say":
        cmd_internal_say(args.number, args.message, bubble_type=args.type, duration_ms=args.duration)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
