#!/usr/bin/env python3
"""
memory_timeline.py — JTBC PostToolUse hook

state.json#phase が変わったら .jtbc/memory/_timeline.md に
「実時刻・更新者役職・新フェーズ」を1行追記する(決定論的タイムライン)。

設計思想:
- 中身の判断が要らない「事実の索引」なのでフックで自動化する。
  役職メモの本体(知識)はエージェント自身が .jtbc/memory/<role>/ に書く
  (フックは機械的なツール入出力しか見えず、何を学んだかは判断できないため)。
- 観測専用: 常に exit 0(セッションをブロックしない)。
- 冪等: 直近に記録したフェーズと新フェーズが同じなら追記しない
  (フェーズ移行を伴わない state.json への書込みでは追記されない)。

入力: stdin に Claude Code の PostToolUse ペイロード JSON
  {"tool_name":..., "tool_input":{...}, "cwd":..., "agent_type":..., ...}
出力: 常に exit 0。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

TARGET_TOOLS = {"Edit", "Write", "MultiEdit"}


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
    rel = rel.replace("\\", "/")

    if rel != ".jtbc/state.json" and not rel.endswith("/.jtbc/state.json"):
        return 0

    state_path = cwd / ".jtbc" / "state.json"
    if not state_path.exists():
        return 0
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0

    phase = state.get("phase")
    if not phase:
        return 0

    mem_dir = cwd / ".jtbc" / "memory"
    timeline = mem_dir / "_timeline.md"

    # 直近に記録したフェーズを読む(冪等化)
    last_phase = None
    if timeline.exists():
        try:
            for line in reversed(timeline.read_text(encoding="utf-8").splitlines()):
                if "phase=" in line:
                    last_phase = line.split("phase=", 1)[1].split("|", 1)[0].strip()
                    break
        except OSError:
            pass

    if last_phase == phase:
        return 0

    actor = payload.get("agent_type") or payload.get("agent_name") or "main"
    actor = str(actor).split(":")[-1].strip() or "main"
    ts = datetime.now().isoformat(timespec="seconds")

    try:
        mem_dir.mkdir(parents=True, exist_ok=True)
        new_file = not timeline.exists()
        with timeline.open("a", encoding="utf-8") as f:
            if new_file:
                f.write("# JTBC フェーズ・タイムライン (自動記録 / memory_timeline フック)\n\n")
            f.write(f"- {ts} | phase={phase} | by={actor}\n")
    except OSError:
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
