"""BaseAgent のソケットサーバーループテスト

serve_forever() のソケットループ、stop() 呼び出しによるループ終了、
接続ハンドリングのテスト。
"""

from __future__ import annotations

import os
import socket
import threading
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from yadon_agents.agent.base import BaseAgent
from yadon_agents.infra.protocol import create_server_socket, send_message


class FakeAgent(BaseAgent):
    """テスト用の最小限エージェント実装"""

    def __init__(self, sock_path: str, handle_task_delay: float = 0):
        super().__init__(name="fake-agent", sock_path=sock_path, project_dir="/tmp")
        self.handle_task_delay = handle_task_delay
        self.task_handled_count = 0

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any]:
        if self.handle_task_delay > 0:
            time.sleep(self.handle_task_delay)
        self.task_handled_count += 1
        return {"type": "result", "from": self.name, "status": "success"}


class TestServeForever:
    """serve_forever() のテスト"""

    def test_serve_forever_starts_and_stops(self, sock_dir: str) -> None:
        """サーバーが起動し、stop() で終了すること"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        server_thread = threading.Thread(target=agent.serve_forever, daemon=True)
        server_thread.start()

        # サーバーが起動するのを待つ
        time.sleep(0.3)

        assert agent.running is True

        # stop() を呼び出して終了
        agent.stop()
        server_thread.join(timeout=3)

        assert agent.running is False
        # ソケットファイルが削除されていること
        assert not os.path.exists(sock_path)

    def test_serve_forever_handles_single_request(self, sock_dir: str) -> None:
        """1つのリクエストを処理できること"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        server_thread = threading.Thread(target=agent.serve_forever, daemon=True)
        server_thread.start()

        # サーバーが起動するのを待つ
        time.sleep(0.3)

        # リクエストを送信
        response = send_message(
            sock_path,
            {"type": "task", "id": "t1", "from": "test", "payload": {"instruction": "test"}},
            timeout=5,
        )

        assert response["type"] == "result"
        assert response["status"] == "success"
        assert agent.task_handled_count == 1

        agent.stop()
        server_thread.join(timeout=3)

    def test_serve_forever_handles_multiple_requests(self, sock_dir: str) -> None:
        """複数のリクエストを順次処理できること"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        server_thread = threading.Thread(target=agent.serve_forever, daemon=True)
        server_thread.start()

        time.sleep(0.3)

        # 複数のリクエストを送信
        for i in range(3):
            response = send_message(
                sock_path,
                {"type": "task", "id": f"t{i}", "from": "test", "payload": {"instruction": f"test{i}"}},
                timeout=5,
            )
            assert response["status"] == "success"

        assert agent.task_handled_count == 3

        agent.stop()
        server_thread.join(timeout=3)

    def test_serve_forever_timeout_loop(self, sock_dir: str) -> None:
        """タイムアウトループが正常に動作すること"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        server_thread = threading.Thread(target=agent.serve_forever, daemon=True)
        server_thread.start()

        time.sleep(0.3)

        # タイムアウトが発生しても継続すること
        time.sleep(2)  # SOCKET_ACCEPT_TIMEOUT より長く待つ

        # まだ動作していること
        assert agent.running is True

        agent.stop()
        server_thread.join(timeout=3)

    def test_serve_forever_socket_cleanup_on_error(self, sock_dir: str) -> None:
        """エラー発生時もソケットがクリーンアップされること"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        # create_server_socket をモックしてエラーを発生させる
        original_create = create_server_socket

        def mock_create(path: str) -> socket.socket:
            sock = original_create(path)
            # 最初の accept でエラーを発生させる
            original_accept = sock.accept

            def error_accept():
                agent.running = False
                raise OSError("Mocked error")

            sock.accept = error_accept
            return sock

        with patch("yadon_agents.agent.base.proto.create_server_socket", side_effect=mock_create):
            agent.serve_forever()

        # ソケットファイルが削除されていること
        assert not os.path.exists(sock_path)


class TestStop:
    """stop() のテスト"""

    def test_stop_sets_running_false(self, sock_dir: str) -> None:
        """stop() が running フラグを False にすること"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)
        agent.running = True

        agent.stop()

        assert agent.running is False

    def test_stop_can_be_called_multiple_times(self, sock_dir: str) -> None:
        """stop() を複数回呼び出してもエラーにならないこと"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)
        agent.running = True

        agent.stop()
        agent.stop()
        agent.stop()

        assert agent.running is False


class TestOnBubbleCallback:
    """on_bubble callback のテスト"""

    def test_bubble_callback_called(self, sock_dir: str) -> None:
        """bubble() が on_bubble callback を呼び出すこと"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        callback_calls = []

        def mock_callback(text: str, bubble_type: str, duration: int) -> None:
            callback_calls.append((text, bubble_type, duration))

        agent.on_bubble = mock_callback
        agent.bubble("テストメッセージ", "info", 3000)

        assert len(callback_calls) == 1
        assert callback_calls[0] == ("テストメッセージ", "info", 3000)

    def test_bubble_no_callback(self, sock_dir: str) -> None:
        """on_bubble が None の場合、エラーにならないこと"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        agent.on_bubble = None
        # エラーにならないこと
        agent.bubble("テストメッセージ")

    def test_on_bubble_property_getter_setter(self, sock_dir: str) -> None:
        """on_bubble プロパティの getter/setter が動作すること"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        assert agent.on_bubble is None

        def callback(text: str, bubble_type: str, duration: int) -> None:
            pass

        agent.on_bubble = callback
        assert agent.on_bubble is callback


class TestHandleConnection:
    """handle_connection() のテスト（追加テスト）"""

    def test_handle_connection_sets_timeout(self, sock_dir: str) -> None:
        """接続にタイムアウトが設定されること"""
        from yadon_agents.config.agent import SOCKET_CONNECTION_TIMEOUT

        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        mock_conn = MagicMock()
        mock_conn.recv.return_value = b'{"type": "status"}'

        agent.handle_connection(mock_conn)

        mock_conn.settimeout.assert_called_with(SOCKET_CONNECTION_TIMEOUT)

    def test_handle_connection_closes_socket(self, sock_dir: str) -> None:
        """接続が終了時にクローズされること"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        mock_conn = MagicMock()
        mock_conn.recv.return_value = b'{"type": "status"}'

        agent.handle_connection(mock_conn)

        mock_conn.close.assert_called_once()


class TestHandleStatusInBaseAgent:
    """BaseAgent の handle_status() テスト"""

    def test_handle_status_idle_state(self, sock_dir: str) -> None:
        """アイドル状態で正しいレスポンスを返すこと"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)
        agent.current_task_id = None

        result = agent.handle_status({})

        assert result["type"] == "status_response"
        assert result["state"] == "idle"
        assert result["current_task"] is None

    def test_handle_status_busy_state(self, sock_dir: str) -> None:
        """ビジー状態で正しいレスポンスを返すこと"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)
        agent.current_task_id = "task-12345"

        result = agent.handle_status({})

        assert result["state"] == "busy"
        assert result["current_task"] == "task-12345"


class TestNameProperty:
    """name プロパティのテスト"""

    def test_name_returns_agent_name(self, sock_dir: str) -> None:
        """name プロパティがエージェント名を返すこと"""
        sock_path = os.path.join(sock_dir, "t.sock")
        agent = FakeAgent(sock_path)

        assert agent.name == "fake-agent"


class TestConcurrentRequests:
    """同時リクエストのテスト"""

    def test_serve_forever_sequential_processing(self, sock_dir: str) -> None:
        """リクエストが順次処理されること（並列ではなく）"""
        sock_path = os.path.join(sock_dir, "t.sock")
        # タスク処理に時間がかかるエージェント
        agent = FakeAgent(sock_path, handle_task_delay=0.1)

        server_thread = threading.Thread(target=agent.serve_forever, daemon=True)
        server_thread.start()

        time.sleep(0.3)

        start_time = time.time()

        # 2つのリクエストを送信（順次処理されるので約0.2秒かかる）
        for i in range(2):
            send_message(
                sock_path,
                {"type": "task", "id": f"t{i}", "from": "test", "payload": {"instruction": f"test{i}"}},
                timeout=5,
            )

        elapsed = time.time() - start_time

        # 順次処理なので約0.2秒以上かかる
        assert elapsed >= 0.2
        assert agent.task_handled_count == 2

        agent.stop()
        server_thread.join(timeout=3)
