---
name: llm-backend
description: LLMバックエンド設定やマルチLLMモードの設定時に使用。Claude/Gemini/Copilot/OpenCodeの切り替えやワーカー個別設定時に参照。
disable-model-invocation: true
user-invocable: false
---

# LLMバックエンド切り替え

複数のLLMバックエンド（Claude、Gemini、Copilot、OpenCode）をサポートし、環境変数 `LLM_BACKEND` で実行時に切り替え可能。
エージェント階層（ヤドキング/ヤドラン/ヤドン）に応じたモデル階層（coordinator/manager/worker）の最適なモデルを自動選択。

## 概要

このスキルは、ヤドン・エージェントシステムにおけるLLMバックエンド管理の詳細情報を提供します。
以下の場面で参照してください：

- **新しいLLMバックエンドの追加** — `config/llm.py` と `infra/claude_runner.py` の修正が必要
- **既存バックエンドの変更** — モデル名・コマンド・フラグの更新
- **マルチLLMモードの設定** — ワーカーごとのバックエンド割り当てとローテーション
- **環境変数の優先度確認** — `YADON_N_BACKEND` > `--multi-llm` > `LLM_BACKEND` > デフォルト

## 対応バックエンド

| バックエンド | コマンド | Coordinator | Manager | Worker | 説明 |
|---|---|---|---|---|---|
| **claude** (デフォルト) | `claude` | opus | sonnet | haiku | Anthropic Claude CLI |
| **claude-opus** | `claude` | opus | opus | opus | Anthropic Claude CLI (All Opus) |
| **gemini** | `gemini` | gemini-3.0-pro | gemini-3.0-flash | gemini-3.0-flash | Google Gemini CLI |
| **copilot** | `copilot` | gpt-5.2 | gpt-5.2-mini | gpt-5.2-mini | Microsoft Copilot CLI |
| **opencode** | `opencode` | kimi/kimi-k2.5 | kimi/kimi-k2.5 | kimi/kimi-k2.5 | OpenCode Framework |

## 使用方法

### デフォルト（Claude）で起動

```bash
yadon start [作業ディレクトリ]
```

### Gemini バックエンドで起動

```bash
LLM_BACKEND=gemini yadon start [作業ディレクトリ]
```

### Copilot バックエンドで起動

```bash
LLM_BACKEND=copilot yadon start [作業ディレクトリ]
```

### OpenCode バックエンドで起動

```bash
LLM_BACKEND=opencode yadon start [作業ディレクトリ]
```

## モデル階層の割り当て

各バックエンドは以下の3つのモデル階層を定義：

### coordinator（ヤドキング）

- 戦略統括、最終レビュー、人間とのインターフェース
- 最も高性能なモデルを使用（例: Claude opus、Gemini Pro、Copilot gpt-5.2）

### manager（ヤドラン）

- タスクを3フェーズに分解、ヤドンへの並列配分、結果集約
- バランスの取れたモデルを使用（例: Claude sonnet、Gemini Flash、Copilot gpt-5.2-mini）

### worker（ヤドン）

- 実作業（コーディング、テスト、ドキュメント、レビュー等）
- 軽量・高速なモデルを使用（例: Claude haiku、Gemini Flash、Copilot gpt-5.2-mini）

## config/llm.py の設計方針

`config/llm.py` は LLMバックエンド設定を一元管理するモジュール。

### 主要コンポーネント

#### 1. LLMModelConfig

- `coordinator`, `manager`, `worker` の3つのモデル名を格納
- frozen dataclass で不変性を保証

#### 2. LLMBackendConfig

- バックエンド名、実行コマンド、モデル設定、追加フラグを格納
- `batch_subcommand` でバッチ実行時のサブコマンドを指定可能（例: "run -q"）

#### 3. BACKEND_CONFIGS

- 対応バックエンド全ての設定を辞書で管理
- キーは小文字バックエンド名（"claude", "gemini", "copilot", "opencode"）

#### 4. グローバル関数

- `get_backend_name()` — 環境変数 `LLM_BACKEND` からバックエンド名を取得（デフォルト: "claude"）
- `get_backend_config()` — 現在のバックエンド設定オブジェクトを取得
- `get_model_for_tier(tier)` — 指定 tier ("coordinator"/"manager"/"worker") に対応するモデル名を取得

## claude_runner.py の実装

`infra/claude_runner.py` は `LLMRunnerPort` の実装で、複数LLMバックエンドをサポート：

### run() — バッチモード実行

- プロンプト実行（`LLM_BACKEND` 反映）
- バッチモードで `-p` フラグを自動追加（Claude/Gemini/Copilot）
- `batch_subcommand` に基づくサブコマンド追加対応
- タイムアウト・エラーハンドリング完備

### build_interactive_command() — 対話モードコマンド構築

- `LLM_BACKEND` 環境変数に基づいて動的に対話モードコマンドを構築
- `--model` に対応 tier のモデル名を自動設定
- `--system` フラグによるシステムプロンプト指定対応
- バックエンド固有フラグ（`--dangerously-skip-permissions` 等）を自動追加

### コマンド構築例

- Claude (デフォルト): `claude --model opus`
- Gemini: `gemini --model gemini-2.5-pro`
- Copilot: `copilot --model gpt-4o`

## 後方互換性（domain/ports/claude_port.py）

`domain/ports/claude_port.py` は後方互換エイリアスモジュール：

```python
ClaudeRunnerPort = LLMRunnerPort
```

既存コードが `ClaudeRunnerPort` を参照している場合も、新しい `LLMRunnerPort` に統一名前付けされた。

## 実装例

### 環境変数の確認

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

### 対話モード起動（LLM_BACKEND 反映）

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

### ワーカーごとのバックエンド設定

`YADON_1_BACKEND`, `YADON_2_BACKEND`, ... `YADON_N_BACKEND` 環境変数を使用して、各ワーカー（ヤドン1〜N）のバックエンドを個別に指定可能。未指定時はグローバル `LLM_BACKEND` 環境変数の値、さらに未設定時はデフォルト（claude）にフォールバック。

```bash
# ヤドン1はCopilot、ヤドン2はGemini、その他はデフォルト（Claude）で起動
YADON_1_BACKEND=copilot YADON_2_BACKEND=gemini yadon start

# ヤドン1〜4全てGeminiで起動
LLM_BACKEND=gemini yadon start

# ヤドン1はCopilot、ヤドン2は Copilot、ヤドン3はGeminiで起動
YADON_1_BACKEND=copilot YADON_2_BACKEND=copilot YADON_3_BACKEND=gemini yadon start
```

### バックエンド優先順位

1. `YADON_N_BACKEND` 環境変数（ワーカー個別指定、最優先）
2. `LLM_BACKEND` 環境変数（グローバル指定）
3. デフォルト値：`claude`（両方未設定時）

### ヤドンの実行（バッチモード）

```bash
# worker tier で Gemini バックエンドを使用
LLM_BACKEND=gemini AGENT_ROLE=yadon yadon start
```

## 設計上の注意点

- **不正なバックエンド指定** — `LLM_BACKEND` が無効な値の場合は自動的に "claude" にフォールバック
- **Port & Adapter** — エージェント層は `LLMRunnerPort` に依存し、具体的なLLM実装には依存しない
- **テスト** — モックを `LLMRunnerPort` に注入することで、各バックエンドをシミュレート可能
- **コマンド形式の統一** — 全バックエンド共通インターフェース（`--model`, `--system` フラグ等）で統一
- **拡張性** — 新バックエンドの追加は `BACKEND_CONFIGS` に新しい設定を追加するだけで実現可能
- **対話モード対応** — `cli.py:137` で `build_interactive_command()` が動的にバックエンドに応じたコマンドを構築。環境変数 `LLM_BACKEND` がそのまま反映される

## マルチLLMモード

複数のLLMバックエンドを同時に活用する「マルチLLMモード」では、各ワーカーに異なるバックエンド・モデルを割り当てて並列実行することで、モデルの特性を組み合わせた最適化が可能です。

### 起動方法

`--multi-llm` フラグで有効化：

```bash
# uv run を使用
uv run yadon start --multi-llm [作業ディレクトリ]

# または uvx で直接起動
uvx --from git+https://github.com/ida29/yadon-agents yadon start --multi-llm [作業ディレクトリ]
```

### デフォルト割り当て

`--multi-llm` フラグ使用時、各ワーカーには以下の優先度でバックエンドが割り当てられます：

| ワーカー | バックエンド | Tier | モデル | 用途 |
|---------|-----------|------|--------|------|
| ヤドン1 | Copilot | worker | gpt-5.2-mini | 高速応答・軽量処理 |
| ヤドン2 | Gemini | worker | gemini-3.0-flash | 多言語対応・拡張性 |
| ヤドン3 | Claude | worker | opus | 安定性・一貫性 |
| ヤドン4 | OpenCode | worker | kimi/kimi-k2.5 | 専門領域最適化 |
| ヤドン5以上 | ローテーション | worker | (上記4つの繰り返し) | バランス分散 |

### 具体的な使用例

```bash
# 4ワーカーでマルチLLMモード起動（ヤドン1: Copilot、ヤドン2: Gemini、ヤドン3: Claude、ヤドン4: OpenCode）
yadon start --multi-llm

# ワーカー数6で起動（ヤドン5: Copilot ← ローテーション、ヤドン6: Gemini ← ローテーション）
YADON_COUNT=6 yadon start --multi-llm

# ワーカー数8で起動（完全ローテーション）
YADON_COUNT=8 yadon start --multi-llm /path/to/project
```

### 実装詳細

マルチLLMモード有効時の環境変数設定フロー（`cli.py` で自動実行）：

1. `--multi-llm` フラグを検知
2. 各ワーカー番号 N に対して `YADON_N_BACKEND` 環境変数を自動設定：
   - `N % 4 == 1` → `copilot`
   - `N % 4 == 2` → `gemini`
   - `N % 4 == 3` → `claude`
   - `N % 4 == 0` → `opencode`
3. 明示的な `YADON_N_BACKEND` 指定がある場合は、その値を優先（オーバーライド）
4. GUI デーモン起動時に各ワーカーに対応するバックエンドが反映される

### 優先度順序（バックエンド選択のルール）

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

### 複合運用例

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

### パフォーマンス考慮

- 各ワーカーが異なるバックエンドを使用するため、**初回起動時** は複数のLLMサービスへの接続確認が行われ、通常より起動時間が増加
- **並列実行時** には各モデルの特性を活かした分散処理が可能（例: Copilot の高速処理 + Claude の安定性）
- 5ワーカー以上の場合、ローテーション方式により 4 種バックエンドを循環利用することで、リソース使用の均衡を取得

### 無効化

`--multi-llm` フラグなしで通常起動した場合、単一 `LLM_BACKEND` 環境変数で全ワーカーを制御（従来の動作）：

```bash
# グローバル Gemini バックエンド（全ワーカー共通）
LLM_BACKEND=gemini yadon start
```
