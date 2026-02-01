"""
ヤドン・エージェント Unixソケット通信プロトコル

JSON over Unix domain socket。
リクエスト送信後 shutdown(SHUT_WR) でEOFを通知、レスポンスを読んで完了。
"""

import json
import os
import socket
import time
import uuid
from pathlib import Path
from typing import Optional

# ソケットパス
SOCKET_DIR = "/tmp"


def agent_socket_path(name: str) -> str:
    """エージェントのソケットパスを返す。

    Args:
        name: "yadoran", "yadon-1", "yadon-2", "yadon-3", "yadon-4"
    """
    return f"{SOCKET_DIR}/yadon-agent-{name}.sock"


def pet_socket_path(number: int) -> str:
    """ペットのソケットパスを返す。"""
    return f"{SOCKET_DIR}/yadon-pet-{number}.sock"


def generate_task_id() -> str:
    """タスクIDを生成する。"""
    ts = time.strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:4]
    return f"task-{ts}-{short_uuid}"


# --- メッセージ作成ヘルパー ---


def make_task_message(
    from_agent: str,
    instruction: str,
    project_dir: str,
    task_id: Optional[str] = None,
) -> dict:
    """タスク送信メッセージを作成する。"""
    return {
        "type": "task",
        "id": task_id or generate_task_id(),
        "from": from_agent,
        "payload": {
            "instruction": instruction,
            "project_dir": project_dir,
        },
    }


def make_result_message(
    task_id: str,
    from_agent: str,
    status: str,
    output: str,
    summary: str,
) -> dict:
    """タスク結果メッセージを作成する。"""
    return {
        "type": "result",
        "id": task_id,
        "from": from_agent,
        "status": status,
        "payload": {
            "output": output,
            "summary": summary,
        },
    }


def make_status_message(from_agent: str) -> dict:
    """ステータス照会メッセージを作成する。"""
    return {
        "type": "status",
        "from": from_agent,
    }


# --- ソケット操作 ---


def create_server_socket(sock_path: str) -> socket.socket:
    """Unixドメインソケットサーバーを作成する。

    既存のソケットファイルがあれば削除してから作成。
    """
    if os.path.exists(sock_path):
        os.unlink(sock_path)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sock_path)
    sock.listen(5)
    return sock


def send_message(sock_path: str, message: dict, timeout: float = 300.0) -> dict:
    """Unixソケットにメッセージを送信し、レスポンスを受信する。

    1. 接続
    2. JSONを送信
    3. shutdown(SHUT_WR) でEOF通知
    4. レスポンスを全て読む
    5. JSONとしてパース

    Args:
        sock_path: 送信先ソケットパス
        message: 送信するメッセージ (dict)
        timeout: タイムアウト秒数 (デフォルト300秒=5分)

    Returns:
        レスポンスメッセージ (dict)
    """
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(sock_path)
        data = json.dumps(message, ensure_ascii=False).encode("utf-8")
        sock.sendall(data)
        sock.shutdown(socket.SHUT_WR)

        # レスポンス受信
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)

        response_data = b"".join(chunks)
        return json.loads(response_data.decode("utf-8"))
    finally:
        sock.close()


def receive_message(conn: socket.socket) -> dict:
    """接続済みソケットからメッセージを受信する。

    クライアントが shutdown(SHUT_WR) するまで読み続ける。

    Args:
        conn: accept() で得た接続ソケット

    Returns:
        受信メッセージ (dict)
    """
    chunks = []
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)

    data = b"".join(chunks)
    return json.loads(data.decode("utf-8"))


def send_response(conn: socket.socket, message: dict) -> None:
    """接続済みソケットにレスポンスを送信する。

    Args:
        conn: accept() で得た接続ソケット
        message: 送信するレスポンス (dict)
    """
    data = json.dumps(message, ensure_ascii=False).encode("utf-8")
    conn.sendall(data)


def cleanup_socket(sock_path: str) -> None:
    """ソケットファイルを削除する。"""
    if os.path.exists(sock_path):
        os.unlink(sock_path)
