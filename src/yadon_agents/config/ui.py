"""UI設定（ピクセルサイズ、フォント、色、アニメーション等）

テーマ固有の色データ (COLOR_SCHEMES, YADORAN_COLORS) は themes/ に移動済み。
後方互換のため get_theme() 経由で動的に提供する。
"""

from __future__ import annotations

PIXEL_SIZE = 4
WINDOW_WIDTH = 16 * PIXEL_SIZE
WINDOW_HEIGHT = 16 * PIXEL_SIZE + 20

BUBBLE_MIN_WIDTH = 250
BUBBLE_PADDING = 20
BUBBLE_DISPLAY_TIME = 4000

BUBBLE_FONT_FAMILY = "Monaco"
BUBBLE_FONT_SIZE = 13
PID_FONT_FAMILY = "Arial"
PID_FONT_SIZE = 12

FACE_ANIMATION_INTERVAL = 500
FACE_ANIMATION_INTERVAL_FAST = 250

RANDOM_ACTION_MIN_INTERVAL = 3000000
RANDOM_ACTION_MAX_INTERVAL = 4200000

MOVEMENT_DURATION = 15000
TINY_MOVEMENT_RANGE = 20
SMALL_MOVEMENT_RANGE = 80
TINY_MOVEMENT_PROBABILITY = 0.95


# --- 後方互換: テーマから色データを取得 ---

COLOR_SCHEMES: dict[str, dict[str, str]]
YADORAN_COLORS: dict[str, str]


def __getattr__(name: str) -> object:
    if name in ("COLOR_SCHEMES", "YADORAN_COLORS"):
        from yadon_agents.themes import get_theme
        t = get_theme()
        if name == "COLOR_SCHEMES":
            return t.worker_color_schemes
        return t.manager_colors
    raise AttributeError(f"module 'yadon_agents.config.ui' has no attribute {name!r}")
