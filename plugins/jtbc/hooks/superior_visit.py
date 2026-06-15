#!/usr/bin/env python3
"""
superior_visit.py — JTBC UserPromptSubmit hook

部長・社長の「予告なし上長視察」をランダムに発生させる。
発火すると stdout に視察イベントの説明テキストを出力し、
それが Claude の文脈として渡される(非ブロッキング)。

発火確率:
  社長: 0.005 (0.5%)
  部長: 0.03  (3.0%) — 社長が外れた場合のみ判定
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

PROB_SHACHO = 0.005
PROB_BUCHO = 0.03

MSG_BUCHO = (
    "[上長視察] 部長が予告なく現場に現れました(稀イベント)。"
    "課長以下はいつもより緊張し、体裁を整えた報告を行うこと。"
    "部長は雑談まじりに遂行状況を探り、思いつきのアドバイスを残すことがある"
    "(社長の思いつきは部長が受けて課長へ正式に下ろす)。"
    "視察は短時間で終わり、平常運転に戻る。"
)

MSG_SHACHO = (
    "[上長視察] ごく稀なことですが、社長が突然現場に現れました(極めて稀なイベント)。"
    "全員が普段以上に緊張し、最大限に体裁を整えた報告を行うこと。"
    "社長は鋭い質問と大局的な観点から遂行状況を確認し、"
    "現場の雰囲気を一変させる思いつきの指示を残すことがある。"
    "この指示は後ほど部長から課長へ正式に展開される。"
    "視察は短時間で終わるが、その余韻はしばらく続く。"
)


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
        state = json.loads(state_path.read_text())
    except json.JSONDecodeError:
        return 0

    # プロジェクト完了済みなら視察しない
    if state.get("phase") == "COMPLETED":
        return 0

    # 緊急対応中は視察しない
    if state.get("active_incidents"):
        return 0

    # 乱数発火判定: 社長を先に判定し、外れたら部長を判定
    r = random.random()
    if r < PROB_SHACHO:
        print(MSG_SHACHO)
    elif r < PROB_SHACHO + PROB_BUCHO:
        print(MSG_BUCHO)

    return 0


if __name__ == "__main__":
    sys.exit(main())
