"""yadon コマンド関数（ソケット通信ラッパー）

CLI や他のモジュールから呼び出される高レベルコマンド関数。
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

from yadon_agents.infra.protocol import agent_socket_path, pet_socket_path, send_message
from yadon_agents.themes import get_theme

__all__ = [
    "send_task",
    "check_status",
    "restart_daemons",
    "pet_say",
]


def send_task(instruction: str, project_dir: str | None = None) -> dict[str, Any]:
    """タスクをヤドランに送信し、結果を受け取る。

    ソケット通信でヤドランにタスクを送信し、実行結果をJSON辞書で返す。

    Args:
        instruction: 実行するタスク指示
        project_dir: 作業ディレクトリ（オプション）

    Returns:
        ヤドランからのレスポンス（JSON辞書）
            {
                "type": "result",
                "id": "task-20260203-120000-a1b2",
                "from": "yadoran",
                "status": "success" | "partial_error",
                "payload": {
                    "output": "各ヤドンの出力",
                    "summary": "結果の要約"
                }
            }

    Raises:
        socket.timeout: ヤドランからの応答がない場合（10分以内）
        ConnectionRefusedError: ソケットに接続できない場合
        json.JSONDecodeError: 応答がJSON形式でない場合
    """
    theme = get_theme()
    manager_name = theme.agent_role_manager
    prefix = theme.socket_prefix
    sock_path = agent_socket_path(manager_name, prefix=prefix)

    message: dict[str, Any] = {
        "type": "task",
        "payload": {
            "instruction": instruction,
        }
    }
    if project_dir:
        message["payload"]["project_dir"] = project_dir

    # タイムアウト10分 = 600秒
    return send_message(sock_path, message, timeout=600)


def check_status(agent_name: str | None = None) -> dict[str, Any]:
    """エージェントのステータスを確認する。

    StatusQuery メッセージを送信し、StatusResponse を受け取る。

    Args:
        agent_name: 確認対象のエージェント名
                   （None の場合はマネージャー 'yadoran' をデフォルト使用）

    Returns:
        エージェントからのステータスレスポンス（JSON辞書）
            {
                "type": "status_response",
                "from": "yadoran",
                "state": "idle" | "busy",
                "current_task": "task-20260203-120000-a1b2" | null,
                "workers": {
                    "yadon-1": "idle",
                    "yadon-2": "busy",
                    ...
                }
            }

    Raises:
        socket.timeout: エージェントからの応答がない場合（5秒以内）
        ConnectionRefusedError: ソケットに接続できない場合
        json.JSONDecodeError: 応答がJSON形式でない場合
    """
    theme = get_theme()
    manager_name = theme.agent_role_manager
    prefix = theme.socket_prefix

    # agent_name が None の場合、デフォルトはマネージャー
    target_agent = agent_name if agent_name else manager_name
    sock_path = agent_socket_path(target_agent, prefix=prefix)

    message: dict[str, Any] = {
        "type": "status",
    }

    # タイムアウト5秒
    return send_message(sock_path, message, timeout=5)


def restart_daemons() -> None:
    """デーモンを再起動する。

    cli.py の cmd_stop() と cmd_start() を順次呼び出して
    デーモン全体を停止してから起動する。
    """
    from yadon_agents.cli import cmd_start, cmd_stop
    from pathlib import Path

    cmd_stop()
    # 作業ディレクトリはカレントディレクトリを使用
    work_dir = str(Path.cwd().resolve())
    cmd_start(work_dir)


def pet_say(number: int, message: str, bubble_type: str = "info", duration_ms: int = 5000) -> None:
    """ペットに吹き出しメッセージを送信する。

    ペット（ヤドン or ヤドラン）の吹き出しにメッセージを表示する。
    ペットが起動していない場合は静かに終了する。

    Args:
        number: ペット番号（1-N、またはマネージャーの場合は "yadoran"）
        message: 表示するメッセージ
        bubble_type: 吹き出しのタイプ（デフォルト: "info"）
        duration_ms: 表示時間（ミリ秒、デフォルト: 5000）

    Returns:
        None（常に成功、接続失敗時は静かに終了）
    """
    theme = get_theme()
    prefix = theme.socket_prefix

    # number が int の場合は文字列化
    pet_id = str(number)
    sock_path = pet_socket_path(pet_id, prefix=prefix)

    # ペットソケットが存在しない場合は静かに終了（ペット未起動を想定）
    if not Path(sock_path).exists():
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
    except (socket.error, socket.timeout, OSError):
        # ペット未起動・接続失敗時は静かに終了
        pass
