"""GUI共通ユーティリティ"""

from yadon_agents.config.ui import DEBUG_LOG


def log_debug(component: str, message: str) -> None:
    """デバッグメッセージをログファイルに書き込む。"""
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(f"[{component}] {message}\n")
    except Exception:
        pass
