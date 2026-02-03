"""後方互換エイリアス: ClaudeRunnerPort → LLMRunnerPort

LLMRunnerPort へ名前を統一したため、既存コードとの互換性を保つ。
"""

from __future__ import annotations

from yadon_agents.domain.ports.llm_port import LLMRunnerPort

__all__ = ["ClaudeRunnerPort"]

ClaudeRunnerPort = LLMRunnerPort
