"""メッセージフロー統合テスト

メッセージ型間の変換フローをテストします:
- TaskMessage -> ResultMessage の変換
- StatusQuery -> StatusResponse の変換
- JSON シリアライズ/デシリアライズの往復
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from yadon_agents.domain.messages import (
    ResultMessage,
    StatusQuery,
    StatusResponse,
    TaskMessage,
    generate_task_id,
)


class TestTaskResultFlow:
    """TaskMessage -> ResultMessage のフローテスト"""

    def test_task_to_result_success_flow(self) -> None:
        """タスク成功時のフロー"""
        task = TaskMessage(
            from_agent="yadoking",
            instruction="README.mdを更新してください",
            project_dir="/work/project",
        )

        # タスク実行後、結果を作成
        result = ResultMessage(
            task_id=task.task_id,
            from_agent="yadon-1",
            status="success",
            output="README.mdを更新しました",
            summary="ドキュメント更新完了",
        )

        # IDが一致
        assert result.task_id == task.task_id
        assert result.status == "success"

    def test_task_to_result_error_flow(self) -> None:
        """タスクエラー時のフロー"""
        task = TaskMessage(
            from_agent="yadoran",
            instruction="テストを実行してください",
            project_dir="/work/project",
        )

        # エラー結果を作成
        result = ResultMessage(
            task_id=task.task_id,
            from_agent="yadon-2",
            status="error",
            output="テストが失敗しました",
            summary="テスト失敗",
        )

        assert result.task_id == task.task_id
        assert result.status == "error"

    def test_task_to_result_partial_error_flow(self) -> None:
        """部分エラー時のフロー"""
        task = TaskMessage(
            from_agent="yadoking",
            instruction="複数ファイルを処理してください",
            project_dir="/work/project",
        )

        result = ResultMessage(
            task_id=task.task_id,
            from_agent="yadoran",
            status="partial_error",
            output="file1.txt: OK\nfile2.txt: ERROR",
            summary="一部処理失敗",
        )

        assert result.status == "partial_error"


class TestStatusQueryResponseFlow:
    """StatusQuery -> StatusResponse のフローテスト"""

    def test_status_query_idle_response(self) -> None:
        """アイドル状態のステータス応答"""
        query = StatusQuery(from_agent="check_status")
        response = StatusResponse(
            from_agent="yadon-1",
            state="idle",
            current_task=None,
        )

        assert query.to_dict()["type"] == "status"
        assert response.to_dict()["state"] == "idle"
        assert response.to_dict()["current_task"] is None

    def test_status_query_busy_response(self) -> None:
        """ビジー状態のステータス応答"""
        task_id = generate_task_id()

        query = StatusQuery(from_agent="check_status")
        response = StatusResponse(
            from_agent="yadon-1",
            state="busy",
            current_task=task_id,
        )

        assert response.to_dict()["state"] == "busy"
        assert response.to_dict()["current_task"] == task_id

    def test_status_query_manager_response_with_workers(self) -> None:
        """マネージャーのステータス応答（ワーカー情報付き）"""
        query = StatusQuery(from_agent="yadoking")
        response = StatusResponse(
            from_agent="yadoran",
            state="busy",
            current_task="task-123",
            workers={
                "yadon-1": "busy",
                "yadon-2": "idle",
                "yadon-3": "busy",
                "yadon-4": "idle",
            },
        )

        result_dict = response.to_dict()
        assert result_dict["state"] == "busy"
        assert "workers" in result_dict
        assert result_dict["workers"]["yadon-1"] == "busy"
        assert result_dict["workers"]["yadon-2"] == "idle"


@pytest.mark.integration
class TestJsonSerializationRoundtrip:
    """JSON シリアライズ/デシリアライズの往復テスト"""

    def test_task_message_roundtrip(self) -> None:
        """TaskMessage の JSON 往復"""
        original = TaskMessage(
            from_agent="yadoking",
            instruction="テスト実行",
            project_dir="/work/project",
            task_id="task-20260101-120000-abcd",
        )

        # シリアライズ
        json_str = json.dumps(original.to_dict(), ensure_ascii=False)

        # デシリアライズ
        parsed = json.loads(json_str)

        assert parsed["type"] == "task"
        assert parsed["id"] == "task-20260101-120000-abcd"
        assert parsed["from"] == "yadoking"
        assert parsed["payload"]["instruction"] == "テスト実行"
        assert parsed["payload"]["project_dir"] == "/work/project"

    def test_result_message_roundtrip(self) -> None:
        """ResultMessage の JSON 往復"""
        original = ResultMessage(
            task_id="task-20260101-120000-abcd",
            from_agent="yadon-1",
            status="success",
            output="完了しました\n詳細: OK",
            summary="成功",
        )

        json_str = json.dumps(original.to_dict(), ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["type"] == "result"
        assert parsed["id"] == "task-20260101-120000-abcd"
        assert parsed["status"] == "success"
        assert parsed["payload"]["output"] == "完了しました\n詳細: OK"
        assert parsed["payload"]["summary"] == "成功"

    def test_status_query_roundtrip(self) -> None:
        """StatusQuery の JSON 往復"""
        original = StatusQuery(from_agent="check_status")

        json_str = json.dumps(original.to_dict(), ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["type"] == "status"
        assert parsed["from"] == "check_status"

    def test_status_response_roundtrip(self) -> None:
        """StatusResponse の JSON 往復"""
        original = StatusResponse(
            from_agent="yadoran",
            state="idle",
            current_task=None,
            workers={"yadon-1": "idle", "yadon-2": "busy"},
        )

        json_str = json.dumps(original.to_dict(), ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["type"] == "status_response"
        assert parsed["from"] == "yadoran"
        assert parsed["state"] == "idle"
        assert parsed["current_task"] is None
        assert parsed["workers"] == {"yadon-1": "idle", "yadon-2": "busy"}

    def test_japanese_text_roundtrip(self) -> None:
        """日本語テキストを含むメッセージの往復"""
        original = TaskMessage(
            from_agent="ヤドキング",
            instruction="日本語の指示: テストを実行してください。絵文字も含む 🎉",
            project_dir="/ワーク/プロジェクト",
        )

        json_str = json.dumps(original.to_dict(), ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["from"] == "ヤドキング"
        assert "絵文字も含む 🎉" in parsed["payload"]["instruction"]
        assert parsed["payload"]["project_dir"] == "/ワーク/プロジェクト"

    def test_special_characters_roundtrip(self) -> None:
        """特殊文字を含むメッセージの往復"""
        original = ResultMessage(
            task_id="task-123",
            from_agent="yadon-1",
            status="success",
            output='改行\n\tタブ\r\nCRLF\\"クォート\\"',
            summary="特殊文字テスト",
        )

        json_str = json.dumps(original.to_dict(), ensure_ascii=False)
        parsed = json.loads(json_str)

        assert "\n" in parsed["payload"]["output"]
        assert "\t" in parsed["payload"]["output"]

    def test_empty_strings_roundtrip(self) -> None:
        """空文字列を含むメッセージの往復"""
        original = ResultMessage(
            task_id="task-123",
            from_agent="yadon-1",
            status="success",
            output="",
            summary="",
        )

        json_str = json.dumps(original.to_dict(), ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["payload"]["output"] == ""
        assert parsed["payload"]["summary"] == ""


@pytest.mark.integration
class TestMessageChaining:
    """メッセージチェーン（複数メッセージの連携）テスト"""

    def test_multiple_task_results_same_task_id(self) -> None:
        """同一タスクIDに対する複数の結果メッセージ"""
        task = TaskMessage(
            from_agent="yadoran",
            instruction="ファイルを処理してください",
            project_dir="/work",
        )

        # 複数ワーカーからの結果
        results = [
            ResultMessage(
                task_id=task.task_id,
                from_agent="yadon-1",
                status="success",
                output="Worker 1 done",
                summary="完了",
            ),
            ResultMessage(
                task_id=task.task_id,
                from_agent="yadon-2",
                status="success",
                output="Worker 2 done",
                summary="完了",
            ),
        ]

        # 全て同じタスクIDを参照
        for result in results:
            assert result.task_id == task.task_id

    def test_sequential_tasks_different_ids(self) -> None:
        """連続タスクは異なるIDを持つ"""
        task1 = TaskMessage(
            from_agent="yadoking",
            instruction="タスク1",
            project_dir="/work",
        )
        task2 = TaskMessage(
            from_agent="yadoking",
            instruction="タスク2",
            project_dir="/work",
        )

        assert task1.task_id != task2.task_id

    def test_task_result_json_reconstruction(self) -> None:
        """タスク→JSON→結果の再構築フロー"""
        # タスク作成
        task = TaskMessage(
            from_agent="yadoking",
            instruction="JSONテスト",
            project_dir="/work",
        )

        # JSON化してソケット送信をシミュレート
        task_json = json.dumps(task.to_dict())

        # 受信側でパース
        received = json.loads(task_json)
        received_task_id = received["id"]

        # 結果を作成
        result = ResultMessage(
            task_id=received_task_id,
            from_agent="yadon-1",
            status="success",
            output="done",
            summary="ok",
        )

        # 結果をJSON化して返送
        result_json = json.dumps(result.to_dict())

        # 送信側でパース
        received_result = json.loads(result_json)

        # タスクIDが一致
        assert received_result["id"] == task.task_id


@pytest.mark.integration
class TestMessageValidation:
    """メッセージバリデーションテスト"""

    def test_task_message_required_fields(self) -> None:
        """TaskMessage の必須フィールド"""
        task = TaskMessage(
            from_agent="test",
            instruction="test instruction",
            project_dir="/test",
        )

        task_dict = task.to_dict()
        required_keys = ["type", "id", "from", "payload"]
        for key in required_keys:
            assert key in task_dict

        payload_keys = ["instruction", "project_dir"]
        for key in payload_keys:
            assert key in task_dict["payload"]

    def test_result_message_required_fields(self) -> None:
        """ResultMessage の必須フィールド"""
        result = ResultMessage(
            task_id="t1",
            from_agent="test",
            status="success",
            output="out",
            summary="sum",
        )

        result_dict = result.to_dict()
        required_keys = ["type", "id", "from", "status", "payload"]
        for key in required_keys:
            assert key in result_dict

        payload_keys = ["output", "summary"]
        for key in payload_keys:
            assert key in result_dict["payload"]

    def test_status_response_optional_workers(self) -> None:
        """StatusResponse の workers は省略可能"""
        # workers なし
        response_no_workers = StatusResponse(
            from_agent="yadon-1",
            state="idle",
        )
        dict_no_workers = response_no_workers.to_dict()
        assert "workers" not in dict_no_workers

        # workers あり
        response_with_workers = StatusResponse(
            from_agent="yadoran",
            state="busy",
            workers={"yadon-1": "idle"},
        )
        dict_with_workers = response_with_workers.to_dict()
        assert "workers" in dict_with_workers

    def test_message_type_discrimination(self) -> None:
        """メッセージタイプによる判別"""
        task = TaskMessage(
            from_agent="test",
            instruction="i",
            project_dir="/p",
        )
        result = ResultMessage(
            task_id="t",
            from_agent="test",
            status="success",
            output="o",
            summary="s",
        )
        query = StatusQuery(from_agent="test")
        response = StatusResponse(from_agent="test", state="idle")

        assert task.to_dict()["type"] == "task"
        assert result.to_dict()["type"] == "result"
        assert query.to_dict()["type"] == "status"
        assert response.to_dict()["type"] == "status_response"
