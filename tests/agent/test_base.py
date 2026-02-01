"""BaseAgent handle_connection のテスト"""

import json
import os
import socket
import threading
from typing import Any

from yadon_agents.agent.base import BaseAgent
from yadon_agents.infra.protocol import create_server_socket, send_message


class FakeAgent(BaseAgent):
    """テスト用の最小限エージェント実装"""

    def __init__(self, sock_path: str, fail_on_task: bool = False):
        super().__init__(name="fake-agent", sock_path=sock_path, project_dir="/tmp")
        self.fail_on_task = fail_on_task

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any]:
        if self.fail_on_task:
            raise RuntimeError("task processing failed")
        return {"type": "result", "from": self.name, "status": "success"}


def _run_agent_one_request(agent: FakeAgent, request: dict[str, Any]) -> dict[str, Any]:
    """エージェントを1リクエストだけ処理させて結果を返すヘルパー"""
    server = create_server_socket(agent.sock_path)

    def handle_once():
        conn, _ = server.accept()
        agent.handle_connection(conn)

    thread = threading.Thread(target=handle_once, daemon=True)
    thread.start()

    result = send_message(agent.sock_path, request, timeout=5.0)

    thread.join(timeout=5)
    server.close()
    return result


class TestHandleConnection:
    def test_json_decode_error_returns_error_response(self, sock_dir):
        """JSONDecodeError でエラーレスポンスが返ること"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)
        server = create_server_socket(sock_path)

        def handle_once():
            conn, _ = server.accept()
            agent.handle_connection(conn)

        thread = threading.Thread(target=handle_once, daemon=True)
        thread.start()

        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(sock_path)
        client.sendall(b"not-json{{{")
        client.shutdown(socket.SHUT_WR)

        chunks = []
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
        client.close()

        response = json.loads(b"".join(chunks).decode("utf-8"))
        assert response["type"] == "error"
        assert "JSONパースエラー" in response["message"]

        thread.join(timeout=5)
        server.close()

    def test_handle_task_exception_returns_error_response(self, sock_dir):
        """Issue 1 修正検証: handle_task例外でエラーレスポンスが返ること"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path, fail_on_task=True)

        result = _run_agent_one_request(agent, {
            "type": "task",
            "id": "t1",
            "from": "test",
            "payload": {"instruction": "do something"},
        })

        assert result["type"] == "error"
        assert "接続処理エラー" in result["message"]

    def test_handle_status_idle(self, sock_dir):
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        result = _run_agent_one_request(agent, {"type": "status", "from": "test"})

        assert result["type"] == "status_response"
        assert result["state"] == "idle"
        assert result["current_task"] is None

    def test_handle_status_busy(self, sock_dir):
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)
        agent.current_task_id = "busy-task"

        result = _run_agent_one_request(agent, {"type": "status", "from": "test"})

        assert result["state"] == "busy"
        assert result["current_task"] == "busy-task"

    def test_unknown_message_type(self, sock_dir):
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        result = _run_agent_one_request(agent, {"type": "unknown", "from": "test"})

        assert result["type"] == "error"
        assert "不明なメッセージタイプ" in result["message"]
