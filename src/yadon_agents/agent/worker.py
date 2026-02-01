"""YadonWorker — ヤドンワーカーエージェント"""

import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

from yadon_agents.agent.base import BaseAgent
from yadon_agents.infra import protocol as proto
from yadon_agents.infra.claude_runner import run_claude

logger = logging.getLogger(__name__)


class YadonWorker(BaseAgent):
    """ヤドンワーカー。タスクを受信してclaude haikuで実行する。"""

    def __init__(self, number: int, project_dir: Optional[str] = None):
        self.number = number
        name = f"yadon-{number}"
        sock_path = proto.agent_socket_path(name)
        if project_dir is None:
            project_dir = str(Path(__file__).parent.parent.parent.parent)
        super().__init__(name=name, sock_path=sock_path, project_dir=project_dir)

    def handle_task(self, msg: dict) -> dict:
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
        self.bubble(f"...やるやぁん... ({instruction[:30]}...)", "claude")

        output, returncode = run_claude(prompt=prompt, model="haiku", cwd=project_dir)
        status = "success" if returncode == 0 else "error"
        summary = output.strip()[:200] if output.strip() else "(出力なし)"

        if status == "success":
            self.bubble("...できたやぁん...", "claude")
        else:
            self.bubble(f"...失敗やぁん... ({summary[:30]})", "claude")

        self.current_task_id = None

        return proto.make_result_message(
            task_id=task_id,
            from_agent=self.name,
            status=status,
            output=output,
            summary=summary,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="ヤドンワーカー")
    parser.add_argument("--number", "-n", type=int, required=True, help="ヤドン番号 (1-4)")
    args = parser.parse_args()

    if not 1 <= args.number <= 4:
        print("エラー: ヤドン番号は1〜4です", file=sys.stderr)
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
