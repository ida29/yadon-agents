"""プロセス管理のプラットフォーム差異テスト"""

import os
import sys
from pathlib import Path

import pytest

from yadon_agents.infra.process import log_dir
from yadon_agents import PROJECT_ROOT


class TestLogDirectory:
    """ログディレクトリ生成のテスト"""

    def test_log_dir_creates_directory(self):
        """ログディレクトリが作成されること"""
        result = log_dir()

        assert result.exists()
        assert result.is_dir()

    def test_log_dir_returns_path(self):
        """ログディレクトリがPathオブジェクトを返すこと"""
        result = log_dir()
        assert isinstance(result, Path)

    def test_log_dir_is_under_project_root(self):
        """ログディレクトリがPROJECT_ROOT配下にあること"""
        result = log_dir()

        # ログディレクトリがプロジェクトルートの配下にあることを確認
        try:
            result.relative_to(PROJECT_ROOT)
        except ValueError:
            pytest.fail(f"Log dir {result} is not under PROJECT_ROOT {PROJECT_ROOT}")

    def test_log_dir_idempotent(self):
        """ログディレクトリ生成が冪等であること"""
        result1 = log_dir()
        result2 = log_dir()

        assert result1 == result2
        assert result1.exists()

    def test_log_dir_writable(self):
        """ログディレクトリが書き込み可能であること"""
        result = log_dir()
        assert os.access(result, os.W_OK)


class TestLogDirectoryStructure:
    """ログディレクトリ構造のテスト"""

    def test_log_dir_name(self):
        """ログディレクトリ名が正しいこと"""
        result = log_dir()
        assert result.name == "logs"

    def test_log_dir_parent_is_project_root(self):
        """ログディレクトリの親ディレクトリがPROJECT_ROOTであること"""
        result = log_dir()
        assert result.parent == PROJECT_ROOT


class TestPlatformSpecific:
    """プラットフォーム固有のテスト"""

    @pytest.mark.platform_darwin
    def test_macos_home_expansion(self):
        """macOSでホームディレクトリが正しく展開されること"""
        if sys.platform != "darwin":
            pytest.skip("macOS only")

        home = Path.home()
        # macOSではHOMEは通常 /Users/username
        assert str(home).startswith("/Users/") or str(home).startswith("/var/")

    @pytest.mark.platform_linux
    def test_linux_home_expansion(self):
        """Linuxでホームディレクトリが正しく展開されること"""
        if sys.platform != "linux":
            pytest.skip("Linux only")

        home = Path.home()
        # Linuxではよく /home/username
        assert str(home).startswith("/home/") or str(home).startswith("/root")

    def test_project_root_exists(self):
        """PROJECT_ROOTが存在すること"""
        assert PROJECT_ROOT.exists()
        assert PROJECT_ROOT.is_dir()
