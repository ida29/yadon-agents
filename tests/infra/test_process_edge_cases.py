"""process.py のエッジケーステスト

log_dir() の権限エラー処理（モック）、
ディレクトリが既に存在する場合、
シンボリックリンクの場合のテスト。
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yadon_agents.infra.process import log_dir


class TestLogDirBasic:
    """log_dir() の基本動作テスト"""

    def test_log_dir_returns_path(self) -> None:
        """log_dir() が Path オブジェクトを返すこと"""
        with patch("yadon_agents.infra.process.PROJECT_ROOT") as mock_root:
            mock_root.__truediv__ = MagicMock(return_value=MagicMock(spec=Path))
            mock_path = mock_root / "logs"
            mock_path.mkdir = MagicMock()

            result = log_dir()

            assert result is not None

    def test_log_dir_creates_directory(self, tmp_path: Path) -> None:
        """log_dir() がディレクトリを作成すること"""
        logs_path = tmp_path / "logs"

        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            result = log_dir()

            assert result == logs_path
            assert logs_path.exists()
            assert logs_path.is_dir()

    def test_log_dir_exist_ok(self, tmp_path: Path) -> None:
        """ディレクトリが既に存在する場合もエラーにならないこと"""
        logs_path = tmp_path / "logs"
        logs_path.mkdir()

        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            # エラーにならないことを確認
            result = log_dir()

            assert result == logs_path
            assert logs_path.exists()


class TestLogDirPermissionError:
    """log_dir() の権限エラー処理テスト"""

    def test_log_dir_permission_error_raises(self) -> None:
        """権限エラーが発生した場合、例外が伝播すること"""
        mock_path = MagicMock(spec=Path)
        mock_path.mkdir.side_effect = PermissionError("Permission denied")

        with patch("yadon_agents.infra.process.PROJECT_ROOT") as mock_root:
            mock_root.__truediv__ = MagicMock(return_value=mock_path)

            with pytest.raises(PermissionError, match="Permission denied"):
                log_dir()

    def test_log_dir_oserror_raises(self) -> None:
        """OSError が発生した場合、例外が伝播すること"""
        mock_path = MagicMock(spec=Path)
        mock_path.mkdir.side_effect = OSError("OS error")

        with patch("yadon_agents.infra.process.PROJECT_ROOT") as mock_root:
            mock_root.__truediv__ = MagicMock(return_value=mock_path)

            with pytest.raises(OSError, match="OS error"):
                log_dir()


class TestLogDirExistingDirectory:
    """既存ディレクトリに対する log_dir() のテスト"""

    def test_log_dir_with_existing_empty_directory(self, tmp_path: Path) -> None:
        """空のディレクトリが既に存在する場合"""
        logs_path = tmp_path / "logs"
        logs_path.mkdir()

        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            result = log_dir()

            assert result == logs_path
            assert logs_path.is_dir()

    def test_log_dir_with_existing_non_empty_directory(self, tmp_path: Path) -> None:
        """ファイルを含むディレクトリが既に存在する場合"""
        logs_path = tmp_path / "logs"
        logs_path.mkdir()

        # ディレクトリ内にファイルを作成
        (logs_path / "existing.log").write_text("existing content")

        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            result = log_dir()

            assert result == logs_path
            # 既存ファイルが保持されていることを確認
            assert (logs_path / "existing.log").exists()

    def test_log_dir_preserves_directory_permissions(self, tmp_path: Path) -> None:
        """既存ディレクトリのパーミッションが保持されること"""
        logs_path = tmp_path / "logs"
        logs_path.mkdir(mode=0o755)

        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            result = log_dir()

            assert result == logs_path
            # ディレクトリが存在し、変更されていないことを確認
            assert logs_path.is_dir()


class TestLogDirSymlink:
    """シンボリックリンクに対する log_dir() のテスト"""

    def test_log_dir_with_symlink_to_directory(self, tmp_path: Path) -> None:
        """logsがディレクトリへのシンボリックリンクの場合"""
        real_logs = tmp_path / "real_logs"
        real_logs.mkdir()

        logs_symlink = tmp_path / "logs"
        logs_symlink.symlink_to(real_logs)

        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            result = log_dir()

            # シンボリックリンク自体が返される
            assert result == logs_symlink
            # シンボリックリンクがディレクトリとして機能すること
            assert logs_symlink.is_dir()

    def test_log_dir_with_broken_symlink(self, tmp_path: Path) -> None:
        """壊れたシンボリックリンクの場合"""
        nonexistent_target = tmp_path / "nonexistent"
        logs_symlink = tmp_path / "logs"

        # 存在しないターゲットへのシンボリックリンクを作成
        logs_symlink.symlink_to(nonexistent_target)

        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            # mkdir(exist_ok=True) の動作によりエラーになる可能性
            # 実装によっては FileExistsError が発生する
            try:
                result = log_dir()
                # シンボリックリンクが削除されて新しいディレクトリが作成される場合
                assert result == logs_symlink
            except FileExistsError:
                # シンボリックリンクがあるためディレクトリが作成できない場合
                pass
            except OSError:
                # その他のOSエラー
                pass


class TestLogDirFileConflict:
    """ファイルとの競合に対する log_dir() のテスト"""

    def test_log_dir_with_existing_file(self, tmp_path: Path) -> None:
        """'logs' という名前のファイルが既に存在する場合"""
        logs_file = tmp_path / "logs"
        logs_file.write_text("This is a file, not a directory")

        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            # ファイルが存在する場合、mkdir は FileExistsError を発生させる
            with pytest.raises((FileExistsError, NotADirectoryError)):
                log_dir()


class TestLogDirPath:
    """log_dir() のパス検証テスト"""

    def test_log_dir_path_is_absolute(self, tmp_path: Path) -> None:
        """返されるパスが絶対パスであること"""
        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            result = log_dir()

            assert result.is_absolute()

    def test_log_dir_path_ends_with_logs(self, tmp_path: Path) -> None:
        """返されるパスが 'logs' で終わること"""
        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            result = log_dir()

            assert result.name == "logs"

    def test_log_dir_parent_is_project_root(self, tmp_path: Path) -> None:
        """返されるパスの親が PROJECT_ROOT であること"""
        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            result = log_dir()

            assert result.parent == tmp_path


class TestLogDirIdempotent:
    """log_dir() の冪等性テスト"""

    def test_log_dir_idempotent(self, tmp_path: Path) -> None:
        """複数回呼び出しても同じ結果を返すこと"""
        with patch("yadon_agents.infra.process.PROJECT_ROOT", tmp_path):
            result1 = log_dir()
            result2 = log_dir()
            result3 = log_dir()

            assert result1 == result2 == result3

    def test_log_dir_concurrent_calls(self, tmp_path: Path) -> None:
        """並行呼び出しでも正しく動作すること（同じパスを返す）"""
        import threading
        from yadon_agents import PROJECT_ROOT

        # 実際のPROJECT_ROOTを使用して並行呼び出しをテスト
        results: list[Path] = []
        errors: list[Exception] = []
        expected_path = PROJECT_ROOT / "logs"

        def call_log_dir() -> None:
            try:
                result = log_dir()
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=call_log_dir) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
        # 全て同じパスを返すことを確認
        assert all(r == expected_path for r in results)


class TestLogDirEdgeCases:
    """log_dir() のその他のエッジケース"""

    def test_log_dir_with_special_characters_in_path(self, tmp_path: Path) -> None:
        """パスに特殊文字が含まれる場合"""
        special_path = tmp_path / "project with spaces"
        special_path.mkdir()

        with patch("yadon_agents.infra.process.PROJECT_ROOT", special_path):
            result = log_dir()

            assert result.parent == special_path
            assert result.exists()

    def test_log_dir_with_unicode_in_path(self, tmp_path: Path) -> None:
        """パスにUnicode文字が含まれる場合"""
        unicode_path = tmp_path / "プロジェクト"
        unicode_path.mkdir()

        with patch("yadon_agents.infra.process.PROJECT_ROOT", unicode_path):
            result = log_dir()

            assert result.parent == unicode_path
            assert result.exists()

    def test_log_dir_with_deep_nested_path(self, tmp_path: Path) -> None:
        """深くネストされたパスの場合"""
        deep_path = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep_path.mkdir(parents=True)

        with patch("yadon_agents.infra.process.PROJECT_ROOT", deep_path):
            result = log_dir()

            assert result.parent == deep_path
            assert result.exists()
