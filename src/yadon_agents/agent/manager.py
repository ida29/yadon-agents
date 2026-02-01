"""YadoranManager — ヤドランタスク管理エージェント"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from yadon_agents import PROJECT_ROOT
from yadon_agents.agent.base import BaseAgent
from yadon_agents.config.agent import (
    CLAUDE_DECOMPOSE_TIMEOUT,
    PHASE_LABELS,
    SOCKET_DISPATCH_TIMEOUT,
    SOCKET_STATUS_TIMEOUT,
    get_yadon_count,
)
from yadon_agents.domain.formatting import summarize_for_bubble
from yadon_agents.domain.messages import (
    ResultMessage,
    StatusQuery,
    StatusResponse,
    TaskMessage,
)
from yadon_agents.infra import protocol as proto
from yadon_agents.infra.claude_runner import run_claude

logger = logging.getLogger(__name__)


class YadoranManager(BaseAgent):
    """ヤドラン。タスクを分解してヤドンに並列配分する。"""

    def __init__(self, project_dir: str | None = None):
        self.yadon_count = get_yadon_count()
        sock_path = proto.agent_socket_path("yadoran")
        if project_dir is None:
            project_dir = str(PROJECT_ROOT)
        super().__init__(name="yadoran", sock_path=sock_path, project_dir=project_dir)

    def decompose_task(self, instruction: str, project_dir: str) -> list[dict[str, Any]]:
        """claude -p --model sonnet でタスクを3フェーズに分解する。

        Returns:
            [{"name": "implement", "subtasks": [...]}, {"name": "docs", ...}, {"name": "review", ...}]
        """
        prompt = f"""instructions/yadoran.md を読んで従ってください。

あなたはヤドランです。以下のタスクを3フェーズ（implement → docs → review）に分解してください。

【タスク】
{instruction}

【作業ディレクトリ】
{project_dir}

【出力形式】
必ず以下のJSON形式で出力してください。他のテキストは一切不要です。
```json
{{
  "phases": [
    {{
      "name": "implement",
      "subtasks": [
        {{"instruction": "実装サブタスク1の具体的な指示"}}
      ]
    }},
    {{
      "name": "docs",
      "subtasks": [
        {{"instruction": "ドキュメント更新の具体的な指示"}}
      ]
    }},
    {{
      "name": "review",
      "subtasks": [
        {{"instruction": "レビュー指示"}}
      ]
    }}
  ],
  "strategy": "分解の方針（1行）"
}}
```

【ルール】
- 3フェーズ（implement, docs, review）を毎回必ず含める
- 各フェーズ内のサブタスクは最大{self.yadon_count}つまで（並列実行される）
- フェーズ間は逐次実行される（implement完了後にdocs、docs完了後にreview）
- 各サブタスクには十分な情報を含める（ヤドンは他のサブタスクの内容を知らない）
- docsフェーズでは、実装内容に関連するCLAUDE.md, README.md, 指示書等を更新する
- reviewフェーズでは、実装とドキュメントの品質・整合性を確認し、問題を指摘する
"""
        try:
            output, _ = run_claude(prompt=prompt, model="sonnet", cwd=project_dir, timeout=CLAUDE_DECOMPOSE_TIMEOUT)
            output = output.strip()

            json_str = output
            if "```json" in output:
                start = output.index("```json") + 7
                end = output.index("```", start)
                json_str = output[start:end].strip()
            elif "```" in output:
                start = output.index("```") + 3
                end = output.index("```", start)
                json_str = output[start:end].strip()

            data = json.loads(json_str)
            phases = data.get("phases", [])
            strategy = data.get("strategy", "")

            if phases:
                total = sum(len(p.get("subtasks", [])) for p in phases)
                logger.info("タスク分解: %dフェーズ %d個 — %s", len(phases), total, strategy)
                return phases

        except json.JSONDecodeError:
            logger.warning("タスク分解のJSONパースに失敗、そのまま1タスクとして実行")
        except Exception as e:
            logger.warning("タスク分解エラー: %s、そのまま1タスクとして実行", e)

        # フォールバック: 旧形式互換（1フェーズ implement のみ）
        return [{"name": "implement", "subtasks": [{"instruction": instruction}]}]

    def dispatch_to_yadon(
        self, yadon_number: int, subtask: dict[str, Any], project_dir: str, sub_task_id: str,
    ) -> dict[str, Any]:
        """1体のヤドンにサブタスクを送信し、結果を受信する。"""
        yadon_name = f"yadon-{yadon_number}"
        sock_path = proto.agent_socket_path(yadon_name)

        msg = TaskMessage(
            from_agent="yadoran",
            instruction=subtask["instruction"],
            project_dir=project_dir,
            task_id=sub_task_id,
        ).to_dict()

        try:
            return proto.send_message(sock_path, msg, timeout=SOCKET_DISPATCH_TIMEOUT)
        except Exception as e:
            logger.error("%s への送信失敗: %s", yadon_name, e)
            return ResultMessage(
                task_id=sub_task_id,
                from_agent=yadon_name,
                status="error",
                output=f"送信失敗: {e}",
                summary=f"ヤドン{yadon_number}への送信に失敗",
            ).to_dict()

    def _dispatch_phase(
        self, phase: dict[str, Any], project_dir: str, task_id: str, phase_index: int,
    ) -> list[dict[str, Any]]:
        """1フェーズ内のサブタスクをヤドンに並列配分して結果を収集する。"""
        subtasks = phase.get("subtasks", [])
        phase_name = phase.get("name", f"phase{phase_index}")

        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=self.yadon_count) as executor:
            futures = {}
            for i, subtask in enumerate(subtasks[:self.yadon_count]):
                yadon_num = i + 1
                sub_task_id = f"{task_id}-{phase_name}-sub{yadon_num}"
                future = executor.submit(
                    self.dispatch_to_yadon, yadon_num, subtask, project_dir, sub_task_id,
                )
                futures[future] = yadon_num

            for future in as_completed(futures):
                yadon_num = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error("ヤドン%d 実行エラー (%s): %s", yadon_num, phase_name, e)
                    results.append(ResultMessage(
                        task_id="unknown",
                        from_agent=f"yadon-{yadon_num}",
                        status="error",
                        output=str(e),
                        summary="実行エラー",
                    ).to_dict())

        return results

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any]:
        task_id = msg.get("id", "unknown")
        self.current_task_id = task_id
        payload = msg.get("payload", {})
        instruction = payload.get("instruction", "")
        project_dir = payload.get("project_dir", self.project_dir)

        logger.info("タスク受信: %s — %s", task_id, instruction[:80])
        self.bubble(f"...ヤドキングがなんか言ってる... ({summarize_for_bubble(instruction, 20)})", "claude")

        phases = self.decompose_task(instruction, project_dir)

        all_results: list[dict[str, Any]] = []
        for i, phase in enumerate(phases):
            phase_name = phase.get("name", f"phase{i}")
            subtask_count = len(phase.get("subtasks", []))
            label = PHASE_LABELS.get(phase_name, f"...{phase_name}...")
            self.bubble(
                f"{label}（{subtask_count}タスク）", "claude", 3000,
            )
            logger.info("フェーズ開始: %s (%d タスク)", phase_name, subtask_count)

            phase_results = self._dispatch_phase(phase, project_dir, task_id, i)
            all_results.extend(phase_results)

            phase_success = all(r.get("status") == "success" for r in phase_results)
            if not phase_success:
                logger.warning("フェーズ %s で一部失敗", phase_name)

        all_success = all(r.get("status") == "success" for r in all_results)
        overall_status = "success" if all_success else "partial_error"

        summaries = []
        full_output_parts = []
        for r in all_results:
            from_agent = r.get("from", "unknown")
            status = r.get("status", "unknown")
            r_payload = r.get("payload", {})
            summary = r_payload.get("summary", "")
            output = r_payload.get("output", "")
            summaries.append(f"[{from_agent}] {status}: {summary}")
            full_output_parts.append(f"=== {from_agent} ({status}) ===\n{output}")

        combined_summary = "\n".join(summaries)
        combined_output = "\n\n".join(full_output_parts)

        if overall_status == "success":
            self.bubble("...みんなできた...", "claude")
        else:
            self.bubble("...一部失敗した...", "claude")

        self.current_task_id = None

        return ResultMessage(
            task_id=task_id,
            from_agent="yadoran",
            status=overall_status,
            output=combined_output,
            summary=combined_summary,
        ).to_dict()

    def handle_status(self, msg: dict[str, Any]) -> dict[str, Any]:
        workers: dict[str, str] = {}
        for i in range(1, self.yadon_count + 1):
            yadon_name = f"yadon-{i}"
            sock_path = proto.agent_socket_path(yadon_name)
            if Path(sock_path).exists():
                try:
                    resp = proto.send_message(
                        sock_path,
                        StatusQuery(from_agent="yadoran").to_dict(),
                        timeout=SOCKET_STATUS_TIMEOUT,
                    )
                    workers[yadon_name] = resp.get("state", "unknown")
                except Exception:
                    workers[yadon_name] = "unreachable"
            else:
                workers[yadon_name] = "stopped"

        state = "busy" if self.current_task_id else "idle"
        return StatusResponse(
            from_agent=self.name,
            state=state,
            current_task=self.current_task_id,
            workers=workers,
        ).to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description="ヤドランマネージャー")
    parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="[yadoran] %(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    manager = YadoranManager()

    def signal_handler(signum, frame):
        logger.info("シグナル受信、停止中...")
        manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        manager.serve_forever()
    except KeyboardInterrupt:
        manager.stop()


if __name__ == "__main__":
    main()
