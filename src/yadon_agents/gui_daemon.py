#!/usr/bin/env python3
"""GUI Daemon - ペットウィンドウを別プロセスで起動"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCursor

from yadon_agents import PROJECT_ROOT
from yadon_agents.agent.manager import YadoranManager
from yadon_agents.agent.worker import YadonWorker
from yadon_agents.config.agent import get_yadon_count, get_yadon_variant
from yadon_agents.config.ui import WINDOW_WIDTH, WINDOW_HEIGHT
from yadon_agents.gui.agent_thread import AgentThread
from yadon_agents.gui.yadon_pet import YadonPet
from yadon_agents.gui.yadoran_pet import YadoranPet
from yadon_agents.infra.protocol import pet_socket_path
from yadon_agents.themes import get_theme


def main() -> None:
    """GUIデーモンのメイン"""
    theme = get_theme()
    yadon_count = get_yadon_count()
    prefix = theme.socket_prefix

    # QApplication作成（フォーカス奪取を防ぐ設定）
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # macOS: Pythonシグナル処理のためのタイマー
    sig_timer = QTimer()
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start(500)

    screen_obj = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
    screen = screen_obj.geometry()
    margin = 20
    spacing = 10

    pets: list[YadonPet | YadoranPet] = []

    # ワーカー 1-N 構築
    for n in range(1, yadon_count + 1):
        worker = YadonWorker(n, str(PROJECT_ROOT))
        agent_thread = AgentThread(worker)
        variant = get_yadon_variant(n)

        pet = YadonPet(
            yadon_number=n,
            agent_thread=agent_thread,
            pet_sock_path=pet_socket_path(str(n), prefix=prefix),
            variant=variant,
        )

        x_pos = screen.width() - margin - (WINDOW_WIDTH + spacing) * n
        y_pos = screen.height() - margin - WINDOW_HEIGHT
        pet.move(x_pos, y_pos)
        pets.append(pet)

    # マネージャー構築
    manager = YadoranManager(str(PROJECT_ROOT))
    manager_agent_thread = AgentThread(manager)

    manager_pet = YadoranPet(
        agent_thread=manager_agent_thread,
        pet_sock_path=pet_socket_path(theme.agent_role_manager, prefix=prefix),
    )

    x_pos = screen.width() - margin - (WINDOW_WIDTH + spacing) * (yadon_count + 1)
    y_pos = screen.height() - margin - WINDOW_HEIGHT
    manager_pet.move(x_pos, y_pos)
    pets.append(manager_pet)

    def _show_welcome():
        for pet in pets:
            if isinstance(pet, YadoranPet):
                pet.show_bubble(random.choice(theme.manager_welcome_messages), "normal")
            else:
                pet.show_bubble(random.choice(theme.welcome_messages), "normal")

    QTimer.singleShot(0, _show_welcome)

    # Qtイベントループ
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
