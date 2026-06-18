#!/usr/bin/env python3
"""
state_guard.py — JTBC PreToolUse hook

フェーズ移行(= .jtbc/state.json の "phase" 書き換え)を PMO 役職に限定する。

設計思想(最小ロック):
- ハーネス(state.json)を物理で縛るのは「phase を変えられるのは PMO だけ」という一点に絞る。
  PMBOK に沿った「進めてよいか」の融通ある判断は、PMO エージェント側(プロンプト)に委ねる。
- 司令塔(営業)も課長も、approvals / client_reviews / roster 等の他フィールドは従来どおり
  state.json に書ける(承認記録の正本管理はこれまで通り)。**phase が変わるときだけ** PMO を要求する。

ルール:
- 対象は .jtbc/state.json への Edit / Write / MultiEdit。
- 書込みの結果 "phase" の値が現状から変わる場合、agent_type が jtbc-pmo でなければ exit 2 でブロック。
- state.json が未作成(初期化 /jtbc:init)や、phase が変わらない書込みは素通り。

入力: stdin に Claude Code が JSON で {"tool_name":..., "tool_input":{...}, "cwd":..., "agent_type":...}
出力: 続行なら exit 0、ブロックなら stderr にメッセージ + exit 2
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PMO_ROLE = "jtbc-pmo"
PHASE_RE = re.compile(r'"phase"\s*:\s*"([A-Z_]+)"')


def resolve_agent_role(payload: dict) -> str | None:
    raw = (
        payload.get("agent_type")
        or payload.get("agent_name")
        or payload.get("subagent_name")
    )
    if not raw:
        return None
    return str(raw).split(":")[-1].strip() or None


def _phase_from_text(text: str) -> str | None:
    m = PHASE_RE.search(text or "")
    return m.group(1) if m else None


def _new_phase_from_write(tool_name: str, tool_input: dict, current: str | None) -> str | None:
    """書込み操作から「結果として設定される phase」を可能な範囲で推定する。

    - Write: content 全体の "phase" を読む。
    - Edit: new_string に "phase":"X" があればそれを採用。
    - MultiEdit: edits の new_string 群から最後に現れる "phase":"X" を採用。
    判定できない場合は current(=変更なし扱い)を返す。
    """
    if tool_name == "Write":
        return _phase_from_text(tool_input.get("content", "")) or current
    if tool_name == "Edit":
        np = _phase_from_text(tool_input.get("new_string", ""))
        return np if np else current
    if tool_name == "MultiEdit":
        latest = current
        for ed in tool_input.get("edits", []) or []:
            np = _phase_from_text((ed or {}).get("new_string", ""))
            if np:
                latest = np
        return latest
    return current


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    tool_input = payload.get("tool_input", {})
    tool_name = payload.get("tool_name", "")
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not file_path:
        return 0

    cwd = Path(payload.get("cwd", "."))
    relative = (
        str(Path(file_path).resolve().relative_to(cwd.resolve()))
        if Path(file_path).is_absolute()
        else file_path
    )

    # 対象は state.json のみ
    if relative.replace("\\", "/") != ".jtbc/state.json":
        return 0

    state_path = cwd / ".jtbc" / "state.json"
    if not state_path.exists():
        # 初期化(新規作成)は素通り
        return 0
    try:
        current_phase = json.loads(state_path.read_text()).get("phase")
    except json.JSONDecodeError:
        return 0

    new_phase = _new_phase_from_write(tool_name, tool_input, current_phase)
    if new_phase == current_phase:
        # phase は変わらない(approvals 等の更新)→ 素通り
        return 0

    agent_name = resolve_agent_role(payload)
    if agent_name == PMO_ROLE:
        return 0

    print(
        f"[state_guard] BLOCKED: フェーズ移行(phase: {current_phase} → {new_phase})は PMO のみが実行できます。\n"
        f"フェーズ移行は PMBOK に沿ったプロセス検証(ゲート承認の充足・必要書類の整備・客先承認)を経て、\n"
        f"PMO エージェント(jtbc:jtbc-pmo)が行います。司令塔は PMO に移行可否の検証を依頼してください。\n"
        f"(approvals / client_reviews / roster 等、phase 以外の更新はブロックされません)",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
