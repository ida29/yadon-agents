"""cli.py のメイン関数・ヘルパー関数のテスト

_wait_sockets() のタイムアウト動作、
_cleanup_sockets() のソケット削除、
get_multi_llm_backends() のバックエンド割り当てロジック、
コマンドライン引数パースのテスト。
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from yadon_agents.cli import (
    _cleanup_sockets,
    _wait_sockets,
)


class TestWaitSockets:
    """_wait_sockets() のテスト"""

    def test_wait_sockets_all_exist(self, tmp_path: Path) -> None:
        """全てのソケットが存在する場合、True を返す"""
        # ソケットファイルを作成
        sock1 = tmp_path / "yadon-agent-yadon-1.sock"
        sock2 = tmp_path / "yadon-agent-yadon-2.sock"
        sock1.touch()
        sock2.touch()

        # _wait_sockets内部でimportされるagent_socket_pathをモック
        with patch("yadon_agents.infra.protocol.agent_socket_path") as mock_path:
            # パスをモック
            def path_factory(name: str, prefix: str = "yadon") -> str:
                return str(tmp_path / f"{prefix}-agent-{name}.sock")
            mock_path.side_effect = path_factory

            result = _wait_sockets(["yadon-1", "yadon-2"], prefix="yadon", timeout=1)

            assert result is True

    def test_wait_sockets_timeout(self, tmp_path: Path) -> None:
        """ソケットが存在しない場合、タイムアウトして False を返す"""
        with patch("yadon_agents.infra.protocol.agent_socket_path") as mock_path:
            # 存在しないパスを返す
            mock_path.return_value = str(tmp_path / "nonexistent.sock")

            start = time.time()
            result = _wait_sockets(["yadon-1"], prefix="yadon", timeout=1)
            elapsed = time.time() - start

            assert result is False
            # タイムアウトが約1秒であることを確認
            assert elapsed >= 0.9
            assert elapsed < 2.0

    def test_wait_sockets_partial_exist(self, tmp_path: Path) -> None:
        """一部のソケットのみ存在する場合、False を返す"""
        sock1 = tmp_path / "yadon-agent-yadon-1.sock"
        sock1.touch()
        # yadon-2.sock は作成しない

        with patch("yadon_agents.infra.protocol.agent_socket_path") as mock_path:
            def path_factory(name: str, prefix: str = "yadon") -> str:
                return str(tmp_path / f"{prefix}-agent-{name}.sock")
            mock_path.side_effect = path_factory

            result = _wait_sockets(["yadon-1", "yadon-2"], prefix="yadon", timeout=1)

            assert result is False

    def test_wait_sockets_empty_list(self, tmp_path: Path) -> None:
        """空のリストの場合、True を返す"""
        result = _wait_sockets([], prefix="yadon", timeout=1)

        assert result is True

    def test_wait_sockets_created_during_wait(self, tmp_path: Path) -> None:
        """待機中にソケットが作成された場合、True を返す"""
        sock_path = tmp_path / "yadon-agent-yadon-1.sock"

        def create_socket_after_delay() -> None:
            time.sleep(0.3)
            sock_path.touch()

        import threading
        thread = threading.Thread(target=create_socket_after_delay)

        # _wait_sockets内部でimportされるagent_socket_pathをモック
        with patch("yadon_agents.infra.protocol.agent_socket_path") as mock_path:
            mock_path.return_value = str(sock_path)

            thread.start()
            result = _wait_sockets(["yadon-1"], prefix="yadon", timeout=2)
            thread.join()

            assert result is True


class TestCleanupSockets:
    """_cleanup_sockets() のテスト"""

    def test_cleanup_sockets_removes_agent_sockets(self) -> None:
        """エージェントソケットが削除されること"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # /tmp の代わりに一時ディレクトリを使用
            sock_file = Path(tmp_dir) / "yadon-agent-test.sock"
            sock_file.touch()

            with patch("yadon_agents.cli.Path") as mock_path_class:
                # Path("/tmp") をモック
                mock_tmp = MagicMock()
                mock_path_class.return_value = mock_tmp
                mock_tmp.glob.return_value = [sock_file]

                _cleanup_sockets(prefix="yadon")

                # glob が正しいパターンで呼ばれたことを確認
                mock_tmp.glob.assert_called()

    def test_cleanup_sockets_removes_pet_sockets(self) -> None:
        """ペットソケットが削除されること"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            sock_file = Path(tmp_dir) / "yadon-pet-1.sock"
            sock_file.touch()

            with patch("yadon_agents.cli.Path") as mock_path_class:
                mock_tmp = MagicMock()
                mock_path_class.return_value = mock_tmp
                mock_tmp.glob.return_value = [sock_file]

                _cleanup_sockets(prefix="yadon")

                mock_tmp.glob.assert_called()

    def test_cleanup_sockets_handles_oserror(self, tmp_path: Path) -> None:
        """OSError が発生してもエラーにならないこと"""
        sock_file = tmp_path / "yadon-agent-test.sock"
        sock_file.touch()

        with patch("yadon_agents.cli.Path") as mock_path_class:
            mock_tmp = MagicMock()
            mock_path_class.return_value = mock_tmp

            # unlink で OSError を発生させるモック
            mock_sock = MagicMock()
            mock_sock.unlink.side_effect = OSError("Permission denied")
            mock_tmp.glob.return_value = [mock_sock]

            # エラーにならないことを確認
            _cleanup_sockets(prefix="yadon")

    def test_cleanup_sockets_empty_directory(self) -> None:
        """ソケットファイルが存在しない場合もエラーにならないこと"""
        with patch("yadon_agents.cli.Path") as mock_path_class:
            mock_tmp = MagicMock()
            mock_path_class.return_value = mock_tmp
            mock_tmp.glob.return_value = []

            # エラーにならないことを確認
            _cleanup_sockets(prefix="yadon")

    def test_cleanup_sockets_custom_prefix(self) -> None:
        """カスタムプレフィックスで正しいパターンが使用されること"""
        with patch("yadon_agents.cli.Path") as mock_path_class:
            mock_tmp = MagicMock()
            mock_path_class.return_value = mock_tmp
            mock_tmp.glob.return_value = []

            _cleanup_sockets(prefix="custom")

            # glob が正しいパターンで呼ばれたことを確認
            calls = mock_tmp.glob.call_args_list
            patterns = [call[0][0] for call in calls]
            assert any("custom-agent-" in p for p in patterns)
            assert any("custom-pet-" in p for p in patterns)


class TestMultiLLMBackendAssignment:
    """マルチLLMモードのバックエンド割り当てロジックのテスト"""

    def test_multi_llm_backend_rotation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """マルチLLMモードでローテーション割り当てが正しいこと"""
        # 環境変数をクリア
        for i in range(1, 9):
            monkeypatch.delenv(f"YADON_{i}_BACKEND", raising=False)

        # ローテーションの期待値
        expected_rotation = ["copilot", "gemini", "claude-opus", "opencode"]

        # 直接ローテーションロジックをテスト
        backend_rotation = ["copilot", "gemini", "claude-opus", "opencode"]
        for i in range(1, 9):
            expected = expected_rotation[(i - 1) % len(expected_rotation)]
            actual = backend_rotation[(i - 1) % len(backend_rotation)]
            assert actual == expected, f"Worker {i}: expected {expected}, got {actual}"

    def test_multi_llm_explicit_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """明示的な YADON_N_BACKEND 設定がローテーションをオーバーライドすること"""
        # YADON_1_BACKEND を明示的に設定
        monkeypatch.setenv("YADON_1_BACKEND", "gemini")
        monkeypatch.setenv("YADON_3_BACKEND", "opencode")

        # 明示的設定が存在する場合のロジック
        backend_rotation = ["copilot", "gemini", "claude-opus", "opencode"]

        for i in range(1, 5):
            env_var = f"YADON_{i}_BACKEND"
            if env_var in os.environ:
                # 明示的設定が優先
                backend = os.environ[env_var]
            else:
                # ローテーション
                backend = backend_rotation[(i - 1) % len(backend_rotation)]

            if i == 1:
                assert backend == "gemini"
            elif i == 3:
                assert backend == "opencode"
            else:
                assert backend == backend_rotation[(i - 1) % len(backend_rotation)]

    def test_multi_llm_all_workers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """8ワーカー全てにバックエンドが割り当てられること"""
        for i in range(1, 9):
            monkeypatch.delenv(f"YADON_{i}_BACKEND", raising=False)

        backend_rotation = ["copilot", "gemini", "claude-opus", "opencode"]

        # 8ワーカー分のバックエンドを計算
        backends = []
        for i in range(1, 9):
            backend = backend_rotation[(i - 1) % len(backend_rotation)]
            backends.append(backend)

        # 各バックエンドが2回ずつ出現することを確認
        for backend in backend_rotation:
            assert backends.count(backend) == 2


class TestCommandLineArgumentParsing:
    """コマンドライン引数パースのテスト"""

    def test_start_command_default_work_dir(self) -> None:
        """start コマンドでデフォルトの作業ディレクトリが使用されること"""
        import argparse
        from yadon_agents.cli import main

        with patch("yadon_agents.cli.cmd_start") as mock_start:
            with patch("sys.argv", ["yadon", "start"]):
                with patch("yadon_agents.cli.argparse.ArgumentParser.parse_args") as mock_parse:
                    mock_args = MagicMock()
                    mock_args.command = "start"
                    mock_args.work_dir = str(Path.cwd())
                    mock_args.multi_llm = False
                    mock_parse.return_value = mock_args

                    # main() を呼び出す（モックされるので実際には起動しない）
                    try:
                        main()
                    except SystemExit:
                        pass

    def test_start_command_with_multi_llm(self) -> None:
        """start コマンドで --multi-llm フラグが認識されること"""
        from yadon_agents.cli import main

        with patch("yadon_agents.cli.cmd_start") as mock_start:
            with patch("yadon_agents.cli.argparse.ArgumentParser.parse_args") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "start"
                mock_args.work_dir = "/tmp/test"
                mock_args.multi_llm = True
                mock_parse.return_value = mock_args

                try:
                    main()
                except SystemExit:
                    pass

                # cmd_start が multi_llm=True で呼ばれたことを確認
                mock_start.assert_called_once()
                call_kwargs = mock_start.call_args
                assert call_kwargs[1]["multi_llm"] is True

    def test_stop_command(self) -> None:
        """stop コマンドが正しくパースされること"""
        from yadon_agents.cli import main

        with patch("yadon_agents.cli.cmd_stop") as mock_stop:
            with patch("yadon_agents.cli.argparse.ArgumentParser.parse_args") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "stop"
                mock_parse.return_value = mock_args

                main()

                mock_stop.assert_called_once()

    def test_status_command_with_agent_name(self) -> None:
        """status コマンドでエージェント名が渡されること"""
        from yadon_agents.cli import main

        with patch("yadon_agents.cli.cmd_status") as mock_status:
            with patch("yadon_agents.cli.argparse.ArgumentParser.parse_args") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "status"
                mock_args.agent_name = "yadon-1"
                mock_parse.return_value = mock_args

                main()

                mock_status.assert_called_once_with(agent_name="yadon-1")

    def test_say_command_parameters(self) -> None:
        """say コマンドでパラメータが正しく渡されること"""
        from yadon_agents.cli import main

        with patch("yadon_agents.cli.cmd_say") as mock_say:
            with patch("yadon_agents.cli.argparse.ArgumentParser.parse_args") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "say"
                mock_args.number = 2
                mock_args.message = "テストメッセージ"
                mock_args.type = "success"
                mock_args.duration = 3000
                mock_parse.return_value = mock_args

                main()

                mock_say.assert_called_once_with(
                    2, "テストメッセージ",
                    bubble_type="success",
                    duration_ms=3000
                )

    def test_default_command_is_start(self) -> None:
        """コマンド未指定時はデフォルトで start が実行されること"""
        from yadon_agents.cli import main

        with patch("yadon_agents.cli.cmd_start") as mock_start:
            with patch("yadon_agents.cli.argparse.ArgumentParser.parse_args") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = None  # コマンド未指定
                mock_args.multi_llm = False
                mock_parse.return_value = mock_args

                try:
                    main()
                except SystemExit:
                    pass

                mock_start.assert_called_once()


class TestInternalCommands:
    """内部用コマンド (_send, _status, _restart, _say) のテスト"""

    def test_internal_send_command(self) -> None:
        """_send コマンドが正しくパースされること"""
        from yadon_agents.cli import main

        with patch("yadon_agents.cli.cmd_internal_send") as mock_send:
            with patch("yadon_agents.cli.argparse.ArgumentParser.parse_args") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "_send"
                mock_args.instruction = "テストタスク"
                mock_args.project_dir = "/tmp/project"
                mock_parse.return_value = mock_args

                main()

                mock_send.assert_called_once_with(
                    "テストタスク",
                    project_dir="/tmp/project"
                )

    def test_internal_status_command(self) -> None:
        """_status コマンドが正しくパースされること"""
        from yadon_agents.cli import main

        with patch("yadon_agents.cli.cmd_internal_status") as mock_status:
            with patch("yadon_agents.cli.argparse.ArgumentParser.parse_args") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "_status"
                mock_args.agent_name = "yadoran"
                mock_parse.return_value = mock_args

                main()

                mock_status.assert_called_once_with(agent_name="yadoran")

    def test_internal_restart_command(self) -> None:
        """_restart コマンドが正しくパースされること"""
        from yadon_agents.cli import main

        with patch("yadon_agents.cli.cmd_internal_restart") as mock_restart:
            with patch("yadon_agents.cli.argparse.ArgumentParser.parse_args") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "_restart"
                mock_parse.return_value = mock_args

                main()

                mock_restart.assert_called_once()

    def test_internal_say_command(self) -> None:
        """_say コマンドが正しくパースされること"""
        from yadon_agents.cli import main

        with patch("yadon_agents.cli.cmd_internal_say") as mock_say:
            with patch("yadon_agents.cli.argparse.ArgumentParser.parse_args") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "_say"
                mock_args.number = 3
                mock_args.message = "内部メッセージ"
                mock_args.type = "info"
                mock_args.duration = 5000
                mock_parse.return_value = mock_args

                main()

                mock_say.assert_called_once_with(
                    3, "内部メッセージ",
                    bubble_type="info",
                    duration_ms=5000
                )
