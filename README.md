# yadon-agents

ヤドキング・ヤドラン・ヤドンによるマルチエージェントシステム。
のんびりしているが、確実にタスクをこなす。

## アーキテクチャ

```
トレーナー（人間）
  │ 直接会話
  ▼
┌──────────────────┐
│   ヤドキング       │  claude --model opus（対話型）
│                  │  send_task.sh / check_status.sh を実行
└──────┬───────────┘
       │ Unix socket
       ▼
┌──────────────────┐
│   ヤドラン        │  デスクトップペット + デーモン (PyQt6)
│                  │  claude -p (sonnet) でタスク分解 → ヤドンに配分
└──┬───┬───┬───┬──┘
   │   │   │   │ Unix socket
   ▼   ▼   ▼   ▼
┌──┐ ┌──┐ ┌──┐ ┌──┐
│Y1│ │Y2│ │Y3│ │Y4│  デスクトップペット + デーモン (PyQt6)
└──┘ └──┘ └──┘ └──┘  claude -p (haiku) で実行 → 結果返却
```

| ポケモン | モデル | 役割 |
|----------|--------|------|
| ヤドキング | opus | 戦略統括、最終レビュー、人間とのIF |
| ヤドラン | sonnet | タスク分解、ヤドンへの配分 |
| ヤドン×4 | haiku | 実作業（コーディング等） |

## 必要なもの

- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (`claude` CLI)
- PyQt6（デスクトップペット表示。なくてもデーモンモードで動作）

```bash
pip install PyQt6
```

## 起動

```bash
./start.sh
```

以下が順に起動する:

1. ヤドン1〜4（デスクトップペット + デーモン）
2. ヤドラン（デスクトップペット + デーモン）
3. ヤドキング（`claude --model opus` — 対話型、現在のターミナル）

ヤドキング終了時にデーモン+ペットも自動停止する。

PyQt6がない環境ではペットの代わりにスタンドアロンデーモンが起動。

```bash
# 手動停止
./stop.sh

# 作業ディレクトリ指定（デフォルト: カレントディレクトリ）
./start.sh /path/to/project
```

## 通信

全エージェント間通信はUnixドメインソケット（JSON over Unix socket）。

| ソケット | パス |
|----------|------|
| ヤドラン | `/tmp/yadon-agent-yadoran.sock` |
| ヤドンN | `/tmp/yadon-agent-yadon-N.sock` |

### フロー

1. 人間がヤドキングに依頼
2. ヤドキングが `send_task.sh "タスク内容"` を実行
3. ヤドランがタスクを分解（claude sonnet）
4. サブタスクをヤドン1〜4に並列送信
5. 各ヤドンが実行（claude haiku）
6. 結果がヤドラン → ヤドキングへ返却

## スクリプト

| スクリプト | 用途 |
|-----------|------|
| `scripts/send_task.sh` | ヤドランへタスク送信（ブロック） |
| `scripts/check_status.sh` | エージェントのステータス照会 |
| `scripts/pet_say.sh` | ペットに吹き出しメッセージ送信 |
| `scripts/restart_daemons.sh` | デーモンのみ再起動 |

## ディレクトリ構成

```
yadon-agents/
├── start.sh / stop.sh        # 起動・停止
├── daemons/                   # デーモン（PyQt6なし環境用フォールバック）
│   ├── socket_protocol.py     # 共有通信プロトコル
│   ├── yadon_daemon.py        # ヤドンデーモン
│   └── yadoran_daemon.py      # ヤドランデーモン
├── pet/                       # デスクトップペット + デーモン統合
│   ├── yadon_pet.py           # ヤドンペット
│   ├── yadoran_pet.py         # ヤドランペット
│   └── ...                    # UI部品（吹き出し、メニュー、ドット絵等）
├── instructions/              # エージェント指示書
├── scripts/                   # ヘルパースクリプト
├── memory/                    # 学習記録
└── logs/                      # ログファイル
```

## 役割制御

`AGENT_ROLE` 環境変数と PreToolUse フックにより、役割に応じたツール実行制限を強制。

| エージェント | Edit/Write | Bash (git書込) | Bash (読取) |
|---|---|---|---|
| ヤドキング | 禁止 | 禁止 | 許可 |
| ヤドラン | 禁止 | 禁止 | 許可 |
| ヤドン1-4 | 許可 | 許可 | 許可 |

## ライセンス

Private
