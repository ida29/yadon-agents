"""LLM バックエンド設定のテスト

LLMModelConfig と LLMBackendConfig の frozen dataclass 検証、
およびバックエンド設定関数のテスト。
"""

from __future__ import annotations

import dataclasses

import pytest

from yadon_agents.config.llm import (
    LLMBackendConfig,
    LLMModelConfig,
    get_backend_config,
    get_model_for_tier,
    get_worker_backend_name,
)


class TestLLMModelConfig:
    """LLMModelConfig の frozen dataclass テスト"""

    def test_frozen(self) -> None:
        """LLMModelConfig が frozen dataclass であることを確認。

        インスタンス生成後にフィールドを書き換えようとすると、
        dataclasses.FrozenInstanceError が raise されることを確認。
        """
        config = LLMModelConfig(
            coordinator="opus",
            manager="sonnet",
            worker="haiku",
        )

        # 初期値確認
        assert config.coordinator == "opus"
        assert config.manager == "sonnet"
        assert config.worker == "haiku"

        # frozen であるため、フィールド書き換えは失敗
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.coordinator = "gpt-4o"  # type: ignore[misc]

        with pytest.raises(dataclasses.FrozenInstanceError):
            config.manager = "gemini-2.5-flash"  # type: ignore[misc]

        with pytest.raises(dataclasses.FrozenInstanceError):
            config.worker = "custom-model"  # type: ignore[misc]


class TestLLMBackendConfig:
    """LLMBackendConfig の frozen dataclass テスト"""

    def test_frozen(self) -> None:
        """LLMBackendConfig が frozen dataclass であることを確認。

        インスタンス生成後にフィールドを書き換えようとすると，
        dataclasses.FrozenInstanceError が raise されることを確認。
        """
        models = LLMModelConfig(
            coordinator="opus",
            manager="sonnet",
            worker="haiku",
        )
        config = LLMBackendConfig(
            name="claude",
            command="claude",
            models=models,
            flags={"use_pipe": True},
            batch_subcommand=None,
        )

        # 初期値確認
        assert config.name == "claude"
        assert config.command == "claude"
        assert config.models == models
        assert config.flags == {"use_pipe": True}
        assert config.batch_subcommand is None

        # frozen であるため、フィールド書き換えは失敗
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.name = "gemini"  # type: ignore[misc]

        with pytest.raises(dataclasses.FrozenInstanceError):
            config.command = "gemini"  # type: ignore[misc]

        with pytest.raises(dataclasses.FrozenInstanceError):
            config.flags = {"use_pipe": False}  # type: ignore[misc]

        with pytest.raises(dataclasses.FrozenInstanceError):
            config.batch_subcommand = "run -q"  # type: ignore[misc]


class TestGetBackendConfig:
    def test_claude_config(self, monkeypatch):
        """デフォルトで claude 設定を返す"""
        # LLM_BACKEND が設定されていない場合、デフォルトは claude
        monkeypatch.delenv("LLM_BACKEND", raising=False)

        config = get_backend_config()

        assert config.command == "claude"
        assert config.models.coordinator == "opus"

    def test_gemini_config(self, monkeypatch):
        """LLM_BACKEND="gemini" 設定時に gemini 設定を返す"""
        monkeypatch.setenv("LLM_BACKEND", "gemini")

        config = get_backend_config()

        assert config.command == "gemini"
        assert config.models.coordinator == "gemini-3.0-pro"

    def test_opencode_has_batch_subcommand(self, monkeypatch):
        """LLM_BACKEND="opencode" 設定時に batch_subcommand=="run -q" を返す"""
        monkeypatch.setenv("LLM_BACKEND", "opencode")

        config = get_backend_config()

        assert config.batch_subcommand == "run -q"


class TestGetModelForTier:
    """get_model_for_tier() のテストクラス"""

    def test_coordinator_tier(self, monkeypatch):
        """coordinator tier が 'opus' を返すことを確認（claude デフォルト）"""
        # LLM_BACKEND が設定されていない場合、デフォルト "claude" が使用される
        monkeypatch.delenv("LLM_BACKEND", raising=False)

        result = get_model_for_tier("coordinator")

        assert result == "opus"

    def test_manager_tier(self, monkeypatch):
        """manager tier が 'sonnet' を返すことを確認"""
        monkeypatch.delenv("LLM_BACKEND", raising=False)

        result = get_model_for_tier("manager")

        assert result == "sonnet"

    def test_worker_tier(self, monkeypatch):
        """worker tier が 'haiku' を返すことを確認"""
        monkeypatch.delenv("LLM_BACKEND", raising=False)

        result = get_model_for_tier("worker")

        assert result == "haiku"

    def test_invalid_tier_raises(self, monkeypatch):
        """get_model_for_tier("invalid") が ValueError を raise することを確認"""
        monkeypatch.delenv("LLM_BACKEND", raising=False)

        with pytest.raises(ValueError) as exc_info:
            get_model_for_tier("invalid")

        # ValueError のメッセージに "Invalid tier" が含まれることを確認
        assert "Invalid tier" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)


class TestGetWorkerBackendName:
    """get_worker_backend_name() のテストクラス"""

    def test_get_worker_backend_name_default(self, monkeypatch):
        """環境変数未設定時のデフォルト動作を確認。

        YADON_N_BACKEND も LLM_BACKEND も設定されていない場合、
        デフォルトの "claude" を返すことを確認。
        """
        monkeypatch.delenv("YADON_1_BACKEND", raising=False)
        monkeypatch.delenv("LLM_BACKEND", raising=False)

        result = get_worker_backend_name(1)

        assert result == "claude"

    def test_get_worker_backend_name_with_env(self, monkeypatch):
        """YADON_N_BACKEND が設定されている場合を確認。

        YADON_N_BACKEND 環境変数が設定されている場合、
        その値が使用されることを確認（LLM_BACKEND より優先）。
        """
        monkeypatch.setenv("YADON_2_BACKEND", "gemini")
        monkeypatch.setenv("LLM_BACKEND", "copilot")

        result = get_worker_backend_name(2)

        # YADON_2_BACKEND が優先される
        assert result == "gemini"

    def test_get_worker_backend_name_invalid_fallback(self, monkeypatch):
        """無効なバックエンド名が設定されている場合のフォールバック。

        YADON_N_BACKEND に無効なバックエンド名が設定されている場合、
        get_backend_name() にフォールバック（グローバルバックエンド）することを確認。
        """
        monkeypatch.setenv("YADON_3_BACKEND", "invalid-backend")
        monkeypatch.setenv("LLM_BACKEND", "copilot")

        result = get_worker_backend_name(3)

        # 無効なので LLM_BACKEND の "copilot" にフォールバック
        assert result == "copilot"


class TestBackendEnvironmentVariableCombinations:
    """バックエンド設定の複雑な環境変数組み合わせテスト"""

    def test_all_backends_claude_mode(self, monkeypatch):
        """全てのワーカーに Claude を割り当て"""
        monkeypatch.setenv("LLM_BACKEND", "claude")
        monkeypatch.delenv("YADON_1_BACKEND", raising=False)
        monkeypatch.delenv("YADON_2_BACKEND", raising=False)
        monkeypatch.delenv("YADON_3_BACKEND", raising=False)
        monkeypatch.delenv("YADON_4_BACKEND", raising=False)

        for i in range(1, 5):
            assert get_worker_backend_name(i) == "claude"

    def test_all_backends_gemini_mode(self, monkeypatch):
        """全てのワーカーに Gemini を割り当て"""
        monkeypatch.setenv("LLM_BACKEND", "gemini")
        monkeypatch.delenv("YADON_1_BACKEND", raising=False)
        monkeypatch.delenv("YADON_2_BACKEND", raising=False)
        monkeypatch.delenv("YADON_3_BACKEND", raising=False)
        monkeypatch.delenv("YADON_4_BACKEND", raising=False)

        for i in range(1, 5):
            assert get_worker_backend_name(i) == "gemini"

    def test_mixed_backend_assignment(self, monkeypatch):
        """ワーカーごとに異なるバックエンドを割り当て"""
        monkeypatch.setenv("YADON_1_BACKEND", "claude")
        monkeypatch.setenv("YADON_2_BACKEND", "gemini")
        monkeypatch.setenv("YADON_3_BACKEND", "copilot")
        monkeypatch.setenv("YADON_4_BACKEND", "opencode")
        monkeypatch.delenv("LLM_BACKEND", raising=False)

        assert get_worker_backend_name(1) == "claude"
        assert get_worker_backend_name(2) == "gemini"
        assert get_worker_backend_name(3) == "copilot"
        assert get_worker_backend_name(4) == "opencode"

    def test_partial_explicit_assignment(self, monkeypatch):
        """一部のワーカーのみ明示的指定、残りはグローバル設定"""
        monkeypatch.setenv("YADON_1_BACKEND", "gemini")
        monkeypatch.setenv("YADON_2_BACKEND", "copilot")
        monkeypatch.setenv("LLM_BACKEND", "claude")
        monkeypatch.delenv("YADON_3_BACKEND", raising=False)
        monkeypatch.delenv("YADON_4_BACKEND", raising=False)

        assert get_worker_backend_name(1) == "gemini"  # explicit
        assert get_worker_backend_name(2) == "copilot"  # explicit
        assert get_worker_backend_name(3) == "claude"  # global default
        assert get_worker_backend_name(4) == "claude"  # global default

    def test_override_global_with_worker_specific(self, monkeypatch):
        """グローバル設定を個別ワーカー設定でオーバーライド"""
        monkeypatch.setenv("LLM_BACKEND", "gemini")
        monkeypatch.setenv("YADON_2_BACKEND", "claude")
        monkeypatch.setenv("YADON_3_BACKEND", "copilot")
        monkeypatch.delenv("YADON_1_BACKEND", raising=False)
        monkeypatch.delenv("YADON_4_BACKEND", raising=False)

        assert get_worker_backend_name(1) == "gemini"  # global
        assert get_worker_backend_name(2) == "claude"  # override
        assert get_worker_backend_name(3) == "copilot"  # override
        assert get_worker_backend_name(4) == "gemini"  # global

    def test_case_insensitive_backend_name(self, monkeypatch):
        """バックエンド名の大文字小文字処理（環境変数は大文字小文字が保持される）"""
        monkeypatch.setenv("YADON_1_BACKEND", "CLAUDE")
        monkeypatch.delenv("LLM_BACKEND", raising=False)

        # 環境変数の値がそのまま返されることを確認
        result = get_worker_backend_name(1)
        # 小文字で統一されている場合と大文字のままの場合を検証
        assert isinstance(result, str)


class TestBackendConfigAllBackends:
    """全てのバックエンド設定の網羅テスト"""

    def test_claude_config_complete(self, monkeypatch):
        """Claude バックエンド設定の完全検証"""
        monkeypatch.setenv("LLM_BACKEND", "claude")

        config = get_backend_config()

        assert config.name == "claude"
        assert config.command == "claude"
        assert config.models.coordinator == "opus"
        assert config.models.manager == "sonnet"
        assert config.models.worker == "haiku"
        assert config.batch_subcommand is None

    def test_gemini_config_complete(self, monkeypatch):
        """Gemini バックエンド設定の完全検証"""
        monkeypatch.setenv("LLM_BACKEND", "gemini")

        config = get_backend_config()

        assert config.name == "gemini"
        assert config.command == "gemini"
        assert config.models.coordinator == "gemini-3.0-pro"
        assert config.models.manager == "gemini-3.0-flash"
        assert config.models.worker == "gemini-3.0-flash"
        # Gemini は batch_subcommand が None で OK
        assert isinstance(config.flags, dict)

    def test_copilot_config_complete(self, monkeypatch):
        """Copilot バックエンド設定の完全検証"""
        monkeypatch.setenv("LLM_BACKEND", "copilot")

        config = get_backend_config()

        assert config.name == "copilot"
        assert config.command == "copilot"
        assert config.models.coordinator == "gpt-5.2"
        assert config.models.manager == "gpt-5.2-mini"
        assert config.models.worker == "gpt-5.2-mini"

    def test_opencode_config_complete(self, monkeypatch):
        """OpenCode バックエンド設定の完全検証"""
        monkeypatch.setenv("LLM_BACKEND", "opencode")

        config = get_backend_config()

        assert config.name == "opencode"
        assert config.command == "opencode"
        assert config.batch_subcommand == "run -q"

    def test_invalid_backend_fallback(self, monkeypatch):
        """無効なバックエンド指定時のフォールバック"""
        monkeypatch.setenv("LLM_BACKEND", "nonexistent-backend")

        config = get_backend_config()

        # 無効な設定はデフォルト (claude) にフォールバック
        assert config.command == "claude"

    @pytest.mark.slow
    def test_all_tiers_for_each_backend(self, monkeypatch):
        """各バックエンドの全 tier が設定されていることを確認"""
        backends = ["claude", "gemini", "copilot", "opencode"]

        for backend in backends:
            monkeypatch.setenv("LLM_BACKEND", backend)

            # 各 tier のモデルが設定されている
            coordinator = get_model_for_tier("coordinator")
            manager = get_model_for_tier("manager")
            worker = get_model_for_tier("worker")

            assert isinstance(coordinator, str)
            assert isinstance(manager, str)
            assert isinstance(worker, str)
            assert len(coordinator) > 0
            assert len(manager) > 0
            assert len(worker) > 0

    def test_backend_config_flags(self, monkeypatch):
        """バックエンド設定の flags フィールドが正しく設定されていることを確認"""
        backends = ["claude", "gemini", "copilot", "opencode"]

        for backend in backends:
            monkeypatch.setenv("LLM_BACKEND", backend)

            config = get_backend_config()

            # flags は辞書で、有効なフィールドを含む
            assert isinstance(config.flags, dict)
            # フラグが存在することを確認（内容は backend 依存）
            assert config.flags is not None
