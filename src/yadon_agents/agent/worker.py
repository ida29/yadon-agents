"""YadonWorker — ヤドンワーカーエージェント"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from typing import Any

from yadon_agents import PROJECT_ROOT
from yadon_agents.agent.base import BaseAgent
from yadon_agents.config.agent import SUMMARY_MAX_LENGTH
from yadon_agents.domain.formatting import summarize_for_bubble
from yadon_agents.domain.messages import ResultMessage
from yadon_agents.infra import protocol as proto
from yadon_agents.infra.claude_runner import run_claude

logger = logging.getLogger(__name__)


class YadonWorker(BaseAgent):
    """ヤドンワーカー。タスクを受信してclaude haikuで実行する。"""

    def __init__(self, number: int, project_dir: str | None = None):
        self.number = number
        name = f"yadon-{number}"
        sock_path = proto.agent_socket_path(name)
        if project_dir is None:
            project_dir = str(PROJECT_ROOT)
        super().__init__(name=name, sock_path=sock_path, project_dir=project_dir)

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any]:
        task_id = msg.get("id", "unknown")
        self.current_task_id = task_id
        payload = msg.get("payload", {})
        instruction = payload.get("instruction", "")
        project_dir = payload.get("project_dir", self.project_dir)

        logger.info("タスク受信: %s", task_id)

        prompt = (
            f"instructions/yadon.md を読んで従ってください。\n\n"
            f"あなたはヤドン{self.number}です。\n\nタスク:\n{instruction}"
        )
        self.bubble(f"...やるやぁん... ({summarize_for_bubble(instruction)})", "claude")

        output, returncode = run_claude(prompt=prompt, model="haiku", cwd=project_dir)
        status = "success" if returncode == 0 else "error"
        summary = output.strip()[:SUMMARY_MAX_LENGTH] if output.strip() else "(出力なし)"

        if status == "success":
            self.bubble("...できたやぁん...", "claude")
        else:
            self.bubble(f"...失敗やぁん... ({summarize_for_bubble(summary)})", "claude")

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

    parser = argparse.ArgumentParser(description="ヤドンワーカー")
    parser.add_argument("--number", "-n", type=int, required=True, help="ヤドン番号 (1-N)")
    args = parser.parse_args()

    yadon_count = get_yadon_count()
    if not 1 <= args.number <= yadon_count:
        print(f"エラー: ヤドン番号は1〜{yadon_count}です", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format=f"[yadon-{args.number}] %(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    worker = YadonWorker(args.number)

    def signal_handler(signum, frame):
        logger.info("シグナル受信、停止中...")
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        worker.serve_forever()
    except KeyboardInterrupt:
        worker.stop()


if __name__ == "__main__":
    main()
