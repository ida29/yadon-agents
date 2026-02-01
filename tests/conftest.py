"""共通テストフィクスチャ

macOS の AF_UNIX パス長制限 (104バイト) を回避するため、
ソケットテスト用に /tmp 直下の短いパスを提供する。
"""

import os
import uuid

import pytest


@pytest.fixture
def sock_dir(tmp_path):
    """ソケット用の短いディレクトリパスを返す。

    tmp_path は macOS では /private/var/folders/... と長くなり、
    AF_UNIX の 104 バイト制限を超える。/tmp 直下に短い名前で作成する。
    """
    short_dir = f"/tmp/_yt{uuid.uuid4().hex[:6]}"
    os.makedirs(short_dir, exist_ok=True)
    yield short_dir
    # cleanup
    import shutil
    shutil.rmtree(short_dir, ignore_errors=True)
