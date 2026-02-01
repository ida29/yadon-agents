"""ヤドンテーマ -- デフォルトテーマ

既存のハードコード値をそのまま ThemeConfig に移行。
"""

from __future__ import annotations

from yadon_agents.domain.theme import (
    RoleNames,
    ThemeConfig,
    WorkerCountConfig,
    YarukiSwitchConfig,
)


def build_theme() -> ThemeConfig:
    """ヤドンテーマの ThemeConfig を構築する。"""
    return ThemeConfig(
        name="yadon",
        display_name="ヤドン・エージェント",
        socket_prefix="yadon",
        role_names=RoleNames(
            coordinator="ヤドキング",
            manager="ヤドラン",
            worker="ヤドン",
        ),
        worker_count=WorkerCountConfig(default=4, min=1, max=8),
        worker_messages={
            1: ["...やるやぁん...", "...できたやぁん...", "...ん?...やぁん?"],
            2: ["...やるやぁん...", "...つかれたやぁん...", "...しっぽで釣りしたい..."],
            3: ["...やるやぁん...", "...がんばるやぁん...", "...ヤド..."],
            4: ["あー やるよお~", "あー できたあ~", "あー でもでも~"],
        },
        manager_messages=[
            "...ヤドキングがなんか言ってる...",
            "...タスク分解...する...",
            "...ヤドンたちに...おねがい...",
            "...しっぽの...シェルダーが...かゆい...",
            "...管理って...たいへん...",
        ],
        random_messages=[
            "おつかれさま　やぁん",
            "きょうは　なんようび　やぁん......?",
            "うどん　たべる　やぁん......?",
        ],
        welcome_messages=[
            "おてつだい　する　やぁん",
            "がんばる　やぁん",
            "よろしく　やぁん",
            "なにか　つくる　やぁん",
            "きょうも　がんばる　やぁん",
        ],
        manager_welcome_messages=[
            "...ヤドラン...起動した...",
            "...タスク管理...する...",
            "...しっぽが...準備できた...",
        ],
        phase_labels={
            "implement": "...実装する...",
            "docs": "...ドキュメント更新する...",
            "review": "...レビューする...",
        },
        worker_variants={
            1: "normal",
            2: "shiny",
            3: "galarian",
            4: "galarian_shiny",
        },
        extra_variants=["normal", "shiny", "galarian", "galarian_shiny"],
        worker_color_schemes={
            "normal": {"body": "#F3D599", "head": "#D32A38", "accent": "#F3D599"},
            "shiny": {"body": "#FFCCFF", "head": "#FF99CC", "accent": "#FFCCFF"},
            "galarian": {"body": "#F3D599", "head": "#D32A38", "accent": "#FFD700"},
            "galarian_shiny": {"body": "#FFD700", "head": "#FFA500", "accent": "#FFD700"},
        },
        manager_colors={
            "body": "#F3D599",
            "head": "#D32A38",
            "shellder": "#8B7D9B",
        },
        yaruki_switch=YarukiSwitchConfig(
            enabled=False,
            on_message="やるきスイッチ　ON",
            off_message="やるきスイッチ　OFF",
            menu_on_text="やるきスイッチ　ONにする",
            menu_off_text="やるきスイッチ　OFFにする",
        ),
        instructions_coordinator="instructions/yadoking.md",
        instructions_manager="instructions/yadoran.md",
        instructions_worker="instructions/yadon.md",
        agent_role_coordinator="yadoking",
        agent_role_manager="yadoran",
        agent_role_worker="yadon",
        worker_task_bubble="...やるやぁん...「{summary}」",
        worker_success_bubble="...できたやぁん...「{summary}」",
        worker_error_bubble="...失敗やぁん...「{summary}」",
        manager_task_bubble="...ヤドキングが言ってる...「{summary}」",
        manager_phase_bubble="{label}{worker_name}{count}体に依頼...",
        manager_success_bubble="...みんなできた...「{summary}」",
        manager_error_bubble="...一部失敗した...「{summary}」",
        worker_prompt_template="{instructions_path} を読んで従ってください。\n\nあなたは{worker_name}{number}です。\n\nタスク:\n{instruction}",
        manager_prompt_prefix="{instructions_path} を読んで従ってください。\n\nあなたは{manager_name}です。",
    )
