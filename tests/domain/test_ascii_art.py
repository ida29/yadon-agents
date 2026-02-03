"""ascii_art モジュールのテスト"""

import io
import sys
from unittest.mock import patch, MagicMock

from yadon_agents.ascii_art import rgb_to_ansi256, print_yadon_sprite, show_yadon_ascii


class TestRgbToAnsi256:
    """rgb_to_ansi256 関数のテスト"""

    def test_white_color(self):
        """白色（#FFFFFF）はANSIコード15を返す"""
        assert rgb_to_ansi256("#FFFFFF") == 15

    def test_black_color(self):
        """黒色（#000000）はANSIコード0を返す"""
        assert rgb_to_ansi256("#000000") == 0

    def test_primary_colors(self):
        """基本色（赤、緑、青）の変換"""
        # 赤系色の範囲チェック
        red = rgb_to_ansi256("#FF0000")
        assert 16 <= red <= 231  # color cube 内

        # 緑系色の範囲チェック
        green = rgb_to_ansi256("#00FF00")
        assert 16 <= green <= 231

        # 青系色の範囲チェック
        blue = rgb_to_ansi256("#0000FF")
        assert 16 <= blue <= 231

    def test_gray_color(self):
        """グレースケール色（#808080）は256色キューブ内"""
        gray = rgb_to_ansi256("#808080")
        assert 16 <= gray <= 231

    def test_ansi_code_range(self):
        """全ての hex 色は有効な ANSI コード（0-255）を返す"""
        # サンプルカラー
        colors = [
            "#FF0000",  # 赤
            "#00FF00",  # 緑
            "#0000FF",  # 青
            "#FFFF00",  # 黄
            "#FF00FF",  # マゼンタ
            "#00FFFF",  # シアン
            "#AABBCC",  # グレーっぽい
        ]
        for color in colors:
            code = rgb_to_ansi256(color)
            assert 0 <= code <= 255, f"Color {color} produced invalid code {code}"


class TestPrintYadonSprite:
    """print_yadon_sprite 関数のテスト"""

    def test_print_with_custom_pixel_data(self):
        """カスタムピクセルデータで出力"""
        pixel_data = [
            ["#FF0000", "#FFFFFF"],  # 赤と白
            ["#00FF00", "#0000FF"],  # 緑と青
        ]

        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            print_yadon_sprite(pixel_data)

        output = captured_output.getvalue()
        # 各行は2行で、各行は複数の ESC シーケンス出力を含む
        lines = output.split("\n")
        # 最後の空行を除いて2行
        assert len(lines) >= 2

    def test_print_with_white_pixels_as_transparent(self):
        """白ピクセル（#FFFFFF）は空白として描画される"""
        pixel_data = [
            ["#FFFFFF", "#FFFFFF"],  # 全て白
        ]

        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            print_yadon_sprite(pixel_data)

        output = captured_output.getvalue()
        # 白は ESC シーケンスなしで 2 文字スペースが出力される
        # つまり "  " (スペース2個) が含まれるはず
        assert "  " in output or output.strip() == ""

    def test_print_uses_theme_when_no_data(self):
        """pixel_data が None のときはテーマから取得"""
        with patch("yadon_agents.themes.get_theme") as mock_get_theme, \
             patch("yadon_agents.themes.get_worker_sprite_builder") as mock_builder:
            mock_theme = MagicMock()
            mock_theme.worker_color_schemes = {}
            mock_get_theme.return_value = mock_theme

            mock_sprite_builder = MagicMock(return_value=[["#FF0000"]])
            mock_builder.return_value = mock_sprite_builder

            captured_output = io.StringIO()
            with patch("sys.stdout", captured_output):
                print_yadon_sprite(None)

            # builder が呼び出されたことを確認
            mock_sprite_builder.assert_called_once_with("normal", {})


class TestShowYadonAscii:
    """show_yadon_ascii 関数のテスト"""

    def test_show_yadon_ascii_calls_print_sprite(self):
        """show_yadon_ascii は print_yadon_sprite を呼び出す"""
        with patch("yadon_agents.ascii_art.print_yadon_sprite") as mock_print:
            show_yadon_ascii()
            mock_print.assert_called_once()

    def test_show_yadon_ascii_output_has_newlines(self):
        """show_yadon_ascii は改行を含む"""
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output), \
             patch("yadon_agents.themes.get_theme") as mock_get_theme, \
             patch("yadon_agents.themes.get_worker_sprite_builder") as mock_builder:
            mock_theme = MagicMock()
            mock_theme.worker_color_schemes = {}
            mock_get_theme.return_value = mock_theme
            mock_sprite_builder = MagicMock(return_value=[["#FF0000"]])
            mock_builder.return_value = mock_sprite_builder

            show_yadon_ascii()

        output = captured_output.getvalue()
        # 前後に空行（改行）が入るはず
        assert output.startswith("\n")
        assert output.strip() != ""
