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


_HOOK = "ringi_guard"


def _strip_html_comments(text: str) -> str:
    """HTML コメント(テンプレの記入例など)を除去する。改訂対象パスの誤検出を防ぐ。"""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def _parse_cr_types(fm_block: str) -> set[str]:
    """frontmatter から変更種別 (type) を集合で取り出す。

    type は単一の予想値ではなく、改訂対象から導出される複数可の従属情報。
    以下の表記をすべて受理する:
      - 単一:        type: design
      - 列挙:        type: requirement, design
      - 角括弧:      type: [requirement, design]
      - YAMLリスト:  type:\\n  - requirement\\n  - design
    プレースホルダ 'a | b | c'(未記入の選択肢列挙)は実値でないため除外する。
    """
    types: set[str] = set()
    lines = fm_block.splitlines()
    for idx, line in enumerate(lines):
        if line.strip().startswith("type:"):
            val = line.split(":", 1)[1].strip()
            if val:
                for part in val.strip("[]").split(","):
                    part = part.strip().strip("'\"")
                    if part and "|" not in part:
                        types.add(part)
            for nxt in lines[idx + 1:]:
                s = nxt.strip()
                if s.startswith("- "):
                    item = s[2:].strip().strip("'\"")
                    if item:
                        types.add(item)
                elif s == "" or s.startswith("#"):
                    continue
                else:
                    break
            break
    return types


def _debug_log(payload: dict, *, decision: str, role: str | None = None, reason: str = "") -> None:
    """JTBC_HOOK_DEBUG 設定時のみ、判定結果を .jtbc/hook_debug.log に1行記録する(調査用)。

    どのフックが・どの役職(正準短名)で・何のツールでどのパスを・なぜ allow/block したかを残す。
    対象外の早期 return(file_path 無し / state 無し / スコープ外)では呼ばず、ノイズを抑える。
    """
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

    # 編集対象ドキュメント(cr_type)を改訂するために、CR の type が含んでいなければ
    # ならない変更種別。改訂対象パスから機械的に定まる(= 起票時に人が予想した type に
    # 依存せず、対象パスを正本とする)。proposal はキーを持たない = CR では解錠しない
    # (初版起案者・承認者のみが書ける)。
    REQUIRED_CR_TYPE = {
        "requirement": "requirement",
        "design_basic": "design",
        "design_detailed": "design",
    }

    phase = state.get("phase")
    for cr_type, (pattern, drafting_phase, drafter_roles, approver_roles) in DOC_PATTERNS.items():
        if re.search(pattern, relative):
            if phase == drafting_phase and agent_name in drafter_roles:
                _debug_log(payload, decision="allow", role=agent_name,
                           reason=f"{cr_type} 起案者の初版({drafting_phase})")
                return 0
            if agent_name in approver_roles:
                _debug_log(payload, decision="allow", role=agent_name,
                           reason=f"{cr_type} 承認者の押印・赤入れ")
                return 0
            approved_dir = cwd / ".jtbc" / "changes" / "approved"
            required_type = REQUIRED_CR_TYPE.get(cr_type)
            approved_for_target = False
            # 改訂対象に挙げてはいるが、type が当該ベースラインを覆っていない承認済み CR。
            # 「承認は通ったのに必要文書が解錠されない」無言の手詰まりを避けるため名指しする。
            type_short_crs: list[str] = []
            if required_type is not None and approved_dir.exists():
                for cr_file in sorted(approved_dir.glob("CR-*.md")):
                    text = cr_file.read_text(errors="ignore")
                    # フロントマター(最初の --- と次の --- の間)を簡易パース
                    fm_status = None
                    fm_block = ""
                    body_after_fm = text
                    if text.startswith("---"):
                        end_idx = text.find("---", 3)
                        if end_idx != -1:
                            fm_block = text[3:end_idx]
                            body_after_fm = text[end_idx + 3:]
                            for line in fm_block.splitlines():
                                key, _, val = line.partition(":")
                                if key.strip() == "status":
                                    fm_status = val.strip()
                    declared_types = _parse_cr_types(fm_block)
                    # 改訂対象パスは本文(記入例コメント除去後)を正本とする。
                    path_listed = relative in _strip_html_comments(body_after_fm)
                    if fm_status == "APPROVED" and path_listed:
                        if required_type in declared_types:
                            approved_for_target = True
                            break
                        type_short_crs.append(cr_file.stem)
            if approved_for_target:
                _debug_log(payload, decision="allow", role=agent_name,
                           reason=f"{cr_type} 承認済み稟議で許可")
                return 0
            _debug_log(payload, decision="block", role=agent_name,
                       reason=f"{cr_type} 稟議未承認(phase={phase})")
            if type_short_crs:
                hint = (
                    f"承認済み CR ({', '.join(type_short_crs)}) はこの文書を改訂対象に\n"
                    f"挙げていますが、その type に必要な変更種別 '{required_type}' が含まれていません。\n"
                    f"type は改訂対象から導出される従属情報です。'{required_type}' を加えて再承認してください。"
                )
            elif required_type is not None:
                hint = (
                    f"この文書を改訂対象に挙げ、変更種別 '{required_type}' を含む\n"
                    f"承認済み(APPROVED)の変更管理票が必要です。"
                )
            else:
                hint = "この文書は変更管理票では解錠されません(初版起案者・承認者のみが書けます)。"
            print(
                f"[ringi_guard] BLOCKED: '{relative}' の変更には稟議承認が必要です。\n"
                f"{hint}\n"
                f"変更管理(稟議)は司令塔が社内で自動処理します(governance スキル)。",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
