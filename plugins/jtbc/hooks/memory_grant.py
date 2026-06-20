#!/usr/bin/env python3
"""
memory_grant.py — JTBC PreToolUse hook

.jtbc/memory/ 配下への書込みを **自動承認**(permissionDecision: allow)する。

狙い:
- ユーザーが settings.json に手で `permissions` を書かなくても、プラグインを
  有効化するだけで役職が確認なしで自分のメモを書けるようにする
  (プラグイン同梱フックは有効化時に自動で走る。権限ルールは配布できないが
   「権限判定フック」は配布できる、という Claude Code の仕様を利用)。
- バックグラウンド・エージェントの「許可なし=自動拒否」も回避できる。

権限のシングル・オーソリティ(memory パスはこのフックだけが decision を出す):
- lead(司令塔=メインセッション。agent_type を持たない) → memory 領域を許可。
- 役職 teammate/subagent → 自分の .jtbc/memory/<role>/ のみ許可。
  他役職のメモへの書込みは deny(混線防止)。
- .jtbc/memory/ 以外のパスには一切関与しない(他のガードに委ねる)。

注意: 他の PreToolUse ガード(phase_guard / role_guard / ringi_guard /
incident_guard / state_guard)はいずれも .jtbc/memory/ パスでは何も判定しない
(素通り)ことを確認済み。よって deny 競合は起きない。

出力: 該当時のみ stdout に hookSpecificOutput JSON、常に exit 0。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TARGET_TOOLS = {"Edit", "Write", "MultiEdit"}


def _emit(decision: str, reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    if payload.get("tool_name") not in TARGET_TOOLS:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not file_path:
        return 0

    cwd = Path(payload.get("cwd", "."))
    try:
        rel = (
            str(Path(file_path).resolve().relative_to(cwd.resolve()))
            if Path(file_path).is_absolute()
            else file_path
        )
    except Exception:
        rel = file_path
    norm = rel.replace("\\", "/")

    if not norm.startswith(".jtbc/memory/"):
        return 0  # メモ領域以外は関与しない

    raw_role = (
        payload.get("agent_type")
        or payload.get("agent_name")
        or payload.get("subagent_name")
    )
    if not raw_role:
        # lead(メインセッション): memory 領域への書込みを自動承認
        _emit("allow", "JTBC: lead の役職メモ書込みを自動承認")
        return 0

    role = str(raw_role).split(":")[-1].strip()
    role_short = role[len("jtbc-"):] if role.startswith("jtbc-") else role
    own_prefix = f".jtbc/memory/{role_short}/"
    if norm.startswith(own_prefix):
        _emit("allow", f"JTBC: 役職 '{role}' の自メモ書込みを自動承認")
        return 0

    _emit("deny", f"JTBC: 役職 '{role}' は他役職のメモ '{rel}' を書けません(自メモは {own_prefix})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
