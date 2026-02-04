"""YadoranManager の統合テスト

handle_task() の完全パス（decompose -> dispatch -> aggregate）、
dispatch() の正常系・エラー系、複数フェーズ実行フロー。
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from yadon_agents.agent.manager import YadoranManager, _aggregate_results
from yadon_agents.domain.messages import ResultMessage
from yadon_agents.domain.ports.llm_port import LLMRunnerPort
from yadon_agents.themes import _reset_cache


class FakeClaudeRunner(LLMRunnerPort):
    """テスト用の LLM ランナーモック"""

    def __init__(self, output: str = "", return_code: int = 0):
        self.output = output
        self.return_code = return_code
        self.run_count = 0

    def run(
        self,
        prompt: str,
        model_tier: str,
        cwd: str | None = None,
        timeout: float = 30,
        output_format: str | None = None,
    ) -> tuple[str, int]:
        self.run_count += 1
        return self.output, self.return_code

    def build_interactive_command(
        self,
        model_tier: str,
        system_prompt_path: str | None = None,
    ) -> list[str]:
        return ["claude", "--model", model_tier]


class TestHandleTaskIntegration:
    """handle_task() の統合テスト"""

    def setup_method(self) -> None:
        """各テスト前にテーマキャッシュをリセット"""
        _reset_cache()

    def test_handle_task_full_flow_success(self, sock_dir: str) -> None:
        """3フェーズ全て成功するフロー"""
        json_output = json.dumps({
            "phases": [
                {"name": "implement", "subtasks": [{"instruction": "コード実装"}]},
                {"name": "docs", "subtasks": [{"instruction": "ドキュメント更新"}]},
                {"name": "review", "subtasks": [{"instruction": "レビュー"}]},
            ],
            "strategy": "3フェーズ分解"
        })

        fake_runner = FakeClaudeRunner(output=json_output, return_code=0)
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        # ワーカーへの dispatch をモック
        mock_result = ResultMessage(
            task_id="task-001-implement-sub1",
            from_agent="yadon-1",
            status="success",
            output="完了",
            summary="タスク完了",
        ).to_dict()

        with patch.object(manager, "dispatch_to_yadon", return_value=mock_result):
            with patch.object(manager, "bubble"):  # 吹き出し通知を無効化
                result = manager.handle_task({
                    "id": "task-001",
                    "from": "yadoking",
                    "payload": {
                        "instruction": "テスト機能を追加する",
                        "project_dir": sock_dir,
                    },
                })

        assert result["status"] == "success"
        assert result["from"] == "yadoran"
        assert result["type"] == "result"

    def test_handle_task_partial_failure(self, sock_dir: str) -> None:
        """一部フェーズが失敗するフロー"""
        json_output = json.dumps({
            "phases": [
                {"name": "implement", "subtasks": [{"instruction": "コード実装"}]},
                {"name": "docs", "subtasks": [{"instruction": "ドキュメント更新"}]},
            ],
            "strategy": "2フェーズ分解"
        })

        fake_runner = FakeClaudeRunner(output=json_output, return_code=0)
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        call_count = [0]

        def mock_dispatch(yadon_number: int, subtask: Any, project_dir: str, sub_task_id: str) -> dict[str, Any]:
            call_count[0] += 1
            if call_count[0] == 1:
                return ResultMessage(
                    task_id=sub_task_id,
                    from_agent=f"yadon-{yadon_number}",
                    status="success",
                    output="成功",
                    summary="完了",
                ).to_dict()
            else:
                return ResultMessage(
                    task_id=sub_task_id,
                    from_agent=f"yadon-{yadon_number}",
                    status="error",
                    output="失敗",
                    summary="エラー発生",
                ).to_dict()

        with patch.object(manager, "dispatch_to_yadon", side_effect=mock_dispatch):
            with patch.object(manager, "bubble"):
                result = manager.handle_task({
                    "id": "task-002",
                    "from": "yadoking",
                    "payload": {
                        "instruction": "テスト機能",
                        "project_dir": sock_dir,
                    },
                })

        assert result["status"] == "partial_error"

    def test_handle_task_json_parse_error_fallback(self, sock_dir: str) -> None:
        """JSONパースエラー時のフォールバック"""
        # 不正な JSON を返す
        fake_runner = FakeClaudeRunner(output="これは不正な{JSON}", return_code=0)
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        mock_result = ResultMessage(
            task_id="task-003-implement-sub1",
            from_agent="yadon-1",
            status="success",
            output="完了",
            summary="完了",
        ).to_dict()

        with patch.object(manager, "dispatch_to_yadon", return_value=mock_result):
            with patch.object(manager, "bubble"):
                result = manager.handle_task({
                    "id": "task-003",
                    "from": "yadoking",
                    "payload": {
                        "instruction": "テスト機能",
                        "project_dir": sock_dir,
                    },
                })

        # フォールバックで実行されて成功
        assert result["status"] == "success"


class TestDispatchToYadon:
    """dispatch_to_yadon() のテスト"""

    def setup_method(self) -> None:
        _reset_cache()

    def test_dispatch_success(self, sock_dir: str) -> None:
        """正常なディスパッチ"""
        fake_runner = FakeClaudeRunner()
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        mock_response = ResultMessage(
            task_id="sub-task-1",
            from_agent="yadon-1",
            status="success",
            output="完了",
            summary="完了",
        ).to_dict()

        with patch("yadon_agents.agent.manager.proto.send_message", return_value=mock_response):
            result = manager.dispatch_to_yadon(
                yadon_number=1,
                subtask={"instruction": "テスト"},
                project_dir=sock_dir,
                sub_task_id="sub-task-1",
            )

        assert result["status"] == "success"
        assert result["from"] == "yadon-1"

    def test_dispatch_connection_error(self, sock_dir: str) -> None:
        """接続エラー時のエラーレスポンス"""
        fake_runner = FakeClaudeRunner()
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        with patch("yadon_agents.agent.manager.proto.send_message", side_effect=ConnectionRefusedError("接続拒否")):
            result = manager.dispatch_to_yadon(
                yadon_number=2,
                subtask={"instruction": "テスト"},
                project_dir=sock_dir,
                sub_task_id="sub-task-2",
            )

        assert result["status"] == "error"
        assert "送信失敗" in result["payload"]["output"]

    def test_dispatch_timeout(self, sock_dir: str) -> None:
        """タイムアウト時のエラーレスポンス"""
        fake_runner = FakeClaudeRunner()
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        import socket
        with patch("yadon_agents.agent.manager.proto.send_message", side_effect=socket.timeout("タイムアウト")):
            result = manager.dispatch_to_yadon(
                yadon_number=3,
                subtask={"instruction": "テスト"},
                project_dir=sock_dir,
                sub_task_id="sub-task-3",
            )

        assert result["status"] == "error"
        assert "送信失敗" in result["payload"]["output"]


class TestDispatchPhase:
    """_dispatch_phase() のテスト"""

    def setup_method(self) -> None:
        _reset_cache()

    def test_dispatch_phase_multiple_subtasks(self, sock_dir: str) -> None:
        """複数サブタスクの並列実行"""
        fake_runner = FakeClaudeRunner()
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        def mock_dispatch(yadon_number: int, subtask: Any, project_dir: str, sub_task_id: str) -> dict[str, Any]:
            return ResultMessage(
                task_id=sub_task_id,
                from_agent=f"yadon-{yadon_number}",
                status="success",
                output=f"ワーカー{yadon_number}完了",
                summary=f"完了{yadon_number}",
            ).to_dict()

        with patch.object(manager, "dispatch_to_yadon", side_effect=mock_dispatch):
            phase = {
                "name": "implement",
                "subtasks": [
                    {"instruction": "タスク1"},
                    {"instruction": "タスク2"},
                    {"instruction": "タスク3"},
                ],
            }
            results = manager._dispatch_phase(phase, sock_dir, "task-001", 0)

        assert len(results) == 3
        assert all(r["status"] == "success" for r in results)

    def test_dispatch_phase_exceeds_worker_count(self, sock_dir: str) -> None:
        """サブタスク数がワーカー数を超える場合"""
        fake_runner = FakeClaudeRunner()
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        call_count = [0]

        def mock_dispatch(yadon_number: int, subtask: Any, project_dir: str, sub_task_id: str) -> dict[str, Any]:
            call_count[0] += 1
            return ResultMessage(
                task_id=sub_task_id,
                from_agent=f"yadon-{yadon_number}",
                status="success",
                output="完了",
                summary="完了",
            ).to_dict()

        with patch.object(manager, "dispatch_to_yadon", side_effect=mock_dispatch):
            # yadon_count を超えるサブタスク
            phase = {
                "name": "implement",
                "subtasks": [{"instruction": f"タスク{i}"} for i in range(10)],
            }
            results = manager._dispatch_phase(phase, sock_dir, "task-002", 0)

        # yadon_count 分のみ実行される
        assert len(results) == manager.yadon_count
        assert call_count[0] == manager.yadon_count

    def test_dispatch_phase_empty_subtasks(self, sock_dir: str) -> None:
        """サブタスクが空の場合"""
        fake_runner = FakeClaudeRunner()
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        phase = {
            "name": "docs",
            "subtasks": [],
        }
        results = manager._dispatch_phase(phase, sock_dir, "task-003", 1)

        assert len(results) == 0


class TestHandleStatus:
    """handle_status() のテスト"""

    def setup_method(self) -> None:
        _reset_cache()

    def test_handle_status_idle(self, sock_dir: str) -> None:
        """アイドル状態のステータス"""
        fake_runner = FakeClaudeRunner()
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        # ワーカーソケットが存在しない状態
        with patch("yadon_agents.agent.manager.Path.exists", return_value=False):
            result = manager.handle_status({})

        assert result["state"] == "idle"
        assert result["current_task"] is None
        # ワーカーは "stopped" として報告
        for worker_status in result["workers"].values():
            assert worker_status == "stopped"

    def test_handle_status_busy(self, sock_dir: str) -> None:
        """ビジー状態のステータス"""
        fake_runner = FakeClaudeRunner()
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)
        manager.current_task_id = "task-running"

        with patch("yadon_agents.agent.manager.Path.exists", return_value=False):
            result = manager.handle_status({})

        assert result["state"] == "busy"
        assert result["current_task"] == "task-running"

    def test_handle_status_worker_unreachable(self, sock_dir: str) -> None:
        """ワーカーが応答しない場合"""
        from pathlib import Path

        fake_runner = FakeClaudeRunner()
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        def mock_exists(self: Path) -> bool:
            return True

        with patch.object(Path, "exists", mock_exists):
            with patch("yadon_agents.agent.manager.proto.send_message", side_effect=ConnectionRefusedError()):
                result = manager.handle_status({})

        # ワーカーは "unreachable" として報告
        for worker_status in result["workers"].values():
            assert worker_status == "unreachable"


class TestDecomposeTaskEdgeCases:
    """decompose_task() のエッジケーステスト"""

    def setup_method(self) -> None:
        _reset_cache()

    def test_decompose_task_exception_fallback(self, sock_dir: str) -> None:
        """例外発生時のフォールバック"""
        def raise_exception(*args, **kwargs):
            raise RuntimeError("Claude 実行エラー")

        fake_runner = FakeClaudeRunner()
        fake_runner.run = raise_exception
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        phases = manager.decompose_task("テストタスク", sock_dir)

        # フォールバック: implement フェーズのみ
        assert len(phases) == 1
        assert phases[0]["name"] == "implement"
        assert phases[0]["subtasks"][0]["instruction"] == "テストタスク"

    def test_decompose_task_empty_phases_in_json(self, sock_dir: str) -> None:
        """JSONに空のフェーズリストが含まれる場合"""
        json_output = json.dumps({
            "phases": [],
            "strategy": "空フェーズ"
        })

        fake_runner = FakeClaudeRunner(output=json_output, return_code=0)
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        phases = manager.decompose_task("テストタスク", sock_dir)

        # 空でもリストとして返される
        assert isinstance(phases, list)

    def test_decompose_task_missing_subtasks(self, sock_dir: str) -> None:
        """フェーズにサブタスクがない場合"""
        json_output = json.dumps({
            "phases": [
                {"name": "implement"},  # subtasks がない
            ],
            "strategy": "サブタスクなし"
        })

        fake_runner = FakeClaudeRunner(output=json_output, return_code=0)
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        phases = manager.decompose_task("テストタスク", sock_dir)

        assert len(phases) == 1
        # subtasks がなくてもエラーにならない
        assert phases[0].get("subtasks", []) == []


class TestBubbleNotifications:
    """吹き出し通知のテスト"""

    def setup_method(self) -> None:
        _reset_cache()

    def test_bubble_called_on_task_received(self, sock_dir: str) -> None:
        """タスク受信時に吹き出しが呼ばれること"""
        json_output = json.dumps({
            "phases": [{"name": "implement", "subtasks": [{"instruction": "実装"}]}],
            "strategy": "単純実装"
        })

        fake_runner = FakeClaudeRunner(output=json_output, return_code=0)
        manager = YadoranManager(project_dir=sock_dir, claude_runner=fake_runner)

        bubble_calls = []

        def mock_bubble(text: str, bubble_type: str = "normal", duration: int = 5000) -> None:
            bubble_calls.append((text, bubble_type))

        manager.bubble = mock_bubble

        mock_result = ResultMessage(
            task_id="sub-1",
            from_agent="yadon-1",
            status="success",
            output="完了",
            summary="完了",
        ).to_dict()

        with patch.object(manager, "dispatch_to_yadon", return_value=mock_result):
            manager.handle_task({
                "id": "task-bubble",
                "from": "test",
                "payload": {"instruction": "テスト", "project_dir": sock_dir},
            })

        # 吹き出しが複数回呼ばれる（タスク受信、フェーズ開始、完了）
        assert len(bubble_calls) >= 3
