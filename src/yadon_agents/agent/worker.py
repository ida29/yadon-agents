"""YadonWorker — ワーカーエージェント"""

from __future__ import annotations

import logging
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
from yadon_agents.domain.ports.llm_port import LLMRunnerPort
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
        claude_runner: LLMRunnerPort | None = None,
    ):
        self.number = number
        self.claude_runner = claude_runner or SubprocessClaudeRunner(worker_number=self.number)
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

        output, returncode = self.claude_runner.run(prompt=prompt, model_tier="worker", cwd=project_dir)
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
