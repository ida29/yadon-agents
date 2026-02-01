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

全エージェント（ヤドラン + ヤドン1〜N）は1つのPyQt6プロセス内でスレッド実行される。

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
├── stop.sh                           # 停止スクリプト（pkill + ソケットクリーンアップ）
├── src/
│   └── yadon_agents/
│       ├── __init__.py
│       ├── cli.py                    # CLIエントリポイント: yadon start/stop
│       │
│       ├── domain/                   # ドメイン層（純粋データ、I/Oなし）
│       │   ├── types.py             # AgentRole enum
│       │   ├── messages.py          # TaskMessage, ResultMessage, StatusQuery, StatusResponse
│       │   ├── formatting.py        # summarize_for_bubble（吹き出し用テキスト要約）
│       │   └── ports/               # ポート定義（抽象インターフェース）
│       │       ├── agent_port.py    # AgentPort ABC, BubbleCallback型
│       │       └── claude_port.py   # ClaudeRunnerPort ABC
│       │
│       ├── agent/                    # アプリケーション層（エージェントロジック）
│       │   ├── base.py              # BaseAgent(AgentPort): ソケットサーバーループ + on_bubble callback
│       │   ├── worker.py            # YadonWorker(BaseAgent): claude haiku実行（ClaudeRunnerPort DI）
│       │   └── manager.py           # YadoranManager(BaseAgent): 3フェーズ分解 + 並列dispatch + 集約（ClaudeRunnerPort DI）
│       │
│       ├── infra/                    # インフラ層（I/Oアダプター）
│       │   ├── protocol.py          # Unixソケット通信（JSON over Unix socket, SHUT_WR EOF）
│       │   ├── claude_runner.py     # SubprocessClaudeRunner(ClaudeRunnerPort): claude -p 実行
│       │   └── process.py           # log_dir()（ログディレクトリ管理）
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
│           └── macos.py             # macOS window elevation (NSWindow)
│
├── tests/                            # テスト（pytest）
│   ├── domain/
│   │   ├── test_formatting.py       # summarize_for_bubble テスト
│   │   └── test_messages.py         # メッセージ型テスト
│   ├── infra/
│   │   ├── test_protocol.py         # Unixソケット通信テスト
│   │   └── test_claude_runner.py    # SubprocessClaudeRunner テスト（subprocess モック）
│   └── agent/
│       ├── test_base.py             # BaseAgent テスト
│       ├── test_manager.py          # YadoranManager テスト（_extract_json, _aggregate_results, decompose_task, handle_task統合テスト）
│       └── test_worker.py           # YadonWorker テスト（handle_task, プロンプト構築）
├── scripts/
│   ├── send_task.sh                 # ヤドキング → ヤドランへタスク送信
│   ├── check_status.sh              # エージェントのステータス照会
│   ├── restart_daemons.sh           # 停止+再起動ラッパー（stop.sh && start.sh）
│   └── pet_say.sh                   # ヤドンペットに吹き出し送信
├── instructions/
│   ├── yadoking.md                  # ヤドキング指示書
│   ├── yadoran.md                   # ヤドラン指示書（3フェーズ分解）
│   └── yadon.md                     # ヤドン指示書
├── memory/
│   └── global_context.md            # ヤドキングの学習記録
├── logs/                             # ログファイル（自動生成）
└── .claude/
    ├── settings.json                 # PreToolUseフック設定
    └── hooks/
        └── enforce-role.sh           # 役割別ツール制御スクリプト
```

## 設計判断

### Port & Adapter（DI）

`domain/ports/` に抽象インターフェースを定義し、コンストラクタ注入で具体実装を差し替え可能にする。

- `AgentPort` — エージェントの公開インターフェース。`BaseAgent` が実装
- `ClaudeRunnerPort` — Claude CLI実行の抽象。`SubprocessClaudeRunner` が実装

`YadonWorker` / `YadoranManager` は `claude_runner: ClaudeRunnerPort | None = None` を受け取り、未指定時は `SubprocessClaudeRunner()` をデフォルト生成する。テスト時にはモックを注入可能。

### BaseAgent + on_bubble callback

`BaseAgent(AgentPort)` の `on_bubble: BubbleCallback | None` で吹き出し通知を抽象化。
`AgentThread` が `on_bubble` を pyqtSignal に接続し、GUI層と連携する。

### AgentThread

`gui/agent_thread.py` で `AgentPort` を QThread でラップ。
`bubble_request` シグナルが BasePet の `show_bubble` スロットに接続される。

### BasePet + Composition Root

`gui/base_pet.py` で共通ペットロジック（ドラッグ、アニメーション、描画、メニュー、吹き出し）を集約。
YadonPet / YadoranPet はコンストラクタで `agent_thread` と `pet_sock_path` を受け取る（DI）。
具体的な依存の組み立ては `cli.py` の `cmd_start()` 関数（Composition Root）で行う。

### YadoranManager — JSON抽出とタスク分解

**_extract_json（40-90行）** — Claude出力からJSONを抽出する。

1. JSONフェンス（```json...```）を探索して抽出
2. 通常のJSON.loads()を試行
3. 失敗時、出力全体から最初の`{`から最後の`}`までを切り出し（**地の文混在対応**）
4. それでも失敗なら JSONDecodeError を raise

この3段階のフォールバック仕組みにより、Claude が`こういった JSON が出力されます: {...}`のような形式で返した場合でも抽出可能。

**decompose_task（138-210行）** — タスクを3フェーズに分解する。

- `claude -p --model sonnet` で Prompt Caching を活用
- タイムアウト: CLAUDE_DECOMPOSE_TIMEOUT（デフォルト 30秒）
- JSON 解析失敗時ログ：`logger.warning()` で 500 文字まで出力を記録（201行）
- フォールバック：JSON パース失敗時は元の instruction を implement フェーズ 1 つのサブタスクとして実行継続
- ログレベル：成功時は INFO（197行）、失敗時は WARNING（201-206行）

### テストの注意点

- **FakeClaudeRunner**: 各テストファイル（`test_manager.py`、`test_worker.py`、`test_claude_runner.py`）内で`ClaudeRunnerPort`モックを独立に定義。共有テストフィクスチャは使用せず、テスト独立性を確保
- **setup_method**: テストクラスの各テストメソッド実行前に`setup_method`で theme cache をリセット（`from yadon_agents.config.ui import PIXEL_DATA_CACHE; PIXEL_DATA_CACHE.clear()`）

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
# 全エージェント一括起動（1プロセスで全ペット+ヤドキング）
./start.sh [作業ディレクトリ]

# ヤドン数を指定して起動（デフォルト4、範囲1-8）
YADON_COUNT=6 ./start.sh [作業ディレクトリ]

# 停止（ヤドキング終了時に自動停止、手動停止も可）
./stop.sh

# 停止+再起動
./scripts/restart_daemons.sh
```

`start.sh` は `python3 -m yadon_agents.cli start` のラッパー。1つのPyQt6プロセス内で以下が起動する:
1. QApplication + メインスレッド（Qtイベントループ）
2. ヤドン1〜N（QThread: AgentThread + QWidget: YadonPet、N = `YADON_COUNT` 環境変数、デフォルト4）
3. ヤドラン（QThread: AgentThread + QWidget: YadoranPet）
4. ヤドキング（threading.Thread: `subprocess.run("claude --model opus")`）

ヤドキング終了時に `QApplication.quit()` → 全ペット・スレッド自動停止。

### PYTHONPATH

`pip install -e .` の代わりに `PYTHONPATH` でパッケージを参照する。
start.sh は自動で `PYTHONPATH=src/` を設定。

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
全体を停止して再起動するスクリプト。`stop.sh && start.sh "$@"` のラッパー。

### pet_say.sh
ペットに吹き出しメッセージを送信するヘルパー。ペットソケット (`/tmp/yadon-pet-N.sock`) 経由。
ヤドン1〜Nに対応（番号指定）。ペット未起動時は静かに終了。

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
