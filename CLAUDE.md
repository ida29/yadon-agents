# ヤドン・エージェント

## 概要

ヤドキング・ヤドラン・ヤドンによるマルチエージェントシステム。
のんびりしているが、確実にタスクをこなす。

## アーキテクチャ

```
トレーナー（人間）
  │ 直接会話
  ▼
┌──────────────────┐
│   ヤドキング       │  claude --model opus（ユーザーが起動）
│                  │  send_task.sh / check_status.sh を実行
└──────┬───────────┘
       │ Unix socket: /tmp/yadon-agent-yadoran.sock
       ▼
┌──────────────────┐
│   ヤドラン        │  デスクトップペット + デーモン (PyQt6 + Python)
│   pet + daemon   │  タスク受信 → claude -p (sonnet) で分解 → ヤドンに配分
└──┬───┬───┬───┬──┘
   │   │   │   │ Unix socket: /tmp/yadon-agent-yadon-N.sock
   ▼   ▼   ▼   ▼
┌──┐ ┌──┐ ┌──┐ ┌──┐
│Y1│ │Y2│ │Y3│ │Y4│  デスクトップペット + デーモン (PyQt6 + Python)
└──┘ └──┘ └──┘ └──┘  タスク受信 → claude -p (haiku) で実行 → 結果返却
```

※ PyQt6がない環境では全エージェントがスタンドアロンデーモンとして起動（ペットなし）

## 役割対応表

| ポケモン | モデル | 動作モード | 役割 |
|----------|--------|-----------|------|
| ヤドキング | opus | ユーザーが直接起動 | 戦略統括、最終レビュー、人間とのIF |
| ヤドラン | sonnet | ペット+デーモン (claude -p) | タスク分解、ヤドンへの配分 |
| ヤドン×4 | haiku | ペット+デーモン (claude -p) | 実作業（コーディング等） |

## 通信プロトコル

全エージェント間通信はUnixドメインソケット。JSON over Unix socket。

### ソケットパス

| 用途 | パス | 所有プロセス |
|---|---|---|
| ヤドラン | `/tmp/yadon-agent-yadoran.sock` | `pet/yadoran_pet.py` (または `daemons/yadoran_daemon.py`) |
| ヤドン1 | `/tmp/yadon-agent-yadon-1.sock` | `pet/yadon_pet.py --number 1` (または `daemons/yadon_daemon.py`) |
| ヤドン2 | `/tmp/yadon-agent-yadon-2.sock` | `pet/yadon_pet.py --number 2` |
| ヤドン3 | `/tmp/yadon-agent-yadon-3.sock` | `pet/yadon_pet.py --number 3` |
| ヤドン4 | `/tmp/yadon-agent-yadon-4.sock` | `pet/yadon_pet.py --number 4` |
| ヤドラン吹き出し | `/tmp/yadon-pet-yadoran.sock` | `pet/yadoran_pet.py` (吹き出し用) |
| ヤドン吹き出し | `/tmp/yadon-pet-N.sock` | `pet/yadon_pet.py` (吹き出し用) |

### 通信フロー

1. 人間がヤドキングに依頼
2. ヤドキングが `./scripts/send_task.sh "タスク内容"` を実行（ブロック）
3. ヤドランデーモンがソケットで受信
4. ヤドランが `claude -p --model sonnet` でタスク分解
5. サブタスクをヤドン1〜4のソケットに並列送信
6. 各ヤドンが `claude -p --model haiku` で実行（ペットに吹き出し表示）
7. 結果がヤドラン → ヤドキングへ逆流

## ディレクトリ構成

```
yadon-agents/
├── CLAUDE.md                 # このファイル
├── start.sh                  # 起動スクリプト（デーモン + ペット）
├── stop.sh                   # 停止スクリプト
├── daemons/
│   ├── socket_protocol.py    # 共有プロトコル（send/receive, ソケット作成, パス定義）
│   ├── yadon_daemon.py       # ヤドンデーモン（PyQt6なし環境用フォールバック）
│   └── yadoran_daemon.py     # ヤドランデーモン（タスク分解 → ヤドンに並列配分 → 結果集約）
├── pet/
│   ├── yadon_pet.py          # ヤドン デスクトップペット + エージェントデーモン統合
│   ├── yadoran_pet.py        # ヤドラン デスクトップペット + エージェントデーモン統合
│   ├── agent_socket_server.py       # ヤドン用エージェントソケットサーバー (QThread)
│   ├── yadoran_agent_socket_server.py # ヤドラン用エージェントソケットサーバー (QThread)
│   ├── socket_server.py      # ペット吹き出しソケットサーバー (QThread, 共通)
│   ├── config.py             # ペット設定（ヤドン + ヤドラン）
│   ├── pixel_data.py         # ヤドン ドット絵データ
│   ├── yadoran_pixel_data.py # ヤドラン ドット絵データ
│   ├── speech_bubble.py      # 吹き出しウィジェット
│   ├── pokemon_menu.py       # 右クリックメニュー
│   └── utils.py              # ユーティリティ
├── instructions/
│   ├── yadoking.md           # ヤドキングの指示書
│   ├── yadoran.md            # ヤドランの指示書（デーモンモード）
│   └── yadon.md              # ヤドンの指示書（デーモンモード）
├── scripts/
│   ├── send_task.sh          # ヤドキング → ヤドランへタスク送信
│   ├── check_status.sh       # エージェントのステータス照会
│   └── pet_say.sh            # ヤドンペットに吹き出し送信
├── config/
│   └── settings.yaml         # 設定
├── memory/                   # 学習記録
├── logs/                     # ログファイル
├── .pids/                    # デーモンPIDファイル（自動生成）
└── .claude/
    ├── settings.json         # PreToolUseフック設定
    └── hooks/
        └── enforce-role.sh   # 役割別ツール制御スクリプト
```

## 起動方法

```bash
# デーモン + ペット起動
./start.sh

# 停止
./stop.sh

# ヤドキング起動（別ターミナルで）
claude --model opus
```

起動すると以下が立ち上がる（PyQt6あり環境）:
- ペット+デーモン: ヤドラン（1プロセス）
- ペット+デーモン: ヤドン1〜4（4プロセス）

PyQt6なし環境ではすべてスタンドアロンデーモンとして起動（ペットなし）。

## scripts/

### send_task.sh
ヤドキングがヤドランにタスクを送信するスクリプト。Unixソケット経由でJSON送受信。結果が返るまでブロックする。

### check_status.sh
全エージェントまたは特定エージェントのステータスをUnixソケット経由で照会。

### pet_say.sh
ペットに吹き出しメッセージを送信するヘルパー。ペットソケット経由。ヤドン1〜4に対応（番号指定）。

## 役割制御（PreToolUseフック）

`AGENT_ROLE` 環境変数と `.claude/hooks/enforce-role.sh` により、役割に応じたツール実行制限を技術的に強制する。

| エージェント | AGENT_ROLE | Edit/Write | Bash (git書込) | Bash (読取) |
|---|---|---|---|---|
| ヤドキング | `yadoking` | 全禁止 | 禁止 | 許可 |
| ヤドラン | `yadoran` | dashboard.mdのみ | 禁止 | 許可 |
| ヤドン1-4 | `yadon` | 全許可 | 全許可 | 全許可 |
