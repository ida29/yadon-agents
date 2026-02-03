"""LLM サブプロセスラッパー（LLMRunnerPort の実装）

複数LLMバックエンド（Claude、Gemini等）に対応。
config.llm の BACKEND_CONFIGS と get_model_for_tier() を使用して
バックエンド固有のコマンドライン引数を動的に構築する。
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from yadon_agents.config.agent import CLAUDE_DEFAULT_TIMEOUT
from yadon_agents.config.llm import get_backend_config, get_model_for_tier, get_worker_backend_config
from yadon_agents.domain.ports.llm_port import LLMRunnerPort

__all__ = ["SubprocessClaudeRunner", "run_claude"]

logger = logging.getLogger(__name__)


class SubprocessClaudeRunner(LLMRunnerPort):
    """subprocess経由でLLM CLIを実行するアダプター。

    BACKEND_CONFIGS に基づいて複数のLLMバックエンドを支援。
    バックエンド固有のコマンドフラグやモデル名を動的に構築する。
    """

    def __init__(self, worker_number: int | None = None):
        """初期化。

        Args:
            worker_number: ワーカー番号（ワーカー固有のバックエンド設定を使用する場合）
        """
        self.worker_number = worker_number

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
            model_tier: モデル階層（"coordinator", "manager", "worker"）
            cwd: 作業ディレクトリ
            timeout: タイムアウト時間（秒）
            output_format: 出力形式（"text", "json"等）

        Returns:
            (出力テキスト, リターンコード)
        """
        # バックエンド設定を取得（ワーカー番号が指定されている場合はワーカー固有設定を使用）
        if self.worker_number is not None:
            backend_config = get_worker_backend_config(self.worker_number)
        else:
            backend_config = get_backend_config()
        model = get_model_for_tier(model_tier)

        # コマンドを構築
        cmd = [backend_config.command]

        # バッチサブコマンドを追加（複数トークンの場合は分割）
        if backend_config.batch_subcommand:
            cmd.extend(backend_config.batch_subcommand.split())

        # batch_prompt_style に応じてコマンドを構築
        use_stdin = True
        style = backend_config.batch_prompt_style

        if style == "stdin":
            # claude, copilot: -p フラグ + 標準入力
            cmd.append("-p")
            use_stdin = True
        elif style == "arg":
            # gemini: --prompt "..." コマンドライン引数
            cmd.extend(["--prompt", prompt])
            use_stdin = False
        elif style == "subcommand_stdin":
            # opencode: サブコマンド + 標準入力（サブコマンドは上で追加済み）
            use_stdin = True

        cmd.extend(["--model", model])

        # 出力形式が指定された場合のみフラグを追加
        if output_format:
            cmd.extend(["--output-format", output_format])

        # バックエンド固有フラグを追加（--dangerously-skip-permissions等）
        # Claude専用フラグ
        if backend_config.command == "claude":
            cmd.append("--dangerously-skip-permissions")

        # Gemini専用フラグ（yoloモード）
        if backend_config.command == "gemini":
            cmd.append("--yolo")

        logger.info(
            "%s batch 実行中 (tier=%s, model=%s, style=%s): %s...",
            backend_config.command,
            model_tier,
            model,
            style,
            prompt[:80],
        )

        try:
            result = subprocess.run(
                cmd,
                input=prompt if use_stdin else None,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout + result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return f"タイムアウト ({int(timeout) // 60}分)", 1
        except Exception as e:
            return f"実行エラー: {e}", 1

    def build_interactive_command(
        self,
        model_tier: str,
        system_prompt_path: str | None = None,
    ) -> list[str]:
        """LLMのインタラクティブコマンドを構築する。

        Args:
            model_tier: モデル階層（"coordinator", "manager", "worker"）
            system_prompt_path: システムプロンプトファイルのパス

        Returns:
            コマンドライン引数リスト

        Raises:
            FileNotFoundError: system_prompt_path が存在しない場合
        """
        # バックエンド設定を取得
        backend_config = get_backend_config()
        model = get_model_for_tier(model_tier)

        # 基本コマンドを構築
        cmd = [backend_config.command, "--model", model]

        # システムプロンプトが指定された場合
        if system_prompt_path:
            system_path = Path(system_prompt_path)
            if not system_path.exists():
                raise FileNotFoundError(f"System prompt not found: {system_prompt_path}")
            cmd.extend(["--system", str(system_path)])

        logger.info(
            "%s interactive command (tier=%s, model=%s)",
            backend_config.command,
            model_tier,
            model,
        )

        return cmd


# デフォルトインスタンス（後方互換用）
_default_runner = SubprocessClaudeRunner()


def run_claude(
    prompt: str,
    model: str,
    cwd: str,
    timeout: int = CLAUDE_DEFAULT_TIMEOUT,
    output_format: str = "text",
) -> tuple[str, int]:
    """claude -p でプロンプトを実行する（後方互換の関数インターフェース）。

    レガシーインターフェース。model パラメータを model_tier に変換。

    Args:
        prompt: 実行するプロンプト
        model: モデル名（後方互換用）。実装ではmodel_tierとして扱う。
               "haiku", "sonnet", "opus" → "worker", "manager", "coordinator"
        cwd: 作業ディレクトリ
        timeout: タイムアウト（秒）
        output_format: 出力形式

    Returns:
        (stdout+stderr, returncode)
    """
    # レガシー model パラメータを model_tier に変換
    model_tier_map = {
        "haiku": "worker",
        "sonnet": "manager",
        "opus": "coordinator",
    }
    model_tier = model_tier_map.get(model, "worker")

    return _default_runner.run(
        prompt=prompt,
        model_tier=model_tier,
        cwd=cwd,
        timeout=timeout,
        output_format=output_format,
    )
