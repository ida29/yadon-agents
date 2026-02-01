"""YadonWorker — ワーカーエージェント"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from typing import Any

__all__ = ["YadonWorker"]

from yadon_agents import PROJECT_ROOT
from yadon_agents.agent.base import BaseAgent
from yadon_agents.config.agent import (
    BUBBLE_RESULT_MAX_LENGTH,
    BUBBLE_TASK_MAX_LENGTH,
    SUMMARY_MAX_LENGTH,
)
from yadon_agents.domain.formatting import summarize_for_bubble
from yadon_agents.domain.messages import ResultMessage
from yadon_agents.domain.ports.claude_port import ClaudeRunnerPort
from yadon_agents.infra import protocol as proto
from yadon_agents.infra.claude_runner import SubprocessClaudeRunner
from yadon_agents.themes import get_theme

logger = logging.getLogger(__name__)


class YadonWorker(BaseAgent):
    """ワーカー。タスクを受信してclaude haikuで実行する。"""

    def __init__(
        self,
        number: int,
        project_dir: str | None = None,
        claude_runner: ClaudeRunnerPort | None = None,
    ):
        self.number = number
        self.claude_runner = claude_runner or SubprocessClaudeRunner()
        theme = get_theme()
        name = f"{theme.agent_role_worker}-{number}"
        sock_path = proto.agent_socket_path(name, prefix=theme.socket_prefix)
        if project_dir is None:
            project_dir = str(PROJECT_ROOT)
        self._theme = theme
        super().__init__(name=name, sock_path=sock_path, project_dir=project_dir)

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any]:
        task_id = msg.get("id", "unknown")
        self.current_task_id = task_id
        payload = msg.get("payload", {})
        instruction = payload.get("instruction", "")
        project_dir = payload.get("project_dir", self.project_dir)

        logger.info("タスク受信: %s", task_id)

        theme = self._theme
        prompt = theme.worker_prompt_template.format(
            instructions_path=theme.instructions_worker,
            worker_name=theme.role_names.worker,
            number=self.number,
            instruction=instruction,
        )

        task_summary = summarize_for_bubble(instruction, BUBBLE_TASK_MAX_LENGTH)
        self.bubble(theme.worker_task_bubble.format(summary=task_summary), "claude")

        output, returncode = self.claude_runner.run(prompt=prompt, model="haiku", cwd=project_dir)
        status = "success" if returncode == 0 else "error"
        summary = output.strip()[:SUMMARY_MAX_LENGTH] if output.strip() else "(出力なし)"

        result_summary = summarize_for_bubble(summary, BUBBLE_RESULT_MAX_LENGTH)
        if status == "success":
            self.bubble(theme.worker_success_bubble.format(summary=result_summary), "claude")
        else:
            self.bubble(theme.worker_error_bubble.format(summary=result_summary), "claude")

        self.current_task_id = None

        return ResultMessage(
            task_id=task_id,
            from_agent=self.name,
            status=status,
            output=output,
            summary=summary,
        ).to_dict()


def main() -> None:
    from yadon_agents.config.agent import get_yadon_count

    theme = get_theme()

    parser = argparse.ArgumentParser(description=f"{theme.role_names.worker}ワーカー")
    parser.add_argument("--number", "-n", type=int, required=True, help=f"{theme.role_names.worker}番号 (1-N)")
    args = parser.parse_args()

    yadon_count = get_yadon_count()
    if not 1 <= args.number <= yadon_count:
        print(f"エラー: {theme.role_names.worker}番号は1〜{yadon_count}です", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format=f"[{theme.role_names.worker}-{args.number}] %(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    worker = YadonWorker(args.number)

    def signal_handler(signum, frame):
        worker.stop()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        worker.serve_forever()
    except KeyboardInterrupt:
        worker.stop()


if __name__ == "__main__":
    main()
