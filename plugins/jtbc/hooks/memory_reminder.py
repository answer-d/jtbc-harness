#!/usr/bin/env python3
"""
memory_reminder.py — JTBC SubagentStop hook (通知のみ)

知識生産系の役職サブエージェントが応答を終えたとき、その役職が
自分のメモ(.jtbc/memory/<role>/)を一度も書いていなければ、
「要所では memory に記録を」と軽く促す。

設計思想:
- これは **ソフトな後押し**。記録の本来の駆動は
  (1) 各 agent 定義の「起動時に memory を読む / 要所で確認なく書く」指示
  (2) role_guard の memory carve-out(自分のメモは確認なしで書ける)
  であり、本フックはあくまで「書き忘れ」への気づきを与えるだけ。
- 常に exit 0(SubagentStop をブロックしない)。書け、と強制はしない。
- ペイロードに役職や cwd が無い場合は静かに素通りする(壊さない)。

入力: stdin に Claude Code の SubagentStop ペイロード JSON
出力: 常に exit 0(該当時のみ stderr に通知)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# メモを残す価値が高い「知識生産」役職。実装のみの担当/SES や、
# 日常運営に口を出さない社長は除外(雑音を避ける)。
KNOWLEDGE_ROLES = {"jtbc-kacho", "jtbc-shunin", "jtbc-bucho", "jtbc-pmo"}


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    actor = (
        payload.get("agent_type")
        or payload.get("agent_name")
        or payload.get("subagent_name")
    )
    if not actor:
        return 0
    actor = str(actor).split(":")[-1].strip()
    if actor not in KNOWLEDGE_ROLES:
        return 0

    role_short = actor[len("jtbc-"):]
    cwd = Path(payload.get("cwd", "."))
    mem_dir = cwd / ".jtbc" / "memory" / role_short

    has_memory = mem_dir.exists() and any(
        p.is_file() and p.name != "INDEX.md" for p in mem_dir.glob("*.md")
    )
    if has_memory:
        return 0

    print(
        f"[memory_reminder] 役職 '{actor}' はまだ '.jtbc/memory/{role_short}/' に学びを記録していません。\n"
        f"次フェーズや次回の自分に残すべき決定・前提・つまずき等があれば、"
        f"確認を取らず随時 memory に記録してください(任意・通知のみ)。",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
