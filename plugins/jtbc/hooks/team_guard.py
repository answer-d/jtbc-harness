#!/usr/bin/env python3
"""
team_guard.py — JTBC PreToolUse hook

teams 有効環境で、役職(jtbc-*)の spawn 規律を物理的に担保する:
  (A) 一発実行(subagent_type のみ・コールドスタート→Done で消滅)を禁止し、常駐 teammate
      (run_in_background:true + name)へ誘導する。
  (B) 同じ役職の teammate を二重に spawn するのを禁止し、既存 teammate への SendMessage へ誘導する。

背景(実機で繰り返し観測):
- (A) 司令塔(lead)が「Teams 有効なのに subagent_type の一発実行に逃げる」退化が複数回起きた。
  役職が毎回記憶ゼロで起き、teammate 連携も起きない(= 実質サブエージェント運用に退化)。
- (B) 司令塔がフェーズをまたぐたびに「既存の常駐 teammate へ SendMessage する」のではなく、
  別 name(`bucho-2` / `pmo-2` 等)で run_in_background の2人目を起こしてしまう退化が起きた。
  これは (A) のチェックを run_in_background:true で素通りするため、別の物理ガードが要る。
- governance スキルに「一発実行禁止」「同じ役職を二重に spawn しない」と明記しても止まらず、
  プロンプト強化(v0.10.3 / v0.13.0)は無効だった。よって phase_guard / state_guard と同じ
  「物理強制」で既定を担保する。

設計思想(最小ロック):
- 縛るのは「teams 有効時に jtbc 役職を (A) 一発実行しない / (B) 二重起動しない」の二点のみ。
- teams 無効環境では一発実行は正当なフォールバックなので (A)(B) とも素通り。
- 二重判定は当該セッションの team config(`~/.claude/teams/session-*/config.json` のうち
  `leadSessionId` が payload の session_id と一致するもの)の `members[].agentType` を正とする。
  待機中(idle / isActive:false)の teammate も「在席」とみなす(idle は生存・再利用可)。

ルール:
- env CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS が "1"(=teams 有効)でなければ素通り。
- 対象ツールは subagent を起こす Task / Agent。
- tool_input の subagent_type(または agentType)が JTBC 役職(末尾が jtbc-*)であること。
- run_in_background が真でない(=一発実行)→ (A) で exit 2。
- run_in_background が真でも、同じ役職が既に team config に在席 → (B) で exit 2。

入力: stdin に Claude Code が JSON で {"tool_name":..., "tool_input":{...}, "session_id":..., ...}
出力: 続行なら exit 0、ブロックなら stderr にメッセージ + exit 2
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SPAWN_TOOLS = {"Task", "Agent"}


def _role_tail(subagent_type):
    """subagent_type を役職 tail に正規化(例 "jtbc:jtbc-kacho" → "jtbc-kacho")。"""
    if not subagent_type:
        return None
    return str(subagent_type).split(":")[-1].strip()


def _is_jtbc_role(subagent_type) -> bool:
    """subagent_type が JTBC 役職か(例 "jtbc:jtbc-kacho" / "jtbc-kacho")。"""
    tail = _role_tail(subagent_type)
    return bool(tail) and tail.startswith("jtbc-")


def _truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes")
    return bool(v)


def _config_root() -> Path:
    """Claude Code の config ルート。`CLAUDE_CONFIG_DIR` があれば尊重し、無ければ ~/.claude。

    Claude Code は config ルートの移設に `CLAUDE_CONFIG_DIR` を使う。これを尊重することで
    (a) ユーザーの config 移設に追従し、(b) テストは一時ディレクトリを指すだけで隔離できる。
    """
    override = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".claude"


def _find_team_config(session_id):
    """payload の session_id に対応する team config(dict)を返す。見つからなければ None。

    team dir は <config_root>/teams/session-<...>/config.json。config.json の leadSessionId が
    司令塔(lead)のセッション ID = spawn を呼ぶ側の session_id と一致するものを正とする。
    """
    if not session_id:
        return None
    teams_dir = _config_root() / "teams"
    if not teams_dir.is_dir():
        return None
    for cfg in teams_dir.glob("session-*/config.json"):
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("leadSessionId") == session_id:
            return data
    return None


def _existing_same_role(config, role_tail):
    """同じ役職(agentType の tail)で既に在席している teammate の name 一覧。"""
    names = []
    for member in (config.get("members") or []):
        agent_type = member.get("agentType")
        if _role_tail(agent_type) == role_tail:
            name = member.get("name")
            if name:
                names.append(name)
    return names


def main() -> int:
    # teams 無効環境は素通り(一発実行=正当なフォールバック)
    if os.environ.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "").strip() != "1":
        return 0

    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    if payload.get("tool_name") not in SPAWN_TOOLS:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    subagent_type = tool_input.get("subagent_type") or tool_input.get("agentType")
    if not _is_jtbc_role(subagent_type):
        return 0

    role = _role_tail(subagent_type)

    # (A) 一発実行(run_in_background が真でない)→ 常駐 teammate へ誘導
    if not _truthy(tool_input.get("run_in_background")):
        print(
            f"[team_guard] BLOCKED: teams 有効環境で役職 '{role}' を一発実行(subagent_type のみ)で\n"
            f"spawn しようとしました。役職は必ず常駐 teammate として起こしてください:\n"
            f'  Agent(subagent_type="{subagent_type}", name="<役職名>", run_in_background=true)\n'
            f"以降の指示は同じ teammate へ SendMessage で送り、当該フェーズのゲート通過まで生かしてください\n"
            f"(フェーズ単位ライフサイクル: フェーズ内は shutdown せず、ゲートで引き継ぎメモ → shutdown_request で畳む)。\n"
            f"(一発実行が許されるのは teams 無効環境のフォールバックのみ。"
            f"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 の現環境では使えません。)",
            file=sys.stderr,
        )
        return 2

    # (B) 常駐 spawn でも、同じ役職が既に team config に在席していれば二重起動を阻止
    config = _find_team_config(payload.get("session_id"))
    if config is not None:
        existing = _existing_same_role(config, role)
        if existing:
            names = " / ".join(existing)
            print(
                f"[team_guard] BLOCKED: 役職 '{role}' の teammate は既に在席しています(name: {names})。\n"
                f"同じ役職を二重に spawn しないでください。次工程の依頼は新しい teammate を起こさず、\n"
                f"既存の teammate へ SendMessage で送ってください:\n"
                f'  SendMessage(to="{existing[0]}", message="<依頼内容>")\n'
                f"待機中(idle / came to rest)の teammate も生存しており、SendMessage で再開できます\n"
                f"(idle を故障扱いしない)。常駐 teammate は記憶を保持しているため、毎回起こし直す必要は\n"
                f"ありません。\n"
                f"※ /resume 直後などで既存 teammate が応答しない(到達不能)場合に限り、その teammate を\n"
                f"  shutdown してから同名で再 spawn してください。",
                file=sys.stderr,
            )
            return 2

    # 同役職が未在席の常駐 spawn → 正常(遅延常駐の初回 spawn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
