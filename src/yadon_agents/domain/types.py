"""ドメイン型定義"""

from enum import Enum


class AgentRole(str, Enum):
    YADOKING = "yadoking"
    YADORAN = "yadoran"
    YADON = "yadon"


YADON_COUNT = 4
