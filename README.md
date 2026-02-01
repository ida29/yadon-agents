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
│Y1│ │Y2│ │..│ │YN│  デスクトップペット + デーモン (PyQt6)
└──┘ └──┘ └──┘ └──┘  claude -p (haiku) で実行 → 結果返却
                      N = YADON_COUNT環境変数（デフォルト4、範囲1-8）
```

| ポケモン | モデル | 役割 |
|----------|--------|------|
| ヤドキング | opus | 戦略統括、最終レビュー、人間とのIF |
| ヤドラン | sonnet | タスク分解、ヤドンへの配分 |
| ヤドン×N | haiku | 実作業（コーディング等） |

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

# ヤドン数を指定して起動（デフォルト4、範囲1-8）
YADON_COUNT=6 ./start.sh
```

以下が順に起動する:

1. ヤドン1〜N（デスクトップペット + デーモン）
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
4. サブタスクをヤドン1〜Nに並列送信
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
├── src/yadon_agents/          # メインパッケージ（DDD構成）
│   ├── domain/                # ドメイン層（型、メッセージ）
│   ├── agent/                 # アプリケーション層（worker, manager）
│   ├── infra/                 # インフラ層（ソケット通信、claude実行）
│   ├── config/                # 設定（メッセージ定数、get_yadon_count()）
│   ├── gui/                   # GUI層（PyQt6デスクトップペット）
│   └── cli.py                 # CLIエントリポイント
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
| ヤドン1-N | 許可 | 許可 | 許可 |

## ライセンス

Private
