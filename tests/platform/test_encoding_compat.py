"""エンコーディング・文字列処理のクロスプラットフォームテスト

UTF-8、SJIS、ロケール固有の文字列処理がプラットフォーム間で一貫することを確認。
"""

import locale
import sys
from pathlib import Path

import pytest


class TestUTF8Consistency:
    """UTF-8 エンコーディングのクロスプラットフォーム一貫性"""

    def test_utf8_encode_decode_consistency(self):
        """UTF-8 エンコード・デコードが可逆的"""
        original_text = "日本語テキスト 🎉 English"

        # エンコード → デコード
        encoded = original_text.encode("utf-8")
        decoded = encoded.decode("utf-8")

        assert decoded == original_text

    def test_utf8_file_io(self, tmp_path):
        """UTF-8 ファイル I/O がプラットフォーム対応"""
        test_file = tmp_path / "utf8_test.txt"
        test_text = "日本語 🎉 한글 العربية"

        # 書き込み
        test_file.write_text(test_text, encoding="utf-8")

        # 読み込み
        read_text = test_file.read_text(encoding="utf-8")

        assert read_text == test_text

    def test_utf8_bytes_preservation(self):
        """UTF-8 バイト列が多プラットフォーム間で同一"""
        text = "テスト"

        # Windows でも Unix でも同じ UTF-8 バイト列
        utf8_bytes = text.encode("utf-8")
        assert utf8_bytes == b'\xe3\x83\x86\xe3\x82\xb9\xe3\x83\x88'

        # デコード可能
        decoded = utf8_bytes.decode("utf-8")
        assert decoded == text

    def test_utf8_bom_handling(self):
        """UTF-8 BOM（Byte Order Mark）処理"""
        text = "テスト"

        # UTF-8 with BOM でエンコード
        utf8_bom = text.encode("utf-8-sig")

        # BOM は先頭 3 バイト
        assert utf8_bom.startswith(b'\xef\xbb\xbf')

        # utf-8-sig でデコード時 BOM は削除される
        decoded = utf8_bom.decode("utf-8-sig")
        assert decoded == text  # BOM なし

        # 通常の utf-8 でデコードすると BOM 文字が残る
        decoded_with_bom = utf8_bom.decode("utf-8")
        assert decoded_with_bom.startswith("\ufeff")


class TestUnicodeNormalization:
    """Unicode 正規化のクロスプラットフォーム処理"""

    def test_nfc_normalization(self):
        """NFC（Normalization Form C）正規化"""
        import unicodedata

        # 合成可能な文字
        decomposed = "é"  # e + combining acute accent
        composed = "é"    # single precomposed character

        # NFC 正規化で統一
        nfc_decomposed = unicodedata.normalize("NFC", decomposed)
        nfc_composed = unicodedata.normalize("NFC", composed)

        # 正規化後は同一
        assert nfc_decomposed == nfc_composed

    def test_nfd_normalization(self):
        """NFD（Normalization Form D）正規化"""
        import unicodedata

        # 合成文字
        text = "café"

        # NFD で分解
        nfd = unicodedata.normalize("NFD", text)
        # NFC で再合成
        nfc = unicodedata.normalize("NFC", nfd)

        # NFC で正規化後は同一
        assert nfc == text

    def test_combining_characters(self):
        """結合文字の処理"""
        import unicodedata

        # 基本文字 + 結合記号
        base = "a"
        combining_acute = "\u0301"  # combining acute accent
        combined = base + combining_acute

        # 結合文字は複数バイト
        assert len(combined) == 2
        assert len(combined.encode("utf-8")) > 1


class TestLocaleSpecificString:
    """ロケール固有の文字列処理"""

    def test_default_encoding_awareness(self):
        """デフォルトエンコーディングがプラットフォーム・ロケール依存"""
        default_encoding = locale.getpreferredencoding(False)

        # エンコーディング名が有効
        assert default_encoding is not None
        assert len(default_encoding) > 0

        # テキストをこのエンコーディングでエンコード可能（日本語ASCII互換テキスト）
        test_text = "hello"
        try:
            encoded = test_text.encode(default_encoding)
            assert encoded is not None
        except (LookupError, UnicodeEncodeError):
            # ロケール言語に対応していない可能性
            pass

    def test_filesystem_default_encoding(self):
        """ファイルシステムのデフォルトエンコーディング"""
        import sys

        # sys.getfilesystemencoding() がプラットフォーム固有
        fs_encoding = sys.getfilesystemencoding()

        if sys.platform == "win32":
            # Windows では utf-8 または mbcs (ANSI)
            assert fs_encoding.lower() in ["utf-8", "mbcs", "cp932"]
        else:
            # Unix/Linux では utf-8
            assert fs_encoding.lower() in ["utf-8", "utf8"]

    def test_stdin_stdout_encoding(self):
        """標準入出力のエンコーディング"""
        import sys

        # stdin/stdout のエンコーディング
        stdin_encoding = sys.stdin.encoding
        stdout_encoding = sys.stdout.encoding

        # 両方がエンコーディング名を持つ
        assert stdin_encoding is not None or stdout_encoding is not None


class TestStringComparison:
    """クロスプラットフォーム文字列比較"""

    def test_case_sensitive_comparison(self):
        """大文字小文字区別"""
        text1 = "Test"
        text2 = "test"

        # Python の文字列比較は常に大文字小文字を区別
        assert text1 != text2

    def test_whitespace_handling(self):
        """空白文字の処理"""
        # 異なる空白文字
        space = " "          # U+0020 SPACE
        nbsp = "\u00A0"      # U+00A0 NO-BREAK SPACE
        em_space = "\u2003"  # U+2003 EM SPACE

        # 異なる文字として認識
        assert space != nbsp
        assert nbsp != em_space

    def test_line_ending_handling(self):
        """改行文字の処理"""
        # 異なる改行
        lf = "line1\nline2"      # Unix: LF
        crlf = "line1\r\nline2"  # Windows: CRLF
        cr = "line1\rline2"      # Old Mac: CR

        # 異なる文字列として保持
        assert lf != crlf
        assert crlf != cr

    def test_unicode_escape_sequences(self):
        """Unicode エスケープシーケンス"""
        # 異なる表記方法
        literal = "日本語"
        escaped = "\u65e5\u672c\u8a9e"

        # 同一文字として認識
        assert literal == escaped


class TestStringFormatting:
    """プラットフォーム別文字列フォーマット"""

    def test_format_with_unicode(self):
        """Unicode を含むフォーマット"""
        template = "Hello {name} 🎉"
        result = template.format(name="世界")

        assert "世界" in result
        assert "🎉" in result

    def test_f_string_with_unicode(self):
        """f-string での Unicode 処理"""
        name = "テスト"
        result = f"結果: {name}"

        assert "テスト" in result
        assert "結果" in result

    def test_string_multiplication_with_unicode(self):
        """Unicode 文字の繰り返し"""
        emoji = "🎯"
        repeated = emoji * 5

        assert len(repeated) == 5
        assert "🎯" in repeated


class TestErrorHandling:
    """エンコーディング関連エラーハンドリング"""

    def test_encode_error_handling(self):
        """エンコードエラー処理"""
        text = "Hello 世界 🎉"

        # UTF-8 はすべての文字をエンコード可能
        utf8_result = text.encode("utf-8")
        assert utf8_result is not None

        # ASCII エンコードはエラー
        with pytest.raises(UnicodeEncodeError):
            text.encode("ascii")

    def test_encode_error_strategy(self):
        """エンコードエラーの戦略別処理"""
        text = "Hello 世界"

        # 'replace' strategy: 置換
        result_replace = text.encode("ascii", errors="replace")
        assert b"Hello" in result_replace

        # 'ignore' strategy: スキップ
        result_ignore = text.encode("ascii", errors="ignore")
        assert b"Hello" in result_ignore

        # 'backslashreplace' strategy: バックスラッシュで表現
        result_backslash = text.encode("ascii", errors="backslashreplace")
        assert b"\\u" in result_backslash or b"Hello" in result_backslash

    def test_decode_error_handling(self):
        """デコードエラー処理"""
        # 無効な UTF-8 バイト列
        invalid_utf8 = b'\xff\xfe'

        # デコードエラー
        with pytest.raises(UnicodeDecodeError):
            invalid_utf8.decode("utf-8")

        # 'replace' strategy で置換文字を使用
        result = invalid_utf8.decode("utf-8", errors="replace")
        assert result is not None


class TestFileEncodingMigration:
    """ファイルエンコーディング移行・変換テスト"""

    def test_utf8_to_utf16_conversion(self, tmp_path):
        """UTF-8 → UTF-16 変換"""
        test_file_utf8 = tmp_path / "test_utf8.txt"
        test_file_utf16 = tmp_path / "test_utf16.txt"

        text = "テストテキスト"

        # UTF-8 に書き込み
        test_file_utf8.write_text(text, encoding="utf-8")

        # 読み込み
        read_text = test_file_utf8.read_text(encoding="utf-8")

        # UTF-16 に書き込み
        test_file_utf16.write_text(read_text, encoding="utf-16")

        # UTF-16 から読み込み
        text_from_utf16 = test_file_utf16.read_text(encoding="utf-16")

        assert text == text_from_utf16

    def test_encoding_detection(self):
        """テキストエンコーディングの検出（推定）"""
        # 複数のエンコーディング
        text = "Hello World"

        utf8_bytes = text.encode("utf-8")
        utf16_bytes = text.encode("utf-16")
        sjis_bytes = text.encode("shift_jis")

        # ASCII 互換テキストはすべてのエンコーディングで同一
        assert utf8_bytes == b'Hello World'
        assert sjis_bytes == b'Hello World'

        # UTF-16 は BOM を含む可能性あり
        assert b'H' in utf16_bytes


class TestJapaneseCharacterHandling:
    """日本語文字処理（テスト対象プロジェクト言語）"""

    def test_hiragana_katakana_distinction(self):
        """ひらがな・カタカナ区別"""
        hiragana = "あいうえお"
        katakana = "アイウエオ"

        # 異なる文字として認識
        assert hiragana != katakana

    def test_kanji_handling(self):
        """漢字処理"""
        kanji = "日本語"

        # UTF-8 エンコード
        utf8_bytes = kanji.encode("utf-8")
        assert len(utf8_bytes) == 9  # 3 文字 × 3 バイト

        # デコード可能
        decoded = utf8_bytes.decode("utf-8")
        assert decoded == kanji

    def test_mixed_japanese_english(self):
        """日本語・英語混在テキスト"""
        mixed = "yadon-agents ヤドンエージェント 🎯"

        # 長さは文字数（バイト数ではない）
        assert len(mixed) > 0

        # 各部分を抽出可能
        parts = mixed.split()
        assert len(parts) >= 1

    def test_japanese_punctuation(self):
        """日本語句読点"""
        text = "これはテストです。「はい」と言いました。"

        # 句点 U+3002、読点 U+3001、括弧も含む
        assert "。" in text
        assert "「" in text
        assert "」" in text

    def test_vertical_text_characters(self):
        """縦書き用文字処理"""
        # 仮名の縦書き用文字も処理可能
        text = "これは日本語のテスト"

        # UTF-8 で処理可能
        encoded = text.encode("utf-8")
        decoded = encoded.decode("utf-8")

        assert decoded == text
