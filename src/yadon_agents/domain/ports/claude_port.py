"""ClaudeRunnerPort — Claude CLI実行の抽象インターフェース

エージェント層はこのポートに依存し、具体的なsubprocess実装には依存しない。
テスト時にモック注入が可能になる。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from yadon_agents.config.agent import CLAUDE_DEFAULT_TIMEOUT

__all__ = ["ClaudeRunnerPort"]


class ClaudeRunnerPort(ABC):
    """Claude CLI実行のインターフェース。"""

    @abstractmethod
    def run(
        self,
        prompt: str,
        model: str,
        cwd: str,
        timeout: int = CLAUDE_DEFAULT_TIMEOUT,
        output_format: str = "text",
    ) -> tuple[str, int]:
        """claude -p でプロンプトを実行する。

        Returns:
            (出力テキスト, リターンコード)
        """
