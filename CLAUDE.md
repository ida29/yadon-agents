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
│   ヤドキング       │  claude --model opus
└──────┬───────────┘
       │ Unix socket: /tmp/yadon-agent-yadoran.sock
       ▼
┌──────────────────┐
│   ヤドラン        │  デスクトップペット + エージェント (PyQt6 + Python)
│                  │  タスク受信 → 3フェーズに分解 → ヤドンに配分
└──┬───┬───┬───┬──┘
   │   │   │   │
   ▼   ▼   ▼   ▼
┌──┐ ┌──┐ ┌──┐ ┌──┐
│Y1│ │Y2│ │..│ │YN│  ヤドン 1-N（PyQt6 + Python、デフォルト4ワーカー）
└──┘ └──┘ └──┘ └──┘  タスク受信 → claude -p (haiku) で実行 → 結果返却
```

GUIデーモン（ヤドラン + ヤドン1-N）は別プロセスで起動され、CLIプロセス（ヤドキング）とは独立して動作。

## 役割対応表

| ポケモン | モデル | 動作モード | 役割 |
|----------|--------|-----------|------|
| ヤドキング | opus | 対話型 | 戦略統括、最終レビュー、ダイレクト対話 |
| ヤドラン | sonnet | バックグラウンド | 3フェーズ分解、並列配分、結果集約 |
| ヤドン×N | haiku | バックグラウンド | 実作業（コーディング、テスト、ドキュメント等） |

## パッケージ構成

```
yadon-agents/
├── pyproject.toml
├── src/yadon_agents/
│   ├── cli.py / commands.py / ascii_art.py / gui_daemon.py
│   ├── domain/           # ドメイン層（型・ポート）
│   ├── agent/            # アプリケーション層（BaseAgent, YadonWorker, YadoranManager）
│   ├── infra/            # インフラ層（protocol.py: Unix socket, claude_runner.py: LLM CLI実行）
│   ├── config/           # 設定（agent.py, ui.py, llm.py）
│   ├── gui/              # GUI層（PyQt6）
│   ├── themes/           # テーマ層（スプライト・メッセージ管理）
│   └── instructions/     # 指示書（yadoking.md, yadoran.md, yadon.md）
├── tests/                # pytest テストスイート（102テスト成功）
├── memory/               # ヤドキングの学習記録
├── logs/                 # ログファイル（自動生成）
└── .claude/              # 設定＆フック
    ├── settings.json     # PreToolUseフック設定
    └── hooks/enforce-role.sh  # 役割別ツール制御
```

## 設計方針

Python設計に関する判断：

- **Port & Adapter（DI）** — 依存注入パターン、ポート定義
- **BaseAgent + on_bubble callback** — リソース管理、try-finally戦略
- **uv依存管理** — `pyproject.toml` で一元管理
- **通信プロトコル** — Unixドメインソケット経由JSON（詳細は [.claude/rules/protocol.md](./.claude/rules/protocol.md) 参照）
- **セキュリティ** — 詳細は [.claude/rules/security.md](./.claude/rules/security.md) 参照

詳細は [.claude/rules/python.md](./.claude/rules/python.md) を参照してください。

## テスト

**実行結果（2026年2月4日）:**
- テスト総数: **102**
- 成功: **102 (100%)**
- 失敗: **0 (0%)**

```bash
python -m pytest tests/ -v
# 102 passed in 0.08s
```

**カバレッジ:** Socket communication、Agent orchestration、Task decomposition、Worker execution、Domain types

詳細は [.claude/rules/testing.md](./.claude/rules/testing.md) 参照。

## 起動方法

### uvx で起動（推奨）

```bash
# 通常起動（Claude）
uvx --from git+https://github.com/ida29/yadon-agents yadon start

# マルチLLMモード有効
uvx --from git+https://github.com/ida29/yadon-agents yadon start --multi-llm

# ワーカー数指定
YADON_COUNT=6 uvx --from git+https://github.com/ida29/yadon-agents yadon start --multi-llm

# 停止・ステータス確認・再起動
yadon stop
yadon status
yadon restart --multi-llm
```

### 永続インストール

```bash
# グローバルインストール
uv tool install git+https://github.com/ida29/yadon-agents

# その後
yadon start --multi-llm
yadon stop
yadon status
```

### 開発時の起動

```bash
git clone https://github.com/ida29/yadon-agents
cd yadon-agents

uv run yadon start --multi-llm
uv run yadon stop
uv run yadon status
```

## CLIコマンド

### yadon start

ヤドン・エージェント全体を起動します。

```bash
# 基本的な起動
yadon start

# マルチLLMモード有効
yadon start --multi-llm

# 作業ディレクトリ指定
yadon start /path/to/project

# ワーカー数指定（デフォルト4、範囲1-8）
YADON_COUNT=6 yadon start --multi-llm

# バックエンド指定（claude/gemini/copilot/opencode）
LLM_BACKEND=gemini yadon start
```

### yadon stop

ヤドン・エージェント全体を停止します。

```bash
yadon stop
```

### yadon status

エージェントのステータスを照会します（タイムアウト: 5秒）。

```bash
yadon status                    # 全エージェント
yadon status yadoran           # 特定エージェント
yadon status yadon-1
```

### yadon restart

エージェント全体を停止して再起動します。

```bash
yadon restart
yadon restart --multi-llm /path/to/project
```

### yadon say

ペットに吹き出しメッセージを送信します。

```bash
yadon say 1 "やるきスイッチ！"
yadon say 2 "頑張ります" --type normal --duration 3000
```

### 内部用CLIコマンド

```bash
yadon _send "タスク内容" /path/to/project    # タスク送信
yadon _status [agent]                        # ステータス照会（詳細版）
yadon _restart --multi-llm                   # 再起動（内部用）
yadon _say 1 "メッセージ" normal 3000        # メッセージ送信（内部用）
```

## LLMバックエンド設定

複数のLLMバックエンド（Claude、Gemini、Copilot、OpenCode）をサポート。

**対応バックエンド:**

| バックエンド | Coordinator | Manager | Worker |
|---|---|---|---|
| **claude** (デフォルト) | opus | sonnet | haiku |
| **gemini** | gemini-3.0-pro | gemini-3.0-flash | gemini-3.0-flash |
| **copilot** | gpt-5.2 | gpt-5.2-mini | gpt-5.2-mini |
| **opencode** | kimi/kimi-k2.5 | kimi/kimi-k2.5 | kimi/kimi-k2.5 |

**使用例:**

```bash
# デフォルト（Claude）
yadon start

# Gemini で起動
LLM_BACKEND=gemini yadon start

# マルチLLMモード（各ワーカーに異なるバックエンドを自動割り当て）
yadon start --multi-llm
# Y1: Copilot, Y2: Gemini, Y3: Claude, Y4: OpenCode（mod 4 ローテーション）

# ワーカー個別指定
YADON_1_BACKEND=copilot YADON_2_BACKEND=gemini yadon start
```

**マルチLLMモード:**

`--multi-llm` フラグで有効化。各ワーカーに異なるバックエンドを自動割り当て。
優先度: `YADON_N_BACKEND` 環境変数 > `--multi-llm` 自動割り当て > グローバル `LLM_BACKEND` > デフォルト。

詳細は [`.claude/skills/llm-backend/SKILL.md`](./.claude/skills/llm-backend/SKILL.md) 参照。

## 役割制御（PreToolUseフック）

`AGENT_ROLE` 環境変数と `.claude/hooks/enforce-role.sh` により、役割に応じたツール実行制限を技術的に強制します。

| エージェント | AGENT_ROLE | Edit/Write | Bash (git書込) | Bash (読取) |
|---|---|---|---|---|
| ヤドキング | `yadoking` | 禁止 | 禁止 | 許可 |
| ヤドラン | `yadoran` | 禁止 | 禁止 | 許可 |
| ヤドン1-N | `yadon` | 許可 | 許可 | 許可 |

`AGENT_ROLE` 未設定時は全て許可（通常のClaude Code使用）。jq未インストール時はフェイルオープン。
