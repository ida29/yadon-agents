"""吹き出し表示用テキスト整形"""

from __future__ import annotations

import re

# 絶対パス（/Users/... /tmp/... /home/... 等）をファイル名だけに短縮する
_ABS_PATH_RE = re.compile(r"/(?:Users|home|tmp|var|private|opt|etc)(?:/[\w._-]+)+")


def summarize_for_bubble(text: str, max_len: int = 30) -> str:
    """吹き出し表示用にテキストを短縮する。

    - 絶対パスをファイル名/ディレクトリ名に置換
    - max_len文字で切り詰め
    """
    shortened = _ABS_PATH_RE.sub(
        lambda m: m.group(0).rsplit("/", 1)[-1], text,
    )
    if len(shortened) > max_len:
        return shortened[:max_len] + "..."
    return shortened
