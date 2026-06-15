#!/usr/bin/env python3
"""
phase_guard.py — JTBC PreToolUse hook

現フェーズで触ってはいけないパスへの Edit/Write/MultiEdit を阻止する。

ルール:
- phase が実装系 (IMPLEMENTATION / UNIT_TEST / INTEGRATION_TEST) でない限り、
  src/ / lib/ / app/ / pkg/ / internal/ への書込みは原則ブロック。
- 設計成果物 (.jtbc/designs/03_*, 04_*, .jtbc/wbs/) は対応フェーズ外では原則編集しない
  (役職判定は role_guard.py が担当。本フックは「工程到達」の観点でガードする)。

入力: stdin に Claude Code が JSON で {"tool_name":..., "tool_input":{...}, "cwd":...}
出力: 続行なら exit 0、ブロックなら stderr にメッセージ + exit 2
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SRC_PATTERNS = [r"^src/", r"^lib/", r"^app/", r"^pkg/", r"^internal/"]

# ソースコードへの書込みを許可するフェーズ
SRC_WRITABLE_PHASES = {"IMPLEMENTATION", "UNIT_TEST", "INTEGRATION_TEST"}


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

    phase = state.get("phase")

    relative = str(Path(file_path).resolve().relative_to(cwd.resolve())) if Path(file_path).is_absolute() else file_path

    is_code_path = any(re.search(p, relative) for p in SRC_PATTERNS)
    if is_code_path and phase not in SRC_WRITABLE_PHASES:
        print(
            f"[phase_guard] BLOCKED: 現フェーズ '{phase}' では '{relative}' への書込みは禁止です。\n"
            f"ソースコードを編集できるのは 実装 / 単体テスト / 総合テスト フェーズのみです。\n"
            f"実装フェーズに入るには /jtbc:gate detailed_design を通過してください。",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
