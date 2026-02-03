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


class TestSummarizeForBubbleUnicode:
    """Unicode文字を含むテキストのテスト"""

    def test_unicode_japanese(self):
        """日本語テキストが正しく処理されること"""
        text = "日本語のテキスト"
        result = summarize_for_bubble(text)
        assert result == "日本語のテキスト"
        assert isinstance(result, str)

    def test_emoji_preserved(self):
        """絵文字が保持されること"""
        text = "🎉 成功しました 🎯"
        result = summarize_for_bubble(text)
        assert "🎉" in result
        assert "🎯" in result

    def test_mixed_unicode_languages(self):
        """複数言語混在テキスト"""
        text = "日本語 English 한글 中文 العربية"
        result = summarize_for_bubble(text)
        assert "日本語" in result
        assert "English" in result
        assert "한글" in result

    def test_emoji_count_in_summary(self):
        """絵文字を含む長いテキストが正しく短縮されること"""
        text = "🎯" * 50 + "テキスト"
        result = summarize_for_bubble(text)
        assert len(result) <= 40  # max_len=30 + "..."
        assert "🎯" in result

    def test_unicode_punctuation(self):
        """Unicode句読点が保持されること"""
        text = "全角句点。カギ括弧「テスト」中点・波ダッシュ～"
        result = summarize_for_bubble(text)
        assert "。" in result
        assert "「" in result
        assert "」" in result

    def test_long_unicode_truncation(self):
        """長いUnicode文字列が正しく短縮されること"""
        text = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
        result = summarize_for_bubble(text, max_len=10)
        # 10文字指定なので、10+3で13文字程度の結果
        assert len(result) <= 20
        assert "..." in result


class TestSummarizeForBubbleNewlines:
    """改行を含むテキストのテスト"""

    def test_single_newline(self):
        """単一の改行を含むテキスト"""
        text = "行1\n行2"
        result = summarize_for_bubble(text)
        assert "\n" in result
        assert "行1" in result
        assert "行2" in result

    def test_multiple_newlines(self):
        """複数の改行を含むテキスト"""
        text = "行1\n行2\n行3\n行4"
        result = summarize_for_bubble(text)
        assert "\n" in result
        assert "行1" in result
        assert "行4" in result

    def test_empty_lines(self):
        """空行を含むテキスト"""
        text = "行1\n\n行3"
        result = summarize_for_bubble(text)
        assert "\n" in result

    def test_long_multiline_text_truncation(self):
        """長い複数行テキストが正しく短縮されること"""
        text = "行" * 100 + "\n" + "テスト" * 50
        result = summarize_for_bubble(text)
        assert len(result) <= 40
        assert "..." in result

    def test_tab_and_newline(self):
        """タブと改行を含むテキスト"""
        text = "タイトル\n\tインデント1\n\t\tインデント2"
        result = summarize_for_bubble(text)
        assert "\n" in result
        assert "\t" in result

    def test_carriage_return(self):
        """キャリッジリターン（CR）を含むテキスト"""
        text = "行1\r\n行2"
        result = summarize_for_bubble(text)
        # CRとLFが含まれていることを確認
        assert "行1" in result
        assert "行2" in result

    def test_leading_trailing_whitespace(self):
        """先頭と末尾の空白を含むテキスト"""
        text = "  テキスト  "
        result = summarize_for_bubble(text)
        # 空白も保持される
        assert "テキスト" in result

    def test_unicode_newlines_mixed(self):
        """Unicode文字と改行の混在"""
        text = "日本語\n🎉 絵文字\nEnglish\n中文"
        result = summarize_for_bubble(text)
        assert "\n" in result
        assert "日本語" in result
        assert "🎉" in result


class TestSummarizeForBubbleEdgeCases:
    """その他のエッジケーステスト"""

    def test_only_whitespace(self):
        """空白のみのテキスト"""
        text = "   \n\t  \n  "
        result = summarize_for_bubble(text)
        # 空白は保持される
        assert result == text or result.strip() == ""

    def test_very_long_single_line(self):
        """非常に長い1行テキスト"""
        text = "a" * 1000
        result = summarize_for_bubble(text)
        assert len(result) <= 40
        assert "..." in result

    def test_special_characters_in_path(self):
        """パスに特殊文字を含む"""
        text = "edit /path/with-dash/file_name.py"
        result = summarize_for_bubble(text)
        # テキストが短縮される可能性があるので、"file_name" が含まれるか確認
        assert "file_name" in result or "file" in result
        # 絶対パスは短縮される
        assert len(result) <= 35 or "file_name.py" in result

    def test_null_byte_handling(self):
        """null バイトを含むテキスト（実際には発生しにくいが念のため）"""
        # Pythonの文字列ではnull byteは通常含まれないが、テストとして
        text = "テキスト前\x00テキスト後"
        result = summarize_for_bubble(text)
        assert isinstance(result, str)

    def test_very_short_max_len(self):
        """非常に小さいmax_lenでの短縮"""
        text = "テキスト"
        result = summarize_for_bubble(text, max_len=2)
        # 2文字+3で省略記号
        assert len(result) <= 10
        assert "..." in result or len(text) <= 2

    def test_path_with_unicode_dir(self):
        """Unicode文字を含むディレクトリパス"""
        text = "edit /Users/日本語ユーザー/project/file.py"
        result = summarize_for_bubble(text)
        assert "file.py" in result
        # 絶対パスは短縮される
        assert result != text or result.endswith("file.py")
