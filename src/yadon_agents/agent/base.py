"""BaseAgent — ソケットサーバーループ + コネクション分岐の共通基盤"""

import json
import logging
import socket
import threading
from typing import Callable, Optional

from yadon_agents.infra import protocol as proto

logger = logging.getLogger(__name__)

BubbleCallback = Callable[[str, str, int], None]


class BaseAgent:
    """エージェントの共通基盤。サブクラスは handle_task(msg) を実装する。"""

    def __init__(self, name: str, sock_path: str, project_dir: str):
        self.name = name
        self.sock_path = sock_path
        self.project_dir = project_dir
        self.server_sock: Optional[socket.socket] = None
        self.running = False
        self.current_task_id: Optional[str] = None
        self.on_bubble: Optional[BubbleCallback] = None

    def bubble(self, text: str, bubble_type: str = "normal", duration: int = 4000) -> None:
        if self.on_bubble:
            self.on_bubble(text, bubble_type, duration)

    def handle_task(self, msg: dict) -> dict:
        raise NotImplementedError

    def handle_status(self, msg: dict) -> dict:
        state = "busy" if self.current_task_id else "idle"
        return {
            "type": "status_response",
            "from": self.name,
            "state": state,
            "current_task": self.current_task_id,
        }

    def handle_connection(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(600)
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
        finally:
            conn.close()

    def serve_forever(self) -> None:
        self.server_sock = proto.create_server_socket(self.sock_path)
        self.running = True
        logger.info("%s 起動: %s", self.name, self.sock_path)

        while self.running:
            try:
                self.server_sock.settimeout(1.0)
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

    def stop(self) -> None:
        self.running = False
        if self.server_sock:
            self.server_sock.close()
        proto.cleanup_socket(self.sock_path)
        logger.info("%s 停止", self.name)
