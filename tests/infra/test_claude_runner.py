"""SubprocessClaudeRunner のテスト"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from yadon_agents.infra.claude_runner import SubprocessClaudeRunner


class TestSubprocessClaudeRunner:
    """SubprocessClaudeRunner の各シナリオをテスト"""

    def test_run_success(self):
        """正常実行で stdout + stderr を結合して返す"""
        runner = SubprocessClaudeRunner()

        mock_result = MagicMock()
        mock_result.stdout = "output line 1\n"
        mock_result.stderr = "error line 1\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            output, returncode = runner.run(
                prompt="test prompt",
                model_tier="worker",
                cwd="/tmp",
                timeout=30,
            )

            assert output == "output line 1\nerror line 1\n"
            assert returncode == 0
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["capture_output"] is True
            assert call_kwargs["text"] is True
            assert call_kwargs["timeout"] == 30
            assert call_kwargs["cwd"] == "/tmp"

    def test_run_timeout(self):
        """TimeoutExpired でタイムアウトメッセージを返す"""
        runner = SubprocessClaudeRunner()

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
            output, returncode = runner.run(
                prompt="test prompt",
                model_tier="manager",
                cwd="/tmp",
                timeout=60,
            )

            assert "タイムアウト" in output
            assert "1分" in output
            assert returncode == 1

    def test_run_exception(self):
        """その他の例外でエラーメッセージを返す"""
        runner = SubprocessClaudeRunner()

        test_error = RuntimeError("subprocess not found")

        with patch("subprocess.run", side_effect=test_error):
            output, returncode = runner.run(
                prompt="test prompt",
                model_tier="coordinator",
                cwd="/tmp",
                timeout=30,
            )

            assert "実行エラー" in output
            assert returncode == 1

    def test_run_with_output_format(self):
        """output_format パラメータが正しく渡される"""
        runner = SubprocessClaudeRunner()

        mock_result = MagicMock()
        mock_result.stdout = '{"key": "value"}'
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner.run(
                prompt="test",
                model_tier="worker",
                cwd="/tmp",
                timeout=30,
                output_format="json",
            )

            call_args = mock_run.call_args[0][0]
            assert "--output-format" in call_args
            assert "json" in call_args
