#!/usr/bin/env python3
"""ワーカー デスクトップペット

BasePet を継承し、やるきスイッチとワーカー固有メッセージを追加。
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

from yadon_agents.config.agent import get_yadon_messages
from yadon_agents.config.ui import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    FACE_ANIMATION_INTERVAL, FACE_ANIMATION_INTERVAL_FAST,
)
from yadon_agents.gui.base_pet import BasePet
from yadon_agents.gui.agent_thread import AgentThread
from yadon_agents.gui.pixel_data import build_pixel_data
from yadon_agents.gui.pokemon_menu import PokemonMenu
from yadon_agents.themes import get_theme

logger = logging.getLogger(__name__)


class YadonPet(BasePet):
    """ワーカー デスクトップペット。やるきスイッチ付き（テーマで制御）。"""

    def __init__(
        self,
        yadon_number: int,
        agent_thread: AgentThread,
        pet_sock_path: str,
        variant: str = 'normal',
    ):
        self.yadon_number = yadon_number
        self.variant = variant
        theme = get_theme()
        self._theme = theme
        self.yaruki_switch_mode = theme.yaruki_switch.enabled

        messages = get_yadon_messages(yadon_number) + theme.random_messages

        super().__init__(
            label_text=f"{theme.role_names.worker}{yadon_number}",
            pixel_data=build_pixel_data(variant),
            messages=messages,
        )

        self.start_servers(pet_sock_path, agent_thread)

    def _build_menu_items(self, menu: PokemonMenu) -> None:
        yaruki = self._theme.yaruki_switch
        if yaruki.menu_on_text and yaruki.menu_off_text:
            toggle_text = yaruki.menu_off_text if self.yaruki_switch_mode else yaruki.menu_on_text
            menu.add_item(toggle_text, 'toggle_yaruki')
        menu.add_item('とじる', 'close')

    def _handle_menu_action(self, action_id: str) -> None:
        if action_id == 'toggle_yaruki':
            yaruki = self._theme.yaruki_switch
            self.yaruki_switch_mode = not self.yaruki_switch_mode
            if self.yaruki_switch_mode:
                message = yaruki.on_message
                bubble_type = 'claude'
            else:
                message = yaruki.off_message
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


def main() -> None:
    # --- Composition Root: 具体的な依存の組み立て ---
    from yadon_agents import PROJECT_ROOT
    from yadon_agents.agent.worker import YadonWorker
    from yadon_agents.config.agent import get_yadon_variant
    from yadon_agents.infra.protocol import pet_socket_path

    theme = get_theme()

    parser = argparse.ArgumentParser(description=f'{theme.role_names.worker} デスクトップペット')
    parser.add_argument('--number', type=int, required=True, help=f'{theme.role_names.worker}番号 (1-N)')
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

    # 具体的なエージェント構築（composition root）
    worker = YadonWorker(args.number, str(PROJECT_ROOT))
    agent_thread = AgentThread(worker)

    pet = YadonPet(
        yadon_number=args.number,
        agent_thread=agent_thread,
        pet_sock_path=pet_socket_path(str(args.number), prefix=theme.socket_prefix),
        variant=variant,
    )

    margin = 20
    spacing = 10
    x_pos = screen.width() - margin - (WINDOW_WIDTH + spacing) * args.number
    y_pos = screen.height() - margin - WINDOW_HEIGHT
    pet.move(x_pos, y_pos)

    logger.debug("Started %s%d variant=%s pos=(%d,%d)", theme.role_names.worker, args.number, variant, x_pos, y_pos)
    pet.show_bubble(random.choice(theme.welcome_messages), 'normal')

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()
