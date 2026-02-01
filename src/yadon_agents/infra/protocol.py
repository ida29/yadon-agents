"""
ヤドン・エージェント Unixソケット通信プロトコル

JSON over Unix domain socket。
リクエスト送信後 shutdown(SHUT_WR) でEOFを通知、レスポンスを読んで完了。
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

from yadon_agents.config.agent import (
    SOCKET_LISTEN_BACKLOG,
    SOCKET_RECV_BUFFER,
    SOCKET_SEND_TIMEOUT,
)

__all__ = [
    "SOCKET_DIR",
    "agent_socket_path",
    "pet_socket_path",
    "create_server_socket",
    "send_message",
    "receive_message",
    "send_response",
    "cleanup_socket",
]

# ソケットパス
SOCKET_DIR = "/tmp"


def agent_socket_path(name: str, prefix: str = "yadon") -> str:
    """エージェントのソケットパスを返す。

    Args:
        name: "yadoran", "yadon-1", "yadon-2", etc.
        prefix: ソケットファイル名のプレフィックス (デフォルト "yadon")
    """
    return f"{SOCKET_DIR}/{prefix}-agent-{name}.sock"


def pet_socket_path(name: str, prefix: str = "yadon") -> str:
    """ペットの吹き出しソケットパスを返す。

    Args:
        name: "yadoran", "1", "2", "3", "4"
        prefix: ソケットファイル名のプレフィックス (デフォルト "yadon")
    """
    return f"{SOCKET_DIR}/{prefix}-pet-{name}.sock"


# --- ソケット操作 ---


def create_server_socket(sock_path: str) -> socket.socket:
    """Unixドメインソケットサーバーを作成する。"""
    Path(sock_path).unlink(missing_ok=True)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(sock_path)
        sock.listen(SOCKET_LISTEN_BACKLOG)
    except Exception:
        sock.close()
        raise
    return sock


def send_message(sock_path: str, message: dict[str, Any], timeout: float = SOCKET_SEND_TIMEOUT) -> dict[str, Any]:
    """Unixソケットにメッセージを送信し、レスポンスを受信する。"""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(sock_path)
        data = json.dumps(message, ensure_ascii=False).encode("utf-8")
        sock.sendall(data)
        sock.shutdown(socket.SHUT_WR)

        chunks = []
        while True:
            chunk = sock.recv(SOCKET_RECV_BUFFER)
            if not chunk:
                break
            chunks.append(chunk)

        response_data = b"".join(chunks)
        return json.loads(response_data.decode("utf-8"))
    finally:
        sock.close()


def receive_message(conn: socket.socket) -> dict[str, Any]:
    """接続済みソケットからメッセージを受信する。"""
    chunks = []
    while True:
        chunk = conn.recv(SOCKET_RECV_BUFFER)
        if not chunk:
            break
        chunks.append(chunk)

    data = b"".join(chunks)
    return json.loads(data.decode("utf-8"))


def send_response(conn: socket.socket, message: dict[str, Any]) -> None:
    """接続済みソケットにレスポンスを送信する。"""
    data = json.dumps(message, ensure_ascii=False).encode("utf-8")
    conn.sendall(data)


def cleanup_socket(sock_path: str) -> None:
    """ソケットファイルを削除する。"""
    Path(sock_path).unlink(missing_ok=True)
