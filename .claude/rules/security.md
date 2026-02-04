---
title: Security Considerations
description: セキュリティ考慮事項・既知の制限事項・運用上の注意点
paths:
  - src/**/*.py
  - .claude/hooks/**/*.sh
---

# セキュリティ考慮事項

## セキュリティ考慮

### Unixソケット通信のセキュリティ

- **パスワード・トークン転送禁止**: `/tmp` に配置されるUnixドメインソケットは、システム上の他のユーザーがアクセス可能。機密情報（API キー、認証トークン等）をタスク指示に含めないこと
- **ソケットパスの予測可能性**: エージェント名から自動生成されるため、悪意あるプロセスが事前にパスを知ることが可能。**本番環境でのデプロイ時は `/tmp` 以外の秘密ディレクトリ（`/var/run/user/$UID/`等）への移動を検討**
- **バッファーオーバーフロー対策**: `SOCKET_RECV_BUFFER` (4096 bytes)に制限。巨大なメッセージは分割受信され、`json.JSONDecodeError` として適切に処理される
- **タイムアウト設定**: `SOCKET_ACCEPT_TIMEOUT=1秒`、`SOCKET_CONNECTION_TIMEOUT=30秒`、`SOCKET_SEND_TIMEOUT=60秒` で無限ハング防止

### JSON パース & エラーハンドリング

- **JSONパース失敗時の吹き出し表示**: `summarize_for_bubble()` が例外を飲み込むため、エラーメッセージがUIに漏れない。ただし stderr ログには詳細が記録される（開発用）
- **地の文混在対応**: `_extract_json()` の3段階フォールバックにより、Claude の出力が `"こういった JSON が出力されます: {...}"` 形式でも抽出可能。ただし最初の `{` から最後の `}` までを抽出するため、複数の JSON オブジェクトが混在する場合は結合される（稀なケース）
- **エラーレスポンスの汎化**: `handle_connection()` でキャッチされた例外のメッセージが`proto.send_response()` でそのまま返却される。内部詳細（スタックトレース等）は stderr ログに記録され、クライアント側には一般的なエラーメッセージのみ返す

### リソース管理とリーク防止

- **ソケットファイル削除の確実性**: `BaseAgent.serve_forever()` の finally ブロックで `proto.cleanup_socket()` を実行。どの経路での終了でも確実にファイルディスクリプタとソケットファイルが削除される
- **スレッドセーフティ**: コネクション処理で `thread.join()` を呼び出しブロッキング待機するため、`handle_task()` 中のリソース（ファイルハンドル、ネットワーク接続等）が確実に完了してから次の接続を受け入れる
- **ゾンビプロセス防止**: ワーカーエージェントの `claude -p` subprocess 実行で `TimeoutError` 発生時も、`finally` ブロックでプロセスを明示的に terminate/kill する（`claude_runner.py` の実装参照）

## 運用性・保守性

### マルチLLMバックエンド切り替えの複雑性

- **環境変数の優先順位**: `YADON_N_BACKEND` > `--multi-llm フラグ` > `LLM_BACKEND` > デフォルト(claude)。複数の設定方式が混在すると意図しない挙動が発生する可能性。起動前に `echo $LLM_BACKEND $YADON_1_BACKEND ...` で確認することを推奨
- **バックエンド固有フラグの非互換性**: Copilot の `--dangerously-skip-permissions`、Gemini の CLI 引数形式など、バックエンド間で共通インターフェースが完全には統一されていない。新しいバックエンドを追加する場合は `config/llm.py` と `infra/claude_runner.py` の両方を更新が必要
- **初回接続遅延**: マルチLLMモードで複数のバックエンド CLI を同時に初期化する場合、接続確認に数秒〜数十秒の遅延が発生する可能性

### テストとモック

- **FakeClaudeRunner の独立定義**: 各テストで `ClaudeRunnerPort` モックを独立に定義しているため、テスト間で設定が共有されない。つまり一つのテストで `FakeClaudeRunner.return_value` を変更しても、別のテストには影響しない（良好）。ただし新しいテストを追加する際は、既存テストのモック定義パターンに従うこと
- **theme キャッシュのリセット**: `setup_method` で `PIXEL_DATA_CACHE.clear()` を呼び出し、テストメソッド実行前にテーマキャッシュをリセット。並列テスト実行時の予測不可能な競合を防止

## パフォーマンス・スケーラビリティ

### 並列実行の制限

- **ThreadPoolExecutor の max_workers**: ワーカー数 (1〜8) に制限されるため、それ以上のパラレリズムは期待できない。CPU バウンドな処理（Remotion 動画生成等）には向かない。I/O バウンド（LLM API 待機等）がメイン
- **3フェーズの逐次実行**: implement 完了後に docs、docs 完了後に review という順序が固定。全フェーズを完全に並列化することはできない（仕様）

### ログディレクトリ肥大化

- `log_dir()` は `~/.yadon-agents/logs/` を作成するが、ログローテーション機能がない。長期運用時に stderr ログが肥大化する可能性
- **推奨**: `logrotate` または別途ログ圧縮スクリプトを定期実行

## 既知の制限事項

### GUI デーモンの フォーカス奪取

- PyQt6 QApplication はX11/Wayland/Cocoa の実装に依存。特に Linux 環境でフォーカス管理が不安定な場合がある
- **回避策**: `setQuitOnLastWindowClosed(False)` を設定し、ウィジェットクローズ時の自動終了を防止。ただし手動での `app.quit()` 呼び出しが必要な場合、タイミングによっては ペット UI が残る可能性

### ソケットパスの長さ制限

- Unix ドメインソケットパスは 108 文字（Linux）または 104 文字（BSD）が上限。デフォルトパス `/tmp/yadon-agent-yadon-N.sock` は安全だが、`SOCKET_DIR` をカスタマイズして深いディレクトリを指定した場合はエラーが発生する可能性
- **チェック方法**: `len("/tmp/yadon-agent-yadon-8.sock") == 28` で確認

### JSON フェンス内の複数オブジェクト

- `_extract_json()` で複数の JSON フェンスが存在する場合、最初のフェンスのみ抽出される
- Claude の出力形式が不安定な場合、`logger.warning()` で出力の先頭 500 文字がログされるため、ログから原因の特定が可能
