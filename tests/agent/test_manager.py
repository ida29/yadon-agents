"""YadoranManager — _aggregate_results と decompose_task のテスト"""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from yadon_agents.agent.manager import (
    YadoranManager,
    _aggregate_results,
    _extract_json,
)
from yadon_agents.domain.ports.claude_port import ClaudeRunnerPort


class FakeClaudeRunner(ClaudeRunnerPort):
    """テスト用の Claude ランナーモック"""

    def __init__(self, output: str = "", return_code: int = 0):
        self.output = output
        self.return_code = return_code

    def run(
        self,
        prompt: str,
        model: str,
        cwd: str,
        timeout: int = 30,
        output_format: str = "text",
    ) -> tuple[str, int]:
        return self.output, self.return_code


class TestAggregateResults:
    """_aggregate_results() のテスト"""

    def test_aggregate_results_all_success(self):
        """全成功時 status=success"""
        all_results = [
            {
                "from": "yadon-1",
                "status": "success",
                "payload": {"summary": "実装完了", "output": "output1"},
            },
            {
                "from": "yadon-2",
                "status": "success",
                "payload": {"summary": "テスト完了", "output": "output2"},
            },
        ]
        overall_status, combined_summary, combined_output = _aggregate_results(all_results)

        assert overall_status == "success"
        assert "[yadon-1] success: 実装完了" in combined_summary
        assert "[yadon-2] success: テスト完了" in combined_summary
        assert "=== yadon-1 (success) ===" in combined_output
        assert "output1" in combined_output
        assert "=== yadon-2 (success) ===" in combined_output
        assert "output2" in combined_output

    def test_aggregate_results_partial_error(self):
        """一部失敗時 status=partial_error"""
        all_results = [
            {
                "from": "yadon-1",
                "status": "success",
                "payload": {"summary": "実装完了", "output": "output1"},
            },
            {
                "from": "yadon-2",
                "status": "error",
                "payload": {"summary": "エラー発生", "output": "error occurred"},
            },
        ]
        overall_status, combined_summary, combined_output = _aggregate_results(all_results)

        assert overall_status == "partial_error"
        assert "[yadon-1] success: 実装完了" in combined_summary
        assert "[yadon-2] error: エラー発生" in combined_summary
        assert "=== yadon-1 (success) ===" in combined_output
        assert "=== yadon-2 (error) ===" in combined_output

    def test_aggregate_results_empty(self):
        """空リスト時も処理できる"""
        all_results: list[dict[str, Any]] = []
        overall_status, combined_summary, combined_output = _aggregate_results(all_results)

        assert overall_status == "success"
        assert combined_summary == ""
        assert combined_output == ""


class TestDecomposeTask:
    """decompose_task() のテスト"""

    def test_decompose_task_success(self):
        """正常な3フェーズ分解、JSON出力をモック"""
        json_output = json.dumps({
            "phases": [
                {
                    "name": "implement",
                    "subtasks": [{"instruction": "コード実装"}]
                },
                {
                    "name": "docs",
                    "subtasks": [{"instruction": "ドキュメント更新"}]
                },
                {
                    "name": "review",
                    "subtasks": [{"instruction": "レビュー"}]
                }
            ],
            "strategy": "3フェーズに分解"
        })

        fake_runner = FakeClaudeRunner(output=json_output, return_code=0)
        manager = YadoranManager(claude_runner=fake_runner)

        phases = manager.decompose_task(
            instruction="テスト機能を追加する",
            project_dir="/tmp",
        )

        assert len(phases) == 3
        assert phases[0]["name"] == "implement"
        assert phases[1]["name"] == "docs"
        assert phases[2]["name"] == "review"
        assert len(phases[0].get("subtasks", [])) == 1
        assert phases[0]["subtasks"][0]["instruction"] == "コード実装"

    def test_decompose_task_json_parse_error_fallback(self):
        """JSONパース失敗時のフォールバック（1タスク）"""
        # JSONパースに失敗する出力を返す
        bad_output = "このは不正なJSON{ invalid json }"

        fake_runner = FakeClaudeRunner(output=bad_output, return_code=0)
        manager = YadoranManager(claude_runner=fake_runner)

        phases = manager.decompose_task(
            instruction="テスト機能を追加する",
            project_dir="/tmp",
        )

        # フォールバック: implement フェーズのみ、元の instruction がそのまま1タスク
        assert len(phases) == 1
        assert phases[0]["name"] == "implement"
        assert len(phases[0].get("subtasks", [])) == 1
        assert phases[0]["subtasks"][0]["instruction"] == "テスト機能を追加する"


class TestExtractJson:
    """_extract_json() のユニットテスト"""

    def test_extract_json_fenced(self):
        """JSONフェンス内のJSONを抽出"""
        output = """こういった JSON が出力されます:
```json
{"key": "value"}
```"""
        result = _extract_json(output)
        assert result == {"key": "value"}

    def test_extract_json_plain(self):
        """フェンスなしの JSON をパース"""
        output = '{"key": "value"}'
        result = _extract_json(output)
        assert result == {"key": "value"}

    def test_extract_json_with_surrounding_text(self):
        """地の文混在時、{ から } までを抽出"""
        output = "以下が JSON です: {\"key\": \"value\"} です。"
        result = _extract_json(output)
        assert result == {"key": "value"}

    def test_extract_json_invalid_raises_error(self):
        """JSONパースに失敗したら例外を raise"""
        output = "これは JSON ではありません"
        with pytest.raises(json.JSONDecodeError):
            _extract_json(output)
