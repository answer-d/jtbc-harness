#!/usr/bin/env python3
"""
ringi_consistency.py — JTBC PreToolUse hook

変更管理票 (CR) の「変更種別 (type)」が、本文に列挙した改訂対象ドキュメントを
漏れなく覆っているかを、起票 (Write) の時点で機械検証する。

背景:
- ringi_guard は「改訂対象パス(具体)」を正本として文書改訂を解錠するが、承認経路は
  frontmatter の type で決まる。type は起票者の予想であり、間違い/不足があると
  「承認は通ったのに必要文書が解錠されない」無言の手詰まりや、承認経路の過小化を招く。
- そこで type は改訂対象パスから導出される従属情報とみなし、ガードされた文書を
  改訂対象に挙げているのに対応する種別が type に無ければ、起票そのものを止める
  (= 予想ミスを起票時点で大声で弾く)。

挙動:
- 対象は .jtbc/changes/ 配下の CR-*.md への Write のみ(全文が得られるため)。
  Edit/MultiEdit は部分差分で全文が不明なためスキップ(解錠時に ringi_guard が最終防衛)。
- HTML コメント(テンプレの記入例)は除去してから判定する。
"""
from __future__ import annotations

import json
import re
import sys

# 改訂対象パス(部分一致) → それを改訂するのに CR の type が含むべき変更種別。
# ringi_guard の REQUIRED_CR_TYPE / DOC_PATTERNS と対応させること。
PATH_REQUIRES_TYPE = [
    (re.compile(r"\.jtbc/requirements/"), "requirement"),
    (re.compile(r"\.jtbc/designs/basic_design"), "design"),
    (re.compile(r"\.jtbc/designs/detailed_design"), "design"),
]


def _strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def _parse_cr_types(fm_block: str) -> set[str]:
    """frontmatter の type を集合で取り出す(ringi_guard._parse_cr_types と同仕様)。"""
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


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    if payload.get("tool_name") != "Write":
        return 0
    tool_input = payload.get("tool_input", {})
    file_path = str(tool_input.get("file_path") or tool_input.get("path") or "")
    content = tool_input.get("content")
    if content is None:
        return 0
    if not re.search(r"\.jtbc/changes/.*CR-.*\.md$", file_path):
        return 0

    # frontmatter と本文を分離
    fm_block = ""
    body = content
    if content.startswith("---"):
        end_idx = content.find("---", 3)
        if end_idx != -1:
            fm_block = content[3:end_idx]
            body = content[end_idx + 3:]

    declared = _parse_cr_types(fm_block)
    body_wo_comments = _strip_html_comments(body)

    missing: dict[str, str] = {}  # 不足種別 -> 代表となる対象行
    for pattern, req_type in PATH_REQUIRES_TYPE:
        if pattern.search(body_wo_comments) and req_type not in declared:
            sample = next(
                (l.strip() for l in body_wo_comments.splitlines() if pattern.search(l)),
                pattern.pattern,
            )
            missing.setdefault(req_type, sample)

    if missing:
        detail = "\n".join(f"  - 種別 '{t}' (対象: {p})" for t, p in missing.items())
        print(
            "[ringi_consistency] BLOCKED: 変更管理票の type が改訂対象を覆っていません。\n"
            "改訂対象に次のドキュメントを挙げていますが、対応する変更種別が type にありません:\n"
            f"{detail}\n"
            "type は改訂対象ドキュメントから導出される従属情報です。"
            "不足種別を type(複数可・例 'type: [requirement, design]')へ追加してください。",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
