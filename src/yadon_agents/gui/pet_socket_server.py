"""PetSocketServer — 吹き出しメッセージ受信用ソケットサーバー (QThread)"""

import json
import os
import socket
import threading

from PyQt6.QtCore import QThread, pyqtSignal

from yadon_agents.gui.utils import log_debug


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
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                log_debug("pet_socket", f"Failed to remove stale socket: {self.socket_path}")
                return

        self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self._server_socket.bind(self.socket_path)
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)
            log_debug("pet_socket", f"Listening on {self.socket_path}")

            while self._running:
                try:
                    conn, _ = self._server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._running:
                        log_debug("pet_socket", "accept() error while running")
                    break

                threading.Thread(
                    target=self._handle_connection,
                    args=(conn,),
                    daemon=True,
                ).start()
        except Exception as e:
            log_debug("pet_socket", f"Server error: {e}")
        finally:
            self._cleanup()

    def _handle_connection(self, conn: socket.socket) -> None:
        try:
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if len(data) > 65536:
                    break

            if not data:
                return

            msg = json.loads(data.decode("utf-8"))
            text = msg.get("text", "")
            bubble_type = msg.get("type", "normal")
            duration = int(msg.get("duration", 4000))

            if text:
                log_debug("pet_socket", f"Received: text={text!r}, type={bubble_type}")
                self.message_received.emit(text, bubble_type, duration)
        except json.JSONDecodeError as e:
            log_debug("pet_socket", f"Invalid JSON: {e}")
        except Exception as e:
            log_debug("pet_socket", f"Connection handler error: {e}")
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
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except Exception:
                pass
        log_debug("pet_socket", f"Cleaned up {self.socket_path}")
