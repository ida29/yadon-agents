"""AgentThread — AgentPortをQThreadでラップしてGUIと統合する"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from yadon_agents.domain.ports.agent_port import AgentPort


class AgentThread(QThread):
    """AgentPortをQThreadで動かし、吹き出しリクエストをシグナルに変換する。"""

    bubble_request = pyqtSignal(str, str, int)  # (text, bubble_type, duration_ms)

    def __init__(self, agent: AgentPort):
        super().__init__()
        self.agent = agent
        self.agent.on_bubble = lambda text, btype, dur: self.bubble_request.emit(
            text, btype, dur
        )

    def run(self) -> None:
        self.agent.serve_forever()

    def stop(self) -> None:
        self.agent.stop()
        self.wait(3000)
