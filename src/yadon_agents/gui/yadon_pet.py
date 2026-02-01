#!/usr/bin/env python3
"""ヤドン デスクトップペット

BasePet を継承し、やるきスイッチとヤドン固有メッセージを追加。
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
from yadon_agents.config.agent import (
    RANDOM_MESSAGES, WELCOME_MESSAGES,
    YARUKI_SWITCH_MODE,
    YARUKI_SWITCH_ON_MESSAGE, YARUKI_SWITCH_OFF_MESSAGE,
    YARUKI_MENU_ON_TEXT, YARUKI_MENU_OFF_TEXT,
    get_yadon_count, get_yadon_messages, get_yadon_variant,
)
from yadon_agents.config.ui import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    FACE_ANIMATION_INTERVAL, FACE_ANIMATION_INTERVAL_FAST,
)
from yadon_agents.gui.base_pet import BasePet
from yadon_agents.gui.agent_thread import AgentThread
from yadon_agents.gui.pixel_data import build_pixel_data
from yadon_agents.gui.pokemon_menu import PokemonMenu
from yadon_agents.agent.worker import YadonWorker
from yadon_agents.infra.protocol import pet_socket_path

logger = logging.getLogger(__name__)


class YadonPet(BasePet):
    """ヤドン デスクトップペット。やるきスイッチ付き。"""

    def __init__(self, yadon_number: int, variant: str = 'normal'):
        self.yadon_number = yadon_number
        self.variant = variant
        self.yaruki_switch_mode = bool(YARUKI_SWITCH_MODE)

        messages = get_yadon_messages(yadon_number) + RANDOM_MESSAGES

        super().__init__(
            label_text=f"ヤドン{yadon_number}",
            pixel_data=build_pixel_data(variant),
            messages=messages,
        )

        # Start agent + pet socket servers
        worker = YadonWorker(yadon_number, str(PROJECT_ROOT))
        agent_thread = AgentThread(worker)
        self.start_servers(pet_socket_path(str(yadon_number)), agent_thread)

    def _build_menu_items(self, menu: PokemonMenu) -> None:
        toggle_text = YARUKI_MENU_OFF_TEXT if self.yaruki_switch_mode else YARUKI_MENU_ON_TEXT
        menu.add_item(toggle_text, 'toggle_yaruki')
        menu.add_item('とじる', 'close')

    def _handle_menu_action(self, action_id: str) -> None:
        if action_id == 'toggle_yaruki':
            self.yaruki_switch_mode = not self.yaruki_switch_mode
            if self.yaruki_switch_mode:
                message = YARUKI_SWITCH_ON_MESSAGE
                bubble_type = 'claude'
            else:
                message = YARUKI_SWITCH_OFF_MESSAGE
                bubble_type = 'normal'
            self._update_animation_speed()
            self.show_bubble(message, bubble_type, display_time=3000)

    def _update_animation_speed(self) -> None:
        interval = FACE_ANIMATION_INTERVAL_FAST if self.yaruki_switch_mode else FACE_ANIMATION_INTERVAL
        if hasattr(self, 'timer') and self.timer is not None:
            if self.timer.isActive():
                self.timer.stop()
            self.timer.start(interval)


def _signal_handler(signum, frame):
    QApplication.quit()
    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description='ヤドン デスクトップペット')
    parser.add_argument('--number', type=int, required=True, help='ヤドン番号 (1-N)')
    parser.add_argument('--variant', default=None, help='カラーバリアント')
    args = parser.parse_args()

    variant = args.variant or get_yadon_variant(args.number)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    app = QApplication(sys.argv)

    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    screen_obj = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
    screen = screen_obj.geometry()

    pet = YadonPet(yadon_number=args.number, variant=variant)

    margin = 20
    spacing = 10
    x_pos = screen.width() - margin - (WINDOW_WIDTH + spacing) * args.number
    y_pos = screen.height() - margin - WINDOW_HEIGHT
    pet.move(x_pos, y_pos)

    logger.debug("Started ヤドン%d variant=%s pos=(%d,%d)", args.number, variant, x_pos, y_pos)
    pet.show_bubble(random.choice(WELCOME_MESSAGES), 'normal')

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()
