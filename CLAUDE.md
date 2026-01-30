# ヤドン・エージェント

## 概要

ヤドキング・ヤドラン・ヤドンによるマルチエージェントシステム。
のんびりしているが、確実にタスクをこなす。

## 階層構造

```
トレーナー（人間）
  │
  ▼ おねがい
┌──────────────────┐
│   YADOKING       │ ← ヤドキング（プロジェクト統括・最終レビュー）
│   (opus)         │   「困ったなぁ...」
└──────┬───────────┘
       │ YAMLファイル経由        ▲
       ▼                        │ 最終レビュー依頼
┌──────────────────┐            │
│   YADORAN        │ ← ヤドラン（タスク管理・一次レビュー）
│   (sonnet)       │   「しっぽが...なんか言ってる...」
└──────┬───────────┘
       │ YAMLファイル経由        ▲
       ▼                        │ 成果物報告
┌───┬───┬───┬───┐              │
│Y1 │Y2 │Y3 │Y4 │ ← ヤドン（実働部隊）
│(haiku)         │   「...やぁん?」
└───┴───┴───┴───┘
```

## 役割対応表

| ポケモン | モデル | 役割 |
|----------|--------|------|
| ヤドキング | opus | 戦略統括、最終レビュー、人間とのIF |
| ヤドラン | sonnet | タスク分解、一次レビュー、進捗管理 |
| ヤドン×4 | haiku | 実作業（コーディング等） |

## レビューフロー

```
ヤドン作業完了 → ヤドラン一次レビュー → ヤドキング最終レビュー → トレーナーに報告
                    │                      │
                    ▼                      ▼
                 差し戻し               差し戻し
```

## ディレクトリ構成

```
yadon-agent/
├── CLAUDE.md                 # このファイル
├── first_setup.sh            # 初回セットアップ
├── start.sh                  # 毎日の起動スクリプト
├── config/
│   └── settings.yaml         # 設定
├── instructions/
│   ├── yadoking.md           # ヤドキングの指示書
│   ├── yadoran.md            # ヤドランの指示書
│   └── yadon.md              # ヤドンの指示書
├── queue/
│   ├── yadoking_to_yadoran.yaml  # ヤドキング→ヤドラン
│   ├── tasks/
│   │   └── yadon{1-4}.yaml   # 各ヤドン専用タスク
│   └── reports/
│       └── yadon{1-4}_report.yaml
├── context/                  # プロジェクト固有コンテキスト
├── memory/
│   ├── yadoking_memory.jsonl
│   └── global_context.md
├── templates/
│   └── context_template.md
├── status/
│   └── master_status.yaml
├── skills/                   # スキル格納
└── docs/
    └── dashboard.md          # リアルタイムダッシュボード
```

## 通信プロトコル

### ヤドキング → ヤドラン
`queue/yadoking_to_yadoran.yaml` に指示を書き込む

### ヤドラン → ヤドン
`queue/tasks/yadon{N}.yaml` に個別タスクを書き込む

### ヤドン → ヤドラン
`queue/reports/yadon{N}_report.yaml` に結果を報告

### ステータス更新
`docs/dashboard.md` をヤドランが更新

## コンパクション復帰手順

コンテキストがリセットされた場合：

1. まず `instructions/` 配下の自分の指示書を読む
2. `docs/dashboard.md` で現在の状況を確認
3. `queue/` 配下の自分宛ファイルを確認
4. 作業を再開

## 起動方法

```bash
# 初回のみ
./first_setup.sh

# 毎回
./start.sh
```
