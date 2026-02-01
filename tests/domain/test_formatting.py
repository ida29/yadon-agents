"""summarize_for_bubble のテスト"""

from yadon_agents.domain.formatting import summarize_for_bubble


class TestSummarizeForBubble:
    def test_short_text_unchanged(self):
        assert summarize_for_bubble("hello") == "hello"

    def test_truncates_long_text(self):
        text = "a" * 50
        result = summarize_for_bubble(text)
        assert result == "a" * 30 + "..."

    def test_absolute_path_shortened(self):
        text = "edit /Users/yida/work/project/README.md"
        result = summarize_for_bubble(text)
        assert "README.md" in result
        assert "/Users/yida" not in result

    def test_multiple_paths_shortened(self):
        text = "/Users/a/b.py と /home/c/d.py"
        result = summarize_for_bubble(text)
        assert "b.py" in result
        assert "d.py" in result
        assert "/Users/" not in result
        assert "/home/" not in result

    def test_custom_max_len(self):
        text = "abcdefghij"
        result = summarize_for_bubble(text, max_len=5)
        assert result == "abcde..."

    def test_empty_string(self):
        assert summarize_for_bubble("") == ""

    def test_relative_path_unchanged(self):
        text = "src/main.py"
        assert summarize_for_bubble(text) == "src/main.py"
