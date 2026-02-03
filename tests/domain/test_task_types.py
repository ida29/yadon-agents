"""domain/task_types.py のテスト

Subtask TypedDict と Phase TypedDict の構造検証、
必須フィールドの確認テスト。
"""

from __future__ import annotations

from typing import get_type_hints

import pytest

from yadon_agents.domain.task_types import Phase, Subtask


class TestSubtask:
    """Subtask TypedDict の構造検証"""

    def test_subtask_has_instruction_field(self) -> None:
        """Subtask に instruction フィールドが存在すること"""
        hints = get_type_hints(Subtask)
        assert "instruction" in hints

    def test_subtask_instruction_is_str(self) -> None:
        """Subtask.instruction が str 型であること"""
        hints = get_type_hints(Subtask)
        assert hints["instruction"] is str

    def test_subtask_can_be_created(self) -> None:
        """Subtask を正しく作成できること"""
        subtask: Subtask = {"instruction": "テストタスク"}
        assert subtask["instruction"] == "テストタスク"

    def test_subtask_with_empty_instruction(self) -> None:
        """空の instruction でも作成できること"""
        subtask: Subtask = {"instruction": ""}
        assert subtask["instruction"] == ""

    def test_subtask_with_unicode_instruction(self) -> None:
        """Unicode 文字を含む instruction を設定できること"""
        subtask: Subtask = {"instruction": "日本語タスク 🎉"}
        assert "日本語" in subtask["instruction"]
        assert "🎉" in subtask["instruction"]

    def test_subtask_with_multiline_instruction(self) -> None:
        """複数行の instruction を設定できること"""
        subtask: Subtask = {
            "instruction": "行1\n行2\n行3"
        }
        assert "\n" in subtask["instruction"]

    def test_subtask_with_special_characters(self) -> None:
        """特殊文字を含む instruction を設定できること"""
        subtask: Subtask = {
            "instruction": "パス /path/to/file && 'quotes' \"double\""
        }
        assert "&&" in subtask["instruction"]
        assert "'" in subtask["instruction"]


class TestPhase:
    """Phase TypedDict の構造検証"""

    def test_phase_has_name_field(self) -> None:
        """Phase に name フィールドが存在すること"""
        hints = get_type_hints(Phase)
        assert "name" in hints

    def test_phase_has_subtasks_field(self) -> None:
        """Phase に subtasks フィールドが存在すること"""
        hints = get_type_hints(Phase)
        assert "subtasks" in hints

    def test_phase_name_is_str(self) -> None:
        """Phase.name が str 型であること"""
        hints = get_type_hints(Phase)
        assert hints["name"] is str

    def test_phase_subtasks_is_list(self) -> None:
        """Phase.subtasks が list 型であること"""
        hints = get_type_hints(Phase)
        # list[Subtask] なので origin を確認
        subtasks_type = hints["subtasks"]
        assert hasattr(subtasks_type, "__origin__") or "list" in str(subtasks_type).lower()

    def test_phase_can_be_created(self) -> None:
        """Phase を正しく作成できること"""
        phase: Phase = {
            "name": "implement",
            "subtasks": [{"instruction": "コード実装"}]
        }
        assert phase["name"] == "implement"
        assert len(phase["subtasks"]) == 1

    def test_phase_with_empty_subtasks(self) -> None:
        """空の subtasks リストでも作成できること"""
        phase: Phase = {
            "name": "review",
            "subtasks": []
        }
        assert phase["subtasks"] == []

    def test_phase_with_multiple_subtasks(self) -> None:
        """複数の subtasks を持つ Phase を作成できること"""
        phase: Phase = {
            "name": "implement",
            "subtasks": [
                {"instruction": "タスク1"},
                {"instruction": "タスク2"},
                {"instruction": "タスク3"},
            ]
        }
        assert len(phase["subtasks"]) == 3
        assert phase["subtasks"][0]["instruction"] == "タスク1"
        assert phase["subtasks"][2]["instruction"] == "タスク3"

    def test_phase_implement(self) -> None:
        """implement フェーズの作成"""
        phase: Phase = {
            "name": "implement",
            "subtasks": [
                {"instruction": "機能Aを実装する"},
                {"instruction": "機能Bを実装する"},
            ]
        }
        assert phase["name"] == "implement"

    def test_phase_docs(self) -> None:
        """docs フェーズの作成"""
        phase: Phase = {
            "name": "docs",
            "subtasks": [
                {"instruction": "READMEを更新する"},
            ]
        }
        assert phase["name"] == "docs"

    def test_phase_review(self) -> None:
        """review フェーズの作成"""
        phase: Phase = {
            "name": "review",
            "subtasks": [
                {"instruction": "コードレビューを実施する"},
            ]
        }
        assert phase["name"] == "review"


class TestPhaseListCreation:
    """複数 Phase のリスト作成テスト"""

    def test_create_three_phases(self) -> None:
        """3フェーズ（implement, docs, review）のリストを作成できること"""
        phases: list[Phase] = [
            {
                "name": "implement",
                "subtasks": [
                    {"instruction": "コード実装1"},
                    {"instruction": "コード実装2"},
                ]
            },
            {
                "name": "docs",
                "subtasks": [
                    {"instruction": "ドキュメント更新"},
                ]
            },
            {
                "name": "review",
                "subtasks": [
                    {"instruction": "最終レビュー"},
                ]
            },
        ]

        assert len(phases) == 3
        assert phases[0]["name"] == "implement"
        assert phases[1]["name"] == "docs"
        assert phases[2]["name"] == "review"

    def test_total_subtasks_count(self) -> None:
        """全フェーズのサブタスク合計を計算できること"""
        phases: list[Phase] = [
            {
                "name": "implement",
                "subtasks": [
                    {"instruction": "タスク1"},
                    {"instruction": "タスク2"},
                    {"instruction": "タスク3"},
                ]
            },
            {
                "name": "docs",
                "subtasks": [
                    {"instruction": "タスク4"},
                ]
            },
            {
                "name": "review",
                "subtasks": [
                    {"instruction": "タスク5"},
                    {"instruction": "タスク6"},
                ]
            },
        ]

        total = sum(len(p["subtasks"]) for p in phases)
        assert total == 6

    def test_empty_phases_list(self) -> None:
        """空のフェーズリストも有効であること"""
        phases: list[Phase] = []
        assert len(phases) == 0

    def test_phases_with_unicode(self) -> None:
        """Unicode 文字を含むフェーズ"""
        phases: list[Phase] = [
            {
                "name": "実装",
                "subtasks": [
                    {"instruction": "日本語タスク 🚀"},
                ]
            },
        ]

        assert phases[0]["name"] == "実装"
        assert "🚀" in phases[0]["subtasks"][0]["instruction"]


class TestTypeCompatibility:
    """型互換性のテスト"""

    def test_subtask_dict_compatibility(self) -> None:
        """Subtask が通常の dict として扱えること"""
        subtask: Subtask = {"instruction": "テスト"}

        # dict 操作ができることを確認
        assert "instruction" in subtask
        assert subtask.get("instruction") == "テスト"

    def test_phase_dict_compatibility(self) -> None:
        """Phase が通常の dict として扱えること"""
        phase: Phase = {
            "name": "test",
            "subtasks": []
        }

        # dict 操作ができることを確認
        assert "name" in phase
        assert "subtasks" in phase
        assert phase.get("name") == "test"

    def test_phase_subtasks_iteration(self) -> None:
        """Phase.subtasks をイテレートできること"""
        phase: Phase = {
            "name": "test",
            "subtasks": [
                {"instruction": "タスク1"},
                {"instruction": "タスク2"},
            ]
        }

        instructions = [s["instruction"] for s in phase["subtasks"]]
        assert instructions == ["タスク1", "タスク2"]

    def test_json_serializable(self) -> None:
        """Subtask と Phase が JSON シリアライズ可能であること"""
        import json

        subtask: Subtask = {"instruction": "テスト"}
        phase: Phase = {
            "name": "implement",
            "subtasks": [subtask]
        }

        # JSON にシリアライズできることを確認
        json_str = json.dumps(phase, ensure_ascii=False)
        assert "implement" in json_str
        assert "テスト" in json_str

        # デシリアライズして元に戻せることを確認
        restored = json.loads(json_str)
        assert restored["name"] == "implement"
        assert restored["subtasks"][0]["instruction"] == "テスト"
