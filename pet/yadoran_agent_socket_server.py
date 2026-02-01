"""Unix domain socket server for yadoran agent task handling.

Listens on /tmp/yadon-agent-yadoran.sock and processes task/status messages.
Decomposes tasks via claude -p --model sonnet, dispatches subtasks to yadon workers,
and aggregates results. Designed to be embedded in the YadoranPet QApplication.
"""

import json
import os
import socket
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from utils import log_debug

# Add daemons/ to path for socket_protocol
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "daemons"))
import socket_protocol as proto


YADON_COUNT = 4


def _log_debug(msg: str):
    log_debug('yadoran_agent', msg)


class YadoranAgentSocketServer(QThread):
    """QThread-based agent socket server for yadoran daemon functionality.

    Handles:
    - "task" messages: decomposes via claude -p --model sonnet, dispatches to yadon workers
    - "status" messages: returns current state and worker statuses

    Emits:
    - task_started(task_id, instruction): when a task begins
    - task_completed(task_id, status, summary): when a task finishes
    - bubble_request(text, bubble_type, duration_ms): request pet bubble display
    """

    task_started = pyqtSignal(str, str)       # (task_id, instruction)
    task_completed = pyqtSignal(str, str, str)  # (task_id, status, summary)
    bubble_request = pyqtSignal(str, str, int)  # (text, bubble_type, duration_ms)

    def __init__(self, project_dir):
        super().__init__()
        self.name = "yadoran"
        self.socket_path = proto.agent_socket_path(self.name)
        self.project_dir = project_dir
        self._running = True
        self._server_socket = None
        self._current_task_id = None  # type: Optional[str]

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
            _log_debug("Yadoran agent listening on %s" % self.socket_path)

            while self._running:
                try:
                    conn, _ = self._server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._running:
                        _log_debug("accept() error while running")
                    break

                # Handle connection (blocking -- one task at a time)
                self._handle_connection(conn)

        except Exception as e:
            _log_debug("Yadoran agent server error: %s" % e)
        finally:
            self._cleanup()

    def _handle_connection(self, conn):
        try:
            conn.settimeout(600)
            msg = proto.receive_message(conn)
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

            proto.send_response(conn, response)
        except json.JSONDecodeError as e:
            _log_debug("JSON parse error: %s" % e)
            try:
                proto.send_response(conn, {
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
            "...しっぽが...なんか言ってる... (%s...)" % instruction[:20],
            "claude", 4000,
        )

        # Decompose task
        subtasks = self._decompose_task(instruction, project_dir)

        self.bubble_request.emit(
            "...ヤドンたちに配分する...",
            "claude", 3000,
        )

        # Dispatch to yadon workers in parallel
        results = self._dispatch_all(subtasks, project_dir, task_id)

        # Aggregate results
        all_success = all(r.get("status") == "success" for r in results)
        overall_status = "success" if all_success else "partial_error"

        summaries = []
        full_output_parts = []
        for r in results:
            from_agent = r.get("from", "unknown")
            status = r.get("status", "unknown")
            r_payload = r.get("payload", {})
            summary = r_payload.get("summary", "")
            output = r_payload.get("output", "")
            summaries.append("[%s] %s: %s" % (from_agent, status, summary))
            full_output_parts.append("=== %s (%s) ===\n%s" % (from_agent, status, output))

        combined_summary = "\n".join(summaries)
        combined_output = "\n\n".join(full_output_parts)

        if overall_status == "success":
            self.bubble_request.emit("...みんなできた...", "claude", 4000)
        else:
            self.bubble_request.emit("...一部失敗した...", "claude", 4000)

        self.task_completed.emit(task_id, overall_status, combined_summary)
        self._current_task_id = None

        return proto.make_result_message(
            task_id=task_id,
            from_agent="yadoran",
            status=overall_status,
            output=combined_output,
            summary=combined_summary,
        )

    def _decompose_task(self, instruction, project_dir):
        """Run claude -p --model sonnet to decompose a task into subtasks."""
        prompt = (
            "instructions/yadoran.md を読んで従ってください。\n\n"
            "あなたはヤドランです。以下のタスクを、ヤドン（最大4体）に配分するために分解してください。\n\n"
            "【タスク】\n%s\n\n"
            "【作業ディレクトリ】\n%s\n\n"
            "【出力形式】\n"
            "必ず以下のJSON形式で出力してください。他のテキストは一切不要です。\n"
            "```json\n"
            "{\n"
            '  "subtasks": [\n'
            '    {"instruction": "サブタスク1の具体的な指示"},\n'
            '    {"instruction": "サブタスク2の具体的な指示"}\n'
            "  ],\n"
            '  "strategy": "分解の方針（1行）"\n'
            "}\n"
            "```\n\n"
            "【ルール】\n"
            "- サブタスクは最大4つまで\n"
            "- 並列実行可能なように分解する（依存関係のあるタスクは1つにまとめる）\n"
            "- 分解不要な小さいタスクはそのまま1つで返す\n"
            "- 各サブタスクには十分な情報を含める（ヤドンは他のサブタスクの内容を知らない）"
        ) % (instruction, project_dir)

        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--model", "sonnet", "--output-format", "text"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout.strip()

            # Extract JSON (may be wrapped in ```json ... ```)
            json_str = output
            if "```json" in output:
                start = output.index("```json") + 7
                end = output.index("```", start)
                json_str = output[start:end].strip()
            elif "```" in output:
                start = output.index("```") + 3
                end = output.index("```", start)
                json_str = output[start:end].strip()

            data = json.loads(json_str)
            subtasks = data.get("subtasks", [])
            strategy = data.get("strategy", "")

            if subtasks:
                _log_debug("Task decomposed: %d subtasks -- %s" % (len(subtasks), strategy))
                return subtasks

        except json.JSONDecodeError:
            _log_debug("Task decomposition JSON parse failed, running as single task")
        except subprocess.TimeoutExpired:
            _log_debug("Task decomposition timed out, running as single task")
        except Exception as e:
            _log_debug("Task decomposition error: %s, running as single task" % e)

        return [{"instruction": instruction}]

    def _dispatch_to_yadon(self, yadon_number, subtask, project_dir, task_id):
        """Send a subtask to one yadon worker and return the result."""
        yadon_name = "yadon-%d" % yadon_number
        sock_path = proto.agent_socket_path(yadon_name)

        msg = proto.make_task_message(
            from_agent="yadoran",
            instruction=subtask["instruction"],
            project_dir=project_dir,
            task_id="%s-sub%d" % (task_id, yadon_number),
        )

        try:
            response = proto.send_message(sock_path, msg, timeout=600)
            return response
        except Exception as e:
            _log_debug("Failed to send to %s: %s" % (yadon_name, e))
            return proto.make_result_message(
                task_id="%s-sub%d" % (task_id, yadon_number),
                from_agent=yadon_name,
                status="error",
                output="送信失敗: %s" % e,
                summary="ヤドン%dへの送信に失敗" % yadon_number,
            )

    def _dispatch_all(self, subtasks, project_dir, task_id):
        """Dispatch subtasks to yadon workers in parallel."""
        results = []
        with ThreadPoolExecutor(max_workers=YADON_COUNT) as executor:
            futures = {}
            for i, subtask in enumerate(subtasks[:YADON_COUNT]):
                yadon_num = i + 1
                future = executor.submit(
                    self._dispatch_to_yadon,
                    yadon_num,
                    subtask,
                    project_dir,
                    task_id,
                )
                futures[future] = yadon_num

            for future in as_completed(futures):
                yadon_num = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    _log_debug("Yadon %d execution error: %s" % (yadon_num, e))
                    results.append({
                        "type": "result",
                        "from": "yadon-%d" % yadon_num,
                        "status": "error",
                        "payload": {"output": str(e), "summary": "実行エラー"},
                    })

        return results

    def _handle_status(self, msg):
        # Query each yadon's status
        workers = {}
        for i in range(1, YADON_COUNT + 1):
            yadon_name = "yadon-%d" % i
            sock_path = proto.agent_socket_path(yadon_name)
            if os.path.exists(sock_path):
                try:
                    resp = proto.send_message(
                        sock_path,
                        proto.make_status_message("yadoran"),
                        timeout=5,
                    )
                    workers[yadon_name] = resp.get("state", "unknown")
                except Exception:
                    workers[yadon_name] = "unreachable"
            else:
                workers[yadon_name] = "stopped"

        state = "busy" if self._current_task_id else "idle"
        return {
            "type": "status_response",
            "from": self.name,
            "state": state,
            "current_task": self._current_task_id,
            "workers": workers,
        }

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
