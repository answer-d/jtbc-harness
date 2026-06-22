#!/usr/bin/env python3
"""
state_guard.py — JTBC PreToolUse hook

フェーズ移行(= .jtbc/state.json の "phase" 書き換え)を、
(A) 権限: PMO 役職のみが実行でき、かつ
(B) プロセス: 移行先ゲートの事前条件(内部承認・客先承認・必要書類)を満たすときのみ
許可する。どちらか一方でも欠ければ exit 2 でブロックする。

設計思想(最小ロック + 事前条件):
- ハーネス(state.json)を物理で縛るのは「phase を変えてよいのは PMO だけ」+
  「正しい順序(承認・客先承認・書類)を踏んでいること」の2点に絞る。
- approvals / client_reviews / roster 等、phase 以外のフィールド更新は従来どおり素通り
  (承認記録の正本管理はリード/PMO が担う)。**phase が変わるときだけ** 検査する。

(B) 事前条件は config/jtbc.yaml#gates を正とし、安定した遷移表を本ファイルに写している
   (role_guard の ROLE_RULES と同じ方式。yaml 依存を避ける)。

入力: stdin に Claude Code が JSON で {"tool_name":..., "tool_input":{...}, "cwd":..., "agent_type":...}
出力: 続行なら exit 0、ブロックなら stderr にメッセージ + exit 2
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

PMO_ROLE = "pmo"
PHASE_RE = re.compile(r'"phase"\s*:\s*"([A-Z_]+)"')
_HOOK = "state_guard"


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

# 移行先 phase ごとの事前条件(config/jtbc.yaml#gates を正とする写し)。
# gate: ゲート名 / approvers: 全員 approved が必要な承認者役職 /
# client_review: 客先承認(APPROVED)が必要なら client_reviews のキー(無ければ None) /
# docs: 埋まっている必要がある必要書類のキー。
TRANSITIONS: dict[str, dict] = {
    "REQUIREMENTS":    {"gate": "proposal",        "approvers": ["bucho", "shacho"], "client_review": "proposal",        "docs": ["proposal"]},
    "BASIC_DESIGN":    {"gate": "project_plan",    "approvers": ["bucho"],           "client_review": "project_plan",    "docs": ["project_plan", "requirements", "risk_register", "wbs"]},
    "DETAILED_DESIGN": {"gate": "basic_design",    "approvers": ["bucho"],           "client_review": "basic_design",    "docs": ["basic_design", "issue_log"]},
    "IMPLEMENTATION":  {"gate": "detailed_design", "approvers": ["kacho", "bucho"],  "client_review": "detailed_design", "docs": ["detailed_design", "wbs", "test_plan"]},
    "RELEASED":        {"gate": "release",         "approvers": ["bucho", "shacho"], "client_review": None,               "docs": ["test_report", "deliverables_list"]},
    "COMPLETED":       {"gate": "completion",      "approvers": ["bucho", "shacho"], "client_review": None,               "docs": ["lessons_learned", "completion_approval"]},
}

DOC_PATHS = {
    "proposal":            ".jtbc/proposal/proposal.md",
    "requirements":        ".jtbc/requirements/requirements.md",
    "project_plan":        ".jtbc/plans/project_plan.md",
    "risk_register":       ".jtbc/risks/risk_register.md",
    "basic_design":        ".jtbc/designs/basic_design.md",
    "issue_log":           ".jtbc/issues/issue_log.md",
    "detailed_design":     ".jtbc/designs/detailed_design.md",
    "wbs":                 ".jtbc/wbs/wbs.md",
    "test_plan":           ".jtbc/tests/test_plan.md",
    "test_report":         ".jtbc/tests/test_report.md",
    "deliverables_list":   ".jtbc/deliverables/deliverables_list.md",
    "lessons_learned":     ".jtbc/lessons/lessons_learned.md",
    "completion_approval": ".jtbc/deliverables/completion_approval.md",
}

# 雛形のまま(未記入)を示すスタブ。残っていれば「埋まっていない」とみなす。
# どのテンプレでも未置換プレースホルダ "{{" が残っていれば未記入。
#
# 値が list の場合は、その書類を要求する全ゲートで同じスタブを判定する。
# 値が dict の場合は **ゲート別** スタブ(キー=gate 名)。同じファイルが
# 複数ゲートで段階的に詳細化される書類(WBS=ローリングウェーブ)に使う:
#   - project_plan ゲート(計画): WBS骨子(ワークパッケージ)が埋まっているか
#   - detailed_design ゲート(詳細設計): タスク分解(実装単位)が埋まっているか
# これにより「骨子だけ」で計画ゲートは通し、詳細設計ゲートで初めてタスク分解を要求できる
# (PMBOK の Create WBS=計画 / 段階的詳細化=後工程 を機械的に表現する)。
DOC_STUBS = {
    "requirements":    ["<要件名>"],
    "risk_register":   ["<リスク内容>"],
    "project_plan":    ["(提案書のサマリを転記)"],
    "issue_log":       ["<課題のタイトル>"],
    "detailed_design": ["<コンポーネント名>"],
    "wbs": {
        "project_plan":    ["<ワークパッケージ名>"],
        "detailed_design": ["<タスク名>"],
    },
}
GENERIC_STUB = "{{"


def resolve_agent_role(payload: dict) -> str | None:
    """役職を正準短名 (例 "pmo") で解決する。

    agent_type は起動方法で形が異なる(一発実行 "jtbc:jtbc-pmo" / 常駐 teammate は name=短名 "pmo")。
    名前空間と "jtbc-" 接頭辞を剥がして短名へ正準化し、両者を同一視する。
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


def _phase_from_text(text: str) -> str | None:
    m = PHASE_RE.search(text or "")
    return m.group(1) if m else None


def _new_phase_from_write(tool_name: str, tool_input: dict, current: str | None) -> str | None:
    """書込み操作から「結果として設定される phase」を可能な範囲で推定する。"""
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


def _resulting_state(tool_name: str, tool_input: dict, on_disk: dict) -> dict:
    """承認・客先承認の判定に使う state。Write は新内容、Edit/MultiEdit は既存(直前まで)を使う。

    通常フロー(承認 → 客先承認 → 最後に phase を進める)では、承認・客先承認は
    phase 書込みの「前」に別操作で記録済みなので on_disk で足りる。
    Write で全文を一括更新する場合のみ、新内容から読む。
    """
    if tool_name == "Write":
        try:
            return json.loads(tool_input.get("content", ""))
        except json.JSONDecodeError:
            return on_disk
    return on_disk


def _stubs_for(key: str, gate: str | None) -> list[str]:
    """書類 key のスタブ一覧を、ゲート別 dict / 共通 list の両形式から解決する。"""
    spec = DOC_STUBS.get(key)
    if isinstance(spec, dict):
        return spec.get(gate, []) if gate else []
    return spec or []


def _doc_unfilled_reason(key: str, cwd: Path, gate: str | None = None) -> str | None:
    """必要書類が未作成 or 雛形のままなら理由文字列、OKなら None。

    gate を渡すと、ゲート別スタブ(DOC_STUBS が dict の書類)を当該ゲート基準で判定する。
    """
    rel = DOC_PATHS.get(key)
    if not rel:
        return None
    path = cwd / rel
    if not path.exists():
        return f"{rel} が未作成"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    if GENERIC_STUB in text:
        return f"{rel} に未置換プレースホルダ {{{{...}}}} が残存(雛形のまま)"
    for stub in _stubs_for(key, gate):
        if stub in text:
            return f"{rel} に雛形スタブ '{stub}' が残存(未記入)"
    return None


def _check_transition_preconditions(state: dict, new_phase: str, cwd: Path) -> str | None:
    """移行先ゲートの事前条件を検査。満たさなければ理由文字列、OKなら None。"""
    spec = TRANSITIONS.get(new_phase)
    if not spec:
        return None  # ゲートを伴わない遷移(*_REVIEW / 工程内遷移)は事前条件なし

    # (1) 内部承認: ゲート承認者全員が approved か
    approvals = (state.get("approvals") or {}).get(f"{spec['gate']}_gate") or {}
    # 非 dict の不正形状は例外にせず fail-closed でブロック(門番の素通りを防ぐ)。
    if not isinstance(approvals, dict):
        return (
            f"approvals.{spec['gate']}_gate の形状が不正(dict ではなく {type(approvals).__name__})。"
            f"正本スキーマは役職→承認状態の dict"
        )
    missing = [r for r in spec["approvers"] if approvals.get(r) != "approved"]
    if missing:
        return f"内部承認が未了({spec['gate']}_gate の承認者 {', '.join(missing)} が未承認)"

    # (2) 客先承認: 必要なゲートは client_reviews が APPROVED か
    cr_key = spec.get("client_review")
    if cr_key:
        cr = (state.get("client_reviews") or {}).get(cr_key) or {}
        # 正本スキーマ(client-review.md)は dict {"status":"APPROVED",...}。
        # 素の文字列等の不正形状で渡されると cr.get() が AttributeError → クラッシュ →
        # ハーネス fail-open で門番が素通りになる。門番は fail-closed であるべきなので、
        # 非 dict は例外にせず「不正形状=未承認」として遷移をブロックする。
        if not isinstance(cr, dict):
            return (
                f"client_reviews.{cr_key} の形状が不正(dict ではなく {type(cr).__name__})。"
                f'正本スキーマは {{"status":"APPROVED",...}} の dict(client-review.md)'
            )
        if cr.get("status") != "APPROVED":
            return f"客先承認が未了(client_reviews.{cr_key} が APPROVED でない)"

    # (3) 必要書類: 未作成 or 雛形のままでないか(ゲート別スタブは当該ゲート基準で判定)
    for key in spec.get("docs", []):
        reason = _doc_unfilled_reason(key, cwd, spec["gate"])
        if reason:
            return f"必要書類が未整備({reason})"

    return None


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
        on_disk = json.loads(state_path.read_text())
    except json.JSONDecodeError:
        return 0
    current_phase = on_disk.get("phase")

    new_phase = _new_phase_from_write(tool_name, tool_input, current_phase)
    if new_phase == current_phase:
        # phase は変わらない(approvals 等の更新)→ 素通り
        return 0

    # (B) プロセス: 移行先ゲートの事前条件(内部承認・客先承認・必要書類)を満たすか。
    #     PMO であっても、順序を飛ばす移行はブロックする(審査・客先承認スキップの物理防止)。
    state_after = _resulting_state(tool_name, tool_input, on_disk)
    reason = _check_transition_preconditions(state_after, new_phase, cwd)
    if reason is not None:
        _debug_log(payload, decision="block", role=resolve_agent_role(payload),
                   reason=f"事前条件未充足({current_phase}→{new_phase}): {reason}")
        print(
            f"[state_guard] BLOCKED: フェーズ移行(phase: {current_phase} → {new_phase})の事前条件を満たしていません。\n"
            f"理由: {reason}。\n"
            f"内部審査(ゲート承認)→ 客先提示(ご承認)→ 必要書類の整備 を完了してから移行してください。\n"
            f"(internal_approval_first ゲートでは、phase を進めるのは客先のご承認 APPROVED 時です。)",
            file=sys.stderr,
        )
        return 2

    # (A) 権限: phase を変えられるのは PMO のみ。
    agent_name = resolve_agent_role(payload)
    if agent_name == PMO_ROLE:
        _debug_log(payload, decision="allow", role=agent_name,
                   reason=f"PMO によるフェーズ移行({current_phase}→{new_phase})")
        return 0

    _debug_log(payload, decision="block", role=agent_name,
               reason=f"PMO 以外のフェーズ移行({current_phase}→{new_phase})")
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
