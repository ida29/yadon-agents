"""claude -p サブプロセスラッパー"""

from __future__ import annotations

import logging
import subprocess

from yadon_agents.config.agent import CLAUDE_DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)


def run_claude(
    prompt: str,
    model: str,
    cwd: str,
    timeout: int = CLAUDE_DEFAULT_TIMEOUT,
    output_format: str = "text",
) -> tuple[str, int]:
    """claude -p でプロンプトを実行する。

    Returns:
        (stdout+stderr, returncode)
    """
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
