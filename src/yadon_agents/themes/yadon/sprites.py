"""ヤドンテーマ スプライトデータ

gui/pixel_data.py + gui/yadoran_pixel_data.py から抽出したスプライトビルダー。
"""

from __future__ import annotations


def build_worker_pixel_data(variant: str, color_schemes: dict[str, dict[str, str]]) -> list[list[str]]:
    """ヤドン 16x16 ドット絵を構築する。

    Args:
        variant: カラーバリアント名 ("normal", "shiny", "galarian", "galarian_shiny")
        color_schemes: バリアント -> 色マップ
    """
    colors = color_schemes.get(variant, color_schemes.get("normal", {}))

    pixel_data = [
        ["#FFFFFF", "#FFFFFF", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#000000", colors['head'], colors['head'], colors['head'], "#000000", "#000000", "#000000", "#000000", "#000000", colors['head'], colors['head'], colors['head'], "#000000", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#000000", colors['head'], "#000000", colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], "#000000", colors['head'], "#000000", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#000000", "#000000", colors['body'], colors['body'], colors['body'], colors['head'], colors['head'], colors['head'], colors['body'], colors['body'], colors['body'], "#000000", "#000000", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#FFFFFF", "#000000", colors['body'], "#000000", colors['body'], colors['head'], colors['head'], colors['head'], colors['body'], "#000000", colors['body'], "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#FFFFFF", "#000000", colors['body'], colors['body'], colors['body'], colors['head'], colors['head'], colors['head'], colors['body'], colors['body'], colors['body'], "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#000000", colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], "#000000", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#000000", colors['body'], colors['body'], "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", colors['body'], colors['body'], "#000000", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#FFFFFF", "#000000", colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], colors['body'], "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000", colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000", colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#FFFFFF", "#000000", colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], "#000000", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#FFFFFF", "#000000", colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], colors['head'], "#000000", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000", colors['head'], colors['head'], "#000000", "#000000", "#000000", colors['head'], colors['head'], colors['head'], "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF"],
        ["#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF"],
    ]

    if variant in ('galarian', 'galarian_shiny'):
        pixel_data[2][6] = colors['accent']
        pixel_data[2][7] = colors['accent']
        pixel_data[2][8] = colors['accent']
        pixel_data[2][9] = colors['accent']
        pixel_data[3][6] = colors['accent']
        pixel_data[3][7] = colors['accent']
        pixel_data[3][8] = colors['accent']

    return pixel_data


def build_manager_pixel_data(manager_colors: dict[str, str]) -> list[list[str]]:
    """ヤドラン 16x16 ドット絵を構築する。

    Args:
        manager_colors: {"body": ..., "head": ..., "shellder": ...}
    """
    c = manager_colors
    W = "#FFFFFF"
    K = "#000000"
    B = c['body']
    H = c['head']
    S = c['shellder']

    return [
        [W, W, K, K, K, W, W, W, W, W, K, K, K, W, W, W],
        [W, K, H, H, H, K, K, K, K, K, H, H, H, K, W, W],
        [W, K, H, K, H, H, H, H, H, H, H, K, H, K, W, W],
        [W, K, K, B, B, B, H, H, H, B, B, B, K, K, W, W],
        [W, W, K, B, K, B, H, H, H, B, K, B, K, W, W, W],
        [W, W, K, B, B, B, H, H, H, B, B, B, K, W, W, W],
        [W, K, B, B, B, B, B, B, B, B, B, B, B, K, W, W],
        [W, K, B, B, K, K, K, K, K, K, K, B, B, K, W, W],
        [W, W, K, B, B, B, B, B, B, B, B, B, K, W, W, W],
        [W, W, W, K, K, K, K, K, K, K, W, K, K, K, W, W],
        [W, W, W, K, H, H, H, H, H, K, K, S, S, K, W, W],
        [W, W, W, K, H, H, H, H, K, K, S, S, S, S, K, W],
        [W, W, K, H, H, H, H, H, K, S, S, S, S, S, K, W],
        [W, W, K, H, H, H, H, H, K, K, S, S, S, S, K, W],
        [W, W, W, K, H, H, K, K, K, K, K, S, S, K, W, W],
        [W, W, W, W, K, K, W, W, W, K, W, K, K, W, W, W],
    ]
