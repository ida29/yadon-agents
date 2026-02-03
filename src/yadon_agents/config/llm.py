"""LLM バックエンド設定（Claude、Gemini、Copilot、OpenCode）

LLM バックエンド（Claude CLI、Gemini CLI、Copilot CLI等）の設定を一元管理。
tier（coordinator/manager/worker）ごとのモデル指定、コマンド形式、フラグを管理。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMModelConfig:
    """LLMモデル設定（tier別：coordinator/manager/worker）"""

    coordinator: str
    """コーディネーター（ヤドキング）用モデル"""

    manager: str
    """マネージャー（ヤドラン）用モデル"""

    worker: str
    """ワーカー（ヤドン）用モデル"""


@dataclass(frozen=True)
class LLMBackendConfig:
    """LLMバックエンド設定"""

    name: str
    """バックエンド名（claude/gemini/copilot/opencode）"""

    command: str
    """CLI実行コマンド（例: claude, gemini, copilot等）"""

    models: LLMModelConfig
    """tier別モデル指定"""

    flags: dict[str, Any]
    """追加フラグ（例: use_pipe=True）"""

    batch_subcommand: str | None = None
    """バッチ実行時のサブコマンド（例: "run -q"）"""

    batch_prompt_style: str = "stdin"
    """バッチモードのプロンプト渡し方式:
    - "stdin": -p フラグ + 標準入力（claude, copilot）
    - "arg": --prompt "..." コマンドライン引数（gemini）
    - "subcommand_stdin": サブコマンド + 標準入力（opencode）
    """


# --- バックエンド設定 ---

BACKEND_CONFIGS: dict[str, LLMBackendConfig] = {
    "claude": LLMBackendConfig(
        name="claude",
        command="claude",
        models=LLMModelConfig(
            coordinator="opus",
            manager="sonnet",
            worker="haiku",
        ),
        flags={"use_pipe": True},
        batch_subcommand=None,
    ),
    "gemini": LLMBackendConfig(
        name="gemini",
        command="gemini",
        models=LLMModelConfig(
            coordinator="gemini-3.0-pro",
            manager="gemini-3.0-flash",
            worker="gemini-3.0-flash",
        ),
        flags={"use_pipe": True},
        batch_subcommand=None,
        batch_prompt_style="arg",
    ),
    "copilot": LLMBackendConfig(
        name="copilot",
        command="copilot",
        models=LLMModelConfig(
            coordinator="gpt-5.2",
            manager="gpt-5.2-mini",
            worker="gpt-5.2-mini",
        ),
        flags={"use_pipe": True},
        batch_subcommand=None,
    ),
    "opencode": LLMBackendConfig(
        name="opencode",
        command="opencode",
        models=LLMModelConfig(
            coordinator="kimi/kimi-k2.5",
            manager="kimi/kimi-k2.5",
            worker="kimi/kimi-k2.5",
        ),
        flags={"use_pipe": True},
        batch_subcommand="run -q",
        batch_prompt_style="subcommand_stdin",
    ),
    "claude-opus": LLMBackendConfig(
        name="claude-opus",
        command="claude",
        models=LLMModelConfig(
            coordinator="opus",
            manager="opus",
            worker="opus",
        ),
        flags={"use_pipe": True},
        batch_subcommand=None,
    ),
}


# --- グローバル関数 ---


def get_backend_name() -> str:
    """環境変数 LLM_BACKEND からバックエンド名を取得。

    デフォルトは "claude"。
    不正な値の場合も "claude" にフォールバック。
    """
    backend = os.environ.get("LLM_BACKEND", "claude").lower()
    if backend not in BACKEND_CONFIGS:
        return "claude"
    return backend


def get_backend_config() -> LLMBackendConfig:
    """現在のバックエンド設定を取得。

    LLM_BACKEND 環境変数で指定されたバックエンド（デフォルト: claude）の
    設定オブジェクトを返す。
    """
    backend_name = get_backend_name()
    return BACKEND_CONFIGS[backend_name]


def get_model_for_tier(tier: str) -> str:
    """指定 tier のモデル名を取得。

    Args:
        tier: "coordinator", "manager", "worker" のいずれか

    Returns:
        モデル名（例: "opus", "sonnet", "haiku"）

    Raises:
        ValueError: tier が無効な場合
    """
    config = get_backend_config()
    models = config.models

    if tier == "coordinator":
        return models.coordinator
    elif tier == "manager":
        return models.manager
    elif tier == "worker":
        return models.worker
    else:
        raise ValueError(
            f"Invalid tier: {tier!r}. Must be 'coordinator', 'manager', or 'worker'."
        )


def get_worker_backend_name(worker_number: int) -> str:
    """ワーカー（ヤドン）固有のバックエンド名を取得。

    環境変数 YADON_{N}_BACKEND からワーカー固有のバックエンド名を取得。
    未設定時は get_backend_name() にフォールバック（グローバルバックエンド設定）。

    Args:
        worker_number: ワーカー番号（1以上）

    Returns:
        バックエンド名（例: "claude", "gemini"）
    """
    env_var = f"YADON_{worker_number}_BACKEND"
    backend = os.environ.get(env_var, "").lower()

    if backend and backend in BACKEND_CONFIGS:
        return backend

    # 未設定またはフォールバック
    return get_backend_name()


def get_worker_backend_config(worker_number: int) -> LLMBackendConfig:
    """ワーカー（ヤドン）固有のバックエンド設定を取得。

    YADON_{N}_BACKEND 環境変数で指定されたバックエンド（未設定時はグローバルバックエンド）
    の設定オブジェクトを返す。

    Args:
        worker_number: ワーカー番号（1以上）

    Returns:
        LLMBackendConfig オブジェクト
    """
    backend_name = get_worker_backend_name(worker_number)
    return BACKEND_CONFIGS[backend_name]
