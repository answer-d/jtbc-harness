#!/usr/bin/env python3
"""
team_guard.py — JTBC PreToolUse hook

teams 有効環境で、役職(jtbc-*)を「一発実行(subagent_type のみ・コールドスタート→Done で消滅)」で
spawn しようとするのを物理的にブロックし、常駐 teammate(run_in_background:true + name)へ誘導する。

背景(実機で繰り返し観測):
- 司令塔(lead)が「Teams 有効なのに subagent_type の一発実行に逃げる」退化が複数回起きた。
  役職が毎回記憶ゼロで起き、teammate 連携も起きない(= 実質サブエージェント運用に退化)。
- governance スキルに「一発実行禁止」と明記しても止まらず、プロンプト強化(v0.10.3 / v0.13.0)は
  2 回とも無効だった。よって phase_guard / state_guard と同じ「物理強制」で既定を担保する。

設計思想(最小ロック):
- 縛るのは「teams 有効時に jtbc 役職を一発実行で起こさない」という一点のみ。
- teams 無効環境では一発実行は正当なフォールバックなので素通り。
- 常駐 teammate(run_in_background:true)や、jtbc 以外の汎用サブエージェントも素通り。

ルール:
- env CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS が "1"(=teams 有効)でなければ素通り。
- 対象ツールは subagent を起こす Task / Agent。
- tool_input の subagent_type(または agentType)が JTBC 役職(末尾が jtbc-*)で、
  かつ run_in_background が真でない(=一発実行)場合に exit 2 でブロック。

入力: stdin に Claude Code が JSON で {"tool_name":..., "tool_input":{...}, ...}
出力: 続行なら exit 0、ブロックなら stderr にメッセージ + exit 2
"""
from __future__ import annotations

import json
import os
import sys

SPAWN_TOOLS = {"Task", "Agent"}


def _is_jtbc_role(subagent_type) -> bool:
    """subagent_type が JTBC 役職か(例 "jtbc:jtbc-kacho" / "jtbc-kacho")。"""
    if not subagent_type:
        return False
    tail = str(subagent_type).split(":")[-1].strip()
    return tail.startswith("jtbc-")


def _truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes")
    return bool(v)


def main() -> int:
    # teams 無効環境は素通り(一発実行=正当なフォールバック)
    if os.environ.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "").strip() != "1":
        return 0

    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    if payload.get("tool_name") not in SPAWN_TOOLS:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    subagent_type = tool_input.get("subagent_type") or tool_input.get("agentType")
    if not _is_jtbc_role(subagent_type):
        return 0

    # 常駐 teammate として起こしている → 正常
    if _truthy(tool_input.get("run_in_background")):
        return 0

    role = str(subagent_type).split(":")[-1].strip()
    print(
        f"[team_guard] BLOCKED: teams 有効環境で役職 '{role}' を一発実行(subagent_type のみ)で\n"
        f"spawn しようとしました。役職は必ず常駐 teammate として起こしてください:\n"
        f'  Agent(subagent_type="{subagent_type}", name="<役職名>", run_in_background=true)\n'
        f"以降の指示は同じ teammate へ SendMessage で送り、PJ完了まで shutdown しないでください。\n"
        f"(一発実行が許されるのは teams 無効環境のフォールバックのみ。"
        f"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 の現環境では使えません。)",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
