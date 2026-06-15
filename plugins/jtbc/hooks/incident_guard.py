#!/usr/bin/env python3
"""
incident_guard.py — JTBC PreToolUse hook

緊急対応モード中(state.json#active_incidents が非空)に
前進系ガバナンス文書への編集をブロックする。

インシデント解決(/jtbc:incident close)前は
新規工程の計画・要件・設計文書の更新を禁止し、
復旧作業(src/tests等)やインシデント記録は許可する。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# インシデント中にブロックする「前進系ガバナンス文書」のパターン
BLOCKED_IN_INCIDENT = re.compile(
    r"^\.jtbc/(proposal|requirements|designs|plans|wbs)/"
)


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not file_path:
        return 0

    cwd = Path(payload.get("cwd", "."))
    state_path = cwd / ".jtbc" / "state.json"
    if not state_path.exists():
        return 0

    try:
        state = json.loads(state_path.read_text())
    except json.JSONDecodeError:
        return 0

    active_incidents = state.get("active_incidents")
    if not active_incidents:
        return 0

    # 相対パスに正規化
    relative = (
        str(Path(file_path).resolve().relative_to(cwd.resolve()))
        if Path(file_path).is_absolute()
        else file_path
    )

    if BLOCKED_IN_INCIDENT.search(relative):
        print(
            f"[incident_guard] BLOCKED: 緊急対応中(INC対応中)につき、"
            f"新規工程のガバナンス文書編集は停止しています。"
            f"インシデント解決(/jtbc:incident close)後に再開してください。"
            f"対応中: {active_incidents}",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
