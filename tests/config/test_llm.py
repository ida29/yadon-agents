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
