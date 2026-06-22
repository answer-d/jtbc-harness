#!/usr/bin/env python3
"""
meeting_orchestrator.py — JTBC UserPromptSubmit hook (通知のみ・決定論トリガ)

会議体(meetings スキル)はモデル判断任せだと省略されがちなので、決定論的な
発火契機を司令塔(メインセッション=営業)へ与える。2つの役割を持つ:

(A) フェーズ開始の作戦会議: state.json#phase が前回観測時から変わっていたら、
    その新フェーズの当該役職(PMO を除く ◎/○)を集めた **作戦会議** を開くよう促す。
(B) 定例のターンカウンタ: ユーザー往復が一定数(TICK_EVERY)に達するごとに、
    config/jtbc.yaml#events.recurring の定例を開催し議事録を残すよう促す。

設計思想:
- superior_visit.py と同じく UserPromptSubmit で stdout に出力し、それが司令塔の
  文脈として渡る(非ブロッキング・常に exit 0)。発火するのはメインセッション側のみ。
- 観測状態は .jtbc/.meeting_orchestrator.json(サイドカー)に保持する。state.json は
  汚さない(承認・フェーズの正本を会議トリガで触らないため)。
- 完了(COMPLETED)・緊急対応中(active_incidents 非空)は会議を促さない。

入力: stdin に Claude Code の UserPromptSubmit ペイロード JSON
出力: 常に exit 0(促すときのみ stdout にメッセージ)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 定例を促す間隔(ユーザー往復数)。
TICK_EVERY = 8

# フェーズ開始時に作戦会議を促すフェーズと、集める当該役職(PMO は除く)。
# governance「フェーズと役職 アクティブマトリクス」の ◎(主担当)/○(副担当)に対応。
KICKOFF_PHASES: dict[str, list[str]] = {
    "REQUIREMENTS":    ["kacho", "shunin"],
    "BASIC_DESIGN":    ["kacho", "shunin"],
    "DETAILED_DESIGN": ["shunin", "kacho"],
    "IMPLEMENTATION":  ["tantou", "shunin"],
}

ROLE_JA = {
    "shacho": "社長", "bucho": "部長", "kacho": "課長",
    "shunin": "主任", "tantou": "担当", "pmo": "PMO",
}


def _load_sidecar(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_sidecar(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    cwd = Path(payload.get("cwd", "."))
    state_path = cwd / ".jtbc" / "state.json"
    if not state_path.exists():
        return 0
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0

    phase = state.get("phase")
    # 完了済み or 緊急対応中は会議を促さない(緊急時は incident-response が最優先)。
    if phase == "COMPLETED" or state.get("active_incidents"):
        return 0

    sidecar = cwd / ".jtbc" / ".meeting_orchestrator.json"
    data = _load_sidecar(sidecar)
    msgs: list[str] = []

    # (A) フェーズ開始の作戦会議
    if data.get("last_kickoff_phase") != phase and phase in KICKOFF_PHASES:
        members = KICKOFF_PHASES[phase]
        names = " / ".join(ROLE_JA.get(r, r) for r in members)
        msgs.append(
            f"[会議トリガ] phase={phase} に入りました。**フェーズ作戦会議**(社内・内部)を開いてください。\n"
            f"  招集(PMO は除く): {names}({', '.join(members)})。ファシリは当該フェーズの主担当(先頭)。\n"
            f"  狙い: このフェーズの段取り・役割分担・想定リスク・完了条件の目線合わせ。\n"
            f"  終わったら議事録を .jtbc/minutes/MTG-NNN_kickoff.md に残すこと(meetings スキル)。"
        )
        data["last_kickoff_phase"] = phase

    # (B) 定例のターンカウンタ
    turns = int(data.get("turns", 0)) + 1
    data["turns"] = turns
    if turns % TICK_EVERY == 0:
        msgs.append(
            f"[会議トリガ] 定例の時間です(往復 {turns} 回到達)。config/jtbc.yaml#events.recurring を確認し、\n"
            f"  現フェーズで開くべき定例(内部定例/状況報告定例 等)を開催してください。状況報告定例では\n"
            f"  リスク登録簿・課題管理簿のレビューを行い、議事録を .jtbc/minutes/ に残すこと(meetings スキル)。"
        )

    _save_sidecar(sidecar, data)

    if msgs:
        print("\n".join(msgs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
