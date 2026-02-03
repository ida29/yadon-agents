"""ソケット通信の統合テスト

Unix ソケットを使用した実際の通信テスト:
- 送受信の往復テスト
- タイムアウト動作
- 複数メッセージの連続送信
- エッジケース
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from typing import Any

import pytest

from yadon_agents.domain.messages import (
    ResultMessage,
    StatusQuery,
    StatusResponse,
    TaskMessage,
)
from yadon_agents.infra.protocol import (
    cleanup_socket,
    create_server_socket,
    receive_message,
    send_message,
    send_response,
)


@pytest.mark.integration
class TestSocketRoundtrip:
    """ソケット通信の往復テスト"""

    def test_task_message_roundtrip(self, sock_dir: str) -> None:
        """TaskMessage の送受信往復"""
        sock_path = os.path.join(sock_dir, "task_rt.sock")
        server = create_server_socket(sock_path)

        task = TaskMessage(
            from_agent="yadoking",
            instruction="テストタスク",
            project_dir="/work/project",
        )

        response_data = {"type": "ack", "status": "received"}

        def server_handler() -> None:
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                # TaskMessage の形式を検証
                assert msg["type"] == "task"
                assert msg["payload"]["instruction"] == "テストタスク"
                send_response(conn, response_data)
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, task.to_dict(), timeout=5.0)
        assert result == response_data

        thread.join(timeout=5)
        server.close()

    def test_result_message_roundtrip(self, sock_dir: str) -> None:
        """ResultMessage の送受信往復"""
        sock_path = os.path.join(sock_dir, "result_rt.sock")
        server = create_server_socket(sock_path)

        result_msg = ResultMessage(
            task_id="task-123",
            from_agent="yadon-1",
            status="success",
            output="完了しました",
            summary="成功",
        )

        ack_data = {"type": "ack", "status": "ok"}

        def server_handler() -> None:
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert msg["type"] == "result"
                assert msg["status"] == "success"
                send_response(conn, ack_data)
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, result_msg.to_dict(), timeout=5.0)
        assert result == ack_data

        thread.join(timeout=5)
        server.close()

    def test_status_query_response_roundtrip(self, sock_dir: str) -> None:
        """StatusQuery と StatusResponse の往復"""
        sock_path = os.path.join(sock_dir, "status_rt.sock")
        server = create_server_socket(sock_path)

        query = StatusQuery(from_agent="check")
        response = StatusResponse(
            from_agent="yadon-1",
            state="idle",
            current_task=None,
        )

        def server_handler() -> None:
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert msg["type"] == "status"
                send_response(conn, response.to_dict())
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, query.to_dict(), timeout=5.0)
        assert result["type"] == "status_response"
        assert result["state"] == "idle"

        thread.join(timeout=5)
        server.close()


@pytest.mark.integration
class TestSocketTimeout:
    """タイムアウト動作のテスト"""

    @pytest.mark.slow
    def test_connection_timeout(self, sock_dir: str) -> None:
        """接続タイムアウトのテスト"""
        # 存在しないソケットパス
        sock_path = os.path.join(sock_dir, "nonexistent.sock")

        # タイムアウトで例外が発生
        with pytest.raises(Exception):  # ConnectionError or FileNotFoundError
            send_message(sock_path, {"type": "test"}, timeout=1.0)

    @pytest.mark.slow
    def test_response_timeout(self, sock_dir: str) -> None:
        """応答タイムアウトのテスト"""
        sock_path = os.path.join(sock_dir, "slow.sock")
        server = create_server_socket(sock_path)

        def slow_handler() -> None:
            conn, _ = server.accept()
            try:
                receive_message(conn)
                # わざと遅延（応答を返さない）
                time.sleep(5)
            except Exception:
                pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        thread = threading.Thread(target=slow_handler, daemon=True)
        thread.start()

        # 短いタイムアウトで送信
        start = time.time()
        try:
            send_message(sock_path, {"type": "test"}, timeout=1.0)
        except Exception:
            pass  # タイムアウト例外を期待
        elapsed = time.time() - start

        # タイムアウト時間以内に完了（許容範囲）
        assert elapsed < 3.0

        thread.join(timeout=1)
        server.close()


@pytest.mark.integration
class TestMultipleMessages:
    """複数メッセージの連続送信テスト"""

    def test_sequential_messages(self, sock_dir: str) -> None:
        """連続した複数メッセージの送受信"""
        sock_path = os.path.join(sock_dir, "multi.sock")
        server = create_server_socket(sock_path)

        messages_received: list[dict[str, Any]] = []
        message_count = 5

        def server_handler() -> None:
            for i in range(message_count):
                conn, _ = server.accept()
                try:
                    msg = receive_message(conn)
                    messages_received.append(msg)
                    send_response(conn, {"type": "ack", "seq": i})
                finally:
                    conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        # 5つのメッセージを順次送信
        for i in range(message_count):
            task = TaskMessage(
                from_agent=f"sender-{i}",
                instruction=f"Task {i}",
                project_dir=f"/work/{i}",
            )
            result = send_message(sock_path, task.to_dict(), timeout=5.0)
            assert result["seq"] == i

        thread.join(timeout=10)
        server.close()

        # 全メッセージ受信確認
        assert len(messages_received) == message_count
        for i, msg in enumerate(messages_received):
            assert msg["from"] == f"sender-{i}"

    def test_rapid_fire_messages(self, sock_dir: str) -> None:
        """高速連続送信テスト"""
        sock_path = os.path.join(sock_dir, "rapid.sock")
        server = create_server_socket(sock_path)

        received_count = 0
        message_count = 10
        lock = threading.Lock()

        def server_handler() -> None:
            nonlocal received_count
            for _ in range(message_count):
                conn, _ = server.accept()
                try:
                    receive_message(conn)
                    with lock:
                        received_count += 1
                    send_response(conn, {"status": "ok"})
                finally:
                    conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        # 高速で送信（待機なし）
        for i in range(message_count):
            send_message(sock_path, {"id": i}, timeout=5.0)

        thread.join(timeout=10)
        server.close()

        assert received_count == message_count


@pytest.mark.integration
class TestSocketEdgeCases:
    """エッジケースのテスト"""

    def test_large_message(self, sock_dir: str) -> None:
        """大きなメッセージの送受信"""
        sock_path = os.path.join(sock_dir, "large.sock")
        server = create_server_socket(sock_path)

        # 100KB のデータ
        large_data = "x" * (100 * 1024)
        payload = {"type": "large", "data": large_data}

        def server_handler() -> None:
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert len(msg["data"]) == 100 * 1024
                send_response(conn, {"status": "received", "size": len(msg["data"])})
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, payload, timeout=10.0)
        assert result["size"] == 100 * 1024

        thread.join(timeout=10)
        server.close()

    def test_unicode_message(self, sock_dir: str) -> None:
        """Unicode メッセージの送受信"""
        sock_path = os.path.join(sock_dir, "unicode.sock")
        server = create_server_socket(sock_path)

        unicode_text = "日本語 🎉 한글 العربية Ελληνικά"
        payload = {"type": "unicode", "text": unicode_text}

        def server_handler() -> None:
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert msg["text"] == unicode_text
                send_response(conn, {"status": "ok", "text": msg["text"]})
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, payload, timeout=5.0)
        assert result["text"] == unicode_text

        thread.join(timeout=5)
        server.close()

    def test_nested_json_structure(self, sock_dir: str) -> None:
        """深くネストされた JSON の送受信"""
        sock_path = os.path.join(sock_dir, "nested.sock")
        server = create_server_socket(sock_path)

        nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "deep"
                        }
                    }
                }
            }
        }

        def server_handler() -> None:
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                deep_value = msg["level1"]["level2"]["level3"]["level4"]["value"]
                assert deep_value == "deep"
                send_response(conn, {"status": "ok"})
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, nested, timeout=5.0)
        assert result["status"] == "ok"

        thread.join(timeout=5)
        server.close()

    def test_special_characters_in_message(self, sock_dir: str) -> None:
        """特殊文字を含むメッセージの送受信"""
        sock_path = os.path.join(sock_dir, "special.sock")
        server = create_server_socket(sock_path)

        special_text = "Newline\nTab\tCarriage\rNull\x00Quote\"Backslash\\"
        payload = {"type": "special", "text": special_text}

        def server_handler() -> None:
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert "\n" in msg["text"]
                assert "\t" in msg["text"]
                send_response(conn, {"status": "ok"})
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, payload, timeout=5.0)
        assert result["status"] == "ok"

        thread.join(timeout=5)
        server.close()

    def test_empty_response(self, sock_dir: str) -> None:
        """空オブジェクトの応答"""
        sock_path = os.path.join(sock_dir, "empty.sock")
        server = create_server_socket(sock_path)

        def server_handler() -> None:
            conn, _ = server.accept()
            try:
                receive_message(conn)
                send_response(conn, {})
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, {"type": "test"}, timeout=5.0)
        assert result == {}

        thread.join(timeout=5)
        server.close()


@pytest.mark.integration
class TestSocketCleanup:
    """ソケットクリーンアップのテスト"""

    def test_cleanup_removes_socket_file(self, sock_dir: str) -> None:
        """cleanup_socket がソケットファイルを削除することを確認"""
        sock_path = os.path.join(sock_dir, "cleanup_test.sock")

        # ソケット作成
        server = create_server_socket(sock_path)
        assert os.path.exists(sock_path)

        server.close()
        cleanup_socket(sock_path)

        # ファイルが削除されている
        assert not os.path.exists(sock_path)

    def test_cleanup_nonexistent_file_no_error(self, sock_dir: str) -> None:
        """存在しないファイルのクリーンアップでエラーが発生しないことを確認"""
        sock_path = os.path.join(sock_dir, "nonexistent.sock")

        # 例外が発生しない
        cleanup_socket(sock_path)

    def test_server_socket_overwrite_existing(self, sock_dir: str) -> None:
        """既存のソケットファイルを上書きできることを確認"""
        sock_path = os.path.join(sock_dir, "overwrite.sock")

        # 最初のソケット作成
        server1 = create_server_socket(sock_path)
        server1.close()

        # ファイルが残っている状態で再作成
        server2 = create_server_socket(sock_path)
        assert server2.fileno() != -1

        server2.close()
        cleanup_socket(sock_path)


@pytest.mark.integration
@pytest.mark.slow
class TestSocketStressTest:
    """ストレステスト"""

    def test_many_connections(self, sock_dir: str) -> None:
        """多数の接続テスト"""
        sock_path = os.path.join(sock_dir, "stress.sock")
        server = create_server_socket(sock_path)

        connection_count = 20
        received = 0
        lock = threading.Lock()

        def server_handler() -> None:
            nonlocal received
            for _ in range(connection_count):
                try:
                    conn, _ = server.accept()
                    receive_message(conn)
                    with lock:
                        received += 1
                    send_response(conn, {"status": "ok"})
                    conn.close()
                except Exception:
                    break

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        # 多数の接続を作成
        for i in range(connection_count):
            try:
                send_message(sock_path, {"id": i}, timeout=5.0)
            except Exception:
                pass

        thread.join(timeout=30)
        server.close()

        # ある程度の接続が成功していることを確認
        assert received >= connection_count - 5  # 多少の失敗を許容
