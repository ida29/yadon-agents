"""タスク分解結果の型定義"""

from __future__ import annotations

from typing import TypedDict

__all__ = [
    "Subtask",
    "Phase",
]


class Subtask(TypedDict):
    """ヤドンに配分される個別サブタスク"""
    instruction: str


class Phase(TypedDict):
    """タスク分解の1フェーズ（implement / docs / review）"""
    name: str
    subtasks: list[Subtask]
