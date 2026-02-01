"""Manager ドット絵データ

テーマのスプライトビルダーに委譲する。後方互換のため同じ関数シグネチャを維持。
"""

from __future__ import annotations


def build_yadoran_pixel_data() -> list[list[str]]:
    """マネージャーのドット絵を構築する。"""
    from yadon_agents.themes import get_manager_sprite_builder, get_theme

    theme = get_theme()
    builder = get_manager_sprite_builder()
    return builder(theme.manager_colors)
