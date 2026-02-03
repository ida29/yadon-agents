"""ソケットパスのプラットフォーム差異テスト

各OS固有のパス長制限やディレクトリ構造に対応するテスト。
"""

import sys
import os

import pytest

from yadon_agents.infra.protocol import (
    SOCKET_DIR,
    agent_socket_path,
    pet_socket_path,
)


class TestSocketPathLength:
    """ソケットパス長の制限テスト"""

    # macOS AF_UNIX パス長制限: 104バイト
    # Linux AF_UNIX パス長制限: 108バイト
    MACOS_PATH_LIMIT = 104
    LINUX_PATH_LIMIT = 108

    def test_agent_socket_path_within_limit(self):
        """エージェントソケットパスがプラットフォーム制限内であること"""
        # 最も長いケース: yadon-agent-yadon-8.sock
        long_path = agent_socket_path("yadon-8")
        path_len = len(long_path.encode("utf-8"))

        if sys.platform == "darwin":
            assert path_len < self.MACOS_PATH_LIMIT, f"Path too long for macOS: {path_len} bytes"
        else:
            assert path_len < self.LINUX_PATH_LIMIT, f"Path too long for Linux: {path_len} bytes"

    def test_pet_socket_path_within_limit(self):
        """ペットソケットパスがプラットフォーム制限内であること"""
        long_path = pet_socket_path("yadoran")
        path_len = len(long_path.encode("utf-8"))

        if sys.platform == "darwin":
            assert path_len < self.MACOS_PATH_LIMIT, f"Path too long for macOS: {path_len} bytes"
        else:
            assert path_len < self.LINUX_PATH_LIMIT, f"Path too long for Linux: {path_len} bytes"

    def test_custom_prefix_path_within_limit(self):
        """カスタムプレフィックスでもパス長制限内であること"""
        # 長いプレフィックスでテスト
        long_prefix = "customprefix"
        path = agent_socket_path("yadon-8", prefix=long_prefix)
        path_len = len(path.encode("utf-8"))

        limit = self.MACOS_PATH_LIMIT if sys.platform == "darwin" else self.LINUX_PATH_LIMIT
        assert path_len < limit, f"Path too long: {path_len} bytes"


class TestSocketDirectory:
    """ソケットディレクトリのテスト"""

    def test_socket_dir_exists(self):
        """デフォルトソケットディレクトリが存在すること"""
        assert os.path.isdir(SOCKET_DIR)

    def test_socket_dir_writable(self):
        """ソケットディレクトリが書き込み可能であること"""
        assert os.access(SOCKET_DIR, os.W_OK)

    @pytest.mark.platform_darwin
    def test_socket_dir_is_tmp_darwin(self):
        """macOSでソケットディレクトリが/tmpであること"""
        if sys.platform != "darwin":
            pytest.skip("macOS only")
        assert SOCKET_DIR == "/tmp"

    @pytest.mark.platform_linux
    def test_socket_dir_is_tmp_linux(self):
        """Linuxでソケットディレクトリが/tmpであること"""
        if sys.platform != "linux":
            pytest.skip("Linux only")
        assert SOCKET_DIR == "/tmp"


class TestSocketPathFormat:
    """ソケットパスフォーマットのテスト"""

    def test_agent_path_format(self):
        """エージェントソケットパスの形式が正しいこと"""
        path = agent_socket_path("test-name")
        assert path.endswith(".sock")
        assert "agent" in path
        assert "test-name" in path

    def test_pet_path_format(self):
        """ペットソケットパスの形式が正しいこと"""
        path = pet_socket_path("test-name")
        assert path.endswith(".sock")
        assert "pet" in path
        assert "test-name" in path

    def test_paths_are_unique(self):
        """異なる名前で異なるパスが生成されること"""
        path1 = agent_socket_path("name1")
        path2 = agent_socket_path("name2")
        assert path1 != path2

    def test_agent_pet_paths_different(self):
        """エージェントとペットで異なるパスが生成されること"""
        agent = agent_socket_path("yadoran")
        pet = pet_socket_path("yadoran")
        assert agent != pet


class TestUnicodeHandling:
    """Unicode文字を含むパス処理のテスト"""

    def test_ascii_name_path(self):
        """ASCII名でパスが正しく生成されること"""
        path = agent_socket_path("yadon-1")
        assert isinstance(path, str)
        assert path.encode("utf-8")  # エンコード可能

    def test_numeric_name_path(self):
        """数値名でパスが正しく生成されること"""
        path = pet_socket_path("123")
        assert "123" in path
