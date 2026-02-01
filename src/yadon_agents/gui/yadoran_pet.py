#!/usr/bin/env python3
"""ヤドラン デスクトップペット

BasePet を継承。ヤドン版より単純（やるきスイッチなし）。
"""

import argparse
import os
import random
import signal
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCursor

from yadon_agents.config.agent import YADORAN_MESSAGES, YADORAN_WELCOME_MESSAGES
from yadon_agents.config.ui import WINDOW_WIDTH, WINDOW_HEIGHT
from yadon_agents.gui.base_pet import BasePet
from yadon_agents.gui.agent_thread import AgentThread
from yadon_agents.gui.yadoran_pixel_data import build_yadoran_pixel_data
from yadon_agents.gui.utils import log_debug
from yadon_agents.agent.manager import YadoranManager
from yadon_agents.infra.protocol import pet_socket_path


class YadoranPet(BasePet):
    """ヤドラン デスクトップペット。"""

    def __init__(self):
        super().__init__(
            label_text="ヤドラン",
            pixel_data=build_yadoran_pixel_data(),
            messages=YADORAN_MESSAGES,
        )

        # Start agent + pet socket servers
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )))
        manager = YadoranManager(project_dir)
        agent_thread = AgentThread(manager)
        self.start_servers(pet_socket_path("yadoran"), agent_thread)


def _signal_handler(sig, frame):
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
    x_pos = screen.width() - margin - (WINDOW_WIDTH + spacing) * 5
    y_pos = screen.height() - margin - WINDOW_HEIGHT
    pet.move(x_pos, y_pos)

    log_debug("yadoran_pet", f"Started ヤドラン pos=({x_pos},{y_pos})")
    pet.show_bubble(random.choice(YADORAN_WELCOME_MESSAGES), 'normal')

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()
