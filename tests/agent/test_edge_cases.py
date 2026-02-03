"""エージェントのエッジケーステスト

空のタスクリスト、非常に長いタスク名、特殊文字を含むタスク、
同時実行シナリオのモックテスト。
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from yadon_agents.agent.manager import YadoranManager, _aggregate_results, _extract_json
from yadon_agents.agent.worker import YadonWorker
from yadon_agents.domain.ports.llm_port import LLMRunnerPort
from yadon_agents.themes import _reset_cache


class FakeClaudeRunner(LLMRunnerPort):
    """テスト用の LLM ランナーモック"""

    def __init__(self, output: str = "", return_code: int = 0, delay: float = 0):
        self.output = output
        self.return_code = return_code
        self.delay = delay
        self.call_count = 0
        self.last_prompt: str | None = None

    def run(
        self,
        prompt: str,
        model_tier: str,
        cwd: str | None = None,
        timeout: float = 30,
        output_format: str | None = None,
    ) -> tuple[str, int]:
        self.call_count += 1
        self.last_prompt = prompt
        if self.delay > 0:
            time.sleep(self.delay)
        return self.output, self.return_code

    def build_interactive_command(
        self,
        model_tier: str,
        system_prompt_path: str | None = None,
    ) -> list[str]:
        """テスト用の実装"""
        return ["claude", "--model", model_tier]


class TestEmptyTaskList:
    """空のタスクリストに関するエッジケース"""

    def setup_method(self) -> None:
        _reset_cache()

    def test_aggregate_empty_results(self) -> None:
        """空の結果リストを集約"""
        results: list[dict[str, Any]] = []
        status, summary, output = _aggregate_results(results)

        assert status == "success"
        assert summary == ""
        assert output == ""

    def test_decompose_returns_empty_phases_fallback(self, sock_dir: str) -> None:
        """空のフェーズリストが返された場合、フォールバックで1フェーズになること"""
        json_output = json.dumps({
            "phases": [],
            "strategy": "空のフェーズ"
        })

        fake_runner = FakeClaudeRunner(output=json_output, return_code=0)
        manager = YadoranManager(claude_runner=fake_runner)

        phases = manager.decompose_task(
            instruction="空フェーズテスト",
            project_dir="/tmp",
        )

        # 空のフェーズリストの場合、フォールバックで implement フェーズが1つ作成される
        assert isinstance(phases, list)
        assert len(phases) == 1
        assert phases[0]["name"] == "implement"
        assert phases[0]["subtasks"][0]["instruction"] == "空フェーズテスト"

    def test_decompose_with_empty_subtasks_in_phase(self, sock_dir: str) -> None:
        """フェーズ内のサブタスクが空の場合"""
        json_output = json.dumps({
            "phases": [
                {"name": "implement", "subtasks": []},
                {"name": "docs", "subtasks": []},
                {"name": "review", "subtasks": []},
            ],
            "strategy": "サブタスクなし"
        })

        fake_runner = FakeClaudeRunner(output=json_output, return_code=0)
        manager = YadoranManager(claude_runner=fake_runner)

        phases = manager.decompose_task(
            instruction="サブタスクなしテスト",
            project_dir="/tmp",
        )

        assert len(phases) == 3
        for phase in phases:
            assert len(phase.get("subtasks", [])) == 0


class TestVeryLongTaskName:
    """非常に長いタスク名に関するエッジケース"""

    def setup_method(self) -> None:
        _reset_cache()

    def test_worker_handles_very_long_instruction(self, sock_dir: str) -> None:
        """ワーカーが非常に長い指示を処理できること"""
        long_instruction = "長いタスク指示 " * 10000  # 約80,000文字（UTF-8）
        fake_runner = FakeClaudeRunner(output="完了", return_code=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-long",
            "from": "test",
            "payload": {
                "instruction": long_instruction,
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "success"
        # プロンプトに長い指示が含まれていることを確認
        assert fake_runner.last_prompt is not None
        # 元の指示が80,000文字程度、テンプレート分を足すと80,000文字以上
        assert len(fake_runner.last_prompt) > 70000
        # 長い指示がプロンプトに含まれていることを確認
        assert "長いタスク指示" in fake_runner.last_prompt

    def test_decompose_very_long_instruction(self, sock_dir: str) -> None:
        """非常に長い指示の分解"""
        long_instruction = "A" * 50000

        json_output = json.dumps({
            "phases": [
                {"name": "implement", "subtasks": [{"instruction": "短い指示"}]}
            ]
        })

        fake_runner = FakeClaudeRunner(output=json_output, return_code=0)
        manager = YadoranManager(claude_runner=fake_runner)

        phases = manager.decompose_task(
            instruction=long_instruction,
            project_dir="/tmp",
        )

        assert len(phases) == 1
        # 分解は成功し、プロンプトに長い指示が含まれていたことを確認
        assert fake_runner.last_prompt is not None
        assert len(fake_runner.last_prompt) > 50000

    def test_aggregate_results_with_long_output(self) -> None:
        """非常に長い出力を持つ結果の集約"""
        long_output = "x" * (1024 * 1024)  # 1MB
        results = [
            {
                "from": "yadon-1",
                "status": "success",
                "payload": {"summary": "長い出力", "output": long_output},
            },
        ]

        status, summary, output = _aggregate_results(results)

        assert status == "success"
        assert len(output) > 1024 * 1024


class TestSpecialCharactersInTask:
    """特殊文字を含むタスクに関するエッジケース"""

    def setup_method(self) -> None:
        _reset_cache()

    def test_worker_handles_special_characters(self, sock_dir: str) -> None:
        """特殊文字を含む指示を処理"""
        special_instruction = """
        パス: /path/to/file.txt
        シェル: echo "hello" && ls -la | grep 'pattern'
        クォート: 'single' "double" `backtick`
        エスケープ: \\n \\t \\r
        NULL: \x00
        タブ: \t\t
        """
        fake_runner = FakeClaudeRunner(output="OK", return_code=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-special",
            "from": "test",
            "payload": {
                "instruction": special_instruction,
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "success"

    def test_worker_handles_unicode_emoji(self, sock_dir: str) -> None:
        """絵文字を含む指示を処理"""
        emoji_instruction = "タスク 🎉 完了 🚀 テスト ✅ 問題 ❌"
        fake_runner = FakeClaudeRunner(output="絵文字出力 🎯", return_code=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-emoji",
            "from": "test",
            "payload": {
                "instruction": emoji_instruction,
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "success"
        assert "🎯" in result["payload"]["output"]

    def test_worker_handles_multilingual(self, sock_dir: str) -> None:
        """多言語を含む指示を処理"""
        multilingual = "日本語 한국어 中文 العربية Ελληνικά русский"
        fake_runner = FakeClaudeRunner(output="多言語完了", return_code=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-multilingual",
            "from": "test",
            "payload": {
                "instruction": multilingual,
                "project_dir": sock_dir,
            },
        })

        assert result["status"] == "success"

    def test_extract_json_with_special_chars_in_value(self) -> None:
        """JSON値に特殊文字を含む場合の抽出"""
        output = '{"key": "値に\\nエスケープ\\tあり"}'
        result = _extract_json(output)
        assert "key" in result

    def test_aggregate_results_with_special_chars_in_summary(self) -> None:
        """サマリに特殊文字を含む結果の集約"""
        results = [
            {
                "from": "yadon-1",
                "status": "success",
                "payload": {
                    "summary": "特殊文字: \t\n\"'\\",
                    "output": "output",
                },
            },
        ]

        status, summary, output = _aggregate_results(results)

        assert status == "success"
        assert "特殊文字" in summary


class TestConcurrentExecution:
    """同時実行シナリオのモックテスト"""

    def setup_method(self) -> None:
        _reset_cache()

    def test_multiple_workers_concurrent_execution(self, sock_dir: str) -> None:
        """複数ワーカーの同時実行をシミュレート"""
        results: list[dict[str, Any]] = []
        errors: list[Exception] = []

        def worker_task(worker_num: int) -> None:
            try:
                fake_runner = FakeClaudeRunner(
                    output=f"ワーカー{worker_num}完了",
                    return_code=0,
                    delay=0.1  # 少し遅延を入れて同時実行をシミュレート
                )
                worker = YadonWorker(
                    number=worker_num,
                    project_dir=sock_dir,
                    claude_runner=fake_runner
                )

                result = worker.handle_task({
                    "id": f"task-{worker_num}",
                    "from": "test",
                    "payload": {
                        "instruction": f"タスク{worker_num}",
                        "project_dir": sock_dir,
                    },
                })
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 4つのワーカーを同時実行
        threads = [
            threading.Thread(target=worker_task, args=(i,))
            for i in range(1, 5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 4

        # 全て成功していることを確認
        for result in results:
            assert result["status"] == "success"

    def test_aggregate_concurrent_results(self) -> None:
        """同時に生成された結果の集約"""
        # 複数スレッドから結果を追加するシミュレーション
        all_results: list[dict[str, Any]] = []

        def add_result(worker_num: int) -> None:
            time.sleep(0.01 * worker_num)  # 少しずらす
            all_results.append({
                "from": f"yadon-{worker_num}",
                "status": "success",
                "payload": {
                    "summary": f"ワーカー{worker_num}完了",
                    "output": f"output{worker_num}",
                },
            })

        threads = [
            threading.Thread(target=add_result, args=(i,))
            for i in range(1, 5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 結果を集約
        status, summary, output = _aggregate_results(all_results)

        assert status == "success"
        assert len(all_results) == 4

    def test_runner_call_count_per_worker(self, sock_dir: str) -> None:
        """各ワーカーがランナーを1回ずつ呼ぶことを確認"""
        runners: list[FakeClaudeRunner] = []

        for i in range(1, 5):
            runner = FakeClaudeRunner(output=f"結果{i}", return_code=0)
            runners.append(runner)
            worker = YadonWorker(number=i, project_dir=sock_dir, claude_runner=runner)

            worker.handle_task({
                "id": f"task-{i}",
                "from": "test",
                "payload": {
                    "instruction": f"タスク{i}",
                    "project_dir": sock_dir,
                },
            })

        # 各ランナーが1回ずつ呼ばれたことを確認
        for i, runner in enumerate(runners):
            assert runner.call_count == 1, f"Runner {i+1} called {runner.call_count} times"


class TestErrorHandling:
    """エラーハンドリングのエッジケース"""

    def setup_method(self) -> None:
        _reset_cache()

    def test_worker_handles_runner_exception(self, sock_dir: str) -> None:
        """ランナーが例外を発生させた場合のワーカー動作"""

        class ExceptionRunner(LLMRunnerPort):
            def run(
                self,
                prompt: str,
                model_tier: str,
                cwd: str | None = None,
                timeout: float = 30,
                output_format: str | None = None,
            ) -> tuple[str, int]:
                raise RuntimeError("テスト例外")

            def build_interactive_command(
                self,
                model_tier: str,
                system_prompt_path: str | None = None,
            ) -> list[str]:
                return ["claude"]

        worker = YadonWorker(
            number=1,
            project_dir=sock_dir,
            claude_runner=ExceptionRunner()
        )

        # 例外が伝播することを確認
        with pytest.raises(RuntimeError, match="テスト例外"):
            worker.handle_task({
                "id": "task-exception",
                "from": "test",
                "payload": {
                    "instruction": "例外発生タスク",
                    "project_dir": sock_dir,
                },
            })

    def test_aggregate_results_with_missing_fields(self) -> None:
        """フィールドが欠けている結果の集約"""
        results = [
            {
                "from": "yadon-1",
                "status": "success",
                "payload": {},  # summary, output がない
            },
            {
                "from": "yadon-2",
                "status": "success",
                # payload 自体がない場合もテスト
            },
        ]

        # エラーにならないことを確認
        status, summary, output = _aggregate_results(results)
        assert status == "success"

    def test_extract_json_malformed(self) -> None:
        """不正なJSONの抽出で例外が発生すること"""
        malformed = "{ this is not json }"

        with pytest.raises(json.JSONDecodeError):
            _extract_json(malformed)

    def test_extract_json_empty_string(self) -> None:
        """空文字列からのJSON抽出"""
        with pytest.raises(json.JSONDecodeError):
            _extract_json("")


class TestBoundaryConditions:
    """境界条件のテスト"""

    def setup_method(self) -> None:
        _reset_cache()

    def test_worker_number_boundary_min(self, sock_dir: str) -> None:
        """ワーカー番号の最小値(1)"""
        fake_runner = FakeClaudeRunner(output="OK", return_code=0)
        worker = YadonWorker(number=1, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-min",
            "from": "test",
            "payload": {
                "instruction": "テスト",
                "project_dir": sock_dir,
            },
        })

        assert result["from"] == "yadon-1"

    def test_worker_number_boundary_max(self, sock_dir: str) -> None:
        """ワーカー番号の最大値(8)"""
        fake_runner = FakeClaudeRunner(output="OK", return_code=0)
        worker = YadonWorker(number=8, project_dir=sock_dir, claude_runner=fake_runner)

        result = worker.handle_task({
            "id": "task-max",
            "from": "test",
            "payload": {
                "instruction": "テスト",
                "project_dir": sock_dir,
            },
        })

        assert result["from"] == "yadon-8"

    def test_aggregate_many_results(self) -> None:
        """大量の結果(100個)を集約"""
        results = [
            {
                "from": f"yadon-{(i % 8) + 1}",
                "status": "success" if i % 10 != 0 else "error",
                "payload": {
                    "summary": f"タスク{i}完了",
                    "output": f"output{i}",
                },
            }
            for i in range(100)
        ]

        status, summary, output = _aggregate_results(results)

        # 1つでもエラーがあればpartial_error
        assert status == "partial_error"
        # 全結果が含まれていることを確認
        for i in range(100):
            assert f"タスク{i}完了" in summary

    def test_decompose_timeout_fallback(self, sock_dir: str) -> None:
        """分解がタイムアウトした場合のフォールバック"""

        class TimeoutRunner(LLMRunnerPort):
            def run(
                self,
                prompt: str,
                model_tier: str,
                cwd: str | None = None,
                timeout: float = 30,
                output_format: str | None = None,
            ) -> tuple[str, int]:
                # タイムアウトをシミュレート（不正な出力を返す）
                return "timeout occurred", 1

            def build_interactive_command(
                self,
                model_tier: str,
                system_prompt_path: str | None = None,
            ) -> list[str]:
                return ["claude"]

        manager = YadoranManager(claude_runner=TimeoutRunner())

        phases = manager.decompose_task(
            instruction="タイムアウトテスト",
            project_dir="/tmp",
        )

        # フォールバック: implement フェーズのみ
        assert len(phases) == 1
        assert phases[0]["name"] == "implement"
        assert phases[0]["subtasks"][0]["instruction"] == "タイムアウトテスト"
