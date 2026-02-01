#!/usr/bin/env python3
"""
ヤドランデーモン — タスク管理エージェント

Unixソケットでタスクを受信 → claude -p --model sonnet でタスク分解 →
ヤドン1〜4に並列配分 → 結果集約 → レスポンス返却。
"""

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
import socket_protocol as proto

logger = logging.getLogger("yadoran-daemon")

YADON_COUNT = 4


class YadoranDaemon:
    def __init__(self):
        self.name = "yadoran"
        self.sock_path = proto.agent_socket_path(self.name)
        self.server_sock = None
        self.running = False
        self.current_task_id: Optional[str] = None
        self.project_dir = str(Path(__file__).parent.parent)
        self.task_queue: List[dict] = []

    def decompose_task(self, instruction: str, project_dir: str) -> List[dict]:
        """claude -p --model sonnet でタスクを分解する。

        Returns:
            サブタスクのリスト。各サブタスクは {"instruction": "..."} 形式。
            分解不要なら1つだけ返す。
        """
        prompt = f"""instructions/yadoran.md を読んで従ってください。

あなたはヤドランです。以下のタスクを、ヤドン（最大4体）に配分するために分解してください。

【タスク】
{instruction}

【作業ディレクトリ】
{project_dir}

【出力形式】
必ず以下のJSON形式で出力してください。他のテキストは一切不要です。
```json
{{
  "subtasks": [
    {{"instruction": "サブタスク1の具体的な指示"}},
    {{"instruction": "サブタスク2の具体的な指示"}}
  ],
  "strategy": "分解の方針（1行）"
}}
```

【ルール】
- サブタスクは最大4つまで
- 並列実行可能なように分解する（依存関係のあるタスクは1つにまとめる）
- 分解不要な小さいタスクはそのまま1つで返す
- 各サブタスクには十分な情報を含める（ヤドンは他のサブタスクの内容を知らない）
"""
        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--model", "sonnet", "--output-format", "text"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout.strip()

            # JSON部分を抽出（```json ... ``` で囲まれている場合）
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
            subtasks = data.get("subtasks", [])
            strategy = data.get("strategy", "")

            if subtasks:
                logger.info(f"タスク分解: {len(subtasks)}個 — {strategy}")
                return subtasks

        except json.JSONDecodeError:
            logger.warning("タスク分解のJSONパースに失敗、そのまま1タスクとして実行")
        except subprocess.TimeoutExpired:
            logger.warning("タスク分解がタイムアウト、そのまま1タスクとして実行")
        except Exception as e:
            logger.warning(f"タスク分解エラー: {e}、そのまま1タスクとして実行")

        # 分解失敗時はそのまま1タスク
        return [{"instruction": instruction}]

    def dispatch_to_yadon(
        self, yadon_number: int, subtask: dict, project_dir: str, task_id: str
    ) -> dict:
        """1体のヤドンにサブタスクを送信し、結果を受信する。"""
        yadon_name = f"yadon-{yadon_number}"
        sock_path = proto.agent_socket_path(yadon_name)

        msg = proto.make_task_message(
            from_agent="yadoran",
            instruction=subtask["instruction"],
            project_dir=project_dir,
            task_id=f"{task_id}-sub{yadon_number}",
        )

        try:
            response = proto.send_message(sock_path, msg, timeout=600)
            return response
        except Exception as e:
            logger.error(f"{yadon_name} への送信失敗: {e}")
            return proto.make_result_message(
                task_id=f"{task_id}-sub{yadon_number}",
                from_agent=yadon_name,
                status="error",
                output=f"送信失敗: {e}",
                summary=f"ヤドン{yadon_number}への送信に失敗",
            )

    def handle_task(self, msg: dict) -> dict:
        """タスクメッセージを処理する。"""
        task_id = msg.get("id", "unknown")
        self.current_task_id = task_id
        payload = msg.get("payload", {})
        instruction = payload.get("instruction", "")
        project_dir = payload.get("project_dir", self.project_dir)

        logger.info(f"タスク受信: {task_id} — {instruction[:80]}")

        # タスク分解
        subtasks = self.decompose_task(instruction, project_dir)

        # ヤドンに並列配分
        results = []
        with ThreadPoolExecutor(max_workers=YADON_COUNT) as executor:
            futures = {}
            for i, subtask in enumerate(subtasks[:YADON_COUNT]):
                yadon_num = i + 1
                future = executor.submit(
                    self.dispatch_to_yadon,
                    yadon_num,
                    subtask,
                    project_dir,
                    task_id,
                )
                futures[future] = yadon_num

            for future in as_completed(futures):
                yadon_num = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"ヤドン{yadon_num} 実行エラー: {e}")
                    results.append({
                        "type": "result",
                        "from": f"yadon-{yadon_num}",
                        "status": "error",
                        "payload": {"output": str(e), "summary": "実行エラー"},
                    })

        # 結果集約
        all_success = all(r.get("status") == "success" for r in results)
        overall_status = "success" if all_success else "partial_error"

        summaries = []
        full_output_parts = []
        for r in results:
            from_agent = r.get("from", "unknown")
            status = r.get("status", "unknown")
            payload = r.get("payload", {})
            summary = payload.get("summary", "")
            output = payload.get("output", "")
            summaries.append(f"[{from_agent}] {status}: {summary}")
            full_output_parts.append(f"=== {from_agent} ({status}) ===\n{output}")

        combined_summary = "\n".join(summaries)
        combined_output = "\n\n".join(full_output_parts)

        self.current_task_id = None

        return proto.make_result_message(
            task_id=task_id,
            from_agent="yadoran",
            status=overall_status,
            output=combined_output,
            summary=combined_summary,
        )

    def handle_status(self, msg: dict) -> dict:
        """ステータス照会を処理する。"""
        # 各ヤドンのステータスも照会
        workers = {}
        for i in range(1, YADON_COUNT + 1):
            yadon_name = f"yadon-{i}"
            sock_path = proto.agent_socket_path(yadon_name)
            if os.path.exists(sock_path):
                try:
                    resp = proto.send_message(
                        sock_path,
                        proto.make_status_message("yadoran"),
                        timeout=5,
                    )
                    workers[yadon_name] = resp.get("state", "unknown")
                except Exception:
                    workers[yadon_name] = "unreachable"
            else:
                workers[yadon_name] = "stopped"

        state = "busy" if self.current_task_id else "idle"
        return {
            "type": "status_response",
            "from": self.name,
            "state": state,
            "current_task": self.current_task_id,
            "workers": workers,
            "queue_size": len(self.task_queue),
        }

    def handle_connection(self, conn: socket.socket) -> None:
        """1つの接続を処理する。"""
        try:
            conn.settimeout(600)
            msg = proto.receive_message(conn)
            msg_type = msg.get("type", "")

            if msg_type == "task":
                response = self.handle_task(msg)
            elif msg_type == "status":
                response = self.handle_status(msg)
            else:
                response = {
                    "type": "error",
                    "from": self.name,
                    "message": f"不明なメッセージタイプ: {msg_type}",
                }

            proto.send_response(conn, response)
        except json.JSONDecodeError as e:
            logger.error(f"JSONパースエラー: {e}")
            try:
                proto.send_response(conn, {
                    "type": "error",
                    "from": self.name,
                    "message": f"JSONパースエラー: {e}",
                })
            except Exception:
                pass
        except Exception as e:
            logger.error(f"接続処理エラー: {e}")
        finally:
            conn.close()

    def start(self) -> None:
        """デーモンを開始する。"""
        self.server_sock = proto.create_server_socket(self.sock_path)
        self.running = True
        logger.info(f"ヤドランデーモン起動: {self.sock_path}")

        while self.running:
            try:
                self.server_sock.settimeout(1.0)
                try:
                    conn, _ = self.server_sock.accept()
                except socket.timeout:
                    continue

                # タスクは逐次処理、ステータスは並行可能
                # 簡潔さのため逐次処理で統一
                thread = threading.Thread(
                    target=self.handle_connection,
                    args=(conn,),
                    daemon=True,
                )
                thread.start()
                thread.join()

            except OSError:
                if self.running:
                    logger.error("ソケットエラー")
                break

    def stop(self) -> None:
        """デーモンを停止する。"""
        self.running = False
        if self.server_sock:
            self.server_sock.close()
        proto.cleanup_socket(self.sock_path)
        logger.info("ヤドランデーモン停止")


def main():
    parser = argparse.ArgumentParser(description="ヤドランデーモン")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="[yadoran] %(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    daemon = YadoranDaemon()

    def signal_handler(signum, frame):
        logger.info("シグナル受信、停止中...")
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        daemon.start()
    except KeyboardInterrupt:
        daemon.stop()


if __name__ == "__main__":
    main()
