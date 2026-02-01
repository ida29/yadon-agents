"""YadonWorker のテスト"""

from __future__ import annotations

from typing import Any

import pytest

from yadon_agents.agent.worker import YadonWorker
from yadon_agents.domain.ports.claude_port import ClaudeRunnerPort
from yadon_agents.themes import _reset_cache


class FakeClaudeRunner(ClaudeRunnerPort):
    """テスト用のClaudeRunner実装。戻り値を制御可能。"""

    def __init__(self, output: str = "", returncode: int = 0):
        self.output = output
        self.returncode = returncode
        self.last_run_kwargs: dict[str, Any] = {}

    def run(
        self,
        prompt: str,
        model: str,
        cwd: str,
        timeout: int = 600,
        output_format: str = "text",
    ) -> tuple[str, int]:
        """引数を記録してから、固定の戻り値を返す。"""
        self.last_run_kwargs = {
            "prompt": prompt,
            "model": model,
            "cwd": cwd,
            "timeout": timeout,
            "output_format": output_format,
        }
        return (self.output, self.returncode)


class TestYadonWorker:
    """YadonWorker.handle_task() のテスト"""

    def setup_method(self):
        """各テスト前にテーマキャッシュをリセットする。"""
        _reset_cache()

    def test_handle_task_success(self, sock_dir):
        """正常実行(returncode=0)で status=success となること"""
        fake_runner = FakeClaudeRunner(output="作業完了やぁん", returncode=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-001",
            "from": "test",
            "payload": {
                "instruction": "テストタスク",
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "success"
        assert result["payload"]["output"] == "作業完了やぁん"
        assert result["payload"]["summary"] == "作業完了やぁん"
        assert result["type"] == "result"
        assert result["from"] == "yadon-1"

    def test_handle_task_error(self, sock_dir):
        """失敗(returncode=1)で status=error となること"""
        fake_runner = FakeClaudeRunner(output="エラーが発生しました", returncode=1)
        worker = YadonWorker(number=2, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-002",
            "from": "test",
            "payload": {
                "instruction": "エラーが起きるタスク",
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "error"
        assert result["payload"]["output"] == "エラーが発生しました"
        assert result["payload"]["summary"] == "エラーが発生しました"

    def test_handle_task_empty_output(self, sock_dir):
        """出力が空の場合、summary に '(出力なし)' が設定されること"""
        fake_runner = FakeClaudeRunner(output="", returncode=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-003",
            "from": "test",
            "payload": {
                "instruction": "出力がないタスク",
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "success"
        assert result["payload"]["output"] == ""
        assert result["payload"]["summary"] == "(出力なし)"

    def test_handle_task_whitespace_only_output(self, sock_dir):
        """出力が空白のみの場合、summary に '(出力なし)' が設定されること"""
        fake_runner = FakeClaudeRunner(output="   \n\t  ", returncode=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-004",
            "from": "test",
            "payload": {
                "instruction": "空白のみのタスク",
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "success"
        assert result["payload"]["summary"] == "(出力なし)"

    def test_prompt_template_formatting(self, sock_dir):
        """テーマの worker_prompt_template が正しくフォーマットされること"""
        fake_runner = FakeClaudeRunner(output="OK", returncode=0)
        worker = YadonWorker(number=3, project_dir=sock_dir, claude_runner=fake_runner)

        worker.handle_task({
            "id": "task-005",
            "from": "test",
            "payload": {
                "instruction": "テンプレートテスト",
                "project_dir": sock_dir,
            },
        })

        # プロンプトが記録されている
        assert "prompt" in fake_runner.last_run_kwargs
        prompt = fake_runner.last_run_kwargs["prompt"]

        # 指示が含まれていることを確認
        assert "テンプレートテスト" in prompt

        # ワーカー番号が含まれていることを確認
        assert "3" in prompt or "number" in prompt.lower()

        # モデルが haiku であることを確認
        assert fake_runner.last_run_kwargs["model"] == "haiku"

        # cwd が指定されたパスであること
        assert fake_runner.last_run_kwargs["cwd"] == sock_dir

    def test_claude_runner_called_with_correct_args(self, sock_dir):
        """claude_runner.run() が正しい引数で呼ばれること"""
        fake_runner = FakeClaudeRunner(output="result", returncode=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        custom_project_dir = "/custom/path"
        worker.handle_task({
            "id": "task-006",
            "from": "test",
            "payload": {
                "instruction": "実行テスト",
                "project_dir": custom_project_dir,
            },
        })

        # モデルが haiku
        assert fake_runner.last_run_kwargs["model"] == "haiku"
        # cwd がペイロードで指定されたパス
        assert fake_runner.last_run_kwargs["cwd"] == custom_project_dir

    def test_handle_task_preserves_task_id(self, sock_dir):
        """タスクIDが結果に反映されること"""
        fake_runner = FakeClaudeRunner(output="done", returncode=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "my-unique-task-id-12345",
            "from": "test",
            "payload": {
                "instruction": "test",
                "project_dir": sock_dir,
            },
        })

        assert result["id"] == "my-unique-task-id-12345"
