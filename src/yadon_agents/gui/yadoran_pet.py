#!/usr/bin/env python3
"""ヤドラン デスクトップペット

BasePet を継承。ヤドン版より単純（やるきスイッチなし）。
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

from yadon_agents import PROJECT_ROOT
from yadon_agents.config.agent import YADORAN_MESSAGES, YADORAN_WELCOME_MESSAGES, get_yadon_count
from yadon_agents.config.ui import WINDOW_WIDTH, WINDOW_HEIGHT
from yadon_agents.gui.base_pet import BasePet
from yadon_agents.gui.agent_thread import AgentThread
from yadon_agents.gui.yadoran_pixel_data import build_yadoran_pixel_data
from yadon_agents.agent.manager import YadoranManager
from yadon_agents.infra.protocol import pet_socket_path

logger = logging.getLogger(__name__)


class YadoranPet(BasePet):
    """ヤドラン デスクトップペット。"""

    def __init__(self):
        super().__init__(
            label_text="ヤドラン",
            pixel_data=build_yadoran_pixel_data(),
            messages=YADORAN_MESSAGES,
        )

        # Start agent + pet socket servers
        manager = YadoranManager(str(PROJECT_ROOT))
        agent_thread = AgentThread(manager)
        self.start_servers(pet_socket_path("yadoran"), agent_thread)


def _signal_handler(signum, frame):
    QApplication.quit()
    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description='ヤドラン デスクトップペット')
    parser.parse_args()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    app = QApplication(sys.argv)

    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    screen_obj = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
    screen = screen_obj.geometry()

    pet = YadoranPet()

    margin = 20
    spacing = 10
    x_pos = screen.width() - margin - (WINDOW_WIDTH + spacing) * (get_yadon_count() + 1)
    y_pos = screen.height() - margin - WINDOW_HEIGHT
    pet.move(x_pos, y_pos)

    logger.debug("Started ヤドラン pos=(%d,%d)", x_pos, y_pos)
    pet.show_bubble(random.choice(YADORAN_WELCOME_MESSAGES), 'normal')

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()
