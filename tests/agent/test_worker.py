"""YadonWorker のテスト"""

from __future__ import annotations

from typing import Any

import pytest

from yadon_agents.agent.worker import YadonWorker
from yadon_agents.domain.ports.llm_port import LLMRunnerPort
from yadon_agents.themes import _reset_cache


class FakeClaudeRunner(LLMRunnerPort):
    """テスト用のLLMRunner実装。戻り値を制御可能。"""

    def __init__(self, output: str = "", returncode: int = 0):
        self.output = output
        self.returncode = returncode
        self.last_run_kwargs: dict[str, Any] = {}

    def run(
        self,
        prompt: str,
        model_tier: str,
        cwd: str | None = None,
        timeout: float = 600,
        output_format: str | None = None,
    ) -> tuple[str, int]:
        """引数を記録してから、固定の戻り値を返す。"""
        self.last_run_kwargs = {
            "prompt": prompt,
            "model_tier": model_tier,
            "cwd": cwd,
            "timeout": timeout,
            "output_format": output_format,
        }
        return (self.output, self.returncode)

    def build_interactive_command(
        self,
        model_tier: str,
        system_prompt_path: str | None = None,
    ) -> list[str]:
        """テスト用の実装。実際には使用されない。"""
        return ["claude", "--model", model_tier]


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

        # モデルティアが worker であることを確認
        assert fake_runner.last_run_kwargs["model_tier"] == "worker"

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

        # モデルティアが worker
        assert fake_runner.last_run_kwargs["model_tier"] == "worker"
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


class TestEdgeCases:
    """エッジケースのテスト"""

    def setup_method(self):
        """各テスト前にテーマキャッシュをリセットする。"""
        _reset_cache()

    def test_handle_task_large_output(self, sock_dir):
        """巨大な出力を持つタスクが正しく処理されること"""
        # 1MB程度の大きな出力
        large_output = "長い出力 " * 100000
        fake_runner = FakeClaudeRunner(output=large_output, returncode=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-large",
            "from": "test",
            "payload": {
                "instruction": "大きな出力を生成",
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "success"
        assert len(result["payload"]["output"]) > 100000

    def test_handle_task_unicode_output(self, sock_dir):
        """Unicode文字を含む出力が正しく処理されること"""
        unicode_output = "日本語出力 🎉 絵文字あり émojis français"
        fake_runner = FakeClaudeRunner(output=unicode_output, returncode=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-unicode",
            "from": "test",
            "payload": {
                "instruction": "Unicode出力テスト",
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "success"
        assert "日本語出力" in result["payload"]["output"]
        assert "🎉" in result["payload"]["output"]

    def test_handle_task_multiline_output(self, sock_dir):
        """複数行の出力が正しく処理されること"""
        multiline_output = "行1\n行2\n行3\n\n行5(空行後)"
        fake_runner = FakeClaudeRunner(output=multiline_output, returncode=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-multiline",
            "from": "test",
            "payload": {
                "instruction": "複数行出力",
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "success"
        assert "行1" in result["payload"]["output"]
        assert "行5(空行後)" in result["payload"]["output"]

    def test_handle_task_special_chars_in_instruction(self, sock_dir):
        """特殊文字を含む指示が正しく処理されること"""
        fake_runner = FakeClaudeRunner(output="OK", returncode=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        special_instruction = "パス /path/to/file.txt を処理 && 'シングルクォート' \"ダブルクォート\""
        worker.handle_task({
            "id": "task-special",
            "from": "test",
            "payload": {
                "instruction": special_instruction,
                "project_dir": sock_dir,
            },
        })

        # プロンプトに特殊文字が含まれていることを確認
        prompt = fake_runner.last_run_kwargs["prompt"]
        assert "/path/to/file.txt" in prompt

    def test_handle_task_max_worker_number(self, sock_dir):
        """最大ワーカー番号(8)でも正しく動作すること"""
        fake_runner = FakeClaudeRunner(output="done", returncode=0)
        worker = YadonWorker(number=8, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-max",
            "from": "test",
            "payload": {
                "instruction": "最大ワーカーテスト",
                "project_dir": sock_dir,
            },
        })

        assert result["from"] == "yadon-8"
        assert result["status"] == "success"

    def test_handle_task_missing_payload_fields(self, sock_dir):
        """payloadに必須フィールドがない場合の動作"""
        fake_runner = FakeClaudeRunner(output="done", returncode=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        # project_dirがpayloadにない場合、コンストラクタのデフォルトが使用される
        result = worker.handle_task({
            "id": "task-missing",
            "from": "test",
            "payload": {
                "instruction": "フィールド不足テスト",
                # project_dir がない
            },
        })

        # デフォルトのproject_dirが使用される
        assert result["status"] == "success"

    def test_handle_task_negative_returncode(self, sock_dir):
        """負のリターンコード（シグナル終了）でもエラーとして処理されること"""
        fake_runner = FakeClaudeRunner(output="killed", returncode=-9)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-signal",
            "from": "test",
            "payload": {
                "instruction": "シグナル終了テスト",
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "error"
