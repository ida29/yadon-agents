"""ドメイン型定義"""

from __future__ import annotations

from enum import Enum

__all__ = ["AgentRole"]


class AgentRole(str, Enum):
    YADOKING = "yadoking"
    YADORAN = "yadoran"
    YADON = "yadon"
