# scripts ディレクトリ

ヤドン・エージェント システムの補助スクリプト集

## スクリプト一覧

### get_pane.sh
エージェント名からペインIDを取得するヘルパースクリプト。panes設定ファイルを自動探索する。

**使用方法:**
```bash
./scripts/get_pane.sh <エージェント名>
```

**例:**
```bash
YADORAN_PANE=$(./scripts/get_pane.sh yadoran)
YADON1_PANE=$(./scripts/get_pane.sh yadon1)
```

### notify.sh
メッセージをtmuxペインに送信し、確認を取るスクリプト。

**使用方法:**
```bash
./scripts/notify.sh <ペインID> "メッセージ"
```

**機能:**
- 引数チェック・ペイン存在チェック
- メッセージ送信前に入力欄をクリア（Ctrl+U）
- メッセージを送信
- 入力欄に残っていないか確認
- 残っていたら最大2回までEnterを再送信

**例:**
```bash
YADORAN_PANE=$(./scripts/get_pane.sh yadoran)
./scripts/notify.sh "$YADORAN_PANE" "【ヤドン2から報告】タスク完了しました。"
```

### auto_runner.sh
dashboard.mdを定期的にチェックして、新しいタスクを自動検出するスクリプト。

**使用方法:**
```bash
./scripts/auto_runner.sh
```

**機能:**
- 10秒ごとにdashboard.mdをチェック
- 新しいタスクを検出したらヤドランに通知
- ペイン設定ファイルを自動探索（panes-*.yaml 優先）
- ペイン存在チェック付き

### monitor_tokens.sh
トークン使用量を監視するスクリプト（単発実行）。

**使用方法:**
```bash
./scripts/monitor_tokens.sh
```

### token_monitor.sh
トークン監視の常駐版スクリプト（30秒間隔ループ）。

**使用方法:**
```bash
./scripts/token_monitor.sh
```

### start_verification.sh
auto_runner.sh と token_monitor.sh をバックグラウンドで起動する継続検証スクリプト。
PIDベースのロックファイルで重複起動を防止。

**使用方法:**
```bash
./scripts/start_verification.sh
```

## 注意事項

- すべてのスクリプトは `SCRIPT_DIR` から相対パスで動作するため、任意の場所から実行可能です
- スクリプトには実行権限（755）が必要です
- tmux関連のスクリプトはtmuxセッションが起動している状態で使用してください
