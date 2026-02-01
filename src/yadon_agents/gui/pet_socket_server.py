"""PetSocketServer — 吹き出しメッセージ受信用ソケットサーバー (QThread)"""

from __future__ import annotations

import json
import logging
import socket
import threading
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from yadon_agents.config.agent import (
    PET_SOCKET_MAX_MESSAGE,
    PET_SOCKET_RECV_BUFFER,
    SOCKET_ACCEPT_TIMEOUT,
    SOCKET_LISTEN_BACKLOG,
)
from yadon_agents.config.ui import BUBBLE_DISPLAY_TIME

logger = logging.getLogger(__name__)


class PetSocketServer(QThread):
    """QThread-based Unix domain socket server for pet bubble messages.

    Listens on a Unix socket path and emits a signal when a JSON message
    is received. Messages are expected in the format:
        {"text": "...", "type": "normal", "duration": 4000}
    """

    message_received = pyqtSignal(str, str, int)  # (text, bubble_type, duration_ms)

    def __init__(self, socket_path: str):
        super().__init__()
        self.socket_path = socket_path
        self._running = True
        self._server_socket = None

    def run(self) -> None:
        try:
            Path(self.socket_path).unlink(missing_ok=True)
        except OSError:
            logger.debug("Failed to remove stale socket: %s", self.socket_path)
            return

        self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self._server_socket.bind(self.socket_path)
            self._server_socket.listen(SOCKET_LISTEN_BACKLOG)
            self._server_socket.settimeout(SOCKET_ACCEPT_TIMEOUT)
            logger.debug("Listening on %s", self.socket_path)

            while self._running:
                try:
                    conn, _ = self._server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._running:
                        logger.debug("accept() error while running")
                    break

                threading.Thread(
                    target=self._handle_connection,
                    args=(conn,),
                    daemon=True,
                ).start()
        except Exception as e:
            logger.debug("Server error: %s", e)
        finally:
            self._cleanup()

    def _handle_connection(self, conn: socket.socket) -> None:
        try:
            data = b""
            while True:
                chunk = conn.recv(PET_SOCKET_RECV_BUFFER)
                if not chunk:
                    break
                data += chunk
                if len(data) > PET_SOCKET_MAX_MESSAGE:
                    break

            if not data:
                return

            msg = json.loads(data.decode("utf-8"))
            text = msg.get("text", "")
            bubble_type = msg.get("type", "normal")
            duration = int(msg.get("duration", BUBBLE_DISPLAY_TIME))

            if text:
                logger.debug("Received: text=%r, type=%s", text, bubble_type)
                self.message_received.emit(text, bubble_type, duration)
        except json.JSONDecodeError as e:
            logger.debug("Invalid JSON: %s", e)
        except Exception as e:
            logger.debug("Connection handler error: %s", e)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def stop(self) -> None:
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
        self.wait(3000)

    def _cleanup(self) -> None:
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
        try:
            Path(self.socket_path).unlink(missing_ok=True)
        except Exception:
            pass
        logger.debug("Cleaned up %s", self.socket_path)
