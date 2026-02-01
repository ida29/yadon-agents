"""Pixel data builder for worker Desktop Pet

テーマのスプライトビルダーに委譲する。後方互換のため同じ関数シグネチャを維持。
"""

from __future__ import annotations


def build_pixel_data(variant: str = 'normal') -> list[list[str]]:
    """Build pixel data for a specific worker variant"""
    from yadon_agents.themes import get_theme, get_worker_sprite_builder

    theme = get_theme()
    builder = get_worker_sprite_builder()
    return builder(variant, theme.worker_color_schemes)
