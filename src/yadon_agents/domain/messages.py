"""ドメインメッセージ型定義"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Literal, TypedDict

__all__ = [
    "generate_task_id",
    "TaskMessage",
    "ResultMessage",
    "StatusQuery",
    "StatusResponse",
    "TaskPayload",
    "TaskMessageDict",
    "ResultPayload",
    "ResultMessageDict",
    "StatusQueryDict",
    "StatusResponseDict",
]


# --- TypedDict: ソケット通信のJSON形状 ---

# NOTE: "from" はPython予約語だが、TypedDictではキーとして使用可能。
# ただしリテラルで構築する分には問題ない。


class TaskPayload(TypedDict):
    instruction: str
    project_dir: str


class TaskMessageDict(TypedDict):
    type: Literal["task"]
    id: str
    payload: TaskPayload


class ResultPayload(TypedDict):
    output: str
    summary: str


class ResultMessageDict(TypedDict):
    type: Literal["result"]
    id: str
    status: str
    payload: ResultPayload


class StatusQueryDict(TypedDict):
    type: Literal["status"]


class StatusResponseDict(TypedDict, total=False):
    type: str
    state: str
    current_task: str | None
    workers: dict[str, str]


# --- dataclass: メッセージ構築 ---


def generate_task_id() -> str:
    """タスクIDを生成する。"""
    ts = time.strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:4]
    return f"task-{ts}-{short_uuid}"


@dataclass(frozen=True)
class TaskMessage:
    """タスク送信メッセージ"""
    from_agent: str
    instruction: str
    project_dir: str
    task_id: str = field(default_factory=generate_task_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "task",
            "id": self.task_id,
            "from": self.from_agent,
            "payload": {
                "instruction": self.instruction,
                "project_dir": self.project_dir,
            },
        }


@dataclass(frozen=True)
class ResultMessage:
    """タスク結果メッセージ"""
    task_id: str
    from_agent: str
    status: str
    output: str
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "result",
            "id": self.task_id,
            "from": self.from_agent,
            "status": self.status,
            "payload": {
                "output": self.output,
                "summary": self.summary,
            },
        }


@dataclass(frozen=True)
class StatusQuery:
    """ステータス照会メッセージ"""
    from_agent: str

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "status",
            "from": self.from_agent,
        }


@dataclass(frozen=True)
class StatusResponse:
    """ステータス応答メッセージ"""
    from_agent: str
    state: str
    current_task: str | None = None
    workers: dict[str, str] | None = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "type": "status_response",
            "from": self.from_agent,
            "state": self.state,
            "current_task": self.current_task,
        }
        if self.workers is not None:
            result["workers"] = self.workers
        return result
