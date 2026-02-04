---
paths: ['tests/**/*.py', 'src/**/*.py']
---

# テスト規約

## テストの注意点

- **FakeClaudeRunner**: 各テストファイル（`test_manager.py`、`test_worker.py`、`test_claude_runner.py`）内で`ClaudeRunnerPort`モックを独立に定義。共有テストフィクスチャは使用せず、テスト独立性を確保
- **setup_method**: テストクラスの各テストメソッド実行前に`setup_method`で theme cache をリセット（`from yadon_agents.config.ui import PIXEL_DATA_CACHE; PIXEL_DATA_CACHE.clear()`）

## test_theme.py（34テスト）— テーマシステム

**テスト対象:** `domain/theme.py`、`themes/yadon/__init__.py`、`themes/yadon/sprites.py`、`config/agent.py`、`config/ui.py`、`infra/protocol.py`

**TestThemeConfig:**
- `test_frozen` — `ThemeConfig` が frozen dataclass で不変性を保証（属性変更で `AttributeError`）
- `test_default_values` — デフォルト値: ワーカー数 (1-8, デフォルト4)、空メッセージ、やるきスイッチ無効

**TestYadonTheme:**
- `test_build_theme_returns_config` — `build_theme()` が名前「yadon」のテーマ設定を返す
- `test_role_names` — 役割名（ヤドキング、ヤドラン、ヤドン）が正しく定義される
- `test_worker_messages` — 4ヤドンのワーカーメッセージ辞書（キー 1-4）が存在
- `test_worker_variants` — ヤドン1-4 の変形が正しく割り当てられる（normal/shiny/galarian/galarian_shiny）
- `test_phase_labels` — 3フェーズラベル（implement/docs/review）が存在
- `test_agent_roles` — エージェント役割識別子（yadoking/yadoran/yadon）が定義される
- `test_color_schemes` — ワーカー＆マネージャーのカラースキーム（normal/shiny/galarian等）が存在

**TestGetTheme:**
- `test_default_theme` — `get_theme()` のシングルトンが yadon テーマをデフォルト返却
- `test_cache_returns_same_instance` — キャッシュにより複数呼び出しで同一インスタンスを返す
- `test_invalid_theme_raises` — 存在しないテーマ指定時に `ModuleNotFoundError` を raise

**TestSpriteBuilders:**
- `test_worker_sprite_16x16` — ワーカースプライトが 16×16 ピクセル配列を生成
- `test_worker_sprite_galarian_accent` — ガラル版はアクセント色が通常版と異なる
- `test_manager_sprite_16x16` — マネージャースプライトが 16×16 ピクセル配列を生成
- `test_manager_sprite_contains_shellder` — マネージャースプライトにシェルダー色が含まれる

**TestBackwardCompat（後方互換性）:**
- `test_get_yadon_count_default` — `config/agent.py:get_yadon_count()` がデフォルト 4 を返す
- `test_get_yadon_messages` — `get_yadon_messages(N)` がメッセージリストを返す
- `test_get_yadon_messages_fallback` — ワーカー数超過時（例: 5番目）は1番目にフォールバック
- `test_get_yadon_variant` — `get_yadon_variant(N)` が正しい変形を返す
- `test_get_yadon_variant_fallback` — 範囲外は normal にフォールバック
- `test_module_getattr_random_messages` — `config.agent.RANDOM_MESSAGES` で __getattr__ 経由のアクセス可
- `test_module_getattr_phase_labels` — `config.agent.PHASE_LABELS` で フェーズラベルへのアクセス可
- `test_color_schemes_compat` — `config.ui.COLOR_SCHEMES` でカラースキーム参照可
- `test_yadoran_colors_compat` — `config.ui.YADORAN_COLORS` でマネージャー色参照可

**TestProtocolPrefix:**
- `test_agent_socket_path_default` — `agent_socket_path("yadon-1")` が `/tmp/yadon-agent-yadon-1.sock` を返す
- `test_agent_socket_path_custom_prefix` — prefix パラメータで `/tmp/custom-agent-...` に変更可
- `test_pet_socket_path_default` — `pet_socket_path("1")` が `/tmp/yadon-pet-1.sock` を返す
- `test_pet_socket_path_custom_prefix` — カスタム prefix で `/tmp/custom-pet-...` に変更可

## test_claude_runner.py（4テスト）— SubprocessClaudeRunner

**テスト対象:** `infra/claude_runner.py:SubprocessClaudeRunner`

**TestSubprocessClaudeRunner:**
- `test_run_success` — 正常実行時、stdout + stderr を結合して (output, returncode=0) を返す。`subprocess.run` に `capture_output=True, text=True, timeout, cwd` が正しく渡される
- `test_run_timeout` — `subprocess.TimeoutExpired` 発生時、タイムアウトメッセージ（「タイムアウト」「1分」）と returncode=1 を返す
- `test_run_exception` — その他の例外で「実行エラー」メッセージと returncode=1 を返す
- `test_run_with_output_format` — `output_format="json"` パラメータが `--output-format json` として CLI コマンドに正しく追加される

**カバレッジ:** subprocess の正常系・タイムアウト・例外フロー、パラメータ伝播、マルチLLMバックエンド実行時の汎用 LLM CLI インターフェース

## test_manager.py（9テスト）— YadoranManager

**テスト対象:** `agent/manager.py:YadoranManager`、`agent/manager.py:_aggregate_results`、`agent/manager.py:_extract_json`

**TestAggregateResults（結果集約）:**
- `test_aggregate_results_all_success` — 全ワーカー成功時、status=success、combined_summary に各ワーカーの成功メッセージ（「[yadon-1] success: 実装完了」）を記載、combined_output に各ワーカー出力をセクション区切りで結合
- `test_aggregate_results_partial_error` — 一部失敗時、status=partial_error、summary は全ワーカー結果を記載、output はワーカーごとのセクション記載
- `test_aggregate_results_empty` — 空リスト入力時も正常処理（status=success、summary/output 空文字）

**TestDecomposeTask（タスク分解）:**
- `test_decompose_task_success` — Claude 出力が JSON で 3 フェーズ（implement/docs/review）を解析。各フェーズの name と subtasks[0].instruction が正しく抽出される。LLM ランナーは FakeClaudeRunner でモック
- `test_decompose_task_json_parse_error_fallback` — JSON パース失敗時、フォールバック: implement フェーズのみ、元の instruction を 1 タスクに含める

**TestExtractJson（JSON 抽出）:**
- `test_extract_json_fenced` — JSONフェンス（```json...```）内の JSON を抽出
- `test_extract_json_plain` — フェンスなしのプレーン JSON を直接パース
- `test_extract_json_with_surrounding_text` — 地の文混在時（「JSON です: {...} です」形式）、最初の `{` から最後の `}` まで抽出して JSON デコード
- `test_extract_json_invalid_raises_error` — JSON パースに失敗したら `json.JSONDecodeError` を raise（呼び出し側で catch & フォールバック）

**カバレッジ:** タスク分解プロンプト実行、JSON 解析（フェンス、プレーン、地の文混在）、フォールバック動作、LLM ランナー依存性注入

## テスト実行結果

**実行日**: 2026年2月4日
**テスト総数**: 102
**成功**: 102 (100%)
**失敗**: 0 (0%)

```bash
python -m pytest tests/ -v
# ============================= test session starts ==============================
# 102 passed in 0.08s
```

## テスト構成（102テスト）

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
| **合計** | | **102** | ✅ **全成功** |

## テスト範囲

- **Agent Layer**: ソケット通信、メッセージハンドリング、タスク分解、結果集約、ワーカータスク実行
- **Config Layer**: LLMバックエンド設定、モデル階層、環境変数フォールバック
- **Domain Layer**: テキスト要約、メッセージ型、ThemeConfig、スプライトビルダー、後方互換性
- **Infra Layer**: Claude CLIランナー（subprocess実行、タイムアウト）、Unixソケット通信（作成・送受信・クリーンアップ）

## 失敗テストなし

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
