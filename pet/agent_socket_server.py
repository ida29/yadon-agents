"""Unix domain socket server for yadon agent task handling.

Listens on /tmp/yadon-agent-yadon-{N}.sock and processes task/status messages.
Runs claude -p in a subprocess and emits signals for pet bubble display.
Designed to be embedded in the YadonPet QApplication.
"""

import json
import os
import socket
import subprocess
import threading

from PyQt6.QtCore import QThread, pyqtSignal

from utils import log_debug


def _log_debug(msg: str):
    log_debug('agent_socket', msg)


class AgentSocketServer(QThread):
    """QThread-based agent socket server for yadon daemon functionality.

    Handles:
    - "task" messages: runs claude -p --model haiku and returns results
    - "status" messages: returns current idle/busy state

    Emits:
    - task_started(task_id, instruction): when a task begins
    - task_completed(task_id, status, summary): when a task finishes
    - bubble_request(text, bubble_type, duration_ms): request pet bubble display
    """

    task_started = pyqtSignal(str, str)       # (task_id, instruction)
    task_completed = pyqtSignal(str, str, str)  # (task_id, status, summary)
    bubble_request = pyqtSignal(str, str, int)  # (text, bubble_type, duration_ms)

    def __init__(self, yadon_number, project_dir):
        super().__init__()
        self.yadon_number = yadon_number
        self.name = "yadon-%d" % yadon_number
        self.socket_path = "/tmp/yadon-agent-%s.sock" % self.name
        self.project_dir = project_dir
        self._running = True
        self._server_socket = None
        self._current_task_id = None

    def run(self):
        # Clean up stale socket
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                _log_debug("Failed to remove stale socket: %s" % self.socket_path)
                return

        self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self._server_socket.bind(self.socket_path)
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)
            _log_debug("Agent listening on %s" % self.socket_path)

            while self._running:
                try:
                    conn, _ = self._server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._running:
                        _log_debug("accept() error while running")
                    break

                # Handle connection (blocking — one task at a time)
                self._handle_connection(conn)

        except Exception as e:
            _log_debug("Agent server error: %s" % e)
        finally:
            self._cleanup()

    def _receive_message(self, conn):
        """Read full message until client sends EOF (shutdown(SHUT_WR))."""
        chunks = []
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
        data = b"".join(chunks)
        return json.loads(data.decode("utf-8"))

    def _send_response(self, conn, message):
        """Send JSON response."""
        data = json.dumps(message, ensure_ascii=False).encode("utf-8")
        conn.sendall(data)

    def _handle_connection(self, conn):
        try:
            conn.settimeout(600)
            msg = self._receive_message(conn)
            msg_type = msg.get("type", "")

            if msg_type == "task":
                response = self._handle_task(msg)
            elif msg_type == "status":
                response = self._handle_status(msg)
            else:
                response = {
                    "type": "error",
                    "from": self.name,
                    "message": "Unknown message type: %s" % msg_type,
                }

            self._send_response(conn, response)
        except json.JSONDecodeError as e:
            _log_debug("JSON parse error: %s" % e)
            try:
                self._send_response(conn, {
                    "type": "error",
                    "from": self.name,
                    "message": "JSON parse error: %s" % e,
                })
            except Exception:
                pass
        except Exception as e:
            _log_debug("Connection error: %s" % e)
        finally:
            conn.close()

    def _handle_task(self, msg):
        task_id = msg.get("id", "unknown")
        self._current_task_id = task_id
        payload = msg.get("payload", {})
        instruction = payload.get("instruction", "")
        project_dir = payload.get("project_dir", self.project_dir)

        _log_debug("Task received: %s" % task_id)
        self.task_started.emit(task_id, instruction)
        self.bubble_request.emit(
            "...やるやぁん... (%s...)" % instruction[:30],
            "claude", 4000,
        )

        output, returncode = self._run_claude(instruction, project_dir)
        status = "success" if returncode == 0 else "error"
        summary = output.strip()[:200] if output.strip() else "(出力なし)"

        if status == "success":
            self.bubble_request.emit("...できたやぁん...", "claude", 4000)
        else:
            self.bubble_request.emit(
                "...失敗やぁん... (%s)" % summary[:30],
                "claude", 4000,
            )

        self.task_completed.emit(task_id, status, summary)
        self._current_task_id = None

        return {
            "type": "result",
            "id": task_id,
            "from": self.name,
            "status": status,
            "payload": {
                "output": output,
                "summary": summary,
            },
        }

    def _handle_status(self, msg):
        state = "busy" if self._current_task_id else "idle"
        return {
            "type": "status_response",
            "from": self.name,
            "state": state,
            "current_task": self._current_task_id,
        }

    def _run_claude(self, instruction, project_dir):
        """Run claude -p --model haiku."""
        cmd = [
            "claude",
            "-p",
            "instructions/yadon.md を読んで従ってください。\n\n"
            "あなたはヤドン%dです。\n\nタスク:\n%s" % (self.yadon_number, instruction),
            "--model", "haiku",
        ]
        _log_debug("Running claude -p: %s..." % instruction[:80])

        try:
            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=600,
            )
            return result.stdout + result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "タイムアウト (10分)", 1
        except Exception as e:
            return "実行エラー: %s" % e, 1

    def stop(self):
        """Stop the server gracefully."""
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
        self.wait(3000)

    def _cleanup(self):
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
        _log_debug("Cleaned up %s" % self.socket_path)
