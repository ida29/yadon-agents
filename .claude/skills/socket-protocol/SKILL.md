---
name: socket-protocol
description: ソケット通信のデバッグ・メッセージ形式変更時に使用。Unix socket通信の問題解決やプロトコル拡張時に参照。
---

# Unixドメインソケット通信プロトコル

全エージェント間通信はUnixドメインソケット経由。JSON over Unix socket で実装。
リクエスト送信後 `shutdown(SHUT_WR)` でEOFを通知し、レスポンスを読んで完了。

## ソケットパス

| 用途 | パス | 所有モジュール |
|---|---|---|
| ヤドラン | `/tmp/yadon-agent-yadoran.sock` | `yadon_agents.agent.manager` / `yadon_agents.gui.yadoran_pet` |
| ヤドン1 | `/tmp/yadon-agent-yadon-1.sock` | `yadon_agents.agent.worker` / `yadon_agents.gui.yadon_pet` |
| ヤドン2 | `/tmp/yadon-agent-yadon-2.sock` | 同上 (--number 2) |
| ヤドン3 | `/tmp/yadon-agent-yadon-3.sock` | 同上 (--number 3) |
| ヤドン4 | `/tmp/yadon-agent-yadon-4.sock` | 同上 (--number 4) |
| ヤドラン吹き出し | `/tmp/yadon-pet-yadoran.sock` | `yadon_agents.gui.yadoran_pet` |
| ヤドンN吹き出し | `/tmp/yadon-pet-N.sock` | `yadon_agents.gui.yadon_pet` |

## メッセージ形式

### タスク送信 (type: "task")

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

### タスク結果 (type: "result")

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

**ステータス値:**
- `status: "success"` — 全サブタスク成功
- `status: "partial_error"` — 一部失敗あり

### ステータス照会 (type: "status") / 応答 (type: "status_response")

**リクエスト:**
```json
{"type": "status", "from": "check_status"}
```

**レスポンス:**
```json
{
  "type": "status_response",
  "from": "yadoran",
  "state": "idle",
  "current_task": null,
  "workers": {"yadon-1": "idle", "yadon-2": "busy", ...}
}
```

## 通信フロー（3フェーズ実行）

1. 人間がヤドキングに依頼
2. ヤドキングがヤドランにソケットで送信（ブロック）
3. ヤドランがソケットで受信 → `claude -p --model sonnet` で3フェーズに分解
4. **Phase 1 (implement)**: 実装サブタスクをヤドン1〜Nに `ThreadPoolExecutor` で並列送信 → 完了待ち
5. **Phase 2 (docs)**: ドキュメント更新サブタスクをヤドンに並列送信 → 完了待ち
6. **Phase 3 (review)**: レビューサブタスクをヤドンに送信 → 完了待ち
7. 全フェーズの結果を集約してヤドキングへ返却

フェーズ間は逐次実行（implement → docs → review）。各フェーズ内のサブタスクは並列実行。

## 実装参照

**プロトコルレイヤー**: `infra/protocol.py`
- Unixソケット作成・送受信・クリーンアップ
- JSON over socket エンコード/デコード
- タイムアウト・エラーハンドリング

**エージェント**: `agent/base.py`（BaseAgent）
- ソケットサーバーループ
- コネクション管理
- リソースクリーンアップ（try-finally）

**メッセージ定義**: `domain/messages.py`
- TaskMessage, ResultMessage, StatusQuery, StatusResponse 型定義
