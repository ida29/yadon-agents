#!/usr/bin/env python3
"""
ヤドンデーモン — ワーカーエージェント

Unixソケットでタスクを受信 → claude -p --model haiku で実行 → 結果を返却。
ペットが起動していれば pet_say.sh で吹き出し表示。
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
from pathlib import Path
from typing import Optional, Tuple

# 自身のディレクトリを基準にimport
sys.path.insert(0, str(Path(__file__).parent))
import socket_protocol as proto

logger = logging.getLogger("yadon-daemon")


class YadonDaemon:
    def __init__(self, number: int):
        self.number = number
        self.name = f"yadon-{number}"
        self.sock_path = proto.agent_socket_path(self.name)
        self.server_sock = None
        self.running = False
        self.current_task_id: Optional[str] = None
        self.project_dir = str(Path(__file__).parent.parent)
        self.pet_say_script = os.path.join(self.project_dir, "scripts", "pet_say.sh")

    def pet_say(self, message: str, bubble_type: str = "normal") -> None:
        """ペットに吹き出しメッセージを送信する。"""
        if os.path.exists(self.pet_say_script):
            try:
                subprocess.run(
                    [self.pet_say_script, str(self.number), message, bubble_type],
                    timeout=5,
                    capture_output=True,
                )
            except Exception:
                pass  # ペットが起動していなくてもエラーにしない

    def run_claude(self, instruction: str, project_dir: str) -> Tuple[str, int]:
        """claude -p でタスクを実行する。

        Returns:
            (stdout, returncode)
        """
        cmd = [
            "claude",
            "-p",
            f"instructions/yadon.md を読んで従ってください。\n\nあなたはヤドン{self.number}です。\n\nタスク:\n{instruction}",
            "--model", "haiku",
            "--dangerously-skip-permissions",
        ]
        logger.info(f"claude -p 実行中: {instruction[:80]}...")
        self.pet_say(f"...やるやぁん... ({instruction[:30]}...)", "claude")

        try:
            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=600,  # 10分タイムアウト
            )
            return result.stdout + result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "タイムアウト (10分)", 1
        except Exception as e:
            return f"実行エラー: {e}", 1

    def handle_task(self, msg: dict) -> dict:
        """タスクメッセージを処理する。"""
        task_id = msg.get("id", "unknown")
        self.current_task_id = task_id
        payload = msg.get("payload", {})
        instruction = payload.get("instruction", "")
        project_dir = payload.get("project_dir", self.project_dir)

        logger.info(f"タスク受信: {task_id}")

        output, returncode = self.run_claude(instruction, project_dir)
        status = "success" if returncode == 0 else "error"

        # 結果の要約（先頭200文字）
        summary = output.strip()[:200] if output.strip() else "(出力なし)"

        self.pet_say(
            f"...できたやぁん... ({status})" if status == "success"
            else f"...失敗やぁん... ({summary[:30]})",
            "claude",
        )
        self.current_task_id = None

        return proto.make_result_message(
            task_id=task_id,
            from_agent=self.name,
            status=status,
            output=output,
            summary=summary,
        )

    def handle_status(self, msg: dict) -> dict:
        """ステータス照会を処理する。"""
        state = "busy" if self.current_task_id else "idle"
        return {
            "type": "status_response",
            "from": self.name,
            "state": state,
            "current_task": self.current_task_id,
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
        logger.info(f"{self.name} デーモン起動: {self.sock_path}")
        self.pet_say("...おはようやぁん...")

        while self.running:
            try:
                self.server_sock.settimeout(1.0)
                try:
                    conn, _ = self.server_sock.accept()
                except socket.timeout:
                    continue

                # 各接続はスレッドで処理（ステータス照会が並行して来る場合）
                # ただしタスク実行は逐次（1タスクずつ）
                thread = threading.Thread(
                    target=self.handle_connection,
                    args=(conn,),
                    daemon=True,
                )
                thread.start()
                # タスクは逐次実行のためjoin
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
        logger.info(f"{self.name} デーモン停止")
        self.pet_say("...おやすみやぁん...")


def main():
    parser = argparse.ArgumentParser(description="ヤドンデーモン")
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

    daemon = YadonDaemon(args.number)

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
