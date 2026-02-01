"""テーマローダー

環境変数 YADON_THEME でテーマを選択し、ThemeConfig を返す。
デフォルトは "yadon" テーマ。
"""

from __future__ import annotations

import importlib
import os
from typing import Callable

from yadon_agents.domain.theme import ThemeConfig

__all__ = ["get_theme", "get_worker_sprite_builder", "get_manager_sprite_builder"]

_cached_theme: ThemeConfig | None = None


def get_theme() -> ThemeConfig:
    """現在のテーマ設定を取得する（キャッシュあり）。

    環境変数 YADON_THEME で指定されたテーマモジュールをインポートし、
    build_theme() を呼び出して ThemeConfig を返す。
    """
    global _cached_theme
    if _cached_theme is not None:
        return _cached_theme

    theme_name = os.environ.get("YADON_THEME", "yadon")
    module = importlib.import_module(f"yadon_agents.themes.{theme_name}")
    _cached_theme = module.build_theme()
    return _cached_theme


def _reset_cache() -> None:
    """テスト用: キャッシュをリセットする。"""
    global _cached_theme
    _cached_theme = None


def get_worker_sprite_builder() -> Callable[[str, dict[str, dict[str, str]]], list[list[str]]]:
    """ワーカーのスプライトビルダー関数を取得する。"""
    theme_name = os.environ.get("YADON_THEME", "yadon")
    sprites = importlib.import_module(f"yadon_agents.themes.{theme_name}.sprites")
    return sprites.build_worker_pixel_data


def get_manager_sprite_builder() -> Callable[[dict[str, str]], list[list[str]]]:
    """マネージャーのスプライトビルダー関数を取得する。"""
    theme_name = os.environ.get("YADON_THEME", "yadon")
    sprites = importlib.import_module(f"yadon_agents.themes.{theme_name}.sprites")
    return sprites.build_manager_pixel_data
