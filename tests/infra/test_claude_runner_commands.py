"""SubprocessClaudeRunner のコマンド構築テスト

build_interactive_command() の全バックエンド、
run() の全エラーパス（タイムアウト、非ゼロ終了）のテスト。
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yadon_agents.infra.claude_runner import SubprocessClaudeRunner, run_claude


class TestBuildInteractiveCommand:
    """build_interactive_command() のテスト"""

    def test_build_command_claude_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Claude バックエンドで正しいコマンドが構築されること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        runner = SubprocessClaudeRunner()
        cmd = runner.build_interactive_command(model_tier="coordinator")

        assert cmd[0] == "claude"
        assert "--model" in cmd
        assert "opus" in cmd

    def test_build_command_gemini_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Gemini バックエンドで正しいコマンドが構築されること"""
        monkeypatch.setenv("LLM_BACKEND", "gemini")

        runner = SubprocessClaudeRunner()
        cmd = runner.build_interactive_command(model_tier="coordinator")

        assert cmd[0] == "gemini"
        assert "--model" in cmd
        assert "gemini-3.0-pro" in cmd

    def test_build_command_copilot_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Copilot バックエンドで正しいコマンドが構築されること"""
        monkeypatch.setenv("LLM_BACKEND", "copilot")

        runner = SubprocessClaudeRunner()
        cmd = runner.build_interactive_command(model_tier="coordinator")

        assert cmd[0] == "copilot"
        assert "--model" in cmd
        assert "gpt-5.2" in cmd

    def test_build_command_opencode_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OpenCode バックエンドで正しいコマンドが構築されること"""
        monkeypatch.setenv("LLM_BACKEND", "opencode")

        runner = SubprocessClaudeRunner()
        cmd = runner.build_interactive_command(model_tier="coordinator")

        assert cmd[0] == "opencode"
        assert "--model" in cmd
        assert "kimi/kimi-k2.5" in cmd

    def test_build_command_claude_opus_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Claude-Opus バックエンドで全 tier が opus になること"""
        monkeypatch.setenv("LLM_BACKEND", "claude-opus")

        runner = SubprocessClaudeRunner()

        for tier in ["coordinator", "manager", "worker"]:
            cmd = runner.build_interactive_command(model_tier=tier)
            assert cmd[0] == "claude"
            assert "opus" in cmd

    def test_build_command_with_system_prompt(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """システムプロンプトが正しく追加されること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        system_file = tmp_path / "system.txt"
        system_file.write_text("システムプロンプト")

        runner = SubprocessClaudeRunner()
        cmd = runner.build_interactive_command(
            model_tier="coordinator",
            system_prompt_path=str(system_file),
        )

        assert "--system" in cmd
        assert str(system_file) in cmd

    def test_build_command_system_prompt_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """システムプロンプトファイルが存在しない場合にエラー"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        runner = SubprocessClaudeRunner()

        with pytest.raises(FileNotFoundError):
            runner.build_interactive_command(
                model_tier="coordinator",
                system_prompt_path="/nonexistent/path.txt",
            )

    def test_build_command_all_tiers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """全ての tier でコマンドが構築できること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        runner = SubprocessClaudeRunner()

        for tier in ["coordinator", "manager", "worker"]:
            cmd = runner.build_interactive_command(model_tier=tier)
            assert len(cmd) >= 3
            assert "--model" in cmd


class TestRunWithBatchPromptStyles:
    """run() のバッチプロンプトスタイルテスト"""

    def test_run_stdin_style(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """stdin スタイル（claude, copilot）で -p フラグが使用されること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        runner = SubprocessClaudeRunner()

        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner.run(prompt="test", model_tier="worker", cwd="/tmp")

        call_args = mock_run.call_args[0][0]
        assert "-p" in call_args
        # input パラメータにプロンプトが渡される
        assert mock_run.call_args[1]["input"] == "test"

    def test_run_arg_style(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """arg スタイル（gemini）で --prompt フラグが使用されること"""
        monkeypatch.setenv("LLM_BACKEND", "gemini")

        runner = SubprocessClaudeRunner()

        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner.run(prompt="test prompt", model_tier="worker", cwd="/tmp")

        call_args = mock_run.call_args[0][0]
        assert "--prompt" in call_args
        assert "test prompt" in call_args
        # input は None
        assert mock_run.call_args[1]["input"] is None

    def test_run_subcommand_stdin_style(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """subcommand_stdin スタイル（opencode）でサブコマンドが追加されること"""
        monkeypatch.setenv("LLM_BACKEND", "opencode")

        runner = SubprocessClaudeRunner()

        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner.run(prompt="test", model_tier="worker", cwd="/tmp")

        call_args = mock_run.call_args[0][0]
        assert "run" in call_args
        assert "-q" in call_args
        # input パラメータにプロンプトが渡される
        assert mock_run.call_args[1]["input"] == "test"


class TestRunErrorHandling:
    """run() のエラーハンドリングテスト"""

    def test_run_timeout_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """タイムアウト時に適切なメッセージが返されること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        runner = SubprocessClaudeRunner()

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 120)):
            output, returncode = runner.run(
                prompt="test",
                model_tier="worker",
                cwd="/tmp",
                timeout=120,
            )

        assert "タイムアウト" in output
        assert "2分" in output  # 120秒 = 2分
        assert returncode == 1

    def test_run_timeout_short_duration(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """短いタイムアウトでも正しいメッセージが返されること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        runner = SubprocessClaudeRunner()

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            output, returncode = runner.run(
                prompt="test",
                model_tier="worker",
                cwd="/tmp",
                timeout=30,
            )

        assert "タイムアウト" in output
        assert "0分" in output  # 30秒 = 0分
        assert returncode == 1

    def test_run_general_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """一般的な例外時に適切なメッセージが返されること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        runner = SubprocessClaudeRunner()

        with patch("subprocess.run", side_effect=RuntimeError("コマンドが見つかりません")):
            output, returncode = runner.run(
                prompt="test",
                model_tier="worker",
                cwd="/tmp",
            )

        assert "実行エラー" in output
        assert returncode == 1

    def test_run_nonzero_returncode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """非ゼロリターンコードが正しく返されること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        runner = SubprocessClaudeRunner()

        mock_result = MagicMock()
        mock_result.stdout = "error output"
        mock_result.stderr = "error message"
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            output, returncode = runner.run(
                prompt="test",
                model_tier="worker",
                cwd="/tmp",
            )

        assert returncode == 1
        assert "error output" in output
        assert "error message" in output


class TestRunWithWorkerNumber:
    """ワーカー番号指定時の run() テスト"""

    def test_run_with_worker_specific_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ワーカー固有のバックエンド設定が使用されること"""
        monkeypatch.setenv("YADON_1_BACKEND", "gemini")
        monkeypatch.setenv("LLM_BACKEND", "claude")  # グローバルは claude

        runner = SubprocessClaudeRunner(worker_number=1)

        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner.run(prompt="test", model_tier="worker", cwd="/tmp")

        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "gemini"  # ワーカー1は gemini を使用

    def test_run_with_worker_fallback_to_global(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ワーカー固有設定がない場合、グローバル設定にフォールバックすること"""
        monkeypatch.delenv("YADON_2_BACKEND", raising=False)
        monkeypatch.setenv("LLM_BACKEND", "copilot")

        runner = SubprocessClaudeRunner(worker_number=2)

        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner.run(prompt="test", model_tier="worker", cwd="/tmp")

        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "copilot"  # グローバルの copilot にフォールバック


class TestRunBackendSpecificFlags:
    """バックエンド固有フラグのテスト"""

    def test_run_claude_dangerously_skip_permissions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Claude で --dangerously-skip-permissions が追加されること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        runner = SubprocessClaudeRunner()

        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner.run(prompt="test", model_tier="worker", cwd="/tmp")

        call_args = mock_run.call_args[0][0]
        assert "--dangerously-skip-permissions" in call_args

    def test_run_gemini_yolo_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Gemini で --yolo フラグが追加されること"""
        monkeypatch.setenv("LLM_BACKEND", "gemini")

        runner = SubprocessClaudeRunner()

        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner.run(prompt="test", model_tier="worker", cwd="/tmp")

        call_args = mock_run.call_args[0][0]
        assert "--yolo" in call_args


class TestRunWithOutputFormat:
    """output_format パラメータのテスト"""

    def test_run_with_output_format_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """output_format=json で --output-format フラグが追加されること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

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
                output_format="json",
            )

        call_args = mock_run.call_args[0][0]
        assert "--output-format" in call_args
        assert "json" in call_args

    def test_run_without_output_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """output_format=None で --output-format フラグが追加されないこと"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        runner = SubprocessClaudeRunner()

        mock_result = MagicMock()
        mock_result.stdout = "text output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner.run(
                prompt="test",
                model_tier="worker",
                cwd="/tmp",
                output_format=None,
            )

        call_args = mock_run.call_args[0][0]
        assert "--output-format" not in call_args


class TestLegacyRunClaude:
    """後方互換の run_claude() 関数テスト"""

    def test_run_claude_legacy_model_mapping(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """レガシーモデル名が tier に変換されること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            # haiku -> worker
            run_claude(prompt="test", model="haiku", cwd="/tmp")
            call_args = mock_run.call_args[0][0]
            assert "haiku" in call_args

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            # sonnet -> manager
            run_claude(prompt="test", model="sonnet", cwd="/tmp")
            call_args = mock_run.call_args[0][0]
            assert "sonnet" in call_args

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            # opus -> coordinator
            run_claude(prompt="test", model="opus", cwd="/tmp")
            call_args = mock_run.call_args[0][0]
            assert "opus" in call_args

    def test_run_claude_unknown_model_defaults_to_worker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """不明なモデル名は worker tier にフォールバックされること"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_claude(prompt="test", model="unknown-model", cwd="/tmp")
            call_args = mock_run.call_args[0][0]
            # worker tier のモデル（haiku）が使用される
            assert "haiku" in call_args
