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
       │ tmux send-keys        ▲
       ▼                        │ 最終レビュー依頼
┌──────────────────┐            │
│   YADORAN        │ ← ヤドラン（タスク管理・一次レビュー）
│   (sonnet)       │   「しっぽが...なんか言ってる...」
└──────┬───────────┘
       │ tmux send-keys        ▲
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
yadon-agents/
├── CLAUDE.md                 # このファイル
├── first_setup.sh            # 初回セットアップ
├── start.sh                  # 毎日の起動スクリプト
├── stop.sh                   # 停止スクリプト
├── config/
│   ├── settings.yaml         # 設定
│   └── panes.yaml            # tmuxペインID（自動生成）
├── instructions/
│   ├── yadoking.md           # ヤドキングの指示書
│   ├── yadoran.md            # ヤドランの指示書
│   ├── yadon.md              # ヤドンの指示書
│   └── yadon_pokoa.md        # ヤドン（ポケモア風）の指示書
├── memory/
│   ├── yadoking_pending.md
│   ├── exchange_counter.md
│   └── global_context.md
├── status/
│   └── master_status.yaml
├── logs/                     # ログファイル格納
├── scripts/
│   ├── notify.sh             # エージェント間通知
│   └── auto_runner.sh        # 自動タスク検出
├── templates/
│   └── context_template.md
└── docs/
    └── dashboard.md          # リアルタイムダッシュボード
```

## 通信プロトコル

全てのエージェント間通信は `tmux send-keys` で直接メッセージを送信する方式。

### ヤドキング → ヤドラン
tmux send-keysでヤドランに直接指示を送る

### ヤドラン → ヤドン
tmux send-keysで各ヤドンに直接タスクを送る

### ヤドン → ヤドラン
tmux send-keysでヤドランに直接報告を送る

### ステータス更新
`docs/dashboard.md` をヤドランが更新

## コンパクション復帰手順

コンテキストがリセットされた場合：

1. まず `instructions/` 配下の自分の指示書を読む
2. `docs/dashboard.md` で現在の状況を確認
3. 作業を再開

## scripts/

### notify.sh
エージェント間通知スクリプト。tmux send-keysでメッセージを送信し、入力欄確認・再送信処理を行う。

### auto_runner.sh
自動タスク検出スクリプト。10秒ごとにdashboard.mdをチェックして新規タスクがあれば通知。

## 起動方法

```bash
# 初回のみ
./first_setup.sh

# 毎回
./start.sh

# 停止
./stop.sh
```

## 検証完了

- **50回以上の交換達成済み** (memory/exchange_counter.md参照)
- メッセージパッシング動作確認済み
- システム負荷テスト全合格

# テスト完了 v2
