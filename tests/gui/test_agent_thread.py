"""agent_thread.py のテスト

AgentThread (QThread) の機能をテストします:
- AgentThread の初期化
- シグナル発行のモックテスト
- 停止処理

PyQt6 依存のため、環境によってはスキップされます。
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

# PyQt6 のインポートは環境に依存
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QThread, pyqtSignal, QObject

    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False

if TYPE_CHECKING:
    from yadon_agents.domain.ports.agent_port import AgentPort


# QApplication はプロセス全体でただ一つだけ存在可能
@pytest.fixture(scope="session")
def qapp():
    """セッション全体で共有される QApplication インスタンス"""
    if not HAS_PYQT6:
        pytest.skip("PyQt6 not available")

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class MockAgent:
    """テスト用のモックエージェント"""

    def __init__(self) -> None:
        self.on_bubble: object = None
        self.serve_forever_called = False
        self.stop_called = False

    def serve_forever(self) -> None:
        self.serve_forever_called = True

    def stop(self) -> None:
        self.stop_called = True


@pytest.mark.skipif(not HAS_PYQT6, reason="PyQt6 not installed")
class TestAgentThreadInitialization:
    """AgentThread 初期化のテスト"""

    def test_agent_thread_creation(self, qapp) -> None:
        """AgentThread が作成できることを確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        thread = AgentThread(mock_agent)

        assert thread is not None
        assert thread.agent is mock_agent

    def test_agent_thread_is_qthread(self, qapp) -> None:
        """AgentThread が QThread を継承していることを確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        thread = AgentThread(mock_agent)

        assert isinstance(thread, QThread)

    def test_agent_thread_sets_on_bubble_callback(self, qapp) -> None:
        """AgentThread が on_bubble コールバックを設定することを確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        assert mock_agent.on_bubble is None

        thread = AgentThread(mock_agent)
        assert mock_agent.on_bubble is not None
        assert callable(mock_agent.on_bubble)


@pytest.mark.skipif(not HAS_PYQT6, reason="PyQt6 not installed")
class TestAgentThreadSignals:
    """AgentThread シグナルのテスト"""

    def test_bubble_request_signal_exists(self, qapp) -> None:
        """bubble_request シグナルが存在することを確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        thread = AgentThread(mock_agent)

        # シグナルが存在することを確認
        assert hasattr(thread, "bubble_request")

    def test_bubble_request_signal_connection(self, qapp) -> None:
        """bubble_request シグナルに接続できることを確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        thread = AgentThread(mock_agent)

        callback = MagicMock()
        thread.bubble_request.connect(callback)

        # シグナルを発行
        thread.bubble_request.emit("test text", "normal", 3000)

        # コールバックが呼ばれたことを確認
        callback.assert_called_once_with("test text", "normal", 3000)

    def test_on_bubble_emits_signal(self, qapp) -> None:
        """on_bubble コールバックがシグナルを発行することを確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        thread = AgentThread(mock_agent)

        received_signals: list[tuple[str, str, int]] = []

        def capture_signal(text: str, btype: str, duration: int) -> None:
            received_signals.append((text, btype, duration))

        thread.bubble_request.connect(capture_signal)

        # on_bubble を呼び出し
        mock_agent.on_bubble("Hello", "hook", 5000)

        assert len(received_signals) == 1
        assert received_signals[0] == ("Hello", "hook", 5000)


@pytest.mark.skipif(not HAS_PYQT6, reason="PyQt6 not installed")
class TestAgentThreadRun:
    """AgentThread run() メソッドのテスト"""

    def test_run_calls_serve_forever(self, qapp) -> None:
        """run() が serve_forever() を呼び出すことを確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        thread = AgentThread(mock_agent)

        # run() を直接呼び出し（スレッドは開始しない）
        thread.run()

        assert mock_agent.serve_forever_called


@pytest.mark.skipif(not HAS_PYQT6, reason="PyQt6 not installed")
class TestAgentThreadStop:
    """AgentThread stop() メソッドのテスト"""

    def test_stop_calls_agent_stop(self, qapp) -> None:
        """stop() がエージェントの stop() を呼び出すことを確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        thread = AgentThread(mock_agent)

        thread.stop()

        assert mock_agent.stop_called

    def test_stop_waits_for_thread(self, qapp) -> None:
        """stop() がスレッドの終了を待機することを確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        thread = AgentThread(mock_agent)

        # wait() をモック化
        with patch.object(thread, "wait") as mock_wait:
            thread.stop()
            mock_wait.assert_called_once_with(3000)


@pytest.mark.skipif(not HAS_PYQT6, reason="PyQt6 not installed")
class TestAgentThreadIntegration:
    """AgentThread の統合テスト"""

    def test_multiple_bubble_emissions(self, qapp) -> None:
        """複数の吹き出しリクエストを処理できることを確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        thread = AgentThread(mock_agent)

        received: list[tuple[str, str, int]] = []

        def capture(text: str, btype: str, duration: int) -> None:
            received.append((text, btype, duration))

        thread.bubble_request.connect(capture)

        # 複数のリクエストを発行
        mock_agent.on_bubble("Message 1", "normal", 1000)
        mock_agent.on_bubble("Message 2", "hook", 2000)
        mock_agent.on_bubble("Message 3", "normal", 3000)

        assert len(received) == 3
        assert received[0] == ("Message 1", "normal", 1000)
        assert received[1] == ("Message 2", "hook", 2000)
        assert received[2] == ("Message 3", "normal", 3000)

    def test_signal_with_unicode_text(self, qapp) -> None:
        """Unicodeテキストを含むシグナルの処理を確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        thread = AgentThread(mock_agent)

        received: list[str] = []

        def capture(text: str, btype: str, duration: int) -> None:
            received.append(text)

        thread.bubble_request.connect(capture)

        # 日本語テキスト
        mock_agent.on_bubble("やるやぁん", "normal", 1000)
        assert "やるやぁん" in received

        # 絵文字
        mock_agent.on_bubble("完了 ✨", "normal", 1000)
        assert "完了 ✨" in received

    def test_signal_with_empty_text(self, qapp) -> None:
        """空テキストを含むシグナルの処理を確認"""
        from yadon_agents.gui.agent_thread import AgentThread

        mock_agent = MockAgent()
        thread = AgentThread(mock_agent)

        received: list[str] = []

        def capture(text: str, btype: str, duration: int) -> None:
            received.append(text)

        thread.bubble_request.connect(capture)

        mock_agent.on_bubble("", "normal", 1000)
        assert "" in received


class TestAgentThreadWithoutQt:
    """PyQt6なしでのAgentThread関連テスト（モック使用）"""

    def test_mock_agent_port_interface(self) -> None:
        """AgentPort インターフェースのモック検証"""
        mock_agent = MockAgent()

        # on_bubble 設定可能
        mock_agent.on_bubble = lambda t, b, d: None
        assert callable(mock_agent.on_bubble)

        # serve_forever 呼び出し可能
        mock_agent.serve_forever()
        assert mock_agent.serve_forever_called

        # stop 呼び出し可能
        mock_agent.stop()
        assert mock_agent.stop_called

    def test_callback_assignment(self) -> None:
        """コールバック割り当てのテスト"""
        mock_agent = MockAgent()

        captured: list[tuple[str, str, int]] = []

        def callback(text: str, btype: str, duration: int) -> None:
            captured.append((text, btype, duration))

        mock_agent.on_bubble = callback

        # コールバック呼び出し
        mock_agent.on_bubble("test", "normal", 1000)

        assert len(captured) == 1
        assert captured[0] == ("test", "normal", 1000)

    def test_signal_emission_pattern(self) -> None:
        """シグナル発行パターンのテスト（Qt不要）"""
        # AgentThread のシグナル発行パターンを模擬
        emitted: list[tuple[str, str, int]] = []

        def mock_emit(text: str, btype: str, duration: int) -> None:
            emitted.append((text, btype, duration))

        # on_bubble がシグナルをemitするパターン
        on_bubble = lambda t, b, d: mock_emit(t, b, d)

        on_bubble("Hello", "normal", 3000)

        assert len(emitted) == 1
        assert emitted[0] == ("Hello", "normal", 3000)
