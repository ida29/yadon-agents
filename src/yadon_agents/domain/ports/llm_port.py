"""LLMRunnerPort — LLM実行の抽象インターフェース

エージェント層はこのポートに依存し、具体的なLLM実装には依存しない。
テスト時にモック注入が可能になる。

LLMRunnerPort は、モデル階層（coordinator/manager/worker）に応じた
プロンプト実行とインタラクティブコマンド構築を抽象化する。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from yadon_agents.config.agent import CLAUDE_DEFAULT_TIMEOUT

__all__ = ["LLMRunnerPort"]


class LLMRunnerPort(ABC):
    """LLM実行のインターフェース。

    モデル階層に応じたプロンプト実行とコマンド構築を定義する。
    """

    @abstractmethod
    def run(
        self,
        prompt: str,
        model_tier: str,
        cwd: str | None = None,
        timeout: float = CLAUDE_DEFAULT_TIMEOUT,
        output_format: str | None = None,
    ) -> tuple[str, int]:
        """LLMプロンプトを実行する。

        Args:
            prompt: 実行するプロンプト文字列
            model_tier: モデル階層。以下の3階層を想定:
                - "coordinator": ヤドキング用（claude-opus、対話型）
                - "manager": ヤドラン用（claude-sonnet、3フェーズ分解）
                - "worker": ヤドン用（claude-haiku、実作業）
            cwd: 作業ディレクトリ。Noneの場合は現在のディレクトリ
            timeout: 実行タイムアウト時間（秒）。デフォルトは CLAUDE_DEFAULT_TIMEOUT
            output_format: 出力形式。"text"、"json"等を想定。Noneの場合は形式指定なし

        Returns:
            tuple[str, int]: (出力テキスト, リターンコード)。
                リターンコード 0 は成功、0以外はエラー

        Raises:
            TimeoutError: タイムアウト時に発生
            RuntimeError: LLM実行に失敗した場合
        """

    @abstractmethod
    def build_interactive_command(
        self,
        model_tier: str,
        system_prompt_path: str | None = None,
    ) -> list[str]:
        """LLMのインタラクティブコマンドを構築する。

        対話型モード（ヤドキング）用のコマンドライン引数を構築する。
        具体的には「claude --model <model-name> [--system <path>]」の形式。

        Args:
            model_tier: モデル階層。以下の3階層に対応:
                - "coordinator": クラウディウス（opus）
                - "manager": ヤドラン用モデル（sonnet等）
                - "worker": ヤドン用モデル（haiku等）
            system_prompt_path: システムプロンプトファイルのパス。
                Noneの場合はシステムプロンプトオプション無し

        Returns:
            list[str]: コマンドライン引数リスト。
                例: ["claude", "--model", "opus", "--system", "/path/to/prompt.txt"]

        Raises:
            ValueError: model_tierが不正な場合
            FileNotFoundError: system_prompt_pathが存在しない場合
        """
