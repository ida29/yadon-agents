"""ワーカー デスクトップペット

BasePet を継承し、やるきスイッチとワーカー固有メッセージを追加。
"""

from __future__ import annotations

import logging

from yadon_agents.config.agent import get_yadon_messages
from yadon_agents.config.ui import (
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
