"""claude -p サブプロセスラッパー（ClaudeRunnerPort の実装）"""

from __future__ import annotations

import logging
import subprocess

from yadon_agents.config.agent import CLAUDE_DEFAULT_TIMEOUT
from yadon_agents.domain.ports.claude_port import ClaudeRunnerPort

__all__ = ["SubprocessClaudeRunner", "run_claude"]

logger = logging.getLogger(__name__)


class SubprocessClaudeRunner(ClaudeRunnerPort):
    """subprocess経由でclaude CLIを実行するアダプター。"""

    def run(
        self,
        prompt: str,
        model: str,
        cwd: str,
        timeout: int = CLAUDE_DEFAULT_TIMEOUT,
        output_format: str = "text",
    ) -> tuple[str, int]:
        cmd = [
            "claude",
            "-p",
            prompt,
            "--model", model,
            "--dangerously-skip-permissions",
            "--output-format", output_format,
        ]
        logger.info("claude -p 実行中 (model=%s): %s...", model, prompt[:80])

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout + result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return f"タイムアウト ({timeout // 60}分)", 1
        except Exception as e:
            return f"実行エラー: {e}", 1


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

    Returns:
        (stdout+stderr, returncode)
    """
    return _default_runner.run(
        prompt=prompt,
        model=model,
        cwd=cwd,
        timeout=timeout,
        output_format=output_format,
    )
