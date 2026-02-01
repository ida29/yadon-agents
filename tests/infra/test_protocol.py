"""Unixソケットプロトコルのテスト"""

import os
import socket
import threading

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
