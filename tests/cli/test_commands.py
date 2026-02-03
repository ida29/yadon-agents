"""commands.py のテスト

CLI コマンド関数（send_task, check_status, pet_say）のユニットテスト。
ソケット通信はモックして、関数のロジックをテストする。
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from yadon_agents.commands import check_status, pet_say, send_task


class TestSendTask:
    """send_task() のテスト"""

    def test_send_task_basic(self, monkeypatch):
        """基本的なタスク送信が正しく動作すること"""
        mock_response = {
            "type": "result",
            "id": "task-001",
            "from": "yadoran",
            "status": "success",
            "payload": {"output": "完了", "summary": "タスク完了"},
        }

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response

            result = send_task("テストタスク")

            assert result["status"] == "success"
            assert result["type"] == "result"

            # send_message が正しい引数で呼ばれたことを確認
            call_args = mock_send.call_args
            assert call_args[0][1]["type"] == "task"
            assert call_args[0][1]["payload"]["instruction"] == "テストタスク"

    def test_send_task_with_project_dir(self, monkeypatch):
        """project_dir が正しく渡されること"""
        mock_response = {"type": "result", "status": "success", "payload": {}}

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response

            result = send_task("タスク", project_dir="/custom/path")

            call_args = mock_send.call_args
            assert call_args[0][1]["payload"]["project_dir"] == "/custom/path"

    def test_send_task_timeout(self, monkeypatch):
        """タイムアウトが600秒で設定されていること"""
        mock_response = {"type": "result", "status": "success", "payload": {}}

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response

            send_task("タスク")

            call_args = mock_send.call_args
            assert call_args[1]["timeout"] == 600 or call_args[0][2] == 600

    def test_send_task_unicode_instruction(self, monkeypatch):
        """Unicode文字を含む指示が正しく送信されること"""
        mock_response = {"type": "result", "status": "success", "payload": {}}

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response

            result = send_task("日本語タスク 🎉 with emoji")

            call_args = mock_send.call_args
            assert call_args[0][1]["payload"]["instruction"] == "日本語タスク 🎉 with emoji"


class TestCheckStatus:
    """check_status() のテスト"""

    def test_check_status_default_agent(self, monkeypatch):
        """デフォルトでマネージャーのステータスを確認すること"""
        mock_response = {
            "type": "status_response",
            "from": "yadoran",
            "state": "idle",
            "current_task": None,
            "workers": {"yadon-1": "idle", "yadon-2": "idle"},
        }

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response

            result = check_status()

            assert result["state"] == "idle"
            assert result["from"] == "yadoran"

    def test_check_status_specific_agent(self, monkeypatch):
        """特定のエージェントを指定してステータス確認できること"""
        mock_response = {
            "type": "status_response",
            "from": "yadon-1",
            "state": "busy",
        }

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response
            with patch("yadon_agents.commands.agent_socket_path") as mock_path:
                mock_path.return_value = "/tmp/test.sock"

                result = check_status("yadon-1")

                # agent_socket_path が yadon-1 で呼ばれたことを確認
                mock_path.assert_called()
                assert "yadon-1" in str(mock_path.call_args)

    def test_check_status_timeout(self, monkeypatch):
        """タイムアウトが5秒で設定されていること"""
        mock_response = {"type": "status_response", "state": "idle"}

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response

            check_status()

            call_args = mock_send.call_args
            # timeout 引数が5秒であることを確認
            assert call_args[1]["timeout"] == 5 or (len(call_args[0]) > 2 and call_args[0][2] == 5)


class TestPetSay:
    """pet_say() のテスト"""

    def test_pet_say_socket_not_exists(self, tmp_path, monkeypatch):
        """ソケットが存在しない場合、静かに終了すること"""
        with patch("yadon_agents.commands.pet_socket_path") as mock_path:
            # 存在しないパスを返す
            mock_path.return_value = str(tmp_path / "nonexistent.sock")

            # エラーなく終了することを確認
            pet_say(1, "テストメッセージ")

    def test_pet_say_with_custom_params(self, tmp_path, monkeypatch):
        """カスタムパラメータが正しく設定されること"""
        sock_file = tmp_path / "test.sock"
        sock_file.touch()

        received_data = []

        def mock_socket_class(*args, **kwargs):
            mock_sock = MagicMock()
            mock_sock.sendall = lambda data: received_data.append(data)
            mock_sock.connect = MagicMock()
            mock_sock.close = MagicMock()
            return mock_sock

        with patch("yadon_agents.commands.pet_socket_path") as mock_path:
            mock_path.return_value = str(sock_file)
            with patch("yadon_agents.commands.socket.socket", mock_socket_class):
                pet_say(2, "カスタムメッセージ", bubble_type="success", duration_ms=3000)

                # 送信されたデータを確認
                if received_data:
                    data = json.loads(received_data[0].decode("utf-8"))
                    assert data["text"] == "カスタムメッセージ"
                    assert data["type"] == "success"
                    assert data["duration"] == 3000

    def test_pet_say_connection_error_silent(self, tmp_path, monkeypatch):
        """接続エラー時も静かに終了すること"""
        sock_file = tmp_path / "test.sock"
        sock_file.touch()

        def mock_socket_class(*args, **kwargs):
            mock_sock = MagicMock()
            mock_sock.connect = MagicMock(side_effect=socket.error("接続拒否"))
            return mock_sock

        with patch("yadon_agents.commands.pet_socket_path") as mock_path:
            mock_path.return_value = str(sock_file)
            with patch("yadon_agents.commands.socket.socket", mock_socket_class):
                # エラーが発生しないことを確認
                pet_say(1, "メッセージ")

    def test_pet_say_timeout_silent(self, tmp_path, monkeypatch):
        """タイムアウト時も静かに終了すること"""
        sock_file = tmp_path / "test.sock"
        sock_file.touch()

        def mock_socket_class(*args, **kwargs):
            mock_sock = MagicMock()
            mock_sock.connect = MagicMock(side_effect=socket.timeout("タイムアウト"))
            return mock_sock

        with patch("yadon_agents.commands.pet_socket_path") as mock_path:
            mock_path.return_value = str(sock_file)
            with patch("yadon_agents.commands.socket.socket", mock_socket_class):
                # エラーが発生しないことを確認
                pet_say(1, "メッセージ")

    def test_pet_say_unicode_message(self, tmp_path, monkeypatch):
        """Unicode文字を含むメッセージが正しく送信されること"""
        sock_file = tmp_path / "test.sock"
        sock_file.touch()

        received_data = []

        def mock_socket_class(*args, **kwargs):
            mock_sock = MagicMock()
            mock_sock.sendall = lambda data: received_data.append(data)
            mock_sock.connect = MagicMock()
            mock_sock.close = MagicMock()
            return mock_sock

        with patch("yadon_agents.commands.pet_socket_path") as mock_path:
            mock_path.return_value = str(sock_file)
            with patch("yadon_agents.commands.socket.socket", mock_socket_class):
                pet_say(1, "日本語メッセージ 🎉 絵文字付き")

                if received_data:
                    data = json.loads(received_data[0].decode("utf-8"))
                    assert "日本語" in data["text"]
                    assert "🎉" in data["text"]


class TestSendTaskEdgeCases:
    """send_task() のエッジケーステスト"""

    def test_send_task_empty_instruction(self, monkeypatch):
        """空の指示でもエラーにならないこと"""
        mock_response = {"type": "result", "status": "success", "payload": {}}

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response

            result = send_task("")

            call_args = mock_send.call_args
            assert call_args[0][1]["payload"]["instruction"] == ""

    def test_send_task_very_long_instruction(self, monkeypatch):
        """非常に長い指示が正しく送信されること"""
        mock_response = {"type": "result", "status": "success", "payload": {}}
        long_instruction = "タスク" * 10000  # 約50,000文字

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response

            result = send_task(long_instruction)

            call_args = mock_send.call_args
            assert len(call_args[0][1]["payload"]["instruction"]) == len(long_instruction)

    def test_send_task_special_characters(self, monkeypatch):
        """特殊文字を含む指示が正しく送信されること"""
        mock_response = {"type": "result", "status": "success", "payload": {}}
        special_instruction = "タブ\tと改行\nとクォート'\"とバックスラッシュ\\"

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response

            result = send_task(special_instruction)

            call_args = mock_send.call_args
            assert "\t" in call_args[0][1]["payload"]["instruction"]
            assert "\n" in call_args[0][1]["payload"]["instruction"]


class TestCheckStatusEdgeCases:
    """check_status() のエッジケーステスト"""

    def test_check_status_busy_with_task(self, monkeypatch):
        """busyステートでcurrent_taskがある場合"""
        mock_response = {
            "type": "status_response",
            "state": "busy",
            "current_task": "task-20260203-120000-a1b2",
        }

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response

            result = check_status()

            assert result["state"] == "busy"
            assert result["current_task"] == "task-20260203-120000-a1b2"

    def test_check_status_with_many_workers(self, monkeypatch):
        """多数のワーカーステータスを含むレスポンス"""
        workers = {f"yadon-{i}": "idle" if i % 2 == 0 else "busy" for i in range(1, 9)}
        mock_response = {
            "type": "status_response",
            "state": "busy",
            "workers": workers,
        }

        with patch("yadon_agents.commands.send_message") as mock_send:
            mock_send.return_value = mock_response

            result = check_status()

            assert len(result["workers"]) == 8
            assert result["workers"]["yadon-1"] == "busy"
            assert result["workers"]["yadon-2"] == "idle"
