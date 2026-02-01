"""プロセス管理 — ログディレクトリ"""

from __future__ import annotations

from pathlib import Path

from yadon_agents import PROJECT_ROOT

__all__ = ["log_dir"]


def log_dir() -> Path:
    """ログファイルディレクトリを返す（なければ作成）。"""
    d = PROJECT_ROOT / "logs"
    d.mkdir(exist_ok=True)
    return d
