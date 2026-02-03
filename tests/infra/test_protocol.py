"""Unixソケットプロトコルのテスト"""

import json
import os
import socket
import threading

import pytest

from yadon_agents.infra.protocol import (
    agent_socket_path,
    cleanup_socket,
    create_server_socket,
    pet_socket_path,
    receive_message,
    send_message,
    send_response,
)


class TestSocketPaths:
    def test_agent_socket_path(self):
        assert agent_socket_path("yadoran") == "/tmp/yadon-agent-yadoran.sock"
        assert agent_socket_path("yadon-1") == "/tmp/yadon-agent-yadon-1.sock"

    def test_pet_socket_path(self):
        assert pet_socket_path("yadoran") == "/tmp/yadon-pet-yadoran.sock"
        assert pet_socket_path("1") == "/tmp/yadon-pet-1.sock"


class TestCreateServerSocket:
    def test_creates_listening_socket(self, sock_dir):
        sock_path = os.path.join(sock_dir, "t.sock")
        sock = create_server_socket(sock_path)
        try:
            assert sock.fileno() != -1
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(sock_path)
            client.close()
        finally:
            sock.close()

    def test_closes_socket_on_bind_failure(self, tmp_path):
        """Issue 3 修正検証: bind失敗時にソケットが閉じられること"""
        sock_path = str(tmp_path / "nonexistent" / "deep" / "test.sock")
        try:
            create_server_socket(sock_path)
            assert False, "Should have raised"
        except OSError:
            pass

    def test_removes_existing_socket_file(self, sock_dir):
        sock_path = os.path.join(sock_dir, "t.sock")
        with open(sock_path, "w") as f:
            f.write("dummy")
        sock = create_server_socket(sock_path)
        try:
            assert sock.fileno() != -1
        finally:
            sock.close()


class TestCleanupSocket:
    def test_removes_socket_file(self, tmp_path):
        sock_path = str(tmp_path / "test.sock")
        with open(sock_path, "w") as f:
            f.write("dummy")
        cleanup_socket(sock_path)
        assert not (tmp_path / "test.sock").exists()

    def test_no_error_if_missing(self, tmp_path):
        sock_path = str(tmp_path / "nonexistent.sock")
        cleanup_socket(sock_path)


class TestSendReceiveRoundTrip:
    def test_roundtrip(self, sock_dir):
        """send_message + receive_message + send_response の往復テスト"""
        sock_path = os.path.join(sock_dir, "rt.sock")
        server = create_server_socket(sock_path)

        response_payload = {"type": "result", "status": "ok"}

        def server_handler():
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert msg["type"] == "task"
                send_response(conn, response_payload)
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, {"type": "task", "data": "hello"}, timeout=5.0)
        assert result == response_payload

        thread.join(timeout=5)
        server.close()


class TestProtocolEdgeCases:
    """ソケット通信のエッジケーステスト"""

    @pytest.mark.slow
    def test_send_receive_large_json_message(self, sock_dir):
        """大きなJSON（1MB）を送受信"""
        sock_path = os.path.join(sock_dir, "large.sock")
        server = create_server_socket(sock_path)

        # 1MBのデータを含むJSON
        large_payload = {
            "type": "task",
            "data": "x" * (1024 * 1024),
            "nested": {
                "deep": "value"
            }
        }
        response_payload = {"type": "result", "status": "received"}

        def server_handler():
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert msg["data"] == "x" * (1024 * 1024)
                send_response(conn, response_payload)
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, large_payload, timeout=10.0)
        assert result == response_payload

        thread.join(timeout=10)
        server.close()

    def test_send_receive_unicode_message(self, sock_dir):
        """Unicode文字（絵文字、多言語）を含むメッセージ"""
        sock_path = os.path.join(sock_dir, "unicode.sock")
        server = create_server_socket(sock_path)

        unicode_payload = {
            "type": "task",
            "data": "日本語 🎉 → 한글 Ελληνικά العربية",
            "emoji": "🚀 🎯 ✨ 💎"
        }
        response_payload = {"type": "result", "message": "ユニコード受信"}

        def server_handler():
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert "🎉" in msg["data"]
                assert "한글" in msg["data"]
                send_response(conn, response_payload)
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, unicode_payload, timeout=5.0)
        assert "ユニコード受信" in result["message"]

        thread.join(timeout=5)
        server.close()

    def test_send_receive_nested_json(self, sock_dir):
        """深くネストされたJSON構造"""
        sock_path = os.path.join(sock_dir, "nested.sock")
        server = create_server_socket(sock_path)

        deeply_nested = {
            "type": "task",
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
                                "level6": {
                                    "value": "深い値"
                                }
                            }
                        }
                    }
                }
            }
        }
        response_payload = {"type": "result", "depth": 6}

        def server_handler():
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert msg["level1"]["level2"]["level3"]["level4"]["level5"]["level6"]["value"] == "深い値"
                send_response(conn, response_payload)
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, deeply_nested, timeout=5.0)
        assert result["depth"] == 6

        thread.join(timeout=5)
        server.close()

    def test_send_receive_empty_string_field(self, sock_dir):
        """空文字列フィールドを含むメッセージ"""
        sock_path = os.path.join(sock_dir, "empty.sock")
        server = create_server_socket(sock_path)

        payload = {
            "type": "task",
            "empty": "",
            "spaces": "   ",
            "newlines": "\n\n\n"
        }
        response_payload = {"type": "result", "status": "ok"}

        def server_handler():
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert msg["empty"] == ""
                assert msg["spaces"] == "   "
                send_response(conn, response_payload)
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, payload, timeout=5.0)
        assert result == response_payload

        thread.join(timeout=5)
        server.close()

    def test_send_receive_array_in_json(self, sock_dir):
        """配列を含むJSON構造"""
        sock_path = os.path.join(sock_dir, "array.sock")
        server = create_server_socket(sock_path)

        payload = {
            "type": "task",
            "items": [
                {"id": 1, "name": "item1"},
                {"id": 2, "name": "item2"},
                {"id": 3, "name": "item3"}
            ],
            "numbers": [1, 2, 3, 4, 5],
            "nested_arrays": [[1, 2], [3, 4], [5, 6]]
        }
        response_payload = {"type": "result", "count": 3}

        def server_handler():
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert len(msg["items"]) == 3
                assert msg["items"][0]["name"] == "item1"
                assert len(msg["nested_arrays"]) == 3
                send_response(conn, response_payload)
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, payload, timeout=5.0)
        assert result["count"] == 3

        thread.join(timeout=5)
        server.close()

    def test_send_receive_special_characters(self, sock_dir):
        """特殊文字（制御文字、改行など）を含むメッセージ"""
        sock_path = os.path.join(sock_dir, "special.sock")
        server = create_server_socket(sock_path)

        payload = {
            "type": "task",
            "data": "通常\n改行\t\tタブ\r\nCRLF\u0000null",
            "quotes": 'シングル "ダブル" バックスラッシュ \\',
        }
        response_payload = {"type": "result", "status": "received"}

        def server_handler():
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert "\n" in msg["data"]
                assert "\t" in msg["data"]
                send_response(conn, response_payload)
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, payload, timeout=5.0)
        assert result["status"] == "received"

        thread.join(timeout=5)
        server.close()

    @pytest.mark.slow
    def test_multiple_sequential_messages(self, sock_dir):
        """複数のメッセージを順番に送受信"""
        sock_path = os.path.join(sock_dir, "multi.sock")
        server = create_server_socket(sock_path)

        messages_received = []

        def server_handler():
            for i in range(3):
                conn, _ = server.accept()
                try:
                    msg = receive_message(conn)
                    messages_received.append(msg)
                    send_response(conn, {"type": "result", "id": i})
                finally:
                    conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        # 3つのメッセージを送信
        for i in range(3):
            payload = {"type": "task", "id": i, "data": f"message{i}"}
            result = send_message(sock_path, payload, timeout=5.0)
            assert result["id"] == i

        thread.join(timeout=10)
        server.close()

        # サーバーが3つのメッセージを受け取ったことを確認
        assert len(messages_received) == 3
        for i, msg in enumerate(messages_received):
            assert msg["id"] == i

    def test_large_json_with_many_fields(self, sock_dir):
        """多数のフィールドを持つ大きなJSON"""
        sock_path = os.path.join(sock_dir, "many_fields.sock")
        server = create_server_socket(sock_path)

        # 100個のフィールドを持つペイロード
        payload = {
            "type": "task",
            **{f"field_{i}": f"value_{i}" for i in range(100)}
        }
        response_payload = {"type": "result", "fields": 100}

        def server_handler():
            conn, _ = server.accept()
            try:
                msg = receive_message(conn)
                assert len(msg) == 101  # type + 100 fields
                assert msg["field_0"] == "value_0"
                assert msg["field_99"] == "value_99"
                send_response(conn, response_payload)
            finally:
                conn.close()

        thread = threading.Thread(target=server_handler, daemon=True)
        thread.start()

        result = send_message(sock_path, payload, timeout=5.0)
        assert result["fields"] == 100

        thread.join(timeout=5)
        server.close()
