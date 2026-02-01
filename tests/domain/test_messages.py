"""ドメインメッセージ型のテスト"""

import re

import pytest

from yadon_agents.domain.messages import (
    ResultMessage,
    StatusQuery,
    StatusResponse,
    TaskMessage,
    generate_task_id,
)


class TestGenerateTaskId:
    def test_format(self):
        task_id = generate_task_id()
        assert re.match(r"^task-\d{8}-\d{6}-[0-9a-f]{4}$", task_id)

    def test_unique(self):
        ids = {generate_task_id() for _ in range(20)}
        assert len(ids) == 20


class TestTaskMessage:
    def test_to_dict(self):
        msg = TaskMessage(
            from_agent="yadoran",
            instruction="READMEを更新",
            project_dir="/work",
            task_id="task-123",
        )
        d = msg.to_dict()
        assert d["type"] == "task"
        assert d["id"] == "task-123"
        assert d["from"] == "yadoran"
        assert d["payload"]["instruction"] == "READMEを更新"
        assert d["payload"]["project_dir"] == "/work"

    def test_frozen(self):
        msg = TaskMessage(from_agent="a", instruction="b", project_dir="/c")
        with pytest.raises(AttributeError):
            msg.from_agent = "x"  # type: ignore[misc]


class TestResultMessage:
    def test_to_dict(self):
        msg = ResultMessage(
            task_id="t1",
            from_agent="yadon-1",
            status="success",
            output="done",
            summary="完了",
        )
        d = msg.to_dict()
        assert d["type"] == "result"
        assert d["status"] == "success"
        assert d["payload"]["output"] == "done"

    def test_frozen(self):
        msg = ResultMessage(task_id="t", from_agent="a", status="s", output="o", summary="s")
        with pytest.raises(AttributeError):
            msg.status = "x"  # type: ignore[misc]


class TestStatusQuery:
    def test_to_dict(self):
        q = StatusQuery(from_agent="check")
        d = q.to_dict()
        assert d["type"] == "status"
        assert d["from"] == "check"


class TestStatusResponse:
    def test_to_dict_without_workers(self):
        r = StatusResponse(from_agent="yadon-1", state="idle")
        d = r.to_dict()
        assert d["state"] == "idle"
        assert d["current_task"] is None
        assert "workers" not in d

    def test_to_dict_with_workers(self):
        r = StatusResponse(
            from_agent="yadoran",
            state="busy",
            current_task="t1",
            workers={"yadon-1": "idle"},
        )
        d = r.to_dict()
        assert d["workers"] == {"yadon-1": "idle"}
        assert d["current_task"] == "t1"
