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
│                  │  yadon send / yadon status を実行
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
├── src/
│   └── yadon_agents/
│       ├── __init__.py
│       ├── cli.py                    # Composition Root: yadon start/stop/send/status/restart/say、GUIデーモン起動+ソケット待機+コーディネーター起動
│       ├── commands.py               # CLIサブコマンド実装（yadon _send/_status/_restart/_say等、内部用）
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
│       │       ├── llm_port.py      # LLMRunnerPort ABC（マルチLLMバックエンド対応）
│       │       └── claude_port.py   # 後方互換エイリアス（ClaudeRunnerPort → LLMRunnerPort）
│       │
│       ├── agent/                    # アプリケーション層（エージェントロジック）
│       │   ├── base.py              # BaseAgent(AgentPort): ソケットサーバーループ + on_bubble callback + try-finallyリソース管理
│       │   ├── worker.py            # YadonWorker(BaseAgent): claude haiku実行（ClaudeRunnerPort DI）
│       │   └── manager.py           # YadoranManager(BaseAgent): 3フェーズ分解 + 並列dispatch + 集約（ClaudeRunnerPort DI）
│       │
│       ├── infra/                    # インフラ層（I/Oアダプター）
│       │   ├── protocol.py          # Unixソケット通信（JSON over Unix socket, SHUT_WR EOF）
│       │   ├── claude_runner.py     # SubprocessClaudeRunner(LLMRunnerPort): マルチLLM CLI実行
│       │   └── process.py           # log_dir()（ログディレクトリ生成のみ、PID管理なし）
│       │
│       ├── config/                   # 設定
│       │   ├── agent.py             # メッセージ定数、バリアント、やるきスイッチ、get_yadon_count()
│       │   ├── ui.py                # ピクセルサイズ、フォント、色、アニメーション設定
│       │   └── llm.py               # LLMバックエンド設定（BACKEND_CONFIGS, get_backend_config等）
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
│       ├── themes/                   # テーマ層（スプライト・スタイル管理）
│       │   ├── __init__.py          # テーマファクトリ
│       │   └── yadon/               # ヤドン標準テーマ
│       │       ├── __init__.py      # YadonTheme定義
│       │       └── sprites.py       # ヤドン ドット絵スプライトデータ
│       └── instructions/             # 指示書（パッケージデータ、リソース）
│           ├── __init__.py          # パッケージマーカー
│           ├── yadoking.md          # ヤドキング指示書
│           ├── yadoran.md           # ヤドラン指示書（3フェーズ分解）
│           └── yadon.md             # ヤドン指示書
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
├── memory/
│   └── global_context.md            # ヤドキングの学習記録
├── logs/                             # ログファイル（自動生成）
└── .claude/
    ├── settings.json                 # PreToolUseフック設定
    └── hooks/
        └── enforce-role.sh           # 役割別ツール制御スクリプト
```

## 設計判断

### commands.py — CLIサブコマンド実装

`commands.py` は全CLIサブコマンド（`yadon start`, `stop`, `send`, `status`, `restart`, `say`）と内部用コマンド（`_send`, `_status`, `_restart`, `_say`）を Pythonモジュール化したもの。

**設計判断：**
- **シェルスクリプト廃止** — 旧アーキテクチャは `scripts/send_task.sh`, `check_status.sh`, `restart_daemons.sh`, `pet_say.sh` など複数のシェルスクリプトで管理していたが、Pythonモジュール化することで：
  - 💪 **コード一元管理** — CLI ロジック全体を Python で統一管理
  - 📦 **パッケージ化** — `pyproject.toml` で定義した `console_scripts` エントリポイント経由で配布・実行可能
  - 🔧 **テスト容易性** — Python unit test でコマンドロジックをテスト可能
  - 🚫 **シェルスクリプト依存廃止** — Unix/Linux 環境特有のスクリプト管理が不要
- **内部用コマンド前置詞** — `yadon _send` など `_` 前置を使用して、内部用と公開用を視覚的に分離
- **スクリプト残存なし** — `start.sh`, `stop.sh` は `uv run yadon` や直接 `yadon` コマンド実行に完全置換

**ファイル構成:**
- `cli.py` — メインのCLI エントリポイント（`@main.command()` で各サブコマンド登録）
- `commands.py` — サブコマンド実装関数（`cmd_start()`, `cmd_stop()`, `cmd_send()` 等）

### Port & Adapter（DI）

`domain/ports/` に抽象インターフェースを定義し、コンストラクタ注入で具体実装を差し替え可能にする。

- `AgentPort` — エージェントの公開インターフェース。`BaseAgent` が実装
- `LLMRunnerPort` — LLM CLI実行の抽象。`SubprocessClaudeRunner` が実装
- `ClaudeRunnerPort` — 後方互換エイリアス（`LLMRunnerPort` への参照）

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
4. **GUIデーモンを別プロセスで起動** — `subprocess.Popen(["python3", "-m", "yadon_agents.gui_daemon"], ..., env=os.environ.copy())` で背景実行。**環境変数継承の確実化**: 親プロセス（CLI プロセス）の環境変数（`LLM_BACKEND`, `YADON_N_BACKEND`, `YADON_COUNT` 等）を GUIデーモンプロセスに確実に継承させるため、`env=os.environ.copy()` を明示的に渡す。未指定時はシステムデフォルト環境が使用される可能性があり、マルチLLMモードやバックエンド指定が GUIデーモンに反映されない問題が発生するため、明示的な指定が必須
5. **ソケット待機** — `_wait_sockets()` で全ペット・ワーカー・マネージャーの起動完了を同期
6. **コーディネーター（Opus）起動** — `subprocess.run(["claude", "--model", "opus", ...])` で人間インターフェース（`yadon send` コマンド実行可能）
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

### 吹き出しテキスト折り返し — 40文字幅固定設計

`gui/speech_bubble.py` の吹き出しウィジェットは、テキスト長に関わらず **常に40文字幅で固定**する設計を採用している。

**実装:**
- `speech_bubble.py:59` で 'M' 40文字分のフォントメトリクスから最大幅を算出（半角40文字幅）
- `max_bubble_width = metrics.horizontalAdvance('M' * 40) + BUBBLE_PADDING * 2 + 20`（定数）
- `speech_bubble.py:60` で `bubble_width = max_bubble_width` として常に固定幅を適用
- テキスト長が短い場合でも、長い場合でも、同じ幅で固定
- テキストは `_wrap_text()` で常に折り返され、**縦方向に伸びる**（高さ可変）
- 画面下部の安全マージンは **50px** に設定（吹き出しが画面下部に切れるのを防止）

**理由:**
1. **折り返し動作の統一** — 画面幅ベースの動的計算を廃止することで、複数行折り返しが発生するテキストの見映えを一定に保つ
2. **ペット吹き出し表示の安定性** — 固定幅により、ペットの位置計算（上下左右配置）がシンプルになり、画面端への衝突判定が予測可能
3. **半角40文字幅基準** — 'M' は等幅フォントで最も幅が広い文字で、半角40文字幅の基準として使用
4. **テキスト修飾なし** — Noto Serif JP フォントで装飾なく描画。横幅制限により自動折り返しが一律に動作
5. **画面下部安全マージン50px** — 吹き出しが画面下部 (`update_position()` の104行目で `screen.height() - self.height() - 50`)に配置される際、画面外にはみ出さないようするため。ペットが画面下部にある場合も、50px のマージンを確保して表示

### テストの注意点

- **FakeClaudeRunner**: 各テストファイル（`test_manager.py`、`test_worker.py`、`test_claude_runner.py`）内で`ClaudeRunnerPort`モックを独立に定義。共有テストフィクスチャは使用せず、テスト独立性を確保
- **setup_method**: テストクラスの各テストメソッド実行前に`setup_method`で theme cache をリセット（`from yadon_agents.config.ui import PIXEL_DATA_CACHE; PIXEL_DATA_CACHE.clear()`）

## テスト

### テスト実行結果

**実行日**: 2026年2月2日
**テスト総数**: 99
**成功**: 99 (100%)
**失敗**: 0 (0%)

```bash
python -m pytest tests/ -v
# ============================= test session starts ==============================
# 99 passed in 0.08s
```

### テスト構成（99テスト）

| モジュール | テストファイル | テスト数 | ステータス |
|-----------|----------------|---------|-----------|
| **agent** | `test_base.py` | 5 | ✅ All pass |
| | `test_manager.py` | 9 | ✅ All pass |
| | `test_worker.py` | 7 | ✅ All pass |
| **config** | `test_llm.py` | 9 | ✅ All pass |
| **domain** | `test_ascii_art.py` | 10 | ✅ All pass |
| | `test_formatting.py` | 7 | ✅ All pass |
| | `test_messages.py` | 9 | ✅ All pass |
| | `test_theme.py` | 34 | ✅ All pass |
| **infra** | `test_claude_runner.py` | 4 | ✅ All pass |
| | `test_protocol.py` | 6 | ✅ All pass |
| **合計** | | **99** | ✅ **全成功** |

### テスト範囲

- **Agent Layer**: ソケット通信、メッセージハンドリング、タスク分解、結果集約、ワーカータスク実行
- **Config Layer**: LLMバックエンド設定、モデル階層、環境変数フォールバック
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
2. ヤドキングが `yadon send "タスク内容"` を実行（ブロック）
3. ヤドランがソケットで受信 → `claude -p --model sonnet` で3フェーズに分解
4. **Phase 1 (implement)**: 実装サブタスクをヤドン1〜Nに `ThreadPoolExecutor` で並列送信 → 完了待ち
5. **Phase 2 (docs)**: ドキュメント更新サブタスクをヤドンに並列送信 → 完了待ち
6. **Phase 3 (review)**: レビューサブタスクをヤドンに送信 → 完了待ち
7. 全フェーズの結果を集約してヤドキングへ返却

フェーズ間は逐次実行（implement → docs → review）。各フェーズ内のサブタスクは並列実行。

## 起動方法

### uvx で起動（推奨）

インストール不要で即実行:

```bash
# 通常起動（全員Claude）
uvx --from git+https://github.com/ida29/yadon-agents yadon start

# マルチLLMモード（各ワーカーに異なるLLMを割り当て）
uvx --from git+https://github.com/ida29/yadon-agents yadon start --multi-llm

# 作業ディレクトリ指定
uvx --from git+https://github.com/ida29/yadon-agents yadon start /path/to/project --multi-llm

# ヤドン数を指定して起動（デフォルト4、範囲1-8）
YADON_COUNT=6 uvx --from git+https://github.com/ida29/yadon-agents yadon start --multi-llm

# 停止
yadon stop

# ステータス確認
yadon status

# 再起動
yadon restart --multi-llm
```

### 永続インストール

頻繁に使う場合は uv tool install でグローバルインストール:

```bash
# 一度だけ実行
uv tool install git+https://github.com/ida29/yadon-agents

# 以降はどこからでも
yadon start --multi-llm
YADON_COUNT=6 yadon start --multi-llm
yadon stop
yadon status
yadon restart --multi-llm
```

### 開発時の起動

リポジトリをクローンして開発する場合:

```bash
# クローン
git clone https://github.com/ida29/yadon-agents
cd yadon-agents

# 起動
uv run yadon start --multi-llm

# 停止
uv run yadon stop

# ステータス確認
uv run yadon status

# 再起動
uv run yadon restart --multi-llm
```

## CLIコマンド

yadon CLI には以下のサブコマンドが用意されています：

### yadon start

ヤドン・エージェント全体を起動します。

```bash
# 基本的な起動
yadon start

# マルチLLMモード有効（各ワーカーに異なるバックエンドを割り当て）
yadon start --multi-llm

# 作業ディレクトリを指定
yadon start /path/to/project

# ワーカー数を指定（デフォルト4、範囲1-8）
YADON_COUNT=6 yadon start --multi-llm

# バックエンド指定
LLM_BACKEND=gemini yadon start
```

### yadon stop

ヤドン・エージェント全体を停止します。

```bash
yadon stop
```

### yadon send

ヤドキング → ヤドランにタスクを送信します（ブロッキング）。

```bash
# シンプルなタスク送信（タイムアウト: 10分）
yadon send "READMEを更新してください"

# 作業ディレクトリを指定
yadon send "テストを追加してください" /path/to/project

# マルチLLMモード＋カスタムワーカー数での実行
YADON_COUNT=6 yadon send "機能を実装してください"
```

### yadon status

エージェントのステータスを照会します（タイムアウト: 5秒）。

```bash
# 全エージェント
yadon status

# 特定エージェント
yadon status yadoran
yadon status yadon-1
yadon status yadon-2
```

### yadon restart

エージェント全体を停止して再起動します。

```bash
# 基本的な再起動
yadon restart

# オプション付き再起動
yadon restart --multi-llm /path/to/project
```

### yadon say

ペットに吹き出しメッセージを送信します。

```bash
# ヤドン1に送信
yadon say 1 "やるきスイッチ！"

# ヤドン2に送信（オプション: バブルタイプ、表示時間）
yadon say 2 "頑張ります" --type normal --duration 3000

# ペット未起動時は静かに終了
yadon say 3 "メッセージ"
```

## 内部用CLIコマンド

以下のコマンドは **ヤドキング・ヤドラン・ヤドン内部通信用** で、通常利用者は直接使用しません。

### yadon _send

ヤドランにタスクを送信します（内部用、ブロッキング）。

```bash
# タスク送信（内部用、通常は yadon send で代用）
yadon _send "タスク内容" /path/to/project
```

### yadon _status

エージェントのステータスを照会します（内部用、詳細版）。

```bash
# ステータス照会（内部用）
yadon _status
yadon _status yadoran
yadon _status yadon-1
```

### yadon _restart

エージェント全体を停止して再起動します（内部用）。

```bash
# 再起動（内部用、通常は yadon restart で代用）
yadon _restart --multi-llm /path/to/project
```

### yadon _say

ペットに吹き出しメッセージを送信します（内部用、スキップ無し）。

```bash
# メッセージ送信（内部用）
yadon _say 1 "メッセージ" normal 3000
```

### GUIデーモン分離アーキテクチャ

`yadon start` を実行すると **2つの独立したプロセス**で起動します:

**CLI プロセス（ヤドキング・ヤドラン・ヤドン エージェント）:**
1. **ASCIIアート表示** — ターミナルにヤドンをアスキーアート表示
2. **既存プロセス停止** — 旧 GUIデーモン・CLIプロセスが起動していれば `pkill -f` で停止
3. **ログディレクトリ確保** — `log_dir()` で ~/.yadon-agents/logs を初期化
4. **GUI デーモンプロセス起動** — `subprocess.Popen(["python3", "-m", "yadon_agents.gui_daemon"])` で背景実行
5. **ソケット待機** — `_wait_sockets()` で全ペット・ワーカー・マネージャーの起動完了を同期
6. **コーディネーター（ヤドキング）起動** — `subprocess.run(["claude", "--model", "opus", ...])`。人間との対話、`yadon send` 呼び出し

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
以前は start.sh ラッパーを使用していましたが、現在は `uv run yadon` または直接 `yadon` コマンドで実行します。

**依存管理方針:**
- **本体依存** — `[project] dependencies` で管理（PyQt6等）
- **開発依存** — `[dependency-groups] dev` で管理（pytest等）。`optional-dependencies` は使用しない
- 全ての依存は `[dependency-groups] dev` セクションで一元管理

### PID管理の撤去

旧アーキテクチャでは複数のデーモンプロセスを PID ファイルで管理していた。

**現在のアーキテクチャ（GUIデーモン + CLI分離）:**
- ✅ **PID ファイル廃止** — プロセスは `pkill -f` パターンマッチで停止。ファイルベース追跡不要
- ✅ **log_dir()への一本化** — `log_dir()` は **ログディレクトリのみ**生成。PID追跡なし
- ✅ **yadon stop の実装** — `pkill -f "yadon_agents.gui_daemon"` と `pkill -f "yadon_agents.cli start"` で2つのプロセスを停止

`infra/process.py` の `log_dir()`:
```python
def log_dir() -> Path:
    """ログディレクトリ確保（PID管理なし、ディレクトリ生成のみ）"""
    base = Path.home() / ".yadon-agents" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base
```

### yadon stop の停止処理

GUIデーモン分離後は、独立した2つのプロセス（`gui_daemon` と `cli start`）を停止する必要があります。

**yadon stop が実行する処理:**
1. GUIデーモンプロセスを停止 — `pkill -f "yadon_agents.gui_daemon"`
2. CLIプロセスを停止 — `pkill -f "yadon_agents.cli start"`
3. ソケットをクリーンアップ — `/tmp/yadon-agent-*.sock` と `/tmp/yadon-pet-*.sock` を削除

**停止対象:**
- `gui_daemon` — ペット UI・吹き出し表示を担当（PyQt6 GUI プロセス）
- `cli start` — ヤドキング・ヤドラン・ヤドン エージェント実行（Python CLI プロセス）
- **ソケット削除** — クリーンアップ用（通常は自動削除されるが、明示的に削除）

## LLMバックエンド切り替え

### 概要

複数のLLMバックエンド（Claude、Gemini、Copilot、OpenCode）をサポートし、環境変数 `LLM_BACKEND` で実行時に切り替え可能。
エージェント階層（ヤドキング/ヤドラン/ヤドン）に応じたモデル階層（coordinator/manager/worker）の最適なモデルを自動選択。

### 対応バックエンド

| バックエンド | コマンド | Coordinator | Manager | Worker | 説明 |
|---|---|---|---|---|---|
| **claude** (デフォルト) | `claude` | opus | sonnet | haiku | Anthropic Claude CLI |
| **claude-opus** | `claude` | opus | opus | opus | Anthropic Claude CLI (All Opus) |
| **gemini** | `gemini` | gemini-3.0-pro | gemini-3.0-flash | gemini-3.0-flash | Google Gemini CLI |
| **copilot** | `copilot` | gpt-5.2 | gpt-5.2-mini | gpt-5.2-mini | Microsoft Copilot CLI |
| **opencode** | `opencode` | kimi/kimi-k2.5 | kimi/kimi-k2.5 | kimi/kimi-k2.5 | OpenCode Framework |

### 使用方法

**デフォルト（Claude）で起動:**
```bash
yadon start [作業ディレクトリ]
```

**Gemini バックエンドで起動:**
```bash
LLM_BACKEND=gemini yadon start [作業ディレクトリ]
```

**Copilot バックエンドで起動:**
```bash
LLM_BACKEND=copilot yadon start [作業ディレクトリ]
```

**OpenCode バックエンドで起動:**
```bash
LLM_BACKEND=opencode yadon start [作業ディレクトリ]
```

### モデル階層の割り当て

各バックエンドは以下の3つのモデル階層を定義：

**coordinator（ヤドキング）**
- 戦略統括、最終レビュー、人間とのインターフェース
- 最も高性能なモデルを使用（例: Claude opus、Gemini Pro、Copilot gpt-5.2）

**manager（ヤドラン）**
- タスクを3フェーズに分解、ヤドンへの並列配分、結果集約
- バランスの取れたモデルを使用（例: Claude sonnet、Gemini Flash、Copilot gpt-5.2-mini）

**worker（ヤドン）**
- 実作業（コーディング、テスト、ドキュメント、レビュー等）
- 軽量・高速なモデルを使用（例: Claude haiku、Gemini Flash、Copilot gpt-5.2-mini）

### config/llm.py の設計方針

`config/llm.py` は LLMバックエンド設定を一元管理するモジュール。

**主要コンポーネント:**

1. **LLMModelConfig**
   - `coordinator`, `manager`, `worker` の3つのモデル名を格納
   - frozen dataclass で不変性を保証

2. **LLMBackendConfig**
   - バックエンド名、実行コマンド、モデル設定、追加フラグを格納
   - `batch_subcommand` でバッチ実行時のサブコマンドを指定可能（例: "run -q"）

3. **BACKEND_CONFIGS**
   - 対応バックエンド全ての設定を辞書で管理
   - キーは小文字バックエンド名（"claude", "gemini", "copilot", "opencode"）

4. **グローバル関数**
   - `get_backend_name()` — 環境変数 `LLM_BACKEND` からバックエンド名を取得（デフォルト: "claude"）
   - `get_backend_config()` — 現在のバックエンド設定オブジェクトを取得
   - `get_model_for_tier(tier)` — 指定 tier ("coordinator"/"manager"/"worker") に対応するモデル名を取得

### claude_runner.py の実装

`infra/claude_runner.py` は `LLMRunnerPort` の実装で、複数LLMバックエンドをサポート：

**主要メソッド:**

1. **run() — バッチモード実行**
   - プロンプト実行（`LLM_BACKEND` 反映）
   - バッチモードで `-p` フラグを自動追加（Claude/Gemini/Copilot）
   - `batch_subcommand` に基づくサブコマンド追加対応
   - タイムアウト・エラーハンドリング完備

2. **build_interactive_command() — 対話モードコマンド構築**
   - `LLM_BACKEND` 環境変数に基づいて動的に対話モードコマンドを構築
   - `--model` に対応 tier のモデル名を自動設定
   - `--system` フラグによるシステムプロンプト指定対応
   - バックエンド固有フラグ（`--dangerously-skip-permissions` 等）を自動追加

**コマンド構築例:**
- Claude (デフォルト): `claude --model opus`
- Gemini: `gemini --model gemini-2.5-pro`
- Copilot: `copilot --model gpt-4o`

### 後方互換性（domain/ports/claude_port.py）

`domain/ports/claude_port.py` は後方互換エイリアスモジュール：
```python
ClaudeRunnerPort = LLMRunnerPort
```

既存コードが `ClaudeRunnerPort` を参照している場合も、新しい `LLMRunnerPort` に統一名前付けされた。

### 実装例

**環境変数の確認:**
```python
from yadon_agents.config.llm import get_backend_name, get_backend_config, get_model_for_tier

# 現在のバックエンド名を取得
backend_name = get_backend_name()  # "claude" / "gemini" / "copilot" / "opencode"

# バックエンド設定を取得
config = get_backend_config()
print(config.command)  # "claude" / "gemini" / "copilot" / "opencode"

# 指定 tier のモデル名を取得
model = get_model_for_tier("coordinator")  # "opus" / "gemini-3.0-pro" / "gpt-5.2" / "kimi/kimi-k2.5"
```

**対話モード起動（LLM_BACKEND 反映）:**
```bash
# デフォルト（Claude opus）
yadon start

# Gemini Pro で起動（cli.py で自動的に build_interactive_command() が LLM_BACKEND を読み取り）
LLM_BACKEND=gemini yadon start

# Copilot で起動
LLM_BACKEND=copilot yadon start

# OpenCode で起動
LLM_BACKEND=opencode yadon start
```

**ワーカーごとのバックエンド設定:**

`YADON_1_BACKEND`, `YADON_2_BACKEND`, ... `YADON_N_BACKEND` 環境変数を使用して、各ワーカー（ヤドン1〜N）のバックエンドを個別に指定可能。未指定時はグローバル `LLM_BACKEND` 環境変数の値、さらに未設定時はデフォルト（claude）にフォールバック。

```bash
# ヤドン1はCopilot、ヤドン2はGemini、その他はデフォルト（Claude）で起動
YADON_1_BACKEND=copilot YADON_2_BACKEND=gemini yadon start

# ヤドン1〜4全てGeminiで起動
LLM_BACKEND=gemini yadon start

# ヤドン1はCopilot、ヤドン2は Copilot、ヤドン3はGeminiで起動
YADON_1_BACKEND=copilot YADON_2_BACKEND=copilot YADON_3_BACKEND=gemini yadon start
```

**バックエンド優先順位:**
1. `YADON_N_BACKEND` 環境変数（ワーカー個別指定、最優先）
2. `LLM_BACKEND` 環境変数（グローバル指定）
3. デフォルト値：`claude`（両方未設定時）

**ヤドンの実行（バッチモード）:**
```bash
# worker tier で Gemini バックエンドを使用
LLM_BACKEND=gemini AGENT_ROLE=yadon yadon start
```

### 設計上の注意点

- **不正なバックエンド指定** — `LLM_BACKEND` が無効な値の場合は自動的に "claude" にフォールバック
- **Port & Adapter** — エージェント層は `LLMRunnerPort` に依存し、具体的なLLM実装には依存しない
- **テスト** — モックを `LLMRunnerPort` に注入することで、各バックエンドをシミュレート可能
- **コマンド形式の統一** — 全バックエンド共通インターフェース（`--model`, `--system` フラグ等）で統一
- **拡張性** — 新バックエンドの追加は `BACKEND_CONFIGS` に新しい設定を追加するだけで実現可能
- **対話モード対応** — `cli.py:137` で `build_interactive_command()` が動的にバックエンドに応じたコマンドを構築。環境変数 `LLM_BACKEND` がそのまま反映される

### マルチLLMモード

複数のLLMバックエンドを同時に活用する「マルチLLMモード」では、各ワーカーに異なるバックエンド・モデルを割り当てて並列実行することで、モデルの特性を組み合わせた最適化が可能です。

**起動方法:**

`--multi-llm` フラグで有効化：
```bash
# uv run を使用
uv run yadon start --multi-llm [作業ディレクトリ]

# または uvx で直接起動
uvx --from git+https://github.com/ida29/yadon-agents yadon start --multi-llm [作業ディレクトリ]
```

**デフォルト割り当て:**

`--multi-llm` フラグ使用時、各ワーカーには以下の優先度でバックエンドが割り当てられます：

| ワーカー | バックエンド | Tier | モデル | 用途 |
|---------|-----------|------|--------|------|
| ヤドン1 | Copilot | worker | gpt-5.2-mini | 高速応答・軽量処理 |
| ヤドン2 | Gemini | worker | gemini-3.0-flash | 多言語対応・拡張性 |
| ヤドン3 | Claude | worker | opus | 安定性・一貫性 |
| ヤドン4 | OpenCode | worker | kimi/kimi-k2.5 | 専門領域最適化 |
| ヤドン5以上 | ローテーション | worker | (上記4つの繰り返し) | バランス分散 |

**具体的な使用例:**

```bash
# 4ワーカーでマルチLLMモード起動（ヤドン1: Copilot、ヤドン2: Gemini、ヤドン3: Claude、ヤドン4: OpenCode）
yadon start --multi-llm

# ワーカー数6で起動（ヤドン5: Copilot ← ローテーション、ヤドン6: Gemini ← ローテーション）
YADON_COUNT=6 yadon start --multi-llm

# ワーカー数8で起動（完全ローテーション）
YADON_COUNT=8 yadon start --multi-llm /path/to/project
```

**実装詳細:**

マルチLLMモード有効時の環境変数設定フロー（`cli.py` で自動実行）：
1. `--multi-llm` フラグを検知
2. 各ワーカー番号 N に対して `YADON_N_BACKEND` 環境変数を自動設定：
   - `N % 4 == 1` → `copilot`
   - `N % 4 == 2` → `gemini`
   - `N % 4 == 3` → `claude`
   - `N % 4 == 0` → `opencode`
3. 明示的な `YADON_N_BACKEND` 指定がある場合は、その値を優先（オーバーライド）
4. GUI デーモン起動時に各ワーカーに対応するバックエンドが反映される

**優先度順序（バックエンド選択のルール）:**

各ワーカーのバックエンド選択は、以下の優先度で決定されます：

```
1. YADON_N_BACKEND 環境変数（ワーカー個別指定）【最優先】
   └─ 明示的に指定された場合、この値が必ず採用される
2. --multi-llm フラグによる自動割り当て（モードで自動設定）
   └─ ワーカー番号の mod 4 によるローテーション（N % 4 で決定）
3. グローバル LLM_BACKEND 環境変数（全体的な指定）
   └─ --multi-llm フラグが未指定時に全ワーカーに適用
4. デフォルト値：claude（未指定時）
   └─ 上記すべて未設定時のフォールバック
```

**重要**: `YADON_N_BACKEND` が明示的に指定されている場合、`--multi-llm` による自動割り当てを **オーバーライド** します。

**複合運用例:**

```bash
# ヤドン1だけは Copilot を強制、他は通常単一バックエンド（Claude）で起動
YADON_1_BACKEND=copilot yadon start
# => Y1: Copilot, Y2-N: Claude（デフォルト）

# ヤドン1を Gemini で強制し、その他はマルチLLMモードのローテーション【最優先かつマルチモード併用】
YADON_1_BACKEND=gemini yadon start --multi-llm
# => Y1: Gemini (explicit), Y2: Gemini (multi-llm), Y3: Claude (multi-llm), Y4: OpenCode (multi-llm)
# 注: Y1 は YADON_1_BACKEND=gemini が優先されるため Copilot にはならない（mod 4 = 1 では Copilot）

# ワーカー1と3を固定し、その他はマルチLLMモード
YADON_1_BACKEND=copilot YADON_3_BACKEND=claude yadon start --multi-llm
# => Y1: Copilot (explicit), Y2: Gemini (multi-llm), Y3: Claude (explicit), Y4: OpenCode (multi-llm)

# グローバル Gemini で統一し、ヤドン2-3 のみ Copilot への明示的オーバーライド
LLM_BACKEND=gemini YADON_2_BACKEND=copilot YADON_3_BACKEND=copilot yadon start
# => Y1-N: Gemini, ただし Y2,Y3: Copilot (explicit override)

# グローバル Claude で統一（--multi-llm フラグなし）
LLM_BACKEND=claude yadon start
# => Y1-N: Claude（全体統一）

# マルチLLMモード使用、ただしグローバルフォールバックを Copilot に設定
LLM_BACKEND=copilot yadon start --multi-llm
# => Y1: Copilot (multi-llm), Y2: Gemini (multi-llm), Y3: Claude (multi-llm), Y4: OpenCode (multi-llm)
# ワーカー5以上はローテーション継続、グローバルフォールバックは使用されない
```

**パフォーマンス考慮:**

- 各ワーカーが異なるバックエンドを使用するため、**初回起動時** は複数のLLMサービスへの接続確認が行われ、通常より起動時間が増加
- **並列実行時** には各モデルの特性を活かした分散処理が可能（例: Copilot の高速処理 + Claude の安定性）
- 5ワーカー以上の場合、ローテーション方式により 4 種バックエンドを循環利用することで、リソース使用の均衡を取得

**無効化:**

`--multi-llm` フラグなしで通常起動した場合、単一 `LLM_BACKEND` 環境変数で全ワーカーを制御（従来の動作）：
```bash
# グローバル Gemini バックエンド（全ワーカー共通）
LLM_BACKEND=gemini yadon start
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
