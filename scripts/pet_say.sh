#!/bin/bash
# ヤドンペットに吹き出しメッセージを送信するヘルパー
#
# 使用法: pet_say.sh <yadon_number> <message> [bubble_type] [duration_ms]
#
# 引数:
#   yadon_number  - ヤドン番号 (1-4)
#   message       - 表示するテキスト
#   bubble_type   - normal | hook | claude (省略時: normal)
#   duration_ms   - 表示時間ミリ秒 (省略時: 4000)
#
# 例:
#   ./scripts/pet_say.sh 1 "できたやぁん"
#   ./scripts/pet_say.sh 2 "レビュー完了" hook
#   ./scripts/pet_say.sh 3 "テスト通った" claude 6000

YADON_NUM="$1"
MESSAGE="$2"
TYPE="${3:-normal}"
DURATION="${4:-4000}"

if [ -z "$YADON_NUM" ] || [ -z "$MESSAGE" ]; then
    echo "使用法: pet_say.sh <yadon_number> <message> [bubble_type] [duration_ms]" >&2
    exit 1
fi

SOCKET="/tmp/yadon-pet-${YADON_NUM}.sock"

# ペットが起動していなければ静かに終了
if [ ! -S "$SOCKET" ]; then
    exit 0
fi

# JSONエスケープ: ダブルクォートとバックスラッシュをエスケープ
ESCAPED_MESSAGE=$(printf '%s' "$MESSAGE" | sed 's/\\/\\\\/g; s/"/\\"/g')

# nc -U でUnixソケットに送信（macOS/Linux両対応）
printf '{"text":"%s","type":"%s","duration":%s}' "$ESCAPED_MESSAGE" "$TYPE" "$DURATION" | nc -U "$SOCKET" 2>/dev/null

exit 0
