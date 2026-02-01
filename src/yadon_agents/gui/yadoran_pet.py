#!/usr/bin/env python3
"""マネージャー デスクトップペット

BasePet を継承。ワーカー版より単純（やるきスイッチなし）。
"""

from __future__ import annotations

import argparse
import logging
import random
import signal
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCursor

from yadon_agents.config.ui import WINDOW_WIDTH, WINDOW_HEIGHT
from yadon_agents.gui.base_pet import BasePet
from yadon_agents.gui.agent_thread import AgentThread
from yadon_agents.gui.yadoran_pixel_data import build_yadoran_pixel_data
from yadon_agents.themes import get_theme

logger = logging.getLogger(__name__)


class YadoranPet(BasePet):
    """マネージャー デスクトップペット。"""

    def __init__(self, agent_thread: AgentThread, pet_sock_path: str):
        theme = get_theme()
        super().__init__(
            label_text=theme.role_names.manager,
            pixel_data=build_yadoran_pixel_data(),
            messages=theme.manager_messages,
        )

        self.start_servers(pet_sock_path, agent_thread)


def _signal_handler(signum, frame):
    QApplication.quit()


def main() -> None:
    # --- Composition Root: 具体的な依存の組み立て ---
    from yadon_agents import PROJECT_ROOT
    from yadon_agents.agent.manager import YadoranManager
    from yadon_agents.config.agent import get_yadon_count
    from yadon_agents.infra.protocol import pet_socket_path

    theme = get_theme()

    parser = argparse.ArgumentParser(description=f'{theme.role_names.manager} デスクトップペット')
    parser.parse_args()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    app = QApplication(sys.argv)

    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    screen_obj = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
    screen = screen_obj.geometry()

    # 具体的なエージェント構築（composition root）
    manager = YadoranManager(str(PROJECT_ROOT))
    agent_thread = AgentThread(manager)

    pet = YadoranPet(
        agent_thread=agent_thread,
        pet_sock_path=pet_socket_path(theme.agent_role_manager, prefix=theme.socket_prefix),
    )

    margin = 20
    spacing = 10
    x_pos = screen.width() - margin - (WINDOW_WIDTH + spacing) * (get_yadon_count() + 1)
    y_pos = screen.height() - margin - WINDOW_HEIGHT
    pet.move(x_pos, y_pos)

    logger.debug("Started %s pos=(%d,%d)", theme.role_names.manager, x_pos, y_pos)
    pet.show_bubble(random.choice(theme.manager_welcome_messages), 'normal')

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()
