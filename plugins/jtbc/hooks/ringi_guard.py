#!/usr/bin/env python3
"""
ringi_guard.py — JTBC PreToolUse hook

要件/設計に "稟議無しで直接手を入れる" 行為をブロックする。

ルール:
- .jtbc/requirements/requirements.md, .jtbc/designs/basic_design*.md, .jtbc/designs/detailed_design*.md
  への Edit/Write/MultiEdit は、承認済みの変更管理票(稟議)に対象が含まれる場合のみ許可。
- 各ドキュメントの初版作成フェーズ中に、その主担当 role が書く場合は例外的に許可
  (初版執筆は稟議対象外。改訂のみ稟議が要る)。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# cr_type: (path_pattern, 初版作成フェーズ, 初版作成を許す役職)
DOC_PATTERNS = {
    "requirement": (r"^\.jtbc/requirements/", "REQUIREMENTS", {"jtbc-kacho"}),
    "design_basic": (r"^\.jtbc/designs/basic_design", "BASIC_DESIGN", {"jtbc-kacho"}),
    "design_detailed": (r"^\.jtbc/designs/detailed_design", "DETAILED_DESIGN", {"jtbc-shunin"}),
}


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
    agent_name = payload.get("agent_name") or payload.get("subagent_name")
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
    for cr_type, (pattern, drafting_phase, drafter_roles) in DOC_PATTERNS.items():
        if re.search(pattern, relative):
            if phase == drafting_phase and agent_name in drafter_roles:
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
                f"以下を試してください:\n"
                f"  1) /jtbc:ringi new {cr_type.split('_')[0]} \"<変更概要>\"\n"
                f"  2) /jtbc:ringi submit CR-NNN\n"
                f"  3) 主任→課長→部長 で /jtbc:shonin <role> CR-NNN approve\n"
                f"全承認後にこのファイル更新を再試行してください。",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
