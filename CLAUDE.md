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
│   ヤドラン        │  デスクトップペット + エージェント (PyQt6 + Python)
│                  │  タスク受信 → claude -p (sonnet) で3フェーズに分解 → ヤドンに配分
└──┬───┬───┬───┬──┘
   │   │   │   │ Unix socket: /tmp/yadon-agent-yadon-N.sock
   ▼   ▼   ▼   ▼
┌──┐ ┌──┐ ┌──┐ ┌──┐
│Y1│ │Y2│ │..│ │YN│  デスクトップペット + エージェント (PyQt6 + Python)
└──┘ └──┘ └──┘ └──┘  タスク受信 → claude -p (haiku) で実行 → 結果返却
                      N = YADON_COUNT環境変数（デフォルト4、範囲1-8）
```

PyQt6がない環境ではペットなしのスタンドアロンデーモンとして起動。

## 役割対応表

| ポケモン | モデル | 動作モード | 役割 |
|----------|--------|-----------|------|
| ヤドキング | opus | 対話型 (`claude --model opus`) | 戦略統括、最終レビュー、人間とのIF |
| ヤドラン | sonnet | バックグラウンド (`claude -p`) | タスクを3フェーズに分解、ヤドンへの並列配分、結果集約 |
| ヤドン×N | haiku | バックグラウンド (`claude -p`) | 実作業（コーディング、テスト、ドキュメント、レビュー等） |

## パッケージ構成

`src/yadon_agents/` にDDDレイヤーで構成。

```
yadon-agents/
├── pyproject.toml                    # パッケージ定義 + CLIエントリポイント
├── setup.py                          # 互換性shim (pip < 23)
├── start.sh                          # 起動ラッパー → python3 -m yadon_agents.cli start
├── stop.sh                           # 停止ラッパー → python3 -m yadon_agents.cli stop
├── src/
│   └── yadon_agents/
│       ├── __init__.py
│       ├── cli.py                    # CLIエントリポイント: yadon start/stop
│       │
│       ├── domain/                   # ドメイン層（純粋データ、I/Oなし）
│       │   ├── types.py             # AgentRole enum
│       │   └── messages.py          # TaskMessage, ResultMessage, StatusQuery, StatusResponse
│       │
│       ├── agent/                    # アプリケーション層（エージェントロジック）
│       │   ├── base.py              # BaseAgent: ソケットサーバーループ + on_bubble callback
│       │   ├── worker.py            # YadonWorker(BaseAgent): claude haiku実行
│       │   └── manager.py           # YadoranManager(BaseAgent): 3フェーズ分解 + 並列dispatch + 集約
│       │
│       ├── infra/                    # インフラ層（I/Oアダプター）
│       │   ├── protocol.py          # Unixソケット通信（JSON over Unix socket, SHUT_WR EOF）
│       │   └── claude_runner.py     # subprocess.run("claude -p") ラッパー
│       │
│       ├── config/                   # 設定
│       │   ├── agent.py             # メッセージ定数、バリアント、やるきスイッチ、get_yadon_count()
│       │   └── ui.py                # ピクセルサイズ、フォント、色、アニメーション設定
│       │
│       └── gui/                      # GUI層（PyQt6、オプション依存）
│           ├── base_pet.py          # BasePet(QWidget): 共通ペットロジック
│           ├── yadon_pet.py         # YadonPet(BasePet): やるきスイッチ等
│           ├── yadoran_pet.py       # YadoranPet(BasePet)
│           ├── agent_thread.py      # AgentThread(QThread): BaseAgent → pyqtSignal変換
│           ├── pet_socket_server.py # PetSocketServer(QThread): 吹き出し受信
│           ├── speech_bubble.py     # 吹き出しウィジェット
│           ├── pokemon_menu.py      # 右クリックメニュー
│           ├── pixel_data.py        # ヤドン ドット絵
│           ├── yadoran_pixel_data.py # ヤドラン ドット絵
│           ├── macos.py             # macOS window elevation (NSWindow)
│           └── utils.py             # log_debug
│
├── scripts/
│   ├── send_task.sh                 # ヤドキング → ヤドランへタスク送信
│   ├── check_status.sh              # エージェントのステータス照会
│   ├── restart_daemons.sh           # デーモンのみ再起動（ヤドキング実行中用）
│   └── pet_say.sh                   # ヤドンペットに吹き出し送信
├── instructions/
│   ├── yadoking.md                  # ヤドキング指示書
│   ├── yadoran.md                   # ヤドラン指示書（3フェーズ分解）
│   └── yadon.md                     # ヤドン指示書
├── memory/
│   └── global_context.md            # ヤドキングの学習記録
├── logs/                             # ログファイル（自動生成）
├── .pids/                            # デーモンPIDファイル（自動生成）
└── .claude/
    ├── settings.json                 # PreToolUseフック設定
    └── hooks/
        └── enforce-role.sh           # 役割別ツール制御スクリプト
```

## 設計判断

### BaseAgent + on_bubble callback

daemon版とGUI版の唯一の違いは「吹き出し通知の方法」。

- daemon版: on_bubble = None（何もしない）
- GUI版: on_bubble → pyqtSignal emit

`agent/base.py` の `on_bubble: Optional[BubbleCallback]` で吸収し、エージェントロジックは1箇所に集約。

### AgentThread

`gui/agent_thread.py`（25行）で BaseAgent を QThread でラップ。
`bubble_request` シグナルが BasePet の `show_bubble` スロットに接続される。

### BasePet

`gui/base_pet.py` で共通ペットロジック（ドラッグ、アニメーション、描画、メニュー、吹き出し）を集約。
YadonPet はやるきスイッチ等を追加、YadoranPet は最小限のサブクラス。

## 通信プロトコル

全エージェント間通信はUnixドメインソケット。JSON over Unix socket。
リクエスト送信後 `shutdown(SHUT_WR)` でEOFを通知し、レスポンスを読んで完了。

### ソケットパス

| 用途 | パス | 所有モジュール |
|---|---|---|
| ヤドラン | `/tmp/yadon-agent-yadoran.sock` | `yadon_agents.agent.manager` / `yadon_agents.gui.yadoran_pet` |
| ヤドン1 | `/tmp/yadon-agent-yadon-1.sock` | `yadon_agents.agent.worker` / `yadon_agents.gui.yadon_pet` |
| ヤドン2 | `/tmp/yadon-agent-yadon-2.sock` | 同上 (--number 2) |
| ヤドン3 | `/tmp/yadon-agent-yadon-3.sock` | 同上 (--number 3) |
| ヤドン4 | `/tmp/yadon-agent-yadon-4.sock` | 同上 (--number 4) |
| ヤドラン吹き出し | `/tmp/yadon-pet-yadoran.sock` | `yadon_agents.gui.yadoran_pet` |
| ヤドンN吹き出し | `/tmp/yadon-pet-N.sock` | `yadon_agents.gui.yadon_pet` |

### メッセージ形式

**タスク送信** (type: "task"):
```json
{
  "type": "task",
  "id": "task-20260201-120000-a1b2",
  "from": "yadoking",
  "payload": {
    "instruction": "READMEを更新してください",
    "project_dir": "/Users/yida/work/some-project"
  }
}
```

**タスク結果** (type: "result"):
```json
{
  "type": "result",
  "id": "task-20260201-120000-a1b2",
  "from": "yadoran",
  "status": "success",
  "payload": {
    "output": "各ヤドンの出力",
    "summary": "結果の要約"
  }
}
```

- `status: "success"` — 全サブタスク成功
- `status: "partial_error"` — 一部失敗あり

**ステータス照会** (type: "status") / **応答** (type: "status_response"):
```json
{"type": "status", "from": "check_status"}
```
```json
{
  "type": "status_response",
  "from": "yadoran",
  "state": "idle",
  "current_task": null,
  "workers": {"yadon-1": "idle", "yadon-2": "busy", ...}
}
```

### 通信フロー（3フェーズ実行）

1. 人間がヤドキングに依頼
2. ヤドキングが `send_task.sh "タスク内容"` を実行（ブロック）
3. ヤドランがソケットで受信 → `claude -p --model sonnet` で3フェーズに分解
4. **Phase 1 (implement)**: 実装サブタスクをヤドン1〜Nに `ThreadPoolExecutor` で並列送信 → 完了待ち
5. **Phase 2 (docs)**: ドキュメント更新サブタスクをヤドンに並列送信 → 完了待ち
6. **Phase 3 (review)**: レビューサブタスクをヤドンに送信 → 完了待ち
7. 全フェーズの結果を集約してヤドキングへ返却

フェーズ間は逐次実行（implement → docs → review）。各フェーズ内のサブタスクは並列実行。

## 起動方法

```bash
# 全エージェント一括起動（ペット+デーモン → ヤドキング）
./start.sh [作業ディレクトリ]

# ヤドン数を指定して起動（デフォルト4、範囲1-8）
YADON_COUNT=6 ./start.sh [作業ディレクトリ]

# 停止（ヤドキング終了時に自動停止、手動停止も可）
./stop.sh

# デーモンのみ再起動（ヤドキング実行中に使用）
./scripts/restart_daemons.sh
```

`start.sh` は `python3 -m yadon_agents.cli start` のラッパー。以下が順に起動する:
1. ヤドン1〜N（ペット+エージェント or デーモンのみ、N = `YADON_COUNT` 環境変数、デフォルト4）
2. ヤドラン（ペット+エージェント or デーモンのみ）
3. ヤドキング（`claude --model opus` — 対話型、現在のターミナル）

ヤドキング終了時にデーモン+ペットも自動停止する。

### 動作モード

| 環境 | ヤドン起動コマンド | ヤドラン起動コマンド |
|------|-------------------|---------------------|
| PyQt6あり | `python3 -m yadon_agents.gui.yadon_pet --number N` | `python3 -m yadon_agents.gui.yadoran_pet` |
| PyQt6なし | `python3 -m yadon_agents.agent.worker --number N` | `python3 -m yadon_agents.agent.manager` |

### PYTHONPATH

`pip install -e .` の代わりに `PYTHONPATH` でパッケージを参照する。
start.sh / stop.sh / restart_daemons.sh は自動で `PYTHONPATH=src/` を設定。
cli.py は子プロセスにも PYTHONPATH を伝播する。

## scripts/

### send_task.sh
ヤドキングがヤドランにタスクを送信するスクリプト。Unixソケット経由でJSON送受信。
結果が返るまでブロックする（タイムアウト: 10分）。

```bash
send_task.sh <instruction> [project_dir]
```

### check_status.sh
全エージェントまたは特定エージェントのステータスをUnixソケット経由で照会（タイムアウト: 5秒）。

```bash
check_status.sh              # 全エージェント
check_status.sh yadoran      # ヤドランのみ
check_status.sh yadon-1      # ヤドン1のみ
```

### restart_daemons.sh
ヤドキング実行中にデーモン（ヤドラン + ヤドン1〜4）のみを再起動するスクリプト。
stop.sh → デーモン再起動の順で実行。ヤドキングは再起動不要。

### pet_say.sh
ペットに吹き出しメッセージを送信するヘルパー。ペットソケット (`/tmp/yadon-pet-N.sock`) 経由。
ヤドン1〜4に対応（番号指定）。ペット未起動時は静かに終了。

```bash
pet_say.sh <yadon_number> <message> [bubble_type] [duration_ms]
```

## 役割制御（PreToolUseフック）

`AGENT_ROLE` 環境変数と `.claude/hooks/enforce-role.sh` により、役割に応じたツール実行制限を技術的に強制する。

| エージェント | AGENT_ROLE | Edit/Write | Bash (git書込) | Bash (読取) |
|---|---|---|---|---|
| ヤドキング | `yadoking` | 全禁止 | 禁止 | 許可 |
| ヤドラン | `yadoran` | 全禁止 | 禁止 | 許可 |
| ヤドン1-N | `yadon` | 全許可 | 全許可 | 全許可 |

`AGENT_ROLE` 未設定時は全て許可（通常のClaude Code使用）。
jq 未インストール時はフェイルオープン。
