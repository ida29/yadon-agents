"""テーマ層のテスト

themes/ パッケージのテスト:
- テーマのロード・キャッシュ動作
- get_theme() の戻り値検証
- 各バリアント（normal, shiny, galarian, galarian_shiny）のスプライト取得
- テーマメッセージの取得
- 不正なテーマ名のハンドリング
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from yadon_agents.domain.theme import ThemeConfig


class TestThemeLoading:
    """テーマローディング機能のテスト"""

    def setup_method(self) -> None:
        """各テストの前にキャッシュをリセット"""
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def teardown_method(self) -> None:
        """各テストの後にキャッシュをリセット"""
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def test_get_theme_returns_theme_config(self) -> None:
        """get_theme() が ThemeConfig を返すことを確認"""
        from yadon_agents.domain.theme import ThemeConfig
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert isinstance(theme, ThemeConfig)

    def test_get_theme_default_is_yadon(self) -> None:
        """デフォルトテーマが yadon であることを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert theme.name == "yadon"
        assert theme.display_name == "ヤドン・エージェント"

    def test_get_theme_returns_cached_instance(self) -> None:
        """get_theme() がキャッシュされたインスタンスを返すことを確認"""
        from yadon_agents.themes import get_theme

        theme1 = get_theme()
        theme2 = get_theme()
        assert theme1 is theme2

    def test_get_theme_cache_reset_clears_cache(self) -> None:
        """_reset_cache() でキャッシュがクリアされることを確認"""
        from yadon_agents.themes import _reset_cache, get_theme

        theme1 = get_theme()
        _reset_cache()
        theme2 = get_theme()

        # 同じ値だが異なるインスタンス
        assert theme1.name == theme2.name
        assert theme1 is not theme2

    def test_get_theme_invalid_theme_raises_module_not_found(self) -> None:
        """不正なテーマ名で ModuleNotFoundError が発生することを確認"""
        from yadon_agents.themes import get_theme

        os.environ["YADON_THEME"] = "nonexistent_theme_12345"
        with pytest.raises(ModuleNotFoundError):
            get_theme()


class TestThemeConfigValues:
    """ThemeConfig の値検証テスト"""

    def setup_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def teardown_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def test_theme_socket_prefix(self) -> None:
        """ソケットプレフィックスが正しいことを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert theme.socket_prefix == "yadon"

    def test_theme_role_names(self) -> None:
        """役割名が正しいことを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert theme.role_names.coordinator == "ヤドキング"
        assert theme.role_names.manager == "ヤドラン"
        assert theme.role_names.worker == "ヤドン"

    def test_theme_worker_count_config(self) -> None:
        """ワーカー数設定が正しいことを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert theme.worker_count.default == 4
        assert theme.worker_count.min == 1
        assert theme.worker_count.max == 8

    def test_theme_phase_labels(self) -> None:
        """フェーズラベルが正しいことを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert "implement" in theme.phase_labels
        assert "docs" in theme.phase_labels
        assert "review" in theme.phase_labels
        assert theme.phase_labels["implement"] == "実装する"

    def test_theme_agent_roles(self) -> None:
        """エージェントロールが正しいことを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert theme.agent_role_coordinator == "yadoking"
        assert theme.agent_role_manager == "yadoran"
        assert theme.agent_role_worker == "yadon"


class TestWorkerVariants:
    """ワーカーバリアント（色違い等）のテスト"""

    def setup_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def teardown_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def test_worker_variants_mapping(self) -> None:
        """ワーカー番号とバリアントのマッピングを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert theme.worker_variants[1] == "normal"
        assert theme.worker_variants[2] == "shiny"
        assert theme.worker_variants[3] == "galarian"
        assert theme.worker_variants[4] == "galarian_shiny"

    def test_extra_variants_list(self) -> None:
        """extra_variants リストが全バリアントを含むことを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        expected_variants = ["normal", "shiny", "galarian", "galarian_shiny"]
        assert theme.extra_variants == expected_variants

    def test_color_schemes_for_all_variants(self) -> None:
        """全バリアントのカラースキームが存在することを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        for variant in ["normal", "shiny", "galarian", "galarian_shiny"]:
            assert variant in theme.worker_color_schemes
            scheme = theme.worker_color_schemes[variant]
            assert "body" in scheme
            assert "head" in scheme
            assert "accent" in scheme

    def test_normal_variant_colors(self) -> None:
        """ノーマルバリアントの色を確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        normal = theme.worker_color_schemes["normal"]
        assert normal["body"] == "#F3D599"
        assert normal["head"] == "#D32A38"

    def test_shiny_variant_colors(self) -> None:
        """色違いバリアントの色を確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        shiny = theme.worker_color_schemes["shiny"]
        assert shiny["body"] == "#FFCCFF"
        assert shiny["head"] == "#FF99CC"


class TestThemeMessages:
    """テーマメッセージ取得のテスト"""

    def setup_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def teardown_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def test_worker_messages_exist_for_workers_1_to_4(self) -> None:
        """ワーカー1〜4のメッセージが存在することを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        for worker_num in [1, 2, 3, 4]:
            assert worker_num in theme.worker_messages
            msgs = theme.worker_messages[worker_num]
            assert "task" in msgs
            assert "success" in msgs
            assert "error" in msgs
            assert "random" in msgs

    def test_worker_messages_are_non_empty(self) -> None:
        """ワーカーメッセージが空でないことを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        for worker_num in [1, 2, 3, 4]:
            msgs = theme.worker_messages[worker_num]
            for category in ["task", "success", "error", "random"]:
                assert len(msgs[category]) > 0, f"Worker {worker_num} {category} messages are empty"

    def test_manager_messages_exist(self) -> None:
        """マネージャーメッセージが存在することを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert len(theme.manager_messages) > 0
        assert len(theme.manager_phase_messages) > 0
        assert len(theme.manager_success_messages) > 0
        assert len(theme.manager_error_messages) > 0

    def test_welcome_messages_exist(self) -> None:
        """ウェルカムメッセージが存在することを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert len(theme.welcome_messages) > 0
        assert len(theme.manager_welcome_messages) > 0

    def test_random_messages_exist(self) -> None:
        """ランダムメッセージが存在することを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert len(theme.random_messages) > 0


class TestSpriteBuilders:
    """スプライトビルダー関数のテスト"""

    def setup_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def teardown_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def test_get_worker_sprite_builder_returns_callable(self) -> None:
        """get_worker_sprite_builder が callable を返すことを確認"""
        from yadon_agents.themes import get_worker_sprite_builder

        builder = get_worker_sprite_builder()
        assert callable(builder)

    def test_get_manager_sprite_builder_returns_callable(self) -> None:
        """get_manager_sprite_builder が callable を返すことを確認"""
        from yadon_agents.themes import get_manager_sprite_builder

        builder = get_manager_sprite_builder()
        assert callable(builder)

    def test_worker_sprite_builder_produces_16x16_grid(self) -> None:
        """ワーカースプライトビルダーが 16x16 のグリッドを生成することを確認"""
        from yadon_agents.themes import get_theme, get_worker_sprite_builder

        theme = get_theme()
        builder = get_worker_sprite_builder()
        pixels = builder("normal", theme.worker_color_schemes)

        assert len(pixels) == 16, "Expected 16 rows"
        for i, row in enumerate(pixels):
            assert len(row) == 16, f"Row {i} should have 16 columns"

    def test_worker_sprite_builder_all_variants(self) -> None:
        """全バリアントでスプライトビルダーが動作することを確認"""
        from yadon_agents.themes import get_theme, get_worker_sprite_builder

        theme = get_theme()
        builder = get_worker_sprite_builder()

        for variant in ["normal", "shiny", "galarian", "galarian_shiny"]:
            pixels = builder(variant, theme.worker_color_schemes)
            assert len(pixels) == 16
            assert all(len(row) == 16 for row in pixels)

    def test_manager_sprite_builder_produces_16x16_grid(self) -> None:
        """マネージャースプライトビルダーが 16x16 のグリッドを生成することを確認"""
        from yadon_agents.themes import get_theme, get_manager_sprite_builder

        theme = get_theme()
        builder = get_manager_sprite_builder()
        pixels = builder(theme.manager_colors)

        assert len(pixels) == 16, "Expected 16 rows"
        for i, row in enumerate(pixels):
            assert len(row) == 16, f"Row {i} should have 16 columns"

    def test_worker_sprite_contains_body_color(self) -> None:
        """ワーカースプライトがボディカラーを含むことを確認"""
        from yadon_agents.themes import get_theme, get_worker_sprite_builder

        theme = get_theme()
        builder = get_worker_sprite_builder()
        pixels = builder("normal", theme.worker_color_schemes)

        body_color = theme.worker_color_schemes["normal"]["body"]
        flat_pixels = [c for row in pixels for c in row]
        assert body_color in flat_pixels

    def test_manager_sprite_contains_shellder_color(self) -> None:
        """マネージャースプライトがシェルダーカラーを含むことを確認"""
        from yadon_agents.themes import get_theme, get_manager_sprite_builder

        theme = get_theme()
        builder = get_manager_sprite_builder()
        pixels = builder(theme.manager_colors)

        shellder_color = theme.manager_colors["shellder"]
        flat_pixels = [c for row in pixels for c in row]
        assert shellder_color in flat_pixels

    def test_different_variants_produce_different_sprites(self) -> None:
        """異なるバリアントが異なるスプライトを生成することを確認"""
        from yadon_agents.themes import get_theme, get_worker_sprite_builder

        theme = get_theme()
        builder = get_worker_sprite_builder()

        normal_pixels = builder("normal", theme.worker_color_schemes)
        shiny_pixels = builder("shiny", theme.worker_color_schemes)

        # フラット化して比較
        normal_flat = [c for row in normal_pixels for c in row]
        shiny_flat = [c for row in shiny_pixels for c in row]

        assert normal_flat != shiny_flat


class TestYarukiSwitchConfig:
    """やるきスイッチ設定のテスト"""

    def setup_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def teardown_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def test_yaruki_switch_default_disabled(self) -> None:
        """やるきスイッチがデフォルトで無効であることを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert theme.yaruki_switch.enabled is False

    def test_yaruki_switch_messages(self) -> None:
        """やるきスイッチのメッセージが設定されていることを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert theme.yaruki_switch.on_message == "やるきスイッチ　ON"
        assert theme.yaruki_switch.off_message == "やるきスイッチ　OFF"

    def test_yaruki_switch_menu_text(self) -> None:
        """やるきスイッチのメニューテキストが設定されていることを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert theme.yaruki_switch.menu_on_text == "やるきスイッチ　ONにする"
        assert theme.yaruki_switch.menu_off_text == "やるきスイッチ　OFFにする"


class TestInstructionPaths:
    """指示書パス設定のテスト"""

    def setup_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def teardown_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def test_instructions_paths_are_set(self) -> None:
        """指示書パスが設定されていることを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert theme.instructions_coordinator == "yadoking.md"
        assert theme.instructions_manager == "yadoran.md"
        assert theme.instructions_worker == "yadon.md"

    def test_instructions_paths_end_with_md(self) -> None:
        """指示書パスが .md で終わることを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert theme.instructions_coordinator.endswith(".md")
        assert theme.instructions_manager.endswith(".md")
        assert theme.instructions_worker.endswith(".md")


class TestPromptTemplates:
    """プロンプトテンプレート設定のテスト"""

    def setup_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def teardown_method(self) -> None:
        from yadon_agents.themes import _reset_cache

        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def test_worker_prompt_template_has_placeholders(self) -> None:
        """ワーカープロンプトテンプレートにプレースホルダがあることを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        template = theme.worker_prompt_template
        assert "{instructions_path}" in template
        assert "{worker_name}" in template
        assert "{number}" in template
        assert "{instruction}" in template

    def test_manager_prompt_prefix_has_placeholders(self) -> None:
        """マネージャープロンプトプレフィックスにプレースホルダがあることを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        template = theme.manager_prompt_prefix
        assert "{instructions_path}" in template
        assert "{manager_name}" in template

    def test_bubble_templates_have_placeholders(self) -> None:
        """吹き出しテンプレートにプレースホルダがあることを確認"""
        from yadon_agents.themes import get_theme

        theme = get_theme()
        assert "{summary}" in theme.worker_task_bubble
        assert "{summary}" in theme.worker_success_bubble
        assert "{summary}" in theme.worker_error_bubble
        assert "{summary}" in theme.manager_task_bubble
        assert "{summary}" in theme.manager_success_bubble
        assert "{summary}" in theme.manager_error_bubble
