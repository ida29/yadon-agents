"""マネージャー デスクトップペット

BasePet を継承。ワーカー版より単純（やるきスイッチなし）。
"""

from __future__ import annotations

import logging

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
