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

GUIデーモン（ヤドラン + ヤドン1〜N のペットUI + エージェントスレッド）は別プロセスで起動され、CLIプロセス（ヤドキング）とは独立して動作する。

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
├── start.sh                          # 起動ラッパー → uv run yadon start
├── stop.sh                           # 停止スクリプト（gui_daemon + cli両方をpkill、ソケットクリーンアップ）
├── src/
│   └── yadon_agents/
│       ├── __init__.py
│       ├── cli.py                    # Composition Root: yadon start/stop、GUIデーモン起動+ソケット待機+コーディネーター起動
│       ├── ascii_art.py              # ターミナル用ヤドンASCIIアート表示（RGB→ANSI256色変換）
│       ├── gui_daemon.py             # GUIデーモン（別プロセス）: PyQt6 QApplication + ペット1-N + マネージャー + エージェントスレッド
│       │
│       ├── domain/                   # ドメイン層（純粋データ、I/Oなし）
│       │   ├── types.py             # AgentRole enum
│       │   ├── messages.py          # TaskMessage, ResultMessage, StatusQuery, StatusResponse
│       │   ├── formatting.py        # summarize_for_bubble（吹き出し用テキスト要約）
│       │   ├── task_types.py        # Subtask, Phase TypedDict（タスク分解結果の型）
│       │   ├── theme.py             # ThemeConfig frozen dataclass（テーマ全設定）
│       │   └── ports/               # ポート定義（抽象インターフェース）
│       │       ├── agent_port.py    # AgentPort ABC, BubbleCallback型
│       │       └── claude_port.py   # ClaudeRunnerPort ABC
│       │
│       ├── agent/                    # アプリケーション層（エージェントロジック）
│       │   ├── base.py              # BaseAgent(AgentPort): ソケットサーバーループ + on_bubble callback + try-finallyリソース管理
│       │   ├── worker.py            # YadonWorker(BaseAgent): claude haiku実行（ClaudeRunnerPort DI）
│       │   └── manager.py           # YadoranManager(BaseAgent): 3フェーズ分解 + 並列dispatch + 集約（ClaudeRunnerPort DI）
│       │
│       ├── infra/                    # インフラ層（I/Oアダプター）
│       │   ├── protocol.py          # Unixソケット通信（JSON over Unix socket, SHUT_WR EOF）
│       │   ├── claude_runner.py     # SubprocessClaudeRunner(ClaudeRunnerPort): claude -p 実行
│       │   └── process.py           # log_dir()（ログディレクトリ生成のみ、PID管理なし）
│       │
│       ├── config/                   # 設定
│       │   ├── agent.py             # メッセージ定数、バリアント、やるきスイッチ、get_yadon_count()
│       │   └── ui.py                # ピクセルサイズ、フォント、色、アニメーション設定
│       │
│       ├── gui/                      # GUI層（PyQt6、オプション依存）
│           ├── base_pet.py          # BasePet(QWidget): 共通ペットロジック
│           ├── yadon_pet.py         # YadonPet(BasePet): やるきスイッチ等
│           ├── yadoran_pet.py       # YadoranPet(BasePet)
│           ├── agent_thread.py      # AgentThread(QThread): BaseAgent → pyqtSignal変換
│           ├── pet_socket_server.py # PetSocketServer(QThread): 吹き出し受信
│           ├── speech_bubble.py     # 吹き出しウィジェット
│           ├── pokemon_menu.py      # 右クリックメニュー
│           ├── pixel_data.py        # テーマ経由のスプライト委譲
│           ├── yadoran_pixel_data.py # テーマ経由のスプライト委譲
│           └── macos.py             # macOS window elevation (NSWindow)
│       └── themes/                   # テーマ層（スプライト・スタイル管理）
│           ├── __init__.py          # テーマファクトリ
│           └── yadon/               # ヤドン標準テーマ
│               ├── __init__.py      # YadonTheme定義
│               └── sprites.py       # ヤドン ドット絵スプライトデータ
│
├── tests/                            # テスト（pytest）
│   ├── domain/
│   │   ├── test_formatting.py       # summarize_for_bubble テスト
│   │   ├── test_messages.py         # メッセージ型テスト
│   │   └── test_theme.py            # ThemeConfig テスト
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

### BaseAgent + on_bubble callback とリソース管理

`BaseAgent(AgentPort)` の `on_bubble: BubbleCallback | None` で吹き出し通知を抽象化。
`AgentThread` が `on_bubble` を pyqtSignal に接続し、GUI層と連携する。

**リソース管理の設計判断：**
- `serve_forever()` が try-finally で一元管理し、どの経路（正常終了・エラー・stop呼び出し）でも確実にリソース解放
  - **外側 try ブロック（106-131行）**: サーバーソケット作成（`proto.create_server_socket()`）→ `running = True` → メインループ（`while self.running`）
    - **内側 try-except（113-131行）**: ソケット受け入れ＆接続処理。タイムアウト例外（`socket.timeout`）は許容して継続、その他の OSError は break して外側 finally へ
    - **接続処理（115-126行）**: `server_sock.accept()` でコネクション受け入れ → スレッド生成 → `thread.join()` で該接続処理終了まで待機（ブロッキング）
  - **finally ブロック（132-135行）**: サーバーソケットのクローズ（`self.server_sock.close()`）と ファイルの削除（`proto.cleanup_socket()`）を一本化
  - **効果**: キープアライブされたファイルディスクリプタやソケットファイルが確実にクリーンアップされ、リスタート時の競合を防止
- `serve_forever()` 内の while ループで `SOCKET_ACCEPT_TIMEOUT` を短く（デフォルト1秒）設定し、`running` フラグの変更を即座に検知可能に
- `stop()` メソッドは `self.running = False` を設定するのみで責務を明確化。ソケットクローズ・ファイル削除は finally ブロックで一本化
- この分離により、エージェント側から stop 呼び出ししても、メインループ終了時には必ず finally ブロックが実行され、リソースが確実に解放される
  - **スレッド安全性**: `thread.join()` がブロッキング待機するため、handle_task() 中の外部リソース（ファイルハンドル、ネットワーク接続等）が確実に完了してから次の接続を処理
  - **stop フロー**: `stop()` 呼び出し → `running = False` → while ループ脱出 → finally 実行 → リソース確実解放

### AgentThread

`gui/agent_thread.py` で `AgentPort` を QThread でラップ。
`bubble_request` シグナルが BasePet の `show_bubble` スロットに接続される。

### BasePet + Composition Root（GUI層）

`gui/base_pet.py` で共通ペットロジック（ドラッグ、アニメーション、描画、メニュー、吹き出し）を集約。
YadonPet / YadoranPet はコンストラクタで `agent_thread` と `pet_sock_path` を受け取る（DI）。

### ascii_art.py — ターミナル起動表示

`ascii_art.py` はターミナルでヤドンのドット絵を表示するモジュール。

**機能:**
- `show_yadon_ascii()` — 起動時にヤドンのドット絵を表示（`cmd_start()` で呼び出し）
- `print_yadon_sprite()` — ドット絵の各ピクセルをANSI背景色で描画（2文字幅ブロック）
- `rgb_to_ansi256()` — RGB hex色（`#RRGGBB`）をANSI 256色パレット（16-231の6×6×6カラーキューブ）に近似変換

**フロー:**
1. テーマから `get_theme()` でテーマオブジェクトを取得し、`get_worker_sprite_builder()` でスプライトビルダーを取得。ビルダーを `"normal"` ステート + `theme.worker_color_schemes` で呼び出し、ドット絵ピクセル配列を構築（各色は`#RRGGBB`hex形式）
2. ピクセルデータを行単位でループし、各ピクセルを処理：白色（`#FFFFFF`）は透明として2文字スペース、その他は `rgb_to_ansi256()` でANSI256コードに変換
3. ターミナルに背景色付きブロック（`\033[48;5;{ansi_code}m  \033[0m`：2文字幅で正方形に見える）で描画、各行末で改行

### gui_daemon.py — GUIデーモン

`gui_daemon.py` は別プロセスで起動するGUIデーモン。全ペットウィジェット・エージェントスレッド・Qtイベントループを管理する。
`cmd_start()` から `subprocess.Popen()` で起動され、stderrは `~/.yadon-agents/logs/gui_daemon.log` に追記モード出力、stdoutはDEVNULL（PyQt不要出力抑制）。

**主要コンポーネント:**
- **QApplication** — Qtイベントループのマスター。フォーカス奪取防止設定（`setQuitOnLastWindowClosed(False)`）
- **ワーカーペット 1〜N** — 各 `YadonPet` とそれに紐付く `AgentThread(YadonWorker)` を構築
- **マネージャーペット** — `YadoranPet` とそれに紐付く `AgentThread(YadoranManager)` を構築
- **配置** — 画面右下からスタック配置（`x_pos = screen.width() - margin - (WIDTH + spacing) * number`）
- **ウェルカムメッセージ** — 起動後、各ペットの吹き出しにテーマから選択したランダムなメッセージを表示（`QTimer.singleShot(0, _show_welcome)`）

**フロー:**
1. テーマ・ヤドン数を取得
2. QApplication作成＆初期化（Pythonシグナル処理用タイマー含む）
3. ワーカーペット（`YadonPet × N`）を構築＆配置
4. マネージャーペット（`YadoranPet`）を構築＆配置
5. ウェルカムメッセージ表示
6. `app.exec()` でQtイベントループ開始（ペット操作・吹き出し・エージェント通信を駆動）

### cmd_start() — グローバル Composition Root

`cli.py` の `cmd_start()` 関数がグローバルな Composition Root として機能する。

**責務:**
1. **ヤドン ASCIIアート表示** — 起動時にターミナルに ASCII アート を表示
2. **既存プロセス停止** — 旧プロセスが起動している場合は `pkill -f` で停止
3. **ログディレクトリ確保** — `log_dir()` で統一ログ領域を初期化
4. **GUIデーモンを別プロセスで起動** — `subprocess.Popen()` で `python3 -m yadon_agents.gui_daemon` を背景実行
5. **ソケット待機** — `_wait_sockets()` で全ペット・ワーカー・マネージャーの起動完了を同期
6. **コーディネーター（Opus）起動** — `subprocess.run(["claude", "--model", "opus", ...])` で人間インターフェース
7. **終了処理** — コーディネーター終了時に GUIプロセスを `terminate()` → `kill()` で停止し、ソケット削除

**特徴:**
- **2プロセス構成** — CLI プロセス（ヤドキング・ヤドラン・ヤドン） + GUI デーモンプロセス（ペット UI・吹き出し）を分離
- **フォーカス奪取防止** — GUI デーモンを別プロセスで実行することで、ターミナルフォーカスの奪取を回避
- **スケーラビリティ** — `YADON_COUNT` で ワーカー数を 1〜8 に動的調整可能。マネージャーは常時1個固定

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

### 吹き出しテキスト折り返し — 80文字幅固定設計

`gui/speech_bubble.py` の吹き出しウィジェットは、テキスト長に関わらず **常に80文字幅で固定**する設計を採用している。

**実装:**
- `speech_bubble.py:59-62` で 'M' 80文字分のフォントメトリクスから最大幅を算出（半角80文字幅）
- `max_bubble_width = metrics.horizontalAdvance('M' * 80) + BUBBLE_PADDING * 2 + 20`（定数）
- テキスト長が短い場合でも、長い場合でも、同じ幅で固定
- テキストは `_wrap_text()` で常に折り返され、**縦方向に伸びる**（高さ可変）

**理由:**
1. **折り返し動作の統一** — 画面幅ベースの動的計算を廃止することで、複数行折り返しが発生するテキストの見映えを一定に保つ
2. **ペット吹き出し表示の安定性** — 固定幅により、ペットの位置計算（上下左右配置）がシンプルになり、画面端への衝突判定が予測可能
3. **半角80文字幅基準** — 'M' は等幅フォントで最も幅が広い文字で、半角80文字幅の基準として使用
4. **テキスト修飾なし** — Noto Serif JP フォントで装飾なく描画。横幅制限により自動折り返しが一律に動作

### テストの注意点

- **FakeClaudeRunner**: 各テストファイル（`test_manager.py`、`test_worker.py`、`test_claude_runner.py`）内で`ClaudeRunnerPort`モックを独立に定義。共有テストフィクスチャは使用せず、テスト独立性を確保
- **setup_method**: テストクラスの各テストメソッド実行前に`setup_method`で theme cache をリセット（`from yadon_agents.config.ui import PIXEL_DATA_CACHE; PIXEL_DATA_CACHE.clear()`）

## テスト

### テスト実行結果

**実行日**: 2026年2月2日
**テスト総数**: 88
**成功**: 88 (100%)
**失敗**: 0 (0%)

```bash
python -m pytest tests/ -v
# ============================= test session starts ==============================
# 88 passed in 0.07s
```

### テスト構成（88テスト）

| モジュール | テストファイル | テスト数 | ステータス |
|-----------|----------------|---------|-----------|
| **agent** | `test_base.py` | 5 | ✅ All pass |
| | `test_manager.py` | 9 | ✅ All pass |
| | `test_worker.py` | 7 | ✅ All pass |
| **domain** | `test_ascii_art.py` | 10 | ✅ All pass |
| | `test_formatting.py` | 7 | ✅ All pass |
| | `test_messages.py` | 9 | ✅ All pass |
| | `test_theme.py` | 34 | ✅ All pass |
| **infra** | `test_claude_runner.py` | 4 | ✅ All pass |
| | `test_protocol.py` | 6 | ✅ All pass |
| **合計** | | **90** | ✅ **全成功** |

### テスト範囲

- **Agent Layer**: ソケット通信、メッセージハンドリング、タスク分解、結果集約、ワーカータスク実行
- **Domain Layer**: テキスト要約、メッセージ型、ThemeConfig、スプライトビルダー、後方互換性
- **Infra Layer**: Claude CLIランナー（subprocess実行、タイムアウト）、Unixソケット通信（作成・送受信・クリーンアップ）

### 失敗テストなし

現在全てのテストが成功しています。

**テスト実行環境:**
- Python 3.10+
- pytest（テストランナー）
- 依存モック（ClaudeRunnerPort、subprocess）

**カバレッジ内容:**
- Socket communication: Unix ドメインソケットの作成・送受信・クリーンアップ
- Agent orchestration: BaseAgent の on_bubble callback、ソケットサーバーループ
- Task decomposition: YadoranManager の JSON抽出＆3フェーズ分解＆並列dispatch＆結果集約
- Worker execution: YadonWorker のタスク実行＆プロンプト構築
- Domain types: メッセージ型、テーマ設定、テキスト要約

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

### GUIデーモン分離アーキテクチャ

`start.sh` は `uv run yadon start` のラッパー。**2つの独立したプロセス**で起動する:

**CLI プロセス（ヤドキング・ヤドラン・ヤドン エージェント）:**
1. **ASCIIアート表示** — ターミナルにヤドンをアスキーアート表示
2. **既存プロセス停止** — 旧 GUIデーモン・CLIプロセスが起動していれば `pkill -f` で停止
3. **ログディレクトリ確保** — `log_dir()` で ~/.yadon-agents/logs を初期化
4. **GUI デーモンプロセス起動** — `subprocess.Popen(["python3", "-m", "yadon_agents.gui_daemon"])` で背景実行
5. **ソケット待機** — `_wait_sockets()` で全ペット・ワーカー・マネージャーの起動完了を同期
6. **コーディネーター（ヤドキング）起動** — `subprocess.run(["claude", "--model", "opus", ...])`。人間との対話、send_task.sh 呼び出し

**GUI デーモンプロセス（ペット UI + エージェントスレッド）:**
1. **QApplication + Qtイベントループ（メインスレッド）** — 全ウィジェット、全Qtシグナル・スロット、タイマーを駆動
2. **ワーカーエージェント 1〜N（QThread × N）** — 各 AgentThread が YadonWorker を実行。ソケットサーバーループで ヤドランからのタスク受信
3. **マネージャーエージェント 1個（QThread × 1）** — AgentThread が YadoranManager を実行。3フェーズ分解・並列dispatch・結果集約、ヤドキングからのタスク受信
4. **ペット UI（PyQt6 QWidget）** — YadonPet × N + YadoranPet。ドラッグ・アニメーション・吹き出し表示
5. **起動時ウェルカムメッセージ** — 各ペットの吹き出しにランダムなウェルカムメッセージが表示される。ヤドンはテーマの `welcome_messages` から、ヤドランは `manager_welcome_messages` から選択

**プロセス終了フロー:**
- ヤドキング（opus）が終了 → Ctrl+C または exit コマンド
- CLI プロセスの `cmd_start()` が終了検知 → GUIプロセスを `terminate()` 試行
- 5秒タイムアウト待機後、応答なければ `gui_process.kill()` で強制停止
- ソケット削除（`_cleanup_sockets()`）
- 両プロセス完全終了

### uv 依存管理

`pip install -e .` の代わりに `uv` でパッケージ依存を管理する。
`pyproject.toml` に定義された依存が自動解決され、`uv run` で実行時に適用される。
start.sh は `uv run yadon start` のラッパーで、自動的に環境を構築・実行。

### PID管理の撤去

旧アーキテクチャでは複数のデーモンプロセスを PID ファイルで管理していた。

**現在のアーキテクチャ（GUIデーモン + CLI分離）:**
- ✅ **PID ファイル廃止** — プロセスは `pkill -f` パターンマッチで停止。ファイルベース追跡不要
- ✅ **log_dir()への一本化** — `log_dir()` は **ログディレクトリのみ**生成。PID追跡なし
- ✅ **stop.sh の更新** — `pkill -f "yadon_agents.gui_daemon"` と `pkill -f "yadon_agents.cli start"` で2つのプロセスを停止

`infra/process.py` の `log_dir()`:
```python
def log_dir() -> Path:
    """ログディレクトリ確保（PID管理なし、ディレクトリ生成のみ）"""
    base = Path.home() / ".yadon-agents" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base
```

### stop.sh の停止処理

GUIデーモン分離後は、独立した2つのプロセス（`gui_daemon` と `cli start`）を停止する必要がある。

**現在のアーキテクチャ（GUIデーモン + CLI分離）:**
```bash
#!/bin/bash
# GUIデーモン + CLIプロセスを両方停止 → ソケット削除
pkill -f "yadon_agents.gui_daemon" 2>/dev/null || true
pkill -f "yadon_agents.cli start" 2>/dev/null || true
for SOCK in /tmp/yadon-agent-*.sock /tmp/yadon-pet-*.sock; do
    [ -S "$SOCK" ] && rm -f "$SOCK" || true
done
```

**停止対象:**
- `gui_daemon` — ペット UI・吹き出し表示を担当（PyQt6 GUI プロセス）
- `cli start` — ヤドキング・ヤドラン・ヤドン エージェント実行（Python CLI プロセス）
- **ソケット削除** — クリーンアップ用（通常は自動削除されるが、明示的に削除）

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
