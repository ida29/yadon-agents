"""ThemeConfig -- テーマ固有データのスキーマ

テーマ（ポケモンスキン）のメッセージ、色、バリアント、ソケットプレフィックス等を
frozen dataclass で保持する。スプライトビルダーは含めない（themes/ 層で提供）。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkerCountConfig:
    """ワーカー数の設定（デフォルト・最小・最大）。"""
    default: int = 4
    min: int = 1
    max: int = 8


@dataclass(frozen=True)
class YarukiSwitchConfig:
    """やるきスイッチ設定。"""
    enabled: bool = False
    on_message: str = ""
    off_message: str = ""
    menu_on_text: str = ""
    menu_off_text: str = ""


@dataclass(frozen=True)
class RoleNames:
    """各エージェントロールの表示名。"""
    coordinator: str = ""
    manager: str = ""
    worker: str = ""


@dataclass(frozen=True)
class ThemeConfig:
    """テーマ固有の全設定データ。

    テーマモジュール (themes/<name>/__init__.py) の build_theme() が構築する。
    """
    # 基本情報
    name: str
    display_name: str
    socket_prefix: str

    # ロール名
    role_names: RoleNames

    # ワーカー設定
    worker_count: WorkerCountConfig = field(default_factory=WorkerCountConfig)

    # ワーカーメッセージ (番号 -> メッセージリスト)
    worker_messages: dict[int, list[str]] = field(default_factory=dict)
    # マネージャーメッセージ
    manager_messages: list[str] = field(default_factory=list)
    # 共通メッセージ
    random_messages: list[str] = field(default_factory=list)
    welcome_messages: list[str] = field(default_factory=list)
    manager_welcome_messages: list[str] = field(default_factory=list)

    # フェーズラベル
    phase_labels: dict[str, str] = field(default_factory=dict)

    # ワーカーバリアント (番号 -> バリアント名)
    worker_variants: dict[int, str] = field(default_factory=dict)
    # 5体以上のフォールバック用バリアントリスト
    extra_variants: list[str] = field(default_factory=list)

    # ワーカー色スキーム (バリアント -> {body, head, accent, ...})
    worker_color_schemes: dict[str, dict[str, str]] = field(default_factory=dict)
    # マネージャー色
    manager_colors: dict[str, str] = field(default_factory=dict)

    # やるきスイッチ
    yaruki_switch: YarukiSwitchConfig = field(default_factory=YarukiSwitchConfig)

    # 指示書パス (PROJECT_ROOT からの相対パス)
    instructions_coordinator: str = ""
    instructions_manager: str = ""
    instructions_worker: str = ""

    # エージェントロール名 (AGENT_ROLE env var の値)
    agent_role_coordinator: str = ""
    agent_role_manager: str = ""
    agent_role_worker: str = ""

    # バブルメッセージテンプレート
    worker_task_bubble: str = "...やるやぁん...「{summary}」"
    worker_success_bubble: str = "...できたやぁん...「{summary}」"
    worker_error_bubble: str = "...失敗やぁん...「{summary}」"
    manager_task_bubble: str = "...ヤドキングが言ってる...「{summary}」"
    manager_phase_bubble: str = "{label}ヤドン{count}体に依頼..."
    manager_success_bubble: str = "...みんなできた...「{summary}」"
    manager_error_bubble: str = "...一部失敗した...「{summary}」"

    # ワーカープロンプトテンプレート
    worker_prompt_template: str = "instructions/yadon.md を読んで従ってください。\n\nあなたはヤドン{number}です。\n\nタスク:\n{instruction}"
    # マネージャープロンプトテンプレート (分解指示のprefix)
    manager_prompt_prefix: str = "instructions/yadoran.md を読んで従ってください。\n\nあなたはヤドランです。"
