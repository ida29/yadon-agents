"""エージェント設定（タイムアウト、ソケット、出力制限等）

テーマ固有データ（メッセージ、バリアント、フェーズラベル等）は
themes/ に移動済み。後方互換のため get_theme() 経由のラッパーを維持。
"""

from __future__ import annotations

import os

# --- タイムアウト (秒) ---
CLAUDE_DEFAULT_TIMEOUT = 600
CLAUDE_DECOMPOSE_TIMEOUT = 120
SOCKET_SEND_TIMEOUT = 300.0
SOCKET_DISPATCH_TIMEOUT = 600
SOCKET_STATUS_TIMEOUT = 5
SOCKET_CONNECTION_TIMEOUT = 600
SOCKET_ACCEPT_TIMEOUT = 1.0

# --- ソケット設定 ---
SOCKET_LISTEN_BACKLOG = 5
SOCKET_RECV_BUFFER = 65536
PET_SOCKET_RECV_BUFFER = 4096
PET_SOCKET_MAX_MESSAGE = 65536

# --- CLI設定 ---
PROCESS_STOP_RETRIES = 20
PROCESS_STOP_INTERVAL = 0.5
SOCKET_WAIT_TIMEOUT = 15
SOCKET_WAIT_INTERVAL = 0.5

# --- 出力制限 ---
SUMMARY_MAX_LENGTH = 200
BUBBLE_TASK_MAX_LENGTH = 80
BUBBLE_RESULT_MAX_LENGTH = 60


# --- 後方互換ラッパー (get_theme() 経由) ---


def _theme():
    from yadon_agents.themes import get_theme
    return get_theme()


def get_yadon_count() -> int:
    """環境変数 YADON_COUNT からワーカー数を取得する。"""
    wc = _theme().worker_count
    raw = os.environ.get("YADON_COUNT", "")
    if not raw:
        return wc.default
    try:
        n = int(raw)
    except ValueError:
        return wc.default
    return max(wc.min, min(n, wc.max))


def get_yadon_messages(n: int) -> list[str]:
    """ワーカーnのメッセージリストを返す。

    新形式では worker_messages[n] は dict[str, list[str]] なので、
    全メッセージタイプを結合して返す。
    """
    t = _theme()
    if n in t.worker_messages:
        msgs_dict = t.worker_messages[n]
        # dict か list かを判定して対応
        if isinstance(msgs_dict, dict):
            # 新形式: task, success, error, random を結合
            result = []
            for key in ["task", "success", "error", "random"]:
                result.extend(msgs_dict.get(key, []))
            return result
        else:
            # 後方互換: 古い形式（リスト）をそのまま返す
            return msgs_dict
    base_count = len(t.worker_messages)
    if base_count == 0:
        return []
    base = ((n - 1) % base_count) + 1
    fallback = t.worker_messages.get(base, [])
    if isinstance(fallback, dict):
        # 新形式のフォールバック
        result = []
        for key in ["task", "success", "error", "random"]:
            result.extend(fallback.get(key, []))
        return result
    else:
        # 後方互換
        return fallback


def get_yadon_variant(n: int) -> str:
    """ワーカーnのバリアントを返す。"""
    t = _theme()
    if n in t.worker_variants:
        return t.worker_variants[n]
    if not t.extra_variants:
        return "normal"
    return t.extra_variants[(n - 1) % len(t.extra_variants)]


# --- 後方互換プロパティ ---
# 既存コードが直接参照している定数。get_theme() 経由で動的に取得する。


class _ThemeProxy:
    """テーマデータへの後方互換アクセスを提供するプロキシ。

    モジュールレベル定数として使えるようにするため、__getattr__ ではなく
    明示的なプロパティで提供する。
    """

    def __getattr__(self, name: str) -> object:
        t = _theme()
        mapping = {
            "RANDOM_MESSAGES": t.random_messages,
            "WELCOME_MESSAGES": t.welcome_messages,
            "YARUKI_SWITCH_ON_MESSAGE": t.yaruki_switch.on_message,
            "YARUKI_SWITCH_OFF_MESSAGE": t.yaruki_switch.off_message,
            "YARUKI_MENU_ON_TEXT": t.yaruki_switch.menu_on_text,
            "YARUKI_MENU_OFF_TEXT": t.yaruki_switch.menu_off_text,
            "YADON_MESSAGES": t.worker_messages,
            "YADORAN_MESSAGES": t.manager_messages,
            "YADORAN_WELCOME_MESSAGES": t.manager_welcome_messages,
            "PHASE_LABELS": t.phase_labels,
            "YADON_VARIANTS": t.worker_variants,
            "YARUKI_SWITCH_MODE": t.yaruki_switch.enabled,
        }
        if name in mapping:
            return mapping[name]
        raise AttributeError(f"module 'yadon_agents.config.agent' has no attribute {name!r}")


_proxy = _ThemeProxy()

# 後方互換: 既存importは引き続き動作する
RANDOM_MESSAGES: list[str]
WELCOME_MESSAGES: list[str]
YARUKI_SWITCH_ON_MESSAGE: str
YARUKI_SWITCH_OFF_MESSAGE: str
YARUKI_MENU_ON_TEXT: str
YARUKI_MENU_OFF_TEXT: str
YADON_MESSAGES: dict[int, dict[str, list[str]]]
YADORAN_MESSAGES: list[str]
YADORAN_WELCOME_MESSAGES: list[str]
PHASE_LABELS: dict[str, str]
YADON_VARIANTS: dict[int, str]
YARUKI_SWITCH_MODE: bool


def __getattr__(name: str) -> object:
    return getattr(_proxy, name)
