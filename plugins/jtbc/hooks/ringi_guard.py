#!/usr/bin/env python3
"""
ringi_guard.py — JTBC PreToolUse hook

要件/設計に "稟議無しで直接手を入れる" 行為をブロックする。

ルール:
- .jtbc/proposal/proposal.md, .jtbc/requirements/requirements.md,
  .jtbc/designs/basic_design*.md, .jtbc/designs/detailed_design*.md
  への Edit/Write/MultiEdit は、承認済みの変更管理票(稟議)に対象が含まれる場合のみ許可。
- 各ドキュメントの初版作成フェーズ中に、その起案者 role(サブエージェント)が書く場合は例外的に許可
  (初版執筆は稟議対象外。改訂のみ稟議が要る)。
- 司令塔(メインセッション)は agent_type を持たないため、これらガバナンス文書を直接書けない。
  必ず起案者の役職サブエージェントを起動して書かせる(役割分離の物理担保)。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def resolve_agent_role(payload: dict) -> str | None:
    """PreToolUse ペイロードから役職を正準短名 (例 "kacho") で解決する。

    Claude Code が agent_type に渡す値は起動方法で形が異なる:
    - 一発実行 (subagent_type): 名前空間付き "jtbc:jtbc-kacho"
    - 常駐 teammate (name 付き Agent): teammate 名そのもの。本プラグインの規約では
      役職の短名 "kacho"(name は agentType を上書きする / 体制図・memory ディレクトリと一致)
    両者を同一視するため、名前空間と "jtbc-" 接頭辞の双方を剥がし、短名へ正準化する。
    旧 agent_name/subagent_name は後方互換で残す。
    司令塔(メインセッション)からの書込みは agent_type を持たず None を返す。
    """
    raw = (
        payload.get("agent_type")
        or payload.get("agent_name")
        or payload.get("subagent_name")
    )
    if not raw:
        return None
    role = str(raw).split(":")[-1].strip()
    if role.startswith("jtbc-"):
        role = role[len("jtbc-"):]
    return role or None


def _debug_payload(payload: dict) -> None:
    """JTBC_HOOK_DEBUG が設定されている時のみ、実ペイロードを記録する(調査用)。"""
    if not os.environ.get("JTBC_HOOK_DEBUG"):
        return
    try:
        cwd = Path(payload.get("cwd", "."))
        log = cwd / ".jtbc" / "hook_debug.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as f:
            f.write(json.dumps({
                "hook": "ringi_guard",
                "keys": sorted(payload.keys()),
                "agent_type": payload.get("agent_type"),
                "agent_id": payload.get("agent_id"),
                "resolved_role": resolve_agent_role(payload),
                "tool_name": payload.get("tool_name"),
                "file_path": (payload.get("tool_input") or {}).get("file_path"),
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


# cr_type: (path_pattern, 初版作成フェーズ, 初版起案者roles, 承認者roles)
# 承認者は稟議なしで当該文書を Edit/Write できる(承認印押印・赤入れが職務のため)。
DOC_PATTERNS = {
    "proposal": (r"^\.jtbc/proposal/", "PROPOSAL", {"kacho"}, {"bucho"}),
    "requirement": (r"^\.jtbc/requirements/", "REQUIREMENTS", {"kacho"}, {"bucho"}),
    "design_basic": (r"^\.jtbc/designs/basic_design", "BASIC_DESIGN", {"kacho"}, {"bucho"}),
    "design_detailed": (r"^\.jtbc/designs/detailed_design", "DETAILED_DESIGN", {"shunin"}, {"kacho", "bucho"}),
}


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    _debug_payload(payload)

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path")
    agent_name = resolve_agent_role(payload)
    cwd = Path(payload.get("cwd", "."))
    if not file_path:
        return 0

    relative = str(Path(file_path).resolve().relative_to(cwd.resolve())) if Path(file_path).is_absolute() else file_path

    state_path = cwd / ".jtbc" / "state.json"
    if not state_path.exists():
        return 0
    try:
        state = json.loads(state_path.read_text())
    except json.JSONDecodeError:
        return 0

    # CRのtype:フィールドと cr_type のマッピング
    CR_TYPE_MAP = {
        "requirement": {"requirement"},
        "design_basic": {"design"},
        "design_detailed": {"design"},
    }

    phase = state.get("phase")
    for cr_type, (pattern, drafting_phase, drafter_roles, approver_roles) in DOC_PATTERNS.items():
        if re.search(pattern, relative):
            if phase == drafting_phase and agent_name in drafter_roles:
                return 0
            if agent_name in approver_roles:
                return 0
            approved_dir = cwd / ".jtbc" / "changes" / "approved"
            if approved_dir.exists():
                approved_for_target = False
                for cr_file in approved_dir.glob("CR-*.md"):
                    text = cr_file.read_text(errors="ignore")
                    # フロントマター(最初の --- と次の --- の間)を簡易パース
                    fm_status = None
                    fm_type = None
                    body_after_fm = text
                    if text.startswith("---"):
                        end_idx = text.find("---", 3)
                        if end_idx != -1:
                            fm_block = text[3:end_idx]
                            body_after_fm = text[end_idx + 3:]
                            for line in fm_block.splitlines():
                                if ":" in line:
                                    key, _, val = line.partition(":")
                                    key = key.strip()
                                    val = val.strip()
                                    if key == "status":
                                        fm_status = val
                                    elif key == "type":
                                        fm_type = val
                    # 3条件: status:APPROVED / type一致 / 本文に対象パス含む
                    allowed_cr_types = CR_TYPE_MAP.get(cr_type, set())
                    if (
                        fm_status == "APPROVED"
                        and fm_type in allowed_cr_types
                        and relative in body_after_fm
                    ):
                        approved_for_target = True
                        break
                if approved_for_target:
                    return 0
            print(
                f"[ringi_guard] BLOCKED: '{relative}' の変更には稟議承認が必要です。\n"
                f"変更管理(稟議)は司令塔が社内で自動処理します(governance スキル)。\n"
                f"  起票({cr_type.split('_')[0]}) → 承認パスで各役職が押印 → APPROVED → 反映\n"
                f"全承認後にこのファイル更新を再試行してください。",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
