"""YadoranManager — マネージャーエージェント"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from yadon_agents import PROJECT_ROOT
from yadon_agents.agent.base import BaseAgent
from yadon_agents.config.agent import (
    BUBBLE_RESULT_MAX_LENGTH,
    BUBBLE_TASK_MAX_LENGTH,
    CLAUDE_DECOMPOSE_TIMEOUT,
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
from yadon_agents.domain.ports.claude_port import ClaudeRunnerPort
from yadon_agents.domain.task_types import Phase, Subtask
from yadon_agents.infra import protocol as proto
from yadon_agents.infra.claude_runner import SubprocessClaudeRunner
from yadon_agents.themes import get_theme

__all__ = ["YadoranManager"]

logger = logging.getLogger(__name__)


def _extract_json(output: str) -> dict[str, Any]:
    """Claude出力からJSONブロックを抽出してパースする。

    3段階フォールバック:
    1. ```json...``` フェンスがあれば抽出
    2. 抽出したJSONを json.loads() で試行
    3. 失敗時、地の文混在対応（{ から } までを切り出し）

    Raises:
        json.JSONDecodeError: JSONパースに失敗した場合
    """
    json_str = output.strip()

    # (1) json フェンス探索・抽出
    if "```json" in json_str:
        try:
            start = json_str.index("```json") + 7
            end = json_str.index("```", start)
            json_str = json_str[start:end].strip()
        except ValueError:
            # フェンスが閉じていない場合は後続のロジックで対応
            pass
    elif "```" in json_str:
        try:
            start = json_str.index("```") + 3
            end = json_str.index("```", start)
            json_str = json_str[start:end].strip()
        except ValueError:
            # フェンスが閉じていない場合は後続のロジックで対応
            pass

    # (2) json.loads 試行
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # (3) 失敗時、output.find('{') から output.rfind('}') までを切り出して json.loads 試行
    start_idx = output.find('{')
    end_idx = output.rfind('}')
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        json_str = output[start_idx:end_idx + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # (4) それでも失敗なら json.JSONDecodeError を raise
    raise json.JSONDecodeError(
        "JSONパースに失敗しました",
        output,
        0,
    )


def _aggregate_results(all_results: list[dict[str, Any]]) -> tuple[str, str, str]:
    """個別結果リストから (overall_status, combined_summary, combined_output) を集約する。"""
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

    return overall_status, "\n".join(summaries), "\n\n".join(full_output_parts)


class YadoranManager(BaseAgent):
    """マネージャー。タスクを分解してワーカーに並列配分する。"""

    def __init__(
        self,
        project_dir: str | None = None,
        claude_runner: ClaudeRunnerPort | None = None,
    ):
        self.yadon_count = get_yadon_count()
        self.claude_runner = claude_runner or SubprocessClaudeRunner()
        theme = get_theme()
        self._theme = theme
        manager_name = theme.agent_role_manager
        sock_path = proto.agent_socket_path(manager_name, prefix=theme.socket_prefix)
        if project_dir is None:
            project_dir = str(PROJECT_ROOT)
        super().__init__(name=manager_name, sock_path=sock_path, project_dir=project_dir)

    def _worker_name(self, number: int) -> str:
        """ワーカーのエージェント名を返す。"""
        return f"{self._theme.agent_role_worker}-{number}"

    def _worker_socket_path(self, name: str) -> str:
        """ワーカーのソケットパスを返す。"""
        return proto.agent_socket_path(name, prefix=self._theme.socket_prefix)

    def decompose_task(self, instruction: str, project_dir: str) -> list[Phase]:
        """claude -p --model sonnet でタスクを3フェーズに分解する。"""
        theme = self._theme
        prefix = theme.manager_prompt_prefix.format(
            instructions_path=theme.instructions_manager,
            manager_name=theme.role_names.manager,
        )
        prompt = f"""{prefix}以下のタスクを3フェーズ（implement → docs → review）に分解してください。

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
- 各サブタスクには十分な情報を含める（{theme.role_names.worker}は他のサブタスクの内容を知らない）
- docsフェーズでは、実装内容に関連するCLAUDE.md, README.md, 指示書等を更新する
- reviewフェーズでは、実装とドキュメントの品質・整合性を確認し、問題を指摘する
"""
        try:
            output, _ = self.claude_runner.run(prompt=prompt, model="sonnet", cwd=project_dir, timeout=CLAUDE_DECOMPOSE_TIMEOUT)
            data = _extract_json(output)
            phases: list[Phase] = data.get("phases", [])
            strategy = data.get("strategy", "")

            if phases:
                total = sum(len(p.get("subtasks", [])) for p in phases)
                logger.info("タスク分解: %dフェーズ %d個 — %s", len(phases), total, strategy)
                return phases

        except json.JSONDecodeError:
            logger.warning("タスク分解のJSONパースに失敗、そのまま1タスクとして実行。出力: %s", output[:500])
        except Exception as e:
            if "output" in locals():
                logger.warning("タスク分解エラー: %s、Claude出力(最初の500文字): %s", e, output[:500])
            else:
                logger.warning("タスク分解エラー: %s、そのまま1タスクとして実行", e)

        # フォールバック: 旧形式互換（1フェーズ implement のみ）
        fallback: Phase = {"name": "implement", "subtasks": [{"instruction": instruction}]}
        return [fallback]

    def dispatch_to_yadon(
        self, yadon_number: int, subtask: Subtask, project_dir: str, sub_task_id: str,
    ) -> dict[str, Any]:
        """1体のワーカーにサブタスクを送信し、結果を受信する。"""
        worker_name = self._worker_name(yadon_number)
        sock_path = self._worker_socket_path(worker_name)

        msg = TaskMessage(
            from_agent=self.name,
            instruction=subtask["instruction"],
            project_dir=project_dir,
            task_id=sub_task_id,
        ).to_dict()

        try:
            return proto.send_message(sock_path, msg, timeout=SOCKET_DISPATCH_TIMEOUT)
        except Exception as e:
            logger.error("%s への送信失敗: %s", worker_name, e)
            return ResultMessage(
                task_id=sub_task_id,
                from_agent=worker_name,
                status="error",
                output=f"送信失敗: {e}",
                summary=f"{self._theme.role_names.worker}{yadon_number}への送信に失敗",
            ).to_dict()

    def _dispatch_phase(
        self, phase: Phase, project_dir: str, task_id: str, phase_index: int,
    ) -> list[dict[str, Any]]:
        """1フェーズ内のサブタスクをワーカーに並列配分して結果を収集する。"""
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
                    worker_name = self._worker_name(yadon_num)
                    logger.error("%s 実行エラー (%s): %s", worker_name, phase_name, e)
                    results.append(ResultMessage(
                        task_id="unknown",
                        from_agent=worker_name,
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

        theme = self._theme

        logger.info("タスク受信: %s — %s", task_id, instruction[:80])
        task_summary = summarize_for_bubble(instruction, BUBBLE_TASK_MAX_LENGTH)
        self.bubble(theme.manager_task_bubble.format(summary=task_summary), "claude")

        phases = self.decompose_task(instruction, project_dir)

        all_results: list[dict[str, Any]] = []
        for i, phase in enumerate(phases):
            phase_name = phase.get("name", f"phase{i}")
            subtask_count = len(phase.get("subtasks", []))
            label = theme.phase_labels.get(phase_name, f"...{phase_name}...")
            yadon_count = min(subtask_count, self.yadon_count)
            self.bubble(
                theme.manager_phase_bubble.format(
                    label=label,
                    worker_name=theme.role_names.worker,
                    count=yadon_count,
                ),
                "claude", 3000,
            )
            logger.info("フェーズ開始: %s (%d タスク)", phase_name, subtask_count)

            phase_results = self._dispatch_phase(phase, project_dir, task_id, i)
            all_results.extend(phase_results)

            phase_success = all(r.get("status") == "success" for r in phase_results)
            if not phase_success:
                logger.warning("フェーズ %s で一部失敗", phase_name)

        overall_status, combined_summary, combined_output = _aggregate_results(all_results)

        result_summary = summarize_for_bubble(combined_summary, BUBBLE_RESULT_MAX_LENGTH)
        if overall_status == "success":
            self.bubble(theme.manager_success_bubble.format(summary=result_summary), "claude")
        else:
            self.bubble(theme.manager_error_bubble.format(summary=result_summary), "claude")

        self.current_task_id = None

        return ResultMessage(
            task_id=task_id,
            from_agent=self.name,
            status=overall_status,
            output=combined_output,
            summary=combined_summary,
        ).to_dict()

    def handle_status(self, msg: dict[str, Any]) -> dict[str, Any]:
        workers: dict[str, str] = {}
        for i in range(1, self.yadon_count + 1):
            worker_name = self._worker_name(i)
            sock_path = self._worker_socket_path(worker_name)
            if Path(sock_path).exists():
                try:
                    resp = proto.send_message(
                        sock_path,
                        StatusQuery(from_agent=self.name).to_dict(),
                        timeout=SOCKET_STATUS_TIMEOUT,
                    )
                    workers[worker_name] = resp.get("state", "unknown")
                except Exception:
                    workers[worker_name] = "unreachable"
            else:
                workers[worker_name] = "stopped"

        state = "busy" if self.current_task_id else "idle"
        return StatusResponse(
            from_agent=self.name,
            state=state,
            current_task=self.current_task_id,
            workers=workers,
        ).to_dict()
