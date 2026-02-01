"""AgentPort — エージェントの抽象インターフェース

GUI層やCLI層はこのポートに依存し、具体的なエージェント実装には依存しない。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

__all__ = ["AgentPort", "BubbleCallback", "DEFAULT_BUBBLE_DURATION"]

# 吹き出しコールバック型: (text, bubble_type, duration_ms) -> None
BubbleCallback = Callable[[str, str, int], None]

# エージェント層のデフォルト吹き出し表示時間 (ms)
# UI層のBUBBLE_DISPLAY_TIMEとは独立
DEFAULT_BUBBLE_DURATION = 5000


class AgentPort(ABC):
    """エージェントの公開インターフェース。

    GUI層の AgentThread やCLI層はこのポートを通じてエージェントを操作する。
    具体的な実装 (YadonWorker, YadoranManager) は agent/ 層で提供される。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """エージェント名 (例: "yadon-1", "yadoran")"""

    @property
    @abstractmethod
    def on_bubble(self) -> BubbleCallback | None:
        """吹き出しコールバック"""

    @on_bubble.setter
    @abstractmethod
    def on_bubble(self, callback: BubbleCallback | None) -> None: ...

    @abstractmethod
    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any]:
        """タスクメッセージを処理し、結果を返す。"""

    @abstractmethod
    def handle_status(self, msg: dict[str, Any]) -> dict[str, Any]:
        """ステータス照会メッセージを処理し、応答を返す。"""

    @abstractmethod
    def serve_forever(self) -> None:
        """ソケットサーバーループを開始する（ブロッキング）。"""

    @abstractmethod
    def stop(self) -> None:
        """エージェントを停止する。"""
