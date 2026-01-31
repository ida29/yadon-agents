# scripts ディレクトリ

ヤドン・エージェント システムの補助スクリプト集

## スクリプト一覧

### notify.sh
メッセージをtmuxペインに送信し、確認を取るスクリプト。

**使用方法:**
```bash
./scripts/notify.sh <ペインID> "メッセージ"
```

**機能:**
- メッセージ送信前に入力欄をクリア（Ctrl+U）
- メッセージを送信
- 入力欄に残っていないか確認
- 残っていたら最大2回までEnterを再送信

**例:**
```bash
YADORAN_PANE=$(grep yadoran config/panes.yaml | cut -d'"' -f2)
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
- 自動でバックグラウンド実行可能

**例:**
```bash
# バックグラウンドで実行
./scripts/auto_runner.sh &
```

### monitor_tokens.sh
トークン使用量を監視するスクリプト。

**使用方法:**
```bash
./scripts/monitor_tokens.sh
```

**機能:**
- 定期的にトークン使用状況を監視
- ログに記録

### token_monitor.sh
トークン監視の別版スクリプト。

**使用方法:**
```bash
./scripts/token_monitor.sh
```

### start_verification.sh
起動時の検証スクリプト。

**使用方法:**
```bash
./scripts/start_verification.sh
```

**機能:**
- システムの初期状態をチェック
- 必要なファイルやディレクトリが存在するか確認

## 注意事項

- すべてのスクリプトは `yadon-agent` ディレクトリから実行してください
- スクリプトには実行権限（755）が必要です
- tmux関連のスクリプトはtmuxセッションが起動している状態で使用してください
