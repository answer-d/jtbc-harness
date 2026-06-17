#!/usr/bin/env python3
"""
role_guard.py — JTBC PreToolUse hook

現在の役職 agent のシステムプロンプトで明示された
「触ってよいパス」「触ってはいけないパス」を強制する。

役職判定は payload.agent_type (Claude Code が PreToolUse に渡す
subagent の frontmatter name) を見る。例: "jtbc-shacho", "jtbc-tantou", "jtbc-ses"。
※ 司令塔(メインセッション)からの書込みは agent_type を持たないため
  本ガードは素通りする(役職振り分けはサブエージェント起動が前提)。

ルール: agents/jtbc-<role>.md の冒頭で記述している禁止/許可パスを
本ファイル内のテーブル ROLE_RULES に映している。

実装担当 (jtbc-tantou / jtbc-ses) の場合は追加で
state.json#active_wbs_task が割り当てられているかを照合する。
外注SES (jtbc-ses) は担当と同じファイル権限だが、設計/要件/計画系の
ドキュメントには一切触れない(常に課長以下の指示でコードのみを扱う)。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# コードを書くロール(active_wbs_task が必要)。主任もテックリードとして実装可。
IMPLEMENTER_ROLES = {"jtbc-tantou", "jtbc-ses", "jtbc-shunin"}

ROLE_RULES: dict[str, dict[str, list[str]]] = {
    "jtbc-shacho": {
        "allow": [r"^\.jtbc/proposal/", r"^\.jtbc/lessons/", r"^\.jtbc/gates/", r"^\.jtbc/deliverables/completion_approval", r"^\.jtbc/incidents/.*report.*"],
        "deny": [r"^src/", r"^lib/", r"^app/", r"^pkg/", r"^internal/", r"^\.jtbc/requirements/", r"^\.jtbc/designs/", r"^\.jtbc/wbs/"],
    },
    "jtbc-bucho": {
        "allow": [r"^\.jtbc/proposal/", r"^\.jtbc/plans/", r"^\.jtbc/risks/", r"^\.jtbc/gates/", r"^\.jtbc/changes/pending/", r"^\.jtbc/incidents/", r"^\.jtbc/minutes/", r"^\.jtbc/client_reviews/"],
        "deny": [r"^src/", r"^lib/", r"^app/", r"^pkg/", r"^internal/"],
    },
    "jtbc-kacho": {
        "allow": [r"^\.jtbc/proposal/", r"^\.jtbc/plans/", r"^\.jtbc/requirements/", r"^\.jtbc/designs/basic_design", r"^\.jtbc/risks/", r"^\.jtbc/issues/", r"^\.jtbc/gates/", r"^\.jtbc/changes/pending/", r"^\.jtbc/incidents/", r"^\.jtbc/minutes/", r"^\.jtbc/client_reviews/"],
        "deny": [r"^src/", r"^lib/", r"^app/", r"^pkg/", r"^internal/", r"^\.jtbc/designs/detailed_design"],
    },
    "jtbc-shunin": {
        # テックリードとして実装も可。コードは active_wbs_task の範囲内かつ実装系フェーズのみ
        # (phase_guard / WBSチェックで制御)。
        "allow": [r"^\.jtbc/designs/detailed_design", r"^\.jtbc/wbs/", r"^\.jtbc/tests/test_plan", r"^\.jtbc/issues/", r"^\.jtbc/gates/", r"^\.jtbc/changes/pending/", r"^\.jtbc/incidents/", r"^\.jtbc/minutes/", r"^src/", r"^lib/", r"^app/", r"^tests/"],
        "deny": [r"^pkg/", r"^internal/", r"^\.jtbc/requirements/", r"^\.jtbc/designs/basic_design", r"^\.jtbc/proposal/", r"^\.jtbc/plans/", r"^\.jtbc/risks/"],
    },
    "jtbc-tantou": {
        "allow": [r"^src/", r"^lib/", r"^app/", r"^tests/", r"^\.jtbc/wbs/", r"^\.jtbc/tests/test_report", r"^\.jtbc/changes/pending/", r"^\.jtbc/issues/", r"^\.jtbc/minutes/"],
        "deny": [r"^\.jtbc/requirements/", r"^\.jtbc/designs/", r"^\.jtbc/proposal/", r"^\.jtbc/plans/", r"^\.jtbc/risks/"],
    },
    "jtbc-ses": {
        # 外注SES: 担当と同等のコード権限。ただしガバナンス文書は稟議/課題起票以外触れない。
        "allow": [r"^src/", r"^lib/", r"^app/", r"^tests/", r"^\.jtbc/wbs/", r"^\.jtbc/tests/test_report", r"^\.jtbc/issues/"],
        "deny": [r"^\.jtbc/requirements/", r"^\.jtbc/designs/", r"^\.jtbc/proposal/", r"^\.jtbc/plans/", r"^\.jtbc/risks/", r"^\.jtbc/gates/", r"^\.jtbc/changes/", r"^\.jtbc/minutes/", r"^\.jtbc/incidents/"],
    },
}


def match_any(patterns: list[str], path: str) -> bool:
    return any(re.search(p, path) for p in patterns)


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    agent_name = (
        payload.get("agent_type")
        or payload.get("agent_name")
        or payload.get("subagent_name")
    )
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not file_path or not agent_name:
        return 0

    rules = ROLE_RULES.get(agent_name)
    if not rules:
        return 0

    cwd = Path(payload.get("cwd", "."))
    relative = str(Path(file_path).resolve().relative_to(cwd.resolve())) if Path(file_path).is_absolute() else file_path

    if match_any(rules["deny"], relative):
        print(
            f"[role_guard] BLOCKED: 役職 '{agent_name}' は '{relative}' への書込みが禁止されています。\n"
            f"役職の振り分けは司令塔が自動で行います(governance スキル)。\n"
            f"要件/設計変更が必要な場合は、司令塔が変更管理(稟議)を社内で自動処理します。",
            file=sys.stderr,
        )
        return 2

    if rules["allow"] and not match_any(rules["allow"], relative):
        print(
            f"[role_guard] BLOCKED: 役職 '{agent_name}' の許可パス一覧に '{relative}' は含まれません。\n"
            f"許可されているパスパターン: {rules['allow']}",
            file=sys.stderr,
        )
        return 2

    if agent_name in IMPLEMENTER_ROLES:
        state_path = cwd / ".jtbc" / "state.json"
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text())
            except json.JSONDecodeError:
                state = {}
            active = state.get("active_wbs_task")
            is_code_path = any(re.search(p, relative) for p in [r"^src/", r"^lib/", r"^app/"])
            if is_code_path and not active:
                print(
                    f"[role_guard] BLOCKED: 実装担当 '{agent_name}' は WBSタスクが active でない状態でコードを編集できません。\n"
                    "主任に active_wbs_task を割り当ててもらってください。",
                    file=sys.stderr,
                )
                return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
