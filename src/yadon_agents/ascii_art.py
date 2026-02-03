"""ターミナル用ASCII/ANSIアート"""

from __future__ import annotations


def rgb_to_ansi256(hex_color: str) -> int:
    """RGB hex色を256色ANSIコードに変換"""
    if hex_color == "#FFFFFF":
        return 15  # 白
    if hex_color == "#000000":
        return 0   # 黒

    # #RRGGBBをRGBに分解
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)

    # 256色パレットの近似計算
    # 16-231: 6x6x6 color cube
    r_idx = round(r / 255 * 5)
    g_idx = round(g / 255 * 5)
    b_idx = round(b / 255 * 5)

    return 16 + 36 * r_idx + 6 * g_idx + b_idx


def print_yadon_sprite(pixel_data: list[list[str]] | None = None) -> None:
    """ヤドンのドット絵をターミナルに表示"""
    if pixel_data is None:
        # テーマ非依存のビルダーでスプライトを構築
        from yadon_agents.themes import get_theme, get_worker_sprite_builder

        theme = get_theme()
        builder = get_worker_sprite_builder()
        pixel_data = builder("normal", theme.worker_color_schemes)

    for row in pixel_data:
        for pixel in row:
            if pixel == "#FFFFFF":
                # 透明として扱う（背景色）
                print("  ", end="")
            else:
                # 色付きブロック（2文字幅で正方形に見える）
                ansi_code = rgb_to_ansi256(pixel)
                print(f"\033[48;5;{ansi_code}m  \033[0m", end="")
        print()  # 改行


def show_yadon_ascii() -> None:
    """起動時にヤドンを表示"""
    print()
    print_yadon_sprite()  # テーマ非依存のビルダーを内部で使用
    print()
