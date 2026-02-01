"""テーマシステムのテスト"""

from __future__ import annotations

import os

import pytest


class TestThemeConfig:
    """ThemeConfig dataclass のテスト"""

    def test_frozen(self):
        from yadon_agents.domain.theme import ThemeConfig, RoleNames
        config = ThemeConfig(
            name="test",
            display_name="Test",
            socket_prefix="test",
            role_names=RoleNames(coordinator="C", manager="M", worker="W"),
        )
        with pytest.raises(AttributeError):
            config.name = "changed"  # type: ignore[misc]

    def test_default_values(self):
        from yadon_agents.domain.theme import ThemeConfig, RoleNames, WorkerCountConfig
        config = ThemeConfig(
            name="test",
            display_name="Test",
            socket_prefix="test",
            role_names=RoleNames(),
        )
        assert config.worker_count == WorkerCountConfig(default=4, min=1, max=8)
        assert config.worker_messages == {}
        assert config.manager_messages == []
        assert config.yaruki_switch.enabled is False


class TestYadonTheme:
    """ヤドンテーマ build_theme() のテスト"""

    def test_build_theme_returns_config(self):
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        assert theme.name == "yadon"
        assert theme.display_name == "ヤドン・エージェント"
        assert theme.socket_prefix == "yadon"

    def test_role_names(self):
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        assert theme.role_names.coordinator == "ヤドキング"
        assert theme.role_names.manager == "ヤドラン"
        assert theme.role_names.worker == "ヤドン"

    def test_worker_messages(self):
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        assert 1 in theme.worker_messages
        assert 4 in theme.worker_messages
        assert len(theme.worker_messages) == 4

    def test_worker_variants(self):
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        assert theme.worker_variants[1] == "normal"
        assert theme.worker_variants[2] == "shiny"
        assert theme.worker_variants[3] == "galarian"
        assert theme.worker_variants[4] == "galarian_shiny"

    def test_phase_labels(self):
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        assert "implement" in theme.phase_labels
        assert "docs" in theme.phase_labels
        assert "review" in theme.phase_labels

    def test_agent_roles(self):
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        assert theme.agent_role_coordinator == "yadoking"
        assert theme.agent_role_manager == "yadoran"
        assert theme.agent_role_worker == "yadon"

    def test_color_schemes(self):
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        assert "normal" in theme.worker_color_schemes
        assert "shiny" in theme.worker_color_schemes
        assert "body" in theme.manager_colors
        assert "shellder" in theme.manager_colors

    def test_yaruki_switch_config(self):
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        assert theme.yaruki_switch.enabled is False
        assert theme.yaruki_switch.on_message == "やるきスイッチ　ON"

    def test_instructions_paths(self):
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        assert theme.instructions_coordinator == "instructions/yadoking.md"
        assert theme.instructions_worker == "instructions/yadon.md"


class TestGetTheme:
    """get_theme() シングルトンのテスト"""

    def setup_method(self):
        from yadon_agents.themes import _reset_cache
        _reset_cache()

    def teardown_method(self):
        from yadon_agents.themes import _reset_cache
        _reset_cache()
        os.environ.pop("YADON_THEME", None)

    def test_default_theme(self):
        from yadon_agents.themes import get_theme
        theme = get_theme()
        assert theme.name == "yadon"

    def test_cache_returns_same_instance(self):
        from yadon_agents.themes import get_theme
        t1 = get_theme()
        t2 = get_theme()
        assert t1 is t2

    def test_invalid_theme_raises(self):
        from yadon_agents.themes import get_theme
        os.environ["YADON_THEME"] = "nonexistent_theme_xyz"
        with pytest.raises(ModuleNotFoundError):
            get_theme()


class TestSpriteBuilders:
    """スプライトビルダーのテスト"""

    def test_worker_sprite_16x16(self):
        from yadon_agents.themes.yadon.sprites import build_worker_pixel_data
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        pixels = build_worker_pixel_data("normal", theme.worker_color_schemes)
        assert len(pixels) == 16
        assert all(len(row) == 16 for row in pixels)

    def test_worker_sprite_galarian_accent(self):
        from yadon_agents.themes.yadon.sprites import build_worker_pixel_data
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        normal = build_worker_pixel_data("normal", theme.worker_color_schemes)
        galarian = build_worker_pixel_data("galarian", theme.worker_color_schemes)
        # ガラル版はアクセント色が異なる
        assert normal[2][6] != galarian[2][6]

    def test_manager_sprite_16x16(self):
        from yadon_agents.themes.yadon.sprites import build_manager_pixel_data
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        pixels = build_manager_pixel_data(theme.manager_colors)
        assert len(pixels) == 16
        assert all(len(row) == 16 for row in pixels)

    def test_manager_sprite_contains_shellder(self):
        from yadon_agents.themes.yadon.sprites import build_manager_pixel_data
        from yadon_agents.themes.yadon import build_theme
        theme = build_theme()
        pixels = build_manager_pixel_data(theme.manager_colors)
        shellder_color = theme.manager_colors["shellder"]
        # シェルダーの色がドット絵に含まれている
        flat = [c for row in pixels for c in row]
        assert shellder_color in flat


class TestBackwardCompat:
    """後方互換性テスト: config/agent.py と config/ui.py の既存API"""

    def setup_method(self):
        from yadon_agents.themes import _reset_cache
        _reset_cache()

    def teardown_method(self):
        from yadon_agents.themes import _reset_cache
        _reset_cache()

    def test_get_yadon_count_default(self):
        from yadon_agents.config.agent import get_yadon_count
        os.environ.pop("YADON_COUNT", None)
        assert get_yadon_count() == 4

    def test_get_yadon_messages(self):
        from yadon_agents.config.agent import get_yadon_messages
        msgs = get_yadon_messages(1)
        assert isinstance(msgs, list)
        assert len(msgs) > 0

    def test_get_yadon_messages_fallback(self):
        from yadon_agents.config.agent import get_yadon_messages
        msgs5 = get_yadon_messages(5)
        msgs1 = get_yadon_messages(1)
        assert msgs5 == msgs1

    def test_get_yadon_variant(self):
        from yadon_agents.config.agent import get_yadon_variant
        assert get_yadon_variant(1) == "normal"
        assert get_yadon_variant(2) == "shiny"

    def test_get_yadon_variant_fallback(self):
        from yadon_agents.config.agent import get_yadon_variant
        assert get_yadon_variant(5) == "normal"

    def test_module_getattr_random_messages(self):
        from yadon_agents.config import agent
        msgs = agent.RANDOM_MESSAGES
        assert isinstance(msgs, list)
        assert len(msgs) > 0

    def test_module_getattr_phase_labels(self):
        from yadon_agents.config import agent
        labels = agent.PHASE_LABELS
        assert "implement" in labels

    def test_color_schemes_compat(self):
        from yadon_agents.config import ui
        schemes = ui.COLOR_SCHEMES
        assert "normal" in schemes
        assert "body" in schemes["normal"]

    def test_yadoran_colors_compat(self):
        from yadon_agents.config import ui
        colors = ui.YADORAN_COLORS
        assert "body" in colors
        assert "shellder" in colors


class TestProtocolPrefix:
    """protocol.py の prefix パラメータテスト"""

    def test_agent_socket_path_default(self):
        from yadon_agents.infra.protocol import agent_socket_path
        assert agent_socket_path("yadon-1") == "/tmp/yadon-agent-yadon-1.sock"

    def test_agent_socket_path_custom_prefix(self):
        from yadon_agents.infra.protocol import agent_socket_path
        assert agent_socket_path("worker-1", prefix="custom") == "/tmp/custom-agent-worker-1.sock"

    def test_pet_socket_path_default(self):
        from yadon_agents.infra.protocol import pet_socket_path
        assert pet_socket_path("1") == "/tmp/yadon-pet-1.sock"

    def test_pet_socket_path_custom_prefix(self):
        from yadon_agents.infra.protocol import pet_socket_path
        assert pet_socket_path("1", prefix="custom") == "/tmp/custom-pet-1.sock"
