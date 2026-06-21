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
import os
import re
import sys
from pathlib import Path

_HOOK = "role_guard"


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


def resolve_agent_role(payload: dict) -> str | None:
    """PreToolUse ペイロードから役職を正準短名 (例 "kacho") で解決する。

    agent_type の形は起動方法で異なる(一発実行は "jtbc:jtbc-kacho"、常駐 teammate は
    name=短名 "kacho")。名前空間と "jtbc-" 接頭辞を剥がして短名へ正準化し、両者を同一視する。
    司令塔(メインセッション)は agent_type を持たず None を返す → 本ガードは素通り。
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


# コードを書くロール(active_wbs_task が必要)。主任もテックリードとして実装可。
IMPLEMENTER_ROLES = {"tantou", "ses", "shunin"}

ROLE_RULES: dict[str, dict[str, list[str]]] = {
    "shacho": {
        "allow": [r"^\.jtbc/proposal/", r"^\.jtbc/lessons/", r"^\.jtbc/gates/", r"^\.jtbc/deliverables/completion_approval", r"^\.jtbc/incidents/.*report.*"],
        "deny": [r"^src/", r"^lib/", r"^app/", r"^pkg/", r"^internal/", r"^\.jtbc/requirements/", r"^\.jtbc/designs/", r"^\.jtbc/wbs/"],
    },
    "bucho": {
        "allow": [r"^\.jtbc/proposal/", r"^\.jtbc/plans/", r"^\.jtbc/risks/", r"^\.jtbc/gates/", r"^\.jtbc/changes/pending/", r"^\.jtbc/incidents/", r"^\.jtbc/minutes/", r"^\.jtbc/client_reviews/"],
        "deny": [r"^src/", r"^lib/", r"^app/", r"^pkg/", r"^internal/"],
    },
    "pmo": {
        # PMO: プロセスの門番。phase 移行の正本管理(state.json)と PM プロセス文書を扱う。
        # 提案/要件/設計の起案・改訂はしない(課長/主任の領域)。コードも書かない。
        "allow": [r"^\.jtbc/state\.json", r"^\.jtbc/plans/", r"^\.jtbc/risks/", r"^\.jtbc/wbs/", r"^\.jtbc/gates/", r"^\.jtbc/issues/", r"^\.jtbc/deliverables/", r"^\.jtbc/lessons/", r"^\.jtbc/minutes/", r"^\.jtbc/changes/pending/"],
        "deny": [r"^src/", r"^lib/", r"^app/", r"^pkg/", r"^internal/", r"^\.jtbc/proposal/", r"^\.jtbc/requirements/", r"^\.jtbc/designs/"],
    },
    "kacho": {
        "allow": [r"^\.jtbc/proposal/", r"^\.jtbc/plans/", r"^\.jtbc/requirements/", r"^\.jtbc/designs/basic_design", r"^\.jtbc/risks/", r"^\.jtbc/issues/", r"^\.jtbc/gates/", r"^\.jtbc/changes/pending/", r"^\.jtbc/incidents/", r"^\.jtbc/minutes/", r"^\.jtbc/client_reviews/"],
        "deny": [r"^src/", r"^lib/", r"^app/", r"^pkg/", r"^internal/", r"^\.jtbc/designs/detailed_design"],
    },
    "shunin": {
        # テックリードとして実装も可。コードは active_wbs_task の範囲内かつ実装系フェーズのみ
        # (phase_guard / WBSチェックで制御)。
        "allow": [r"^\.jtbc/designs/detailed_design", r"^\.jtbc/wbs/", r"^\.jtbc/tests/test_plan", r"^\.jtbc/issues/", r"^\.jtbc/gates/", r"^\.jtbc/changes/pending/", r"^\.jtbc/incidents/", r"^\.jtbc/minutes/", r"^src/", r"^lib/", r"^app/", r"^tests/"],
        "deny": [r"^pkg/", r"^internal/", r"^\.jtbc/requirements/", r"^\.jtbc/designs/basic_design", r"^\.jtbc/proposal/", r"^\.jtbc/plans/", r"^\.jtbc/risks/"],
    },
    "tantou": {
        "allow": [r"^src/", r"^lib/", r"^app/", r"^tests/", r"^\.jtbc/wbs/", r"^\.jtbc/tests/test_report", r"^\.jtbc/changes/pending/", r"^\.jtbc/issues/", r"^\.jtbc/minutes/"],
        "deny": [r"^\.jtbc/requirements/", r"^\.jtbc/designs/", r"^\.jtbc/proposal/", r"^\.jtbc/plans/", r"^\.jtbc/risks/"],
    },
    "ses": {
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

    agent_name = resolve_agent_role(payload)
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not file_path or not agent_name:
        return 0

    rules = ROLE_RULES.get(agent_name)
    if not rules:
        return 0

    cwd = Path(payload.get("cwd", "."))
    relative = str(Path(file_path).resolve().relative_to(cwd.resolve())) if Path(file_path).is_absolute() else file_path

    # --- 役職メモ(.jtbc/memory/): 許可/拒否は memory_grant フックが一元管理する ---
    # role_guard はここに関与しない(whitelist で誤ってブロックしないよう素通り)。
    if relative.replace("\\", "/").startswith(".jtbc/memory/"):
        return 0

    if match_any(rules["deny"], relative):
        _debug_log(payload, decision="block", role=agent_name, reason="deny パターン一致")
        print(
            f"[role_guard] BLOCKED: 役職 '{agent_name}' は '{relative}' への書込みが禁止されています。\n"
            f"役職の振り分けは司令塔が自動で行います(governance スキル)。\n"
            f"要件/設計変更が必要な場合は、司令塔が変更管理(稟議)を社内で自動処理します。",
            file=sys.stderr,
        )
        return 2

    if rules["allow"] and not match_any(rules["allow"], relative):
        _debug_log(payload, decision="block", role=agent_name, reason="allow 許可リスト外")
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
                _debug_log(payload, decision="block", role=agent_name, reason="WBS 未割当でコード編集")
                print(
                    f"[role_guard] BLOCKED: 実装担当 '{agent_name}' は WBSタスクが active でない状態でコードを編集できません。\n"
                    "主任に active_wbs_task を割り当ててもらってください。",
                    file=sys.stderr,
                )
                return 2

    _debug_log(payload, decision="allow", role=agent_name, reason="役職の許可パス内")
    return 0


if __name__ == "__main__":
    sys.exit(main())
