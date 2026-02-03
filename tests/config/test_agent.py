"""config/agent.py のテスト

エージェント設定定数および後方互換ラッパーのテスト。
"""

from __future__ import annotations

import pytest

from yadon_agents.config.agent import (
    # 定数
    CLAUDE_DEFAULT_TIMEOUT,
    CLAUDE_DECOMPOSE_TIMEOUT,
    SOCKET_SEND_TIMEOUT,
    SOCKET_DISPATCH_TIMEOUT,
    SOCKET_STATUS_TIMEOUT,
    SOCKET_CONNECTION_TIMEOUT,
    SOCKET_ACCEPT_TIMEOUT,
    SOCKET_LISTEN_BACKLOG,
    SOCKET_RECV_BUFFER,
    PET_SOCKET_RECV_BUFFER,
    PET_SOCKET_MAX_MESSAGE,
    PROCESS_STOP_RETRIES,
    PROCESS_STOP_INTERVAL,
    SOCKET_WAIT_TIMEOUT,
    SOCKET_WAIT_INTERVAL,
    SUMMARY_MAX_LENGTH,
    BUBBLE_TASK_MAX_LENGTH,
    BUBBLE_RESULT_MAX_LENGTH,
    # 関数
    get_yadon_count,
    get_yadon_messages,
    get_yadon_variant,
)
from yadon_agents.themes import _reset_cache


class TestTimeoutConstants:
    """タイムアウト定数のテスト"""

    def test_claude_default_timeout(self):
        """CLAUDE_DEFAULT_TIMEOUT が適切な値であること"""
        assert CLAUDE_DEFAULT_TIMEOUT == 600
        assert isinstance(CLAUDE_DEFAULT_TIMEOUT, int)

    def test_claude_decompose_timeout(self):
        """CLAUDE_DECOMPOSE_TIMEOUT が適切な値であること"""
        assert CLAUDE_DECOMPOSE_TIMEOUT == 120
        assert isinstance(CLAUDE_DECOMPOSE_TIMEOUT, int)

    def test_socket_timeouts(self):
        """ソケットタイムアウト定数が適切な値であること"""
        assert SOCKET_SEND_TIMEOUT == 300.0
        assert isinstance(SOCKET_SEND_TIMEOUT, float)

        assert SOCKET_DISPATCH_TIMEOUT == 600
        assert SOCKET_STATUS_TIMEOUT == 5
        assert SOCKET_CONNECTION_TIMEOUT == 600
        assert SOCKET_ACCEPT_TIMEOUT == 1.0


class TestSocketConstants:
    """ソケット設定定数のテスト"""

    def test_socket_listen_backlog(self):
        """SOCKET_LISTEN_BACKLOG が適切な値であること"""
        assert SOCKET_LISTEN_BACKLOG == 5
        assert SOCKET_LISTEN_BACKLOG > 0

    def test_socket_recv_buffer(self):
        """ソケット受信バッファサイズが適切であること"""
        assert SOCKET_RECV_BUFFER == 65536
        assert PET_SOCKET_RECV_BUFFER == 4096
        assert PET_SOCKET_MAX_MESSAGE == 65536

        # バッファサイズは2のべき乗であるべき
        assert SOCKET_RECV_BUFFER & (SOCKET_RECV_BUFFER - 1) == 0
        assert PET_SOCKET_RECV_BUFFER & (PET_SOCKET_RECV_BUFFER - 1) == 0


class TestCliConstants:
    """CLI設定定数のテスト"""

    def test_process_stop_settings(self):
        """プロセス停止設定が適切であること"""
        assert PROCESS_STOP_RETRIES == 20
        assert PROCESS_STOP_INTERVAL == 0.5
        # 最大待機時間が妥当であること
        max_wait = PROCESS_STOP_RETRIES * PROCESS_STOP_INTERVAL
        assert max_wait <= 30  # 30秒以内

    def test_socket_wait_settings(self):
        """ソケット待機設定が適切であること"""
        assert SOCKET_WAIT_TIMEOUT == 15
        assert SOCKET_WAIT_INTERVAL == 0.5


class TestOutputLimitConstants:
    """出力制限定数のテスト"""

    def test_summary_max_length(self):
        """SUMMARY_MAX_LENGTH が適切であること"""
        assert SUMMARY_MAX_LENGTH == 200
        assert SUMMARY_MAX_LENGTH > 0

    def test_bubble_max_lengths(self):
        """吹き出し用最大長が適切であること"""
        assert BUBBLE_TASK_MAX_LENGTH == 80
        assert BUBBLE_RESULT_MAX_LENGTH == 60
        # タスク用はより長い説明が必要
        assert BUBBLE_TASK_MAX_LENGTH >= BUBBLE_RESULT_MAX_LENGTH


class TestGetYadonCount:
    """get_yadon_count() のテスト"""

    def setup_method(self):
        """各テスト前にテーマキャッシュをリセット"""
        _reset_cache()

    def test_default_count(self, monkeypatch):
        """環境変数未設定時はデフォルト値を返すこと"""
        monkeypatch.delenv("YADON_COUNT", raising=False)

        count = get_yadon_count()

        assert count == 4  # デフォルト値

    def test_custom_count(self, monkeypatch):
        """環境変数でカスタム値を設定できること"""
        monkeypatch.setenv("YADON_COUNT", "6")

        count = get_yadon_count()

        assert count == 6

    def test_min_count_enforced(self, monkeypatch):
        """最小値より小さい場合は最小値になること"""
        monkeypatch.setenv("YADON_COUNT", "0")

        count = get_yadon_count()

        assert count >= 1  # 最小値

    def test_max_count_enforced(self, monkeypatch):
        """最大値より大きい場合は最大値になること"""
        monkeypatch.setenv("YADON_COUNT", "100")

        count = get_yadon_count()

        assert count <= 8  # 最大値

    def test_invalid_value_returns_default(self, monkeypatch):
        """無効な値の場合はデフォルトを返すこと"""
        monkeypatch.setenv("YADON_COUNT", "invalid")

        count = get_yadon_count()

        assert count == 4  # デフォルト値

    def test_empty_string_returns_default(self, monkeypatch):
        """空文字列の場合はデフォルトを返すこと"""
        monkeypatch.setenv("YADON_COUNT", "")

        count = get_yadon_count()

        assert count == 4  # デフォルト値

    def test_float_value_truncated(self, monkeypatch):
        """小数値の場合は切り捨てられること（または無効として扱われる）"""
        monkeypatch.setenv("YADON_COUNT", "3.7")

        count = get_yadon_count()

        # Pythonのint()は小数を変換できないので、デフォルトに戻る
        assert count == 4

    def test_negative_value(self, monkeypatch):
        """負の値の場合は最小値になること"""
        monkeypatch.setenv("YADON_COUNT", "-5")

        count = get_yadon_count()

        assert count >= 1


class TestGetYadonMessages:
    """get_yadon_messages() のテスト"""

    def setup_method(self):
        """各テスト前にテーマキャッシュをリセット"""
        _reset_cache()

    def test_messages_for_worker_1(self):
        """ワーカー1のメッセージが取得できること"""
        messages = get_yadon_messages(1)

        assert isinstance(messages, list)
        assert len(messages) > 0
        # 全要素が文字列であること
        assert all(isinstance(m, str) for m in messages)

    def test_messages_for_worker_4(self):
        """ワーカー4のメッセージが取得できること"""
        messages = get_yadon_messages(4)

        assert isinstance(messages, list)
        assert len(messages) > 0

    def test_messages_for_high_number_fallback(self):
        """定義されていないワーカー番号はフォールバックすること"""
        messages = get_yadon_messages(10)

        assert isinstance(messages, list)
        # フォールバックで何らかのメッセージが返る
        # 空リストでもエラーにならないことを確認
        assert isinstance(messages, list)

    def test_messages_contain_different_types(self):
        """メッセージに task, success, error, random が含まれること"""
        messages = get_yadon_messages(1)

        # 新形式では複数のメッセージタイプが結合される
        assert len(messages) >= 4  # 最低でも各タイプから1つ


class TestGetYadonVariant:
    """get_yadon_variant() のテスト"""

    def setup_method(self):
        """各テスト前にテーマキャッシュをリセット"""
        _reset_cache()

    def test_variant_for_worker_1(self):
        """ワーカー1のバリアントが取得できること"""
        variant = get_yadon_variant(1)

        assert isinstance(variant, str)
        assert variant == "normal"

    def test_variant_for_worker_2(self):
        """ワーカー2のバリアントが取得できること"""
        variant = get_yadon_variant(2)

        assert isinstance(variant, str)
        assert variant == "shiny"

    def test_variant_for_worker_3(self):
        """ワーカー3のバリアントが取得できること"""
        variant = get_yadon_variant(3)

        assert isinstance(variant, str)
        assert variant == "galarian"

    def test_variant_for_worker_4(self):
        """ワーカー4のバリアントが取得できること"""
        variant = get_yadon_variant(4)

        assert isinstance(variant, str)
        assert variant == "galarian_shiny"

    def test_variant_fallback_for_high_number(self):
        """定義されていないワーカー番号はフォールバックすること"""
        variant = get_yadon_variant(10)

        assert isinstance(variant, str)
        # 有効なバリアント名であること
        assert variant in ["normal", "shiny", "galarian", "galarian_shiny"]


class TestBackwardCompatProxy:
    """後方互換プロキシのテスト"""

    def setup_method(self):
        """各テスト前にテーマキャッシュをリセット"""
        _reset_cache()

    def test_random_messages_accessible(self):
        """RANDOM_MESSAGES がアクセス可能であること"""
        from yadon_agents.config import agent

        messages = agent.RANDOM_MESSAGES

        assert isinstance(messages, list)
        assert len(messages) > 0

    def test_welcome_messages_accessible(self):
        """WELCOME_MESSAGES がアクセス可能であること"""
        from yadon_agents.config import agent

        messages = agent.WELCOME_MESSAGES

        assert isinstance(messages, list)
        assert len(messages) > 0

    def test_phase_labels_accessible(self):
        """PHASE_LABELS がアクセス可能であること"""
        from yadon_agents.config import agent

        labels = agent.PHASE_LABELS

        assert isinstance(labels, dict)
        assert "implement" in labels
        assert "docs" in labels
        assert "review" in labels

    def test_yadon_variants_accessible(self):
        """YADON_VARIANTS がアクセス可能であること"""
        from yadon_agents.config import agent

        variants = agent.YADON_VARIANTS

        assert isinstance(variants, dict)
        assert 1 in variants
        assert 4 in variants

    def test_yaruki_switch_mode_accessible(self):
        """YARUKI_SWITCH_MODE がアクセス可能であること"""
        from yadon_agents.config import agent

        mode = agent.YARUKI_SWITCH_MODE

        assert isinstance(mode, bool)

    def test_invalid_attribute_raises(self):
        """存在しない属性にアクセスするとAttributeErrorになること"""
        from yadon_agents.config import agent

        with pytest.raises(AttributeError):
            _ = agent.NONEXISTENT_ATTRIBUTE
