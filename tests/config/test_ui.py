"""config/ui.py のテスト

ピクセルサイズ定数、フォント設定、色定数、
アニメーション設定の検証テスト。
"""

from __future__ import annotations

import pytest

from yadon_agents.config import ui


class TestPixelSizeConstants:
    """ピクセルサイズ定数のテスト"""

    def test_pixel_size_is_positive(self) -> None:
        """PIXEL_SIZE が正の整数であること"""
        assert isinstance(ui.PIXEL_SIZE, int)
        assert ui.PIXEL_SIZE > 0

    def test_pixel_size_default_value(self) -> None:
        """PIXEL_SIZE のデフォルト値が 4 であること"""
        assert ui.PIXEL_SIZE == 4

    def test_window_width_calculated_correctly(self) -> None:
        """WINDOW_WIDTH が PIXEL_SIZE から正しく計算されること"""
        expected = 16 * ui.PIXEL_SIZE
        assert ui.WINDOW_WIDTH == expected

    def test_window_height_calculated_correctly(self) -> None:
        """WINDOW_HEIGHT が PIXEL_SIZE から正しく計算されること"""
        expected = 16 * ui.PIXEL_SIZE + 20
        assert ui.WINDOW_HEIGHT == expected

    def test_window_dimensions_positive(self) -> None:
        """ウィンドウサイズが正の値であること"""
        assert ui.WINDOW_WIDTH > 0
        assert ui.WINDOW_HEIGHT > 0

    def test_window_width_is_multiple_of_pixel_size(self) -> None:
        """WINDOW_WIDTH が PIXEL_SIZE の倍数であること（16倍）"""
        assert ui.WINDOW_WIDTH % ui.PIXEL_SIZE == 0
        assert ui.WINDOW_WIDTH // ui.PIXEL_SIZE == 16


class TestBubbleConstants:
    """吹き出し関連定数のテスト"""

    def test_bubble_min_width_is_positive(self) -> None:
        """BUBBLE_MIN_WIDTH が正の整数であること"""
        assert isinstance(ui.BUBBLE_MIN_WIDTH, int)
        assert ui.BUBBLE_MIN_WIDTH > 0

    def test_bubble_min_width_default_value(self) -> None:
        """BUBBLE_MIN_WIDTH のデフォルト値が 250 であること"""
        assert ui.BUBBLE_MIN_WIDTH == 250

    def test_bubble_padding_is_positive(self) -> None:
        """BUBBLE_PADDING が正の整数であること"""
        assert isinstance(ui.BUBBLE_PADDING, int)
        assert ui.BUBBLE_PADDING > 0

    def test_bubble_padding_default_value(self) -> None:
        """BUBBLE_PADDING のデフォルト値が 20 であること"""
        assert ui.BUBBLE_PADDING == 20

    def test_bubble_display_time_is_positive(self) -> None:
        """BUBBLE_DISPLAY_TIME が正のミリ秒値であること"""
        assert isinstance(ui.BUBBLE_DISPLAY_TIME, int)
        assert ui.BUBBLE_DISPLAY_TIME > 0

    def test_bubble_display_time_default_value(self) -> None:
        """BUBBLE_DISPLAY_TIME のデフォルト値が 4000ms であること"""
        assert ui.BUBBLE_DISPLAY_TIME == 4000

    def test_bubble_display_time_reasonable_range(self) -> None:
        """BUBBLE_DISPLAY_TIME が妥当な範囲内（1-30秒）であること"""
        assert 1000 <= ui.BUBBLE_DISPLAY_TIME <= 30000


class TestFontSettings:
    """フォント設定のテスト"""

    def test_bubble_font_family_is_string(self) -> None:
        """BUBBLE_FONT_FAMILY が文字列であること"""
        assert isinstance(ui.BUBBLE_FONT_FAMILY, str)
        assert len(ui.BUBBLE_FONT_FAMILY) > 0

    def test_bubble_font_family_default_value(self) -> None:
        """BUBBLE_FONT_FAMILY のデフォルト値が 'Monaco' であること"""
        assert ui.BUBBLE_FONT_FAMILY == "Monaco"

    def test_bubble_font_size_is_positive(self) -> None:
        """BUBBLE_FONT_SIZE が正の整数であること"""
        assert isinstance(ui.BUBBLE_FONT_SIZE, int)
        assert ui.BUBBLE_FONT_SIZE > 0

    def test_bubble_font_size_default_value(self) -> None:
        """BUBBLE_FONT_SIZE のデフォルト値が 13 であること"""
        assert ui.BUBBLE_FONT_SIZE == 13

    def test_bubble_font_size_reasonable_range(self) -> None:
        """BUBBLE_FONT_SIZE が妥当な範囲内（8-48pt）であること"""
        assert 8 <= ui.BUBBLE_FONT_SIZE <= 48

    def test_pid_font_family_is_string(self) -> None:
        """PID_FONT_FAMILY が文字列であること"""
        assert isinstance(ui.PID_FONT_FAMILY, str)
        assert len(ui.PID_FONT_FAMILY) > 0

    def test_pid_font_family_default_value(self) -> None:
        """PID_FONT_FAMILY のデフォルト値が 'Arial' であること"""
        assert ui.PID_FONT_FAMILY == "Arial"

    def test_pid_font_size_is_positive(self) -> None:
        """PID_FONT_SIZE が正の整数であること"""
        assert isinstance(ui.PID_FONT_SIZE, int)
        assert ui.PID_FONT_SIZE > 0

    def test_pid_font_size_default_value(self) -> None:
        """PID_FONT_SIZE のデフォルト値が 12 であること"""
        assert ui.PID_FONT_SIZE == 12


class TestFaceAnimationSettings:
    """顔アニメーション設定のテスト"""

    def test_face_animation_interval_is_positive(self) -> None:
        """FACE_ANIMATION_INTERVAL が正のミリ秒値であること"""
        assert isinstance(ui.FACE_ANIMATION_INTERVAL, int)
        assert ui.FACE_ANIMATION_INTERVAL > 0

    def test_face_animation_interval_default_value(self) -> None:
        """FACE_ANIMATION_INTERVAL のデフォルト値が 500ms であること"""
        assert ui.FACE_ANIMATION_INTERVAL == 500

    def test_face_animation_interval_fast_is_positive(self) -> None:
        """FACE_ANIMATION_INTERVAL_FAST が正のミリ秒値であること"""
        assert isinstance(ui.FACE_ANIMATION_INTERVAL_FAST, int)
        assert ui.FACE_ANIMATION_INTERVAL_FAST > 0

    def test_face_animation_interval_fast_default_value(self) -> None:
        """FACE_ANIMATION_INTERVAL_FAST のデフォルト値が 250ms であること"""
        assert ui.FACE_ANIMATION_INTERVAL_FAST == 250

    def test_fast_animation_is_faster_than_normal(self) -> None:
        """FAST アニメーションが通常より速いこと"""
        assert ui.FACE_ANIMATION_INTERVAL_FAST < ui.FACE_ANIMATION_INTERVAL


class TestRandomActionSettings:
    """ランダムアクション設定のテスト"""

    def test_random_action_min_interval_is_positive(self) -> None:
        """RANDOM_ACTION_MIN_INTERVAL が正のミリ秒値であること"""
        assert isinstance(ui.RANDOM_ACTION_MIN_INTERVAL, int)
        assert ui.RANDOM_ACTION_MIN_INTERVAL > 0

    def test_random_action_min_interval_default_value(self) -> None:
        """RANDOM_ACTION_MIN_INTERVAL のデフォルト値が 3000000ms であること"""
        assert ui.RANDOM_ACTION_MIN_INTERVAL == 3000000

    def test_random_action_max_interval_is_positive(self) -> None:
        """RANDOM_ACTION_MAX_INTERVAL が正のミリ秒値であること"""
        assert isinstance(ui.RANDOM_ACTION_MAX_INTERVAL, int)
        assert ui.RANDOM_ACTION_MAX_INTERVAL > 0

    def test_random_action_max_interval_default_value(self) -> None:
        """RANDOM_ACTION_MAX_INTERVAL のデフォルト値が 4200000ms であること"""
        assert ui.RANDOM_ACTION_MAX_INTERVAL == 4200000

    def test_max_interval_greater_than_min(self) -> None:
        """MAX_INTERVAL が MIN_INTERVAL より大きいこと"""
        assert ui.RANDOM_ACTION_MAX_INTERVAL > ui.RANDOM_ACTION_MIN_INTERVAL


class TestMovementSettings:
    """移動設定のテスト"""

    def test_movement_duration_is_positive(self) -> None:
        """MOVEMENT_DURATION が正のミリ秒値であること"""
        assert isinstance(ui.MOVEMENT_DURATION, int)
        assert ui.MOVEMENT_DURATION > 0

    def test_movement_duration_default_value(self) -> None:
        """MOVEMENT_DURATION のデフォルト値が 15000ms であること"""
        assert ui.MOVEMENT_DURATION == 15000

    def test_tiny_movement_range_is_positive(self) -> None:
        """TINY_MOVEMENT_RANGE が正のピクセル値であること"""
        assert isinstance(ui.TINY_MOVEMENT_RANGE, int)
        assert ui.TINY_MOVEMENT_RANGE > 0

    def test_tiny_movement_range_default_value(self) -> None:
        """TINY_MOVEMENT_RANGE のデフォルト値が 20 であること"""
        assert ui.TINY_MOVEMENT_RANGE == 20

    def test_small_movement_range_is_positive(self) -> None:
        """SMALL_MOVEMENT_RANGE が正のピクセル値であること"""
        assert isinstance(ui.SMALL_MOVEMENT_RANGE, int)
        assert ui.SMALL_MOVEMENT_RANGE > 0

    def test_small_movement_range_default_value(self) -> None:
        """SMALL_MOVEMENT_RANGE のデフォルト値が 80 であること"""
        assert ui.SMALL_MOVEMENT_RANGE == 80

    def test_small_movement_greater_than_tiny(self) -> None:
        """SMALL_MOVEMENT_RANGE が TINY_MOVEMENT_RANGE より大きいこと"""
        assert ui.SMALL_MOVEMENT_RANGE > ui.TINY_MOVEMENT_RANGE

    def test_tiny_movement_probability_is_float(self) -> None:
        """TINY_MOVEMENT_PROBABILITY が浮動小数点数であること"""
        assert isinstance(ui.TINY_MOVEMENT_PROBABILITY, float)

    def test_tiny_movement_probability_default_value(self) -> None:
        """TINY_MOVEMENT_PROBABILITY のデフォルト値が 0.95 であること"""
        assert ui.TINY_MOVEMENT_PROBABILITY == 0.95

    def test_tiny_movement_probability_valid_range(self) -> None:
        """TINY_MOVEMENT_PROBABILITY が 0.0-1.0 の範囲内であること"""
        assert 0.0 <= ui.TINY_MOVEMENT_PROBABILITY <= 1.0


class TestBackwardCompatibility:
    """後方互換性のテスト（テーマからの動的取得）"""

    def test_color_schemes_accessible(self) -> None:
        """COLOR_SCHEMES がテーマ経由でアクセス可能であること"""
        # __getattr__ 経由でアクセス
        color_schemes = ui.COLOR_SCHEMES
        assert isinstance(color_schemes, dict)

    def test_yadoran_colors_accessible(self) -> None:
        """YADORAN_COLORS がテーマ経由でアクセス可能であること"""
        yadoran_colors = ui.YADORAN_COLORS
        assert isinstance(yadoran_colors, dict)

    def test_color_schemes_has_required_keys(self) -> None:
        """COLOR_SCHEMES に必要なキーが存在すること"""
        color_schemes = ui.COLOR_SCHEMES
        # テーマによって異なるが、少なくとも1つ以上のキーがあること
        assert len(color_schemes) > 0

    def test_yadoran_colors_has_required_keys(self) -> None:
        """YADORAN_COLORS に必要なキーが存在すること"""
        yadoran_colors = ui.YADORAN_COLORS
        # テーマによって異なるが、少なくとも1つ以上のキーがあること
        assert len(yadoran_colors) > 0

    def test_undefined_attribute_raises_error(self) -> None:
        """定義されていない属性へのアクセスで AttributeError が発生すること"""
        with pytest.raises(AttributeError):
            _ = ui.UNDEFINED_CONSTANT  # type: ignore[attr-defined]


class TestConstantTypes:
    """定数の型検証"""

    def test_all_interval_constants_are_int(self) -> None:
        """全ての間隔定数が整数であること"""
        intervals = [
            ui.FACE_ANIMATION_INTERVAL,
            ui.FACE_ANIMATION_INTERVAL_FAST,
            ui.RANDOM_ACTION_MIN_INTERVAL,
            ui.RANDOM_ACTION_MAX_INTERVAL,
            ui.MOVEMENT_DURATION,
            ui.BUBBLE_DISPLAY_TIME,
        ]
        for interval in intervals:
            assert isinstance(interval, int), f"{interval} is not int"

    def test_all_size_constants_are_int(self) -> None:
        """全てのサイズ定数が整数であること"""
        sizes = [
            ui.PIXEL_SIZE,
            ui.WINDOW_WIDTH,
            ui.WINDOW_HEIGHT,
            ui.BUBBLE_MIN_WIDTH,
            ui.BUBBLE_PADDING,
            ui.TINY_MOVEMENT_RANGE,
            ui.SMALL_MOVEMENT_RANGE,
        ]
        for size in sizes:
            assert isinstance(size, int), f"{size} is not int"

    def test_all_font_sizes_are_int(self) -> None:
        """全てのフォントサイズ定数が整数であること"""
        font_sizes = [
            ui.BUBBLE_FONT_SIZE,
            ui.PID_FONT_SIZE,
        ]
        for size in font_sizes:
            assert isinstance(size, int), f"{size} is not int"

    def test_all_font_families_are_str(self) -> None:
        """全てのフォントファミリー定数が文字列であること"""
        font_families = [
            ui.BUBBLE_FONT_FAMILY,
            ui.PID_FONT_FAMILY,
        ]
        for family in font_families:
            assert isinstance(family, str), f"{family} is not str"


class TestConstantRelationships:
    """定数間の関係性テスト"""

    def test_window_height_greater_than_width(self) -> None:
        """WINDOW_HEIGHT が WINDOW_WIDTH より大きいこと（縦長）"""
        # 16x16 + 20 なので HEIGHT > WIDTH
        assert ui.WINDOW_HEIGHT > ui.WINDOW_WIDTH

    def test_bubble_min_width_greater_than_window_width(self) -> None:
        """BUBBLE_MIN_WIDTH が WINDOW_WIDTH より大きいこと"""
        # 吹き出しはペットより大きい
        assert ui.BUBBLE_MIN_WIDTH > ui.WINDOW_WIDTH

    def test_animation_intervals_reasonable(self) -> None:
        """アニメーション間隔が妥当であること"""
        # 通常アニメーション: 100ms - 2000ms
        assert 100 <= ui.FACE_ANIMATION_INTERVAL <= 2000
        # 高速アニメーション: 50ms - 1000ms
        assert 50 <= ui.FACE_ANIMATION_INTERVAL_FAST <= 1000

    def test_movement_ranges_reasonable(self) -> None:
        """移動範囲が妥当であること"""
        # TINY: 1 - 100px
        assert 1 <= ui.TINY_MOVEMENT_RANGE <= 100
        # SMALL: 10 - 500px
        assert 10 <= ui.SMALL_MOVEMENT_RANGE <= 500
