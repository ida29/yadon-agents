"""エージェント設定（メッセージ、モデル名、タイムアウト等）"""

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

# --- メッセージ ---

RANDOM_MESSAGES = [
    "おつかれさま　やぁん",
    "きょうは　なんようび　やぁん......?",
    "うどん　たべる　やぁん......?",
]

WELCOME_MESSAGES = [
    "おてつだい　する　やぁん",
    "がんばる　やぁん",
    "よろしく　やぁん",
    "なにか　つくる　やぁん",
    "きょうも　がんばる　やぁん",
]

YARUKI_SWITCH_ON_MESSAGE = "やるきスイッチ　ON"
YARUKI_SWITCH_OFF_MESSAGE = "やるきスイッチ　OFF"
YARUKI_MENU_ON_TEXT = "やるきスイッチ　ONにする"
YARUKI_MENU_OFF_TEXT = "やるきスイッチ　OFFにする"

YADON_MESSAGES = {
    1: ["...やるやぁん...", "...できたやぁん...", "...ん?...やぁん?"],
    2: ["...やるやぁん...", "...つかれたやぁん...", "...しっぽで釣りしたい..."],
    3: ["...やるやぁん...", "...がんばるやぁん...", "...ヤド..."],
    4: ["あー やるよお~", "あー できたあ~", "あー でもでも~"],
}

YADORAN_MESSAGES = [
    "...ヤドキングがなんか言ってる...",
    "...タスク分解...する...",
    "...ヤドンたちに...おねがい...",
    "...しっぽの...シェルダーが...かゆい...",
    "...管理って...たいへん...",
]

YADORAN_WELCOME_MESSAGES = [
    "...ヤドラン...起動した...",
    "...タスク管理...する...",
    "...しっぽが...準備できた...",
]

PHASE_LABELS = {
    "implement": "...実装する...",
    "docs": "...ドキュメント更新する...",
    "review": "...レビューする...",
}

YADON_VARIANTS = {
    1: "normal",
    2: "shiny",
    3: "galarian",
    4: "galarian_shiny",
}

YARUKI_SWITCH_MODE = False

# --- 動的ヤドン数 ---

_YADON_COUNT_DEFAULT = 4
_YADON_COUNT_MIN = 1
_YADON_COUNT_MAX = 8

_EXTRA_VARIANTS = ["normal", "shiny", "galarian", "galarian_shiny"]


def get_yadon_count() -> int:
    """環境変数 YADON_COUNT からヤドン数を取得する（デフォルト4、範囲1-8）。"""
    raw = os.environ.get("YADON_COUNT", "")
    if not raw:
        return _YADON_COUNT_DEFAULT
    try:
        n = int(raw)
    except ValueError:
        return _YADON_COUNT_DEFAULT
    return max(_YADON_COUNT_MIN, min(n, _YADON_COUNT_MAX))


def get_yadon_messages(n: int) -> list[str]:
    """ヤドンnのメッセージリストを返す。5以上はYADON_MESSAGES[1-4]からフォールバック。"""
    if n in YADON_MESSAGES:
        return YADON_MESSAGES[n]
    base = ((n - 1) % 4) + 1
    return YADON_MESSAGES[base]


def get_yadon_variant(n: int) -> str:
    """ヤドンnのバリアントを返す。5以上はローテーション。"""
    if n in YADON_VARIANTS:
        return YADON_VARIANTS[n]
    return _EXTRA_VARIANTS[(n - 1) % len(_EXTRA_VARIANTS)]
