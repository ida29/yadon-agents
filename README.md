# yadon-agents

デスクトップにヤドンたちが住み着いて、コーディングを手伝ってくれるマルチエージェントシステム。

ヤドキング（opus）に話しかけると、ヤドラン（sonnet）がタスクを分解し、ヤドンたち（haiku）が並列で実作業を行う。PyQt6環境ではドット絵のデスクトップペットが表示され、作業状況を吹き出しで教えてくれる。

```
トレーナー（人間）
  │ 直接会話
  ▼
┌──────────────────┐
│   ヤドキング       │  claude --model opus（対話型）
└──────┬───────────┘
       │ Unix socket
       ▼
┌──────────────────┐
│   ヤドラン        │  claude -p (sonnet) でタスク分解 → ヤドンに配分
└──┬───┬───┬───┬──┘
   ▼   ▼   ▼   ▼
┌──┐ ┌──┐ ┌──┐ ┌──┐
│Y1│ │Y2│ │..│ │YN│  claude -p (haiku) で並列実行
└──┘ └──┘ └──┘ └──┘
```

| ポケモン | モデル | 役割 |
|----------|--------|------|
| ヤドキング | opus | 戦略統括、最終レビュー、人間との対話 |
| ヤドラン | sonnet | タスクを3フェーズに分解、ヤドンへの並列配分 |
| ヤドン×N | haiku | 実作業（コーディング、テスト、ドキュメント、レビュー） |

## セットアップ

### 1. Claude Code をインストール

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) の手順に従い、`claude` CLI をインストール・認証する。

```bash
claude  # 初回起動で認証
```

### 2. uv をインストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. リポジトリをクローン

```bash
git clone https://github.com/ida29/yadon-agents.git
cd yadon-agents
```

### 4. 依存関係をインストール

```bash
uv sync
```

PyQt6も自動的にインストールされ、デスクトップペットが使えるようになります。

### 5. グローバルコマンドとしてインストール（オプション）

システム全体で`yadon`コマンドを使いたい場合:

```bash
uv tool install git+https://github.com/ida29/yadon-agents
```

## クイックスタート

インストール不要で即座に起動:

```bash
# インストール不要で即起動
uvx --from git+https://github.com/ida29/yadon-agents yadon start --multi-llm
```

詳細は「起動」セクションを参照。

## 起動

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
```

### 開発時（リポジトリクローン後）

```bash
# リポジトリをクローン
git clone https://github.com/ida29/yadon-agents.git
cd yadon-agents

# 依存をインストール
uv sync

# uv run で起動
uv run yadon start --multi-llm

# ヤドン数を変更
YADON_COUNT=6 uv run yadon start --multi-llm
```

### グローバルインストール

頻繁に使う場合は uv tool install でグローバルインストール:

```bash
# 一度だけ実行
uv tool install git+https://github.com/ida29/yadon-agents

# 以降はどこからでも
yadon start --multi-llm
YADON_COUNT=6 yadon start --multi-llm
```

### 停止

```bash
# uvx/uv tool install 起動時
pkill -f yadon

# 開発時
pkill -f yadon
```

### コマンド一覧

起動中のヤドンたちに指示を出す:

```bash
# タスク送信（ブロッキング実行）
yadon send "READMEを更新してください"
yadon send "テストを追加してください" /path/to/project

# ステータス確認
yadon status

# 再起動
yadon restart --multi-llm

# ペットに吹き出しメッセージを送信
yadon say 1 "やるきスイッチ！"
yadon say 2 "頑張ります" --type normal --duration 3000
yadon say 3 "メッセージ"
```

ヤドキングのプロンプトが表示されたら、自然言語でタスクを依頼するだけ。ヤドキング終了時にデーモン+ペットも自動停止する。

## 仕組み

1. 人間がヤドキングに依頼（例: 「認証機能を追加して」）
2. ヤドキングがヤドランにタスクを送信
3. ヤドランがタスクを3フェーズに分解（implement → docs → review）
4. 各フェーズ内のサブタスクをヤドンたちが並列実行
5. 結果がヤドラン → ヤドキングへ返却され、人間に報告

## ライセンス

Private
