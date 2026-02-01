"""Pixel data builder for Yadon Desktop Pet"""

from __future__ import annotations

from yadon_agents.config.ui import COLOR_SCHEMES


def build_pixel_data(variant: str = 'normal') -> list[list[str]]:
    """Build pixel data for a specific Yadon variant"""
    colors = COLOR_SCHEMES.get(variant, COLOR_SCHEMES['normal'])

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
        ["#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000", "#000000", "#000000", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF"]
    ]

    if variant in ['galarian', 'galarian_shiny']:
        pixel_data[2][6] = colors['accent']
        pixel_data[2][7] = colors['accent']
        pixel_data[2][8] = colors['accent']
        pixel_data[2][9] = colors['accent']
        pixel_data[3][6] = colors['accent']
        pixel_data[3][7] = colors['accent']
        pixel_data[3][8] = colors['accent']

    return pixel_data
