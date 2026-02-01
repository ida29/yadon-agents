"""Unix domain socket server for receiving external messages"""

import json
import os
import socket
import threading

from PyQt6.QtCore import QThread, pyqtSignal

from utils import log_debug


def _log_debug(msg: str):
    log_debug('socket_server', msg)


class PetSocketServer(QThread):
    """QThread-based Unix domain socket server.

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

    def run(self):
        # Clean up stale socket file
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                _log_debug(f"Failed to remove stale socket: {self.socket_path}")
                return

        self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self._server_socket.bind(self.socket_path)
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)  # Allow periodic check of _running
            _log_debug(f"Listening on {self.socket_path}")

            while self._running:
                try:
                    conn, _ = self._server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._running:
                        _log_debug("accept() error while running")
                    break

                # Handle connection in a short-lived thread to avoid blocking
                threading.Thread(
                    target=self._handle_connection,
                    args=(conn,),
                    daemon=True,
                ).start()
        except Exception as e:
            _log_debug(f"Server error: {e}")
        finally:
            self._cleanup()

    def _handle_connection(self, conn: socket.socket):
        try:
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                # Limit to 64KB to prevent abuse
                if len(data) > 65536:
                    break

            if not data:
                return

            msg = json.loads(data.decode('utf-8'))
            text = msg.get('text', '')
            bubble_type = msg.get('type', 'normal')
            duration = int(msg.get('duration', 4000))

            if text:
                _log_debug(f"Received: text={text!r}, type={bubble_type}, duration={duration}")
                self.message_received.emit(text, bubble_type, duration)
        except json.JSONDecodeError as e:
            _log_debug(f"Invalid JSON: {e}")
        except Exception as e:
            _log_debug(f"Connection handler error: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def stop(self):
        """Stop the server gracefully."""
        self._running = False
        # Close the server socket to unblock accept()
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
        self.wait(3000)  # Wait up to 3 seconds for thread to finish

    def _cleanup(self):
        """Remove socket file and close server socket."""
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
        _log_debug(f"Cleaned up {self.socket_path}")
