"""cli.py のインテグレーションテスト

cmd_start(), cmd_stop(), cmd_status(), cmd_say() 等の
統合的な動作をテストする。subprocess と socket はモックで置き換え。
"""

from __future__ import annotations

import io
import json
import os
import socket
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest


class TestCmdStart:
    """cmd_start() のテスト"""

    def test_cmd_start_spawns_gui_daemon(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """GUI デーモンが subprocess.Popen で起動されること"""
        from yadon_agents.cli import cmd_start

        mock_popen = MagicMock()
        mock_popen.pid = 12345
        mock_popen.terminate = MagicMock()
        mock_popen.wait = MagicMock()

        mock_subprocess_run = MagicMock()
        mock_subprocess_run.returncode = 0

        with patch("yadon_agents.cli.subprocess.Popen", return_value=mock_popen) as popen_mock:
            with patch("yadon_agents.cli.subprocess.run", return_value=mock_subprocess_run):
                with patch("yadon_agents.cli._wait_sockets", return_value=True):
                    with patch("yadon_agents.cli.cmd_stop"):
                        with patch("yadon_agents.cli._cleanup_sockets"):
                            with patch("yadon_agents.ascii_art.show_yadon_ascii"):
                                with patch("yadon_agents.cli.log_dir", return_value=tmp_path):
                                    with patch("builtins.open", MagicMock()):
                                        with patch("sys.exit"):
                                            cmd_start(str(tmp_path), multi_llm=False)

        # Popen が呼ばれたことを確認
        popen_mock.assert_called_once()
        call_args = popen_mock.call_args
        # python -m yadon_agents.gui_daemon を呼び出している
        assert "yadon_agents.gui_daemon" in " ".join(call_args[0][0])

    def test_cmd_start_multi_llm_sets_env_vars(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """マルチLLMモードで YADON_N_BACKEND 環境変数が設定されること"""
        from yadon_agents.cli import cmd_start

        # 環境変数をクリア
        for i in range(1, 9):
            monkeypatch.delenv(f"YADON_{i}_BACKEND", raising=False)

        captured_env = {}

        def capture_popen(*args, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            mock = MagicMock()
            mock.pid = 12345
            mock.terminate = MagicMock()
            mock.wait = MagicMock()
            return mock

        mock_subprocess_run = MagicMock()
        mock_subprocess_run.returncode = 0

        with patch("yadon_agents.cli.subprocess.Popen", side_effect=capture_popen):
            with patch("yadon_agents.cli.subprocess.run", return_value=mock_subprocess_run):
                with patch("yadon_agents.cli._wait_sockets", return_value=True):
                    with patch("yadon_agents.cli.cmd_stop"):
                        with patch("yadon_agents.cli._cleanup_sockets"):
                            with patch("yadon_agents.ascii_art.show_yadon_ascii"):
                                with patch("yadon_agents.cli.log_dir", return_value=tmp_path):
                                    with patch("builtins.open", MagicMock()):
                                        with patch("sys.exit"):
                                            cmd_start(str(tmp_path), multi_llm=True)

        # マルチLLMモードの環境変数が設定されていることを確認
        assert "YADON_1_BACKEND" in captured_env
        assert "YADON_2_BACKEND" in captured_env
        # ローテーション確認
        assert captured_env.get("YADON_1_BACKEND") == "copilot"
        assert captured_env.get("YADON_2_BACKEND") == "gemini"

    def test_cmd_start_preserves_explicit_env_vars(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """明示的な YADON_N_BACKEND 環境変数が保持されること"""
        from yadon_agents.cli import cmd_start

        # 明示的に YADON_1_BACKEND を設定
        monkeypatch.setenv("YADON_1_BACKEND", "gemini")
        # 他はクリア
        for i in range(2, 9):
            monkeypatch.delenv(f"YADON_{i}_BACKEND", raising=False)

        captured_env = {}

        def capture_popen(*args, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            mock = MagicMock()
            mock.pid = 12345
            mock.terminate = MagicMock()
            mock.wait = MagicMock()
            return mock

        mock_subprocess_run = MagicMock()
        mock_subprocess_run.returncode = 0

        with patch("yadon_agents.cli.subprocess.Popen", side_effect=capture_popen):
            with patch("yadon_agents.cli.subprocess.run", return_value=mock_subprocess_run):
                with patch("yadon_agents.cli._wait_sockets", return_value=True):
                    with patch("yadon_agents.cli.cmd_stop"):
                        with patch("yadon_agents.cli._cleanup_sockets"):
                            with patch("yadon_agents.ascii_art.show_yadon_ascii"):
                                with patch("yadon_agents.cli.log_dir", return_value=tmp_path):
                                    with patch("builtins.open", MagicMock()):
                                        with patch("sys.exit"):
                                            cmd_start(str(tmp_path), multi_llm=True)

        # 明示的設定が保持されていることを確認
        assert captured_env.get("YADON_1_BACKEND") == "gemini"

    def test_cmd_start_non_multi_llm_clears_env_vars(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """非マルチLLMモードで YADON_N_BACKEND 環境変数がクリアされること"""
        from yadon_agents.cli import cmd_start

        # 環境変数を設定
        monkeypatch.setenv("YADON_1_BACKEND", "gemini")
        monkeypatch.setenv("YADON_2_BACKEND", "copilot")

        mock_popen = MagicMock()
        mock_popen.pid = 12345
        mock_popen.terminate = MagicMock()
        mock_popen.wait = MagicMock()

        mock_subprocess_run = MagicMock()
        mock_subprocess_run.returncode = 0

        with patch("yadon_agents.cli.subprocess.Popen", return_value=mock_popen):
            with patch("yadon_agents.cli.subprocess.run", return_value=mock_subprocess_run):
                with patch("yadon_agents.cli._wait_sockets", return_value=True):
                    with patch("yadon_agents.cli.cmd_stop"):
                        with patch("yadon_agents.cli._cleanup_sockets"):
                            with patch("yadon_agents.ascii_art.show_yadon_ascii"):
                                with patch("yadon_agents.cli.log_dir", return_value=tmp_path):
                                    with patch("builtins.open", MagicMock()):
                                        with patch("sys.exit"):
                                            cmd_start(str(tmp_path), multi_llm=False)

        # 環境変数がクリアされていることを確認
        assert "YADON_1_BACKEND" not in os.environ
        assert "YADON_2_BACKEND" not in os.environ

    def test_cmd_start_socket_timeout_prints_warning(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """ソケット待機タイムアウト時に警告が出力されること"""
        from yadon_agents.cli import cmd_start

        mock_popen = MagicMock()
        mock_popen.pid = 12345
        mock_popen.terminate = MagicMock()
        mock_popen.wait = MagicMock()

        mock_subprocess_run = MagicMock()
        mock_subprocess_run.returncode = 0

        with patch("yadon_agents.cli.subprocess.Popen", return_value=mock_popen):
            with patch("yadon_agents.cli.subprocess.run", return_value=mock_subprocess_run):
                with patch("yadon_agents.cli._wait_sockets", return_value=False):  # タイムアウト
                    with patch("yadon_agents.cli.cmd_stop"):
                        with patch("yadon_agents.cli._cleanup_sockets"):
                            with patch("yadon_agents.ascii_art.show_yadon_ascii"):
                                with patch("yadon_agents.cli.log_dir", return_value=tmp_path):
                                    with patch("builtins.open", MagicMock()):
                                        with patch("sys.exit"):
                                            cmd_start(str(tmp_path), multi_llm=False)

        captured = capsys.readouterr()
        assert "エージェントソケットが作成されませんでした" in captured.out

    def test_cmd_start_keyboard_interrupt(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """KeyboardInterrupt で正常に終了すること"""
        from yadon_agents.cli import cmd_start

        mock_popen = MagicMock()
        mock_popen.pid = 12345
        mock_popen.terminate = MagicMock()
        mock_popen.wait = MagicMock()

        # subprocess.run で KeyboardInterrupt を発生
        def raise_keyboard_interrupt(*args, **kwargs):
            raise KeyboardInterrupt()

        with patch("yadon_agents.cli.subprocess.Popen", return_value=mock_popen):
            with patch("yadon_agents.cli.subprocess.run", side_effect=raise_keyboard_interrupt):
                with patch("yadon_agents.cli._wait_sockets", return_value=True):
                    with patch("yadon_agents.cli.cmd_stop"):
                        with patch("yadon_agents.cli._cleanup_sockets"):
                            with patch("yadon_agents.ascii_art.show_yadon_ascii"):
                                with patch("yadon_agents.cli.log_dir", return_value=tmp_path):
                                    with patch("builtins.open", MagicMock()):
                                        with patch("sys.exit") as mock_exit:
                                            cmd_start(str(tmp_path), multi_llm=False)

        # 終了コード 0 で終了
        mock_exit.assert_called_with(0)


class TestCmdStop:
    """cmd_stop() のテスト"""

    def test_cmd_stop_calls_pkill(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """pkill コマンドが呼ばれること"""
        from yadon_agents.cli import cmd_stop

        with patch("yadon_agents.cli.subprocess.run") as mock_run:
            with patch("yadon_agents.cli._cleanup_sockets"):
                cmd_stop()

        # pkill が呼ばれたことを確認
        assert mock_run.call_count >= 2
        call_args_list = mock_run.call_args_list
        patterns = [call[0][0][2] for call in call_args_list if call[0][0][0] == "pkill"]
        assert any("yadon_agents.cli start" in p for p in patterns)
        assert any("yadon_agents.gui_daemon" in p for p in patterns)

    def test_cmd_stop_handles_pkill_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """pkill の例外がハンドルされること"""
        from yadon_agents.cli import cmd_stop

        def raise_exception(*args, **kwargs):
            raise RuntimeError("pkill failed")

        with patch("yadon_agents.cli.subprocess.run", side_effect=raise_exception):
            with patch("yadon_agents.cli._cleanup_sockets"):
                # エラーにならないこと
                cmd_stop()


class TestCmdStatus:
    """cmd_status() のテスト"""

    def test_cmd_status_success(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """正常時にステータスが表示されること"""
        from yadon_agents.cli import cmd_status

        mock_response = {
            "type": "status_response",
            "from": "yadoran",
            "state": "idle",
            "current_task": None,
            "workers": {"yadon-1": "idle", "yadon-2": "busy"},
        }

        with patch("yadon_agents.cli.send_message", return_value=mock_response):
            cmd_status()

        captured = capsys.readouterr()
        assert "状態: idle" in captured.out
        assert "yadon-1: idle" in captured.out
        assert "yadon-2: busy" in captured.out

    def test_cmd_status_timeout(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """タイムアウト時にエラーが表示されること"""
        from yadon_agents.cli import cmd_status

        with patch("yadon_agents.cli.send_message", side_effect=socket.timeout("timed out")):
            with pytest.raises(SystemExit) as exc_info:
                cmd_status()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "タイムアウト" in captured.out

    def test_cmd_status_specific_agent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """特定のエージェント名でステータス確認できること"""
        from yadon_agents.cli import cmd_status

        mock_response = {
            "type": "status_response",
            "from": "yadon-1",
            "state": "busy",
            "current_task": "task-001",
        }

        with patch("yadon_agents.cli.send_message", return_value=mock_response) as mock_send:
            with patch("yadon_agents.cli.agent_socket_path", return_value="/tmp/test.sock"):
                cmd_status(agent_name="yadon-1")

        # send_message が呼ばれたことを確認
        mock_send.assert_called_once()

    def test_cmd_status_with_current_task(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """現在のタスクがある場合に表示されること"""
        from yadon_agents.cli import cmd_status

        mock_response = {
            "type": "status_response",
            "from": "yadoran",
            "state": "busy",
            "current_task": "task-20260204-120000-abcd",
            "workers": {},
        }

        with patch("yadon_agents.cli.send_message", return_value=mock_response):
            cmd_status()

        captured = capsys.readouterr()
        assert "現在のタスク: task-20260204-120000-abcd" in captured.out


class TestCmdSay:
    """cmd_say() のテスト"""

    def test_cmd_say_socket_not_exists(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """ソケットが存在しない場合にエラーが表示されること"""
        from yadon_agents.cli import cmd_say

        with patch("yadon_agents.cli.pet_socket_path", return_value=str(tmp_path / "nonexistent.sock")):
            with pytest.raises(SystemExit) as exc_info:
                cmd_say(1, "テストメッセージ")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "ペットソケットが見つかりません" in captured.out

    def test_cmd_say_success(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """正常送信時にOKが表示されること"""
        from yadon_agents.cli import cmd_say

        sock_file = tmp_path / "test.sock"
        sock_file.touch()

        mock_sock = MagicMock()

        with patch("yadon_agents.cli.pet_socket_path", return_value=str(sock_file)):
            with patch("yadon_agents.cli.socket.socket", return_value=mock_sock):
                cmd_say(1, "テストメッセージ")

        captured = capsys.readouterr()
        assert "OK" in captured.out

    def test_cmd_say_timeout(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """タイムアウト時にエラーが表示されること"""
        from yadon_agents.cli import cmd_say

        sock_file = tmp_path / "test.sock"
        sock_file.touch()

        mock_sock = MagicMock()
        mock_sock.connect.side_effect = socket.timeout("timed out")

        with patch("yadon_agents.cli.pet_socket_path", return_value=str(sock_file)):
            with patch("yadon_agents.cli.socket.socket", return_value=mock_sock):
                with pytest.raises(SystemExit) as exc_info:
                    cmd_say(1, "テストメッセージ")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "タイムアウト" in captured.out


class TestCmdInternalSend:
    """cmd_internal_send() のテスト"""

    def test_cmd_internal_send_socket_not_exists(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """ソケットが存在しない場合にJSONエラーが出力されること"""
        from yadon_agents.cli import cmd_internal_send

        with patch("yadon_agents.cli.agent_socket_path", return_value=str(tmp_path / "nonexistent.sock")):
            cmd_internal_send("テストタスク")

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] is False
        assert "ソケットが見つかりません" in result["message"]

    def test_cmd_internal_send_success(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """正常送信時にJSON形式で成功が出力されること"""
        from yadon_agents.cli import cmd_internal_send

        sock_file = tmp_path / "test.sock"
        sock_file.touch()

        mock_response = {
            "type": "result",
            "status": "success",
            "payload": {"output": "完了"},
        }

        with patch("yadon_agents.cli.agent_socket_path", return_value=str(sock_file)):
            with patch("yadon_agents.cli.send_message", return_value=mock_response):
                cmd_internal_send("テストタスク")

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] is True
        assert result["data"]["status"] == "success"

    def test_cmd_internal_send_timeout(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """タイムアウト時にJSON形式でエラーが出力されること"""
        from yadon_agents.cli import cmd_internal_send

        sock_file = tmp_path / "test.sock"
        sock_file.touch()

        with patch("yadon_agents.cli.agent_socket_path", return_value=str(sock_file)):
            with patch("yadon_agents.cli.send_message", side_effect=socket.timeout("timed out")):
                cmd_internal_send("テストタスク")

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] is False
        assert "タイムアウト" in result["message"]


class TestCmdInternalStatus:
    """cmd_internal_status() のテスト"""

    def test_cmd_internal_status_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        """正常時にJSON形式でステータスが出力されること"""
        from yadon_agents.cli import cmd_internal_status

        mock_response = {
            "type": "status_response",
            "state": "idle",
            "workers": {"yadon-1": "idle"},
        }

        with patch("yadon_agents.cli.send_message", return_value=mock_response):
            cmd_internal_status()

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] is True
        assert result["data"]["state"] == "idle"

    def test_cmd_internal_status_timeout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """タイムアウト時にJSON形式でエラーが出力されること"""
        from yadon_agents.cli import cmd_internal_status

        with patch("yadon_agents.cli.send_message", side_effect=socket.timeout("timed out")):
            cmd_internal_status()

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] is False
        assert "タイムアウト" in result["message"]


class TestCmdInternalSay:
    """cmd_internal_say() のテスト"""

    def test_cmd_internal_say_socket_not_exists(self, tmp_path: Path) -> None:
        """ソケットが存在しない場合に静かに終了すること"""
        from yadon_agents.cli import cmd_internal_say

        with patch("yadon_agents.cli.pet_socket_path", return_value=str(tmp_path / "nonexistent.sock")):
            # エラーにならないこと
            cmd_internal_say(1, "テストメッセージ")

    def test_cmd_internal_say_connection_error_silent(self, tmp_path: Path) -> None:
        """接続エラー時に静かに終了すること"""
        from yadon_agents.cli import cmd_internal_say

        sock_file = tmp_path / "test.sock"
        sock_file.touch()

        mock_sock = MagicMock()
        mock_sock.connect.side_effect = ConnectionRefusedError("connection refused")

        with patch("yadon_agents.cli.pet_socket_path", return_value=str(sock_file)):
            with patch("yadon_agents.cli.socket.socket", return_value=mock_sock):
                # エラーにならないこと
                cmd_internal_say(1, "テストメッセージ")


class TestCmdRestart:
    """cmd_restart() のテスト"""

    def test_cmd_restart_calls_stop_then_start(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """cmd_restart が cmd_stop と cmd_start を順に呼び出すこと"""
        from yadon_agents.cli import cmd_restart

        call_order = []

        def mock_stop():
            call_order.append("stop")

        def mock_start(work_dir, multi_llm=False):
            call_order.append("start")

        with patch("yadon_agents.cli.cmd_stop", side_effect=mock_stop):
            with patch("yadon_agents.cli.cmd_start", side_effect=mock_start):
                cmd_restart(str(tmp_path), multi_llm=True)

        assert call_order == ["stop", "start"]
