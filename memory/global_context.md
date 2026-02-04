# ヤドン・エージェント Learning Log

## Session Learnings

### Common Mistakes Caught & Fixed
- Socket cleanup timing（must use finally blocks）
- JSON parsing edge cases（地の文混在対応 in _extract_json）
- PyQt6 thread safety（use pyqtSignal, not direct callbacks）
- Theme cache reset in tests（PIXEL_DATA_CACHE.clear() in setup_method）

### Performance Notes
- Tests complete in ~0.08s（102 tests）
- CLAUDE.md reduced from 70KB to 8KB for better performance

### Debugging Commands
- Check agent status: yadon status
- View socket files: ls -la /tmp/yadon-*.sock
- Tail logs: tail -f ~/.yadon-agents/logs/*.log
- Run tests: python -m pytest tests/ -v

### Architecture Decisions
- Port & Adapter pattern for LLM runner injection
- BaseAgent try-finally for resource cleanup
- 3-phase task decomposition (implement → docs → review)
- GUI daemon separated from CLI process
