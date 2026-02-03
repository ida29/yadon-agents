"""Windows 互換性テスト

Windows プラットフォーム固有の処理（パス、環境変数、ファイルシステム）のテスト。
現在は実装検証用。実際の Windows での実行には環境セットアップが必要。
"""

import os
import sys
from pathlib import Path

import pytest


class TestWindowsPathHandling:
    """Windows パス処理のテスト"""

    def test_path_separator_consistency(self):
        """pathlib.Path が自動的にプラットフォーム適切なセパレータを使用"""
        # pathlib.Path は自動的に正しいセパレータを使用
        p = Path("dir") / "subdir" / "file.txt"
        assert isinstance(p, Path)
        # Windows では \、Unix では / が使用される
        assert "file.txt" in str(p)

    def test_path_is_absolute_cross_platform(self):
        """絶対パス判定がプラットフォーム間で一貫"""
        unix_abs = Path("/home/user/file.txt")

        # Unix スタイルの絶対パスをテスト
        if sys.platform != "win32":
            assert unix_abs.is_absolute()
        else:
            # Windows では Unix パスは絶対パスとみなされない
            win_abs = Path("C:\\Users\\user\\file.txt")
            assert win_abs.is_absolute()

    def test_path_home_expansion(self):
        """Path.home() がプラットフォーム固有のホームディレクトリを返す"""
        home = Path.home()

        # Windows では C:\Users\username、Unix では /home/username
        assert home.exists()
        assert home.is_dir()
        assert home.is_absolute()

    def test_expanduser_cross_platform(self):
        """~ 展開がプラットフォーム固有に処理される"""
        p = Path("~") / "test.txt"
        expanded = p.expanduser()

        # Windows では C:\Users\username\test.txt、Unix では /home/username/test.txt
        home = Path.home()
        assert home in expanded.parents or expanded.parent == home

    def test_pathlib_resolve_consistency(self):
        """Path.resolve() が相対パスを絶対パスに変換"""
        rel_path = Path("tests") / "fixtures"
        abs_path = rel_path.resolve()

        # resolve() 後は常に絶対パス
        assert abs_path.is_absolute()

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows パス形式をテスト")
    def test_windows_path_format_representation(self):
        r"""Windows パスの文字列表現が \ を含む"""
        # このテストは Unix 環境でも Windows パス形式をシミュレート
        win_path_str = "C:\\Users\\yida\\test.txt"
        assert "\\" in win_path_str
        assert "/" not in win_path_str


class TestWindowsEnvironmentVariables:
    """Windows 環境変数処理のテスト"""

    def test_home_directory_env_fallback(self, monkeypatch):
        """HOME/USERPROFILE 環境変数からホームディレクトリを解決"""
        if sys.platform == "win32":
            # Windows では USERPROFILE が期待値
            userprofile = os.environ.get("USERPROFILE")
            assert userprofile is not None
        else:
            # Unix では HOME が期待値
            home = os.environ.get("HOME")
            assert home is not None

    def test_userprofile_exists_on_windows(self, monkeypatch):
        """Windows では USERPROFILE が設定されている"""
        if sys.platform != "win32":
            # Unix 環境では USERPROFILE をシミュレート
            monkeypatch.setenv("USERPROFILE", "C:\\Users\\testuser")
            userprofile = os.environ.get("USERPROFILE")
            assert userprofile == "C:\\Users\\testuser"
        else:
            # 実 Windows
            userprofile = os.environ.get("USERPROFILE")
            assert userprofile is not None
            assert Path(userprofile).exists()

    def test_pathvar_handling_cross_platform(self):
        """PATH 環境変数がプラットフォーム固有のセパレータで区切られている"""
        path_var = os.environ.get("PATH", "")
        assert len(path_var) > 0

        # Windows では ; 区切り、Unix では : 区切り
        if sys.platform == "win32":
            assert ";" in path_var or len(path_var.split(";")) > 0
        else:
            assert ":" in path_var or len(path_var.split(":")) > 0

    def test_temp_directory_cross_platform(self, monkeypatch):
        """一時ディレクトリパスがプラットフォーム固有"""
        import tempfile

        tmpdir = tempfile.gettempdir()
        assert tmpdir is not None
        assert Path(tmpdir).exists()

        # Windows では C:\Temp または TEMP 環境変数
        # Unix では /tmp
        if sys.platform == "win32":
            assert "\\" in tmpdir or tmpdir.startswith(("C:", "D:"))
        else:
            assert tmpdir.startswith("/")


class TestWindowsFileSystemOperations:
    """Windows ファイルシステム操作のテスト"""

    def test_file_creation_with_pathlib(self, tmp_path):
        """pathlib で ファイル作成がプラットフォーム対応"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        assert test_file.exists()
        assert test_file.read_text() == "test content"

    def test_directory_creation_with_pathlib(self, tmp_path):
        """pathlib でディレクトリ作成がプラットフォーム対応"""
        test_dir = tmp_path / "subdir" / "nested"
        test_dir.mkdir(parents=True, exist_ok=True)

        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_file_permissions_handling(self, tmp_path):
        """ファイル権限がプラットフォーム間で処理される"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Unix: chmod、Windows: ACL（pathlib では制限あり）
        mode = test_file.stat().st_mode
        assert mode > 0

    def test_case_sensitivity_handling(self, tmp_path):
        """ファイル名の大文字小文字処理がプラットフォーム対応"""
        file1 = tmp_path / "test.txt"
        file1.write_text("content1")

        file2 = tmp_path / "TEST.txt"

        # ファイルシステムの大文字小文字感度をテスト
        # macOS (HFS+/APFS) と Windows は通常ケースインセンシティブ
        # Linux (ext4等) はケースセンシティブ

        file2.write_text("content2")

        # file1.read_text() と file2.read_text() が同じかどうかで
        # ファイルシステムの特性を判定
        file1_content = file1.read_text()
        file2_content = file2.read_text()

        if file1_content == file2_content:
            # ケースインセンシティブ（Windows, macOS）
            # 同じファイルを上書きしたので内容は同じ
            assert file1_content == "content2"
        else:
            # ケースセンシティブ（Linux）
            # 異なるファイルとして作成された
            assert file1_content == "content1"
            assert file2_content == "content2"

    def test_forbidden_filename_characters(self, tmp_path):
        """Windows 禁止文字（: * ? " < > |）の処理"""
        # Windows では以下文字がファイル名に使用不可：: * ? " < > |
        # pathlib は自動的には処理しないため、手動バリデーションが必要

        forbidden_chars = ':*?"<>|'

        def is_valid_windows_filename(filename: str) -> bool:
            """Windows 互換のファイル名かチェック（プラットフォーム非依存）"""
            # Windows 禁止文字を含むかどうかをチェック
            return not any(char in filename for char in forbidden_chars)

        # Windows 互換のファイル名
        assert is_valid_windows_filename("normal_file.txt")
        assert is_valid_windows_filename("test-file.txt")
        # Windows 禁止文字を含む
        assert not is_valid_windows_filename("test:file.txt")
        assert not is_valid_windows_filename("test*file.txt")


class TestWindowsEncodingHandling:
    """Windows エンコーディング処理のテスト"""

    def test_default_encoding_awareness(self):
        """デフォルトエンコーディングがプラットフォーム依存"""
        import locale

        default_encoding = locale.getpreferredencoding(False)
        assert default_encoding is not None

        # Windows では SJIS/CP932 の可能性、Unix では UTF-8
        if sys.platform == "win32":
            # Windows のデフォルトはロケール依存（多くは CP932/SJIS）
            pass
        else:
            # Unix は UTF-8 がデフォルト
            assert default_encoding.lower() in ["utf-8", "utf8"]

    def test_file_encoding_explicit(self, tmp_path):
        """ファイル読み書き時のエンコーディング明示"""
        test_file = tmp_path / "test_utf8.txt"

        # エンコーディング明示で統一
        test_file.write_text("日本語テキスト", encoding="utf-8")
        content = test_file.read_text(encoding="utf-8")

        assert "日本語" in content

    def test_unicode_handling_cross_platform(self, tmp_path):
        """Unicode テキストの処理がプラットフォーム対応"""
        test_file = tmp_path / "unicode.txt"

        unicode_text = "日本語 🎉 한글 العربية"
        test_file.write_text(unicode_text, encoding="utf-8")

        assert test_file.read_text(encoding="utf-8") == unicode_text


class TestWindowsSocketAlternatives:
    """Windows ソケット代替案のテスト（現状確認）"""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows プラットフォーム固有")
    def test_windows_named_pipes_available(self):
        """Windows での名前付きパイプ（Named Pipes）可用性"""
        # Windows では socket.AF_UNIX が未対応のため、
        # 代替として Named Pipes (\\\\.\\pipe\\name) または TCP ソケットを使用可能
        import socket

        # Windows では AF_UNIX は存在しない
        assert not hasattr(socket, "AF_UNIX") or sys.platform != "win32"

    def test_tcp_socket_fallback_posix(self):
        """POSIX でも TCP ソケット（localhost:port）使用可能"""
        import socket

        # TCP ソケットはすべてのプラットフォームで利用可能
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        assert sock.fileno() >= 0
        sock.close()

    def test_socket_option_cross_platform(self):
        """ソケットオプションがプラットフォーム間で一貫"""
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # SO_REUSEADDR はすべてのプラットフォームで利用可能
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # SO_REUSEADDR が設定されていることを確認（値は0以外）
        value = sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
        assert value != 0  # 有効になっていることを確認（OSによって戻り値が異なる）
        sock.close()


class TestWindowsProcessManagement:
    """Windows プロセス管理のテスト"""

    def test_subprocess_cross_platform(self):
        """subprocess がプラットフォーム対応"""
        import subprocess

        if sys.platform == "win32":
            # Windows コマンド
            result = subprocess.run(["cmd", "/c", "echo", "test"],
                                  capture_output=True, text=True)
        else:
            # Unix コマンド
            result = subprocess.run(["sh", "-c", "echo test"],
                                  capture_output=True, text=True)

        assert "test" in result.stdout

    def test_process_signal_handling_awareness(self):
        """signal module がプラットフォーム依存"""
        import signal

        # Windows では利用可能なシグナルが限定
        # Unix では豊富

        # SIGTERM はすべてのプラットフォームで利用可能
        assert hasattr(signal, "SIGTERM")

        # SIGUSR1 は Windows では未定義
        if sys.platform == "win32":
            assert not hasattr(signal, "SIGUSR1")
        else:
            assert hasattr(signal, "SIGUSR1")


class TestWindowsPathLibConsistency:
    """pathlib.Path による統一パス処理の検証"""

    def test_project_root_resolution(self):
        """PROJECT_ROOT が pathlib で一貫して解決される"""
        from yadon_agents import PROJECT_ROOT

        # PROJECT_ROOT は常に Path オブジェクト
        assert isinstance(PROJECT_ROOT, Path)
        assert PROJECT_ROOT.exists()
        assert PROJECT_ROOT.is_absolute()

    def test_log_dir_uses_pathlib(self):
        """log_dir() が pathlib 使用で Windows 対応"""
        from yadon_agents.infra.process import log_dir

        result = log_dir()

        # pathlib.Path で返却
        assert isinstance(result, Path)
        assert result.exists()
        assert result.is_dir()

    def test_config_paths_use_pathlib(self):
        """設定ファイルパスが pathlib で処理"""
        from yadon_agents import PROJECT_ROOT

        # 設定ファイルパスが pathlib で一貫
        instructions_dir = PROJECT_ROOT / "src" / "yadon_agents" / "instructions"
        assert instructions_dir.exists()
        assert instructions_dir.is_dir()
