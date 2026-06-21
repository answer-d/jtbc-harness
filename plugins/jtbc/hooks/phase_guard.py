#!/usr/bin/env python3
"""
phase_guard.py — JTBC PreToolUse hook

現フェーズで触ってはいけないパスへの Edit/Write/MultiEdit を阻止する。

ルール:
- phase が実装系 (IMPLEMENTATION / UNIT_TEST / INTEGRATION_TEST) でない限り、
  src/ / lib/ / app/ / pkg/ / internal/ への書込みは原則ブロック。
- 設計成果物 (.jtbc/designs/basic_design.md, detailed_design.md, .jtbc/wbs/) は対応フェーズ外では原則編集しない
  (役職判定は role_guard.py が担当。本フックは「工程到達」の観点でガードする)。

入力: stdin に Claude Code が JSON で {"tool_name":..., "tool_input":{...}, "cwd":...}
出力: 続行なら exit 0、ブロックなら stderr にメッセージ + exit 2
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SRC_PATTERNS = [r"^src/", r"^lib/", r"^app/", r"^pkg/", r"^internal/"]

# ソースコードへの書込みを許可するフェーズ
SRC_WRITABLE_PHASES = {"IMPLEMENTATION", "UNIT_TEST", "INTEGRATION_TEST"}

_HOOK = "phase_guard"


def _debug_log(payload: dict, *, decision: str, role: str | None = None, reason: str = "") -> None:
    """JTBC_HOOK_DEBUG 設定時のみ、判定結果を .jtbc/hook_debug.log に1行記録する(調査用)。"""
    if not os.environ.get("JTBC_HOOK_DEBUG"):
        return
    try:
        cwd = Path(payload.get("cwd", "."))
        log = cwd / ".jtbc" / "hook_debug.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        tool_input = payload.get("tool_input") or {}
        with log.open("a") as f:
            f.write(json.dumps({
                "hook": _HOOK,
                "decision": decision,
                "role": role,
                "agent_type": payload.get("agent_type"),
                "tool_name": payload.get("tool_name"),
                "file_path": tool_input.get("file_path") or tool_input.get("path"),
                "reason": reason,
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


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
        _debug_log(payload, decision="block", reason=f"コード書込み禁止フェーズ phase={phase}")
        print(
            f"[phase_guard] BLOCKED: 現フェーズ '{phase}' では '{relative}' への書込みは禁止です。\n"
            f"ソースコードを編集できるのは 実装 / 単体テスト / 総合テスト フェーズのみです。\n"
            f"実装フェーズに入るには、詳細設計の内部審査(社内で自動開催)とお客様のご承認を完了してください。",
            file=sys.stderr,
        )
        return 2

    if is_code_path:
        _debug_log(payload, decision="allow", reason=f"コード書込み許可フェーズ phase={phase}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
