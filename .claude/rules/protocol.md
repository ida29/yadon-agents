---
paths: ['src/**/*.py', 'tests/**/*.py']
---

# Unix ドメインソケット通信プロトコル

全エージェント間通信はUnixドメインソケット経由。JSON over Unix socket で実装。

## クイックリファレンス

| 用途 | パス | 所有モジュール |
|---|---|---|
| ヤドラン | `/tmp/yadon-agent-yadoran.sock` | `yadon_agents.agent.manager` |
| ヤドンN | `/tmp/yadon-agent-yadon-N.sock` | `yadon_agents.agent.worker` |

## メッセージ形式

### タスク送信 (type: "task")

```json
{
  "type": "task",
  "id": "task-20260201-120000-a1b2",
  "from": "yadoking",
  "payload": {
    "instruction": "READMEを更新してください",
    "project_dir": "/path/to/project"
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

## 通信フロー（3フェーズ実行）

1. ヤドキングがヤドランにソケットで送信（ブロック）
2. ヤドランがソケットで受信 → `claude -p --model sonnet` で3フェーズに分解
3. **Phase 1 (implement)**: 実装サブタスクをヤドン1〜Nに並列送信 → 完了待ち
4. **Phase 2 (docs)**: ドキュメント更新サブタスクをヤドンに並列送信 → 完了待ち
5. **Phase 3 (review)**: レビューサブタスクをヤドンに送信 → 完了待ち
6. 全フェーズの結果を集約してヤドキングへ返却

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

## 詳細ドキュメント

詳しくは [`.claude/skills/socket-protocol/SKILL.md`](./../skills/socket-protocol/SKILL.md) を参照。
