"""ドメインメッセージ型定義"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


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

    def to_dict(self) -> dict[str, Any]:
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

    def to_dict(self) -> dict[str, Any]:
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

    def to_dict(self) -> dict[str, Any]:
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

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": "status_response",
            "from": self.from_agent,
            "state": self.state,
            "current_task": self.current_task,
        }
        if self.workers is not None:
            result["workers"] = self.workers
        return result
