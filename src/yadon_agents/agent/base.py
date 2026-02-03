"""BaseAgent — ソケットサーバーループ + コネクション分岐の共通基盤"""

from __future__ import annotations

import json
import logging
import socket
import threading
from typing import Any

from yadon_agents.config.agent import SOCKET_ACCEPT_TIMEOUT, SOCKET_CONNECTION_TIMEOUT
from yadon_agents.domain.messages import StatusResponse
from yadon_agents.domain.ports.agent_port import (
    DEFAULT_BUBBLE_DURATION,
    AgentPort,
    BubbleCallback,
)
from yadon_agents.infra import protocol as proto

__all__ = ["BaseAgent"]

logger = logging.getLogger(__name__)


class BaseAgent(AgentPort):
    """エージェントの共通基盤。サブクラスは handle_task(msg) を実装する。"""

    def __init__(self, name: str, sock_path: str, project_dir: str):
        self._name = name
        self.sock_path = sock_path
        self.project_dir = project_dir
        self.server_sock: socket.socket | None = None
        self.running = False
        self.current_task_id: str | None = None
        self._on_bubble: BubbleCallback | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def on_bubble(self) -> BubbleCallback | None:
        return self._on_bubble

    @on_bubble.setter
    def on_bubble(self, callback: BubbleCallback | None) -> None:
        self._on_bubble = callback

    def bubble(self, text: str, bubble_type: str = "normal", duration: int = DEFAULT_BUBBLE_DURATION) -> None:
        callback = self.on_bubble
        if callback:
            callback(text, bubble_type, duration)

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def handle_status(self, msg: dict[str, Any]) -> dict[str, Any]:
        state = "busy" if self.current_task_id else "idle"
        return StatusResponse(
            from_agent=self.name,
            state=state,
            current_task=self.current_task_id,
        ).to_dict()

    def handle_connection(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(SOCKET_CONNECTION_TIMEOUT)
            msg = proto.receive_message(conn)
            msg_type = msg.get("type", "")

            if msg_type == "task":
                response = self.handle_task(msg)
            elif msg_type == "status":
                response = self.handle_status(msg)
            else:
                response = {
                    "type": "error",
                    "from": self.name,
                    "message": f"不明なメッセージタイプ: {msg_type}",
                }

            proto.send_response(conn, response)
        except json.JSONDecodeError as e:
            logger.error("JSONパースエラー: %s", e)
            try:
                proto.send_response(conn, {
                    "type": "error",
                    "from": self.name,
                    "message": f"JSONパースエラー: {e}",
                })
            except Exception:
                pass
        except Exception as e:
            logger.error("接続処理エラー: %s", e)
            try:
                proto.send_response(conn, {
                    "type": "error",
                    "from": self.name,
                    "message": f"接続処理エラー: {e}",
                })
            except Exception:
                pass
        finally:
            conn.close()

    def serve_forever(self) -> None:
        try:
            self.server_sock = proto.create_server_socket(self.sock_path)
            self.running = True
            logger.info("%s 起動: %s", self.name, self.sock_path)

            while self.running:
                try:
                    self.server_sock.settimeout(SOCKET_ACCEPT_TIMEOUT)
                    try:
                        conn, _ = self.server_sock.accept()
                    except socket.timeout:
                        continue

                    thread = threading.Thread(
                        target=self.handle_connection,
                        args=(conn,),
                        daemon=True,
                    )
                    thread.start()
                    thread.join()

                except OSError:
                    if self.running:
                        logger.error("ソケットエラー")
                    break
        finally:
            if self.server_sock:
                self.server_sock.close()
            proto.cleanup_socket(self.sock_path)

    def stop(self) -> None:
        self.running = False
