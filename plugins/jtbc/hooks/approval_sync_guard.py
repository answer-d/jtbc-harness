#!/usr/bin/env python3
"""
approval_sync_guard.py — JTBC UserPromptSubmit hook

gate 記録(.jtbc/gates/<gate>_gate.md)に承認印(🔴・実日付)が押されているのに、
承認の正本である state.json#approvals へ転記されていない「転記漏れ」を検出し、
リード(司令塔)/PMO へ転記を促す(非ブロッキング。stdout が文脈として渡る)。

背景: 承認者役職(部長/社長/課長)は gate 記録 .md へ 🔴 を押すだけで、
state.json は直接書けない(role_guard が物理ブロック=設計どおり)。押印結果を
state.json#approvals へ転記するのはリード/PMO の役目。この転記が抜けると、
ゲートが承認済みに見えてフェーズ移行(state_guard)の事前条件を満たせない。
governance/SKILL.md に文言はあるが司令塔が一発実行に退化して飛ばす実績があるため、
プロンプトではなくフックで検出する。

判定:
  gates/*_gate.md の各行で「🔴 を含み・(jtbc-<role>) があり・実日付(YYYY-MM-DD 雛形でない)
  があり・[ ] 未チェックでない」行を押印済みとみなし、role を抽出。
  state.json#approvals[<gate_stem>][<role>] == "approved" でなければ転記漏れ。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

STAMP_ROLE_RE = re.compile(r"\(jtbc-([a-z]+)\)")
REAL_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def stamped_roles(text: str) -> dict[str, str]:
    """gate 記録本文から {役職キー: 押印日} を抽出(押印済みのみ)。"""
    found: dict[str, str] = {}
    for line in text.splitlines():
        if "🔴" not in line:
            continue
        if "[ ]" in line:  # 明示的に未チェック=未押印
            continue
        m_role = STAMP_ROLE_RE.search(line)
        m_date = REAL_DATE_RE.search(line)
        if not m_role or not m_date:  # 実日付が無い=YYYY-MM-DD 雛形=未押印
            continue
        found[m_role.group(1)] = m_date.group(1)
    return found


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    cwd = Path(payload.get("cwd", "."))
    jtbc = cwd / ".jtbc"
    state_path = jtbc / "state.json"
    gates_dir = jtbc / "gates"
    if not state_path.exists() or not gates_dir.is_dir():
        return 0

    try:
        state = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
        return 0

    approvals = state.get("approvals") or {}
    pending: list[str] = []

    for gate_file in sorted(gates_dir.glob("*_gate.md")):
        gate_key = gate_file.stem  # 例: proposal_gate
        try:
            text = gate_file.read_text()
        except OSError:
            continue
        recorded = approvals.get(gate_key) or {}
        for role, date in stamped_roles(text).items():
            if recorded.get(role) != "approved":
                pending.append(f"  - {gate_key}: {role} が {date} に押印済み → approvals 未転記")

    if not pending:
        return 0

    print(
        "[承認転記リマインド] gate 記録に押印済みだが state.json#approvals へ未転記の承認があります:\n"
        + "\n".join(pending)
        + "\nこの転記はリード(司令塔)/PMO の責務です(承認者役職は state.json を直接書きません)。"
        " リード/PMO は該当する state.json#approvals[\"<gate>\"][\"<role>\"]=\"approved\" を記録してください。"
        " 転記が完了するまでフェーズ移行(state_guard)の事前条件は満たされません。"
        "\n(あなたが承認者役職=部長/社長/課長の場合は、この転記を自分で行わないでください"
        "=role_guard で物理ブロックされます。リードへ報告済みなら追加対応は不要です。)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
