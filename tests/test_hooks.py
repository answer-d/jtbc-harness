"""層1: フック単体テスト(table-driven)。

各フックの「stdin JSON → exit 0/2」契約を、実プロセスと同じ経路(サブプロセス)で検証する。
stderr は壊れやすい完全一致を避け、フック名タグの部分一致で確認する。
"""
from __future__ import annotations

import json

import pytest

# ---------------------------------------------------------------------------
# team_guard: 一発実行ブロック / 二重起動ブロック
# ---------------------------------------------------------------------------

SID = "abcd1234-0000-0000-0000-000000000000"


def _member(name: str, agent_type: str, active: bool = False) -> dict:
    return {"name": name, "agentType": agent_type, "isActive": active}


def test_team_guard_blocks_oneshot(teams_config):
    env = teams_config(SID, [_member("team-lead", "team-lead")])
    r = run_team(
        {"tool_name": "Agent", "session_id": SID,
         "tool_input": {"agentType": "jtbc:jtbc-kacho"}},
        env,
    )
    assert r.blocked
    assert "[team_guard]" in r.stderr
    assert "一発実行" in r.stderr


def test_team_guard_blocks_duplicate_resident(teams_config):
    env = teams_config(SID, [
        _member("team-lead", "team-lead"),
        _member("bucho", "jtbc:jtbc-bucho", active=True),
    ])
    r = run_team(
        {"tool_name": "Agent", "session_id": SID,
         "tool_input": {"agentType": "jtbc:jtbc-bucho", "name": "bucho-2",
                        "run_in_background": True}},
        env,
    )
    assert r.blocked
    assert "既に在席" in r.stderr
    assert "bucho" in r.stderr


def test_team_guard_blocks_duplicate_even_when_idle(teams_config):
    """idle(isActive:false)でも「在席」とみなして二重起動を阻止する(本修正の核)。"""
    env = teams_config(SID, [
        _member("team-lead", "team-lead"),
        _member("pmo", "jtbc:jtbc-pmo", active=False),
    ])
    r = run_team(
        {"tool_name": "Agent", "session_id": SID,
         "tool_input": {"agentType": "jtbc:jtbc-pmo", "name": "pmo-2",
                        "run_in_background": True}},
        env,
    )
    assert r.blocked
    assert "pmo" in r.stderr


def test_team_guard_allows_first_resident(teams_config):
    env = teams_config(SID, [
        _member("team-lead", "team-lead"),
        _member("bucho", "jtbc:jtbc-bucho", active=True),
    ])
    r = run_team(
        {"tool_name": "Agent", "session_id": SID,
         "tool_input": {"agentType": "jtbc:jtbc-tantou", "name": "tantou",
                        "run_in_background": True}},
        env,
    )
    assert r.passed


def test_team_guard_allows_non_jtbc(teams_config):
    env = teams_config(SID, [_member("team-lead", "team-lead")])
    r = run_team(
        {"tool_name": "Agent", "session_id": SID,
         "tool_input": {"agentType": "general-purpose", "run_in_background": True}},
        env,
    )
    assert r.passed


def test_team_guard_passes_when_teams_disabled(teams_config):
    # config はあっても teams 無効なら素通り(env から teams フラグを除く)
    env = teams_config(SID, [_member("bucho", "jtbc:jtbc-bucho")])
    env.pop("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS")
    r = run_team(
        {"tool_name": "Agent", "session_id": SID,
         "tool_input": {"agentType": "jtbc:jtbc-bucho", "name": "bucho-2",
                        "run_in_background": True}},
        env,
    )
    assert r.passed


def test_team_guard_passes_unknown_session(teams_config):
    """config が見つからない(初回 spawn 相当)なら阻止しない。"""
    env = teams_config(SID, [_member("bucho", "jtbc:jtbc-bucho")])
    r = run_team(
        {"tool_name": "Agent", "session_id": "zzzz9999-no-such-session",
         "tool_input": {"agentType": "jtbc:jtbc-bucho", "name": "bucho",
                        "run_in_background": True}},
        env,
    )
    assert r.passed


# team_guard は run_hook を直接使う(project fixture 不要)
def run_team(payload, env):
    from conftest import run_hook
    return run_hook("team_guard", payload, env=env)


# ---------------------------------------------------------------------------
# role_guard: 役職ごとの許可/禁止パス
# ---------------------------------------------------------------------------

def test_role_guard_denies_explicit_path(project):
    from conftest import run_hook
    p = project()
    payload = p.payload(agent_type="jtbc:jtbc-pmo", tool_name="Write",
                        tool_input={"file_path": ".jtbc/requirements/requirements.md"})
    r = run_hook("role_guard", payload)
    assert r.blocked and "[role_guard]" in r.stderr


def test_role_guard_denies_outside_allowlist(project):
    from conftest import run_hook
    p = project()
    # bucho は許可リストにあるパスのみ。.jtbc/designs/ は許可外
    payload = p.payload(agent_type="jtbc:jtbc-bucho", tool_name="Write",
                        tool_input={"file_path": ".jtbc/designs/basic_design.md"})
    r = run_hook("role_guard", payload)
    assert r.blocked


def test_role_guard_allows_permitted_path(project):
    from conftest import run_hook
    p = project()
    payload = p.payload(agent_type="jtbc:jtbc-kacho", tool_name="Write",
                        tool_input={"file_path": ".jtbc/requirements/requirements.md"})
    r = run_hook("role_guard", payload)
    assert r.passed


def test_role_guard_passes_main_session(project):
    """司令塔(agent_type なし)は素通り。"""
    from conftest import run_hook
    p = project()
    payload = p.payload(tool_name="Write",
                        tool_input={"file_path": ".jtbc/requirements/requirements.md"})
    r = run_hook("role_guard", payload)
    assert r.passed


def test_role_guard_implementer_needs_active_wbs(project):
    from conftest import run_hook
    p = project(active_wbs_task=None)
    payload = p.payload(agent_type="jtbc:jtbc-tantou", tool_name="Write",
                        tool_input={"file_path": "src/main.py"})
    r = run_hook("role_guard", payload)
    assert r.blocked and "WBS" in r.stderr


def test_role_guard_implementer_with_active_wbs(project):
    from conftest import run_hook
    p = project(active_wbs_task="T-001")
    payload = p.payload(agent_type="jtbc:jtbc-tantou", tool_name="Write",
                        tool_input={"file_path": "src/main.py"})
    r = run_hook("role_guard", payload)
    assert r.passed


# ---------------------------------------------------------------------------
# phase_guard: フェーズに応じたソースコード書込み可否
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phase,path,expect_block", [
    ("REQUIREMENTS", "src/main.py", True),
    ("BASIC_DESIGN", "lib/x.py", True),
    ("IMPLEMENTATION", "src/main.py", False),
    ("UNIT_TEST", "src/main.py", False),
    ("INTEGRATION_TEST", "app/x.py", False),
    ("REQUIREMENTS", ".jtbc/requirements/requirements.md", False),  # 非コードは対象外
])
def test_phase_guard_src_writes(project, phase, path, expect_block):
    from conftest import run_hook
    p = project(phase=phase)
    payload = p.payload(tool_name="Write", tool_input={"file_path": path})
    r = run_hook("phase_guard", payload)
    assert r.blocked == expect_block


# ---------------------------------------------------------------------------
# incident_guard: 緊急対応中の前進系文書編集の停止
# ---------------------------------------------------------------------------

def test_incident_guard_blocks_forward_doc(project):
    from conftest import run_hook
    p = project(active_incidents=["INC-001"])
    payload = p.payload(tool_name="Write",
                        tool_input={"file_path": ".jtbc/requirements/requirements.md"})
    r = run_hook("incident_guard", payload)
    assert r.blocked and "[incident_guard]" in r.stderr


def test_incident_guard_allows_src_during_incident(project):
    from conftest import run_hook
    p = project(active_incidents=["INC-001"])
    payload = p.payload(tool_name="Write", tool_input={"file_path": "src/fix.py"})
    r = run_hook("incident_guard", payload)
    assert r.passed


def test_incident_guard_passes_without_incident(project):
    from conftest import run_hook
    p = project(active_incidents=[])
    payload = p.payload(tool_name="Write",
                        tool_input={"file_path": ".jtbc/designs/basic_design.md"})
    r = run_hook("incident_guard", payload)
    assert r.passed


# ---------------------------------------------------------------------------
# ringi_guard: 稟議なし改訂の阻止
# ---------------------------------------------------------------------------

def test_ringi_guard_allows_drafter_in_drafting_phase(project):
    from conftest import run_hook
    p = project(phase="REQUIREMENTS")
    payload = p.payload(agent_type="jtbc:jtbc-kacho", tool_name="Write",
                        tool_input={"file_path": ".jtbc/requirements/requirements.md"})
    r = run_hook("ringi_guard", payload)
    assert r.passed


def test_ringi_guard_blocks_revision_without_cr(project):
    from conftest import run_hook
    # 要件起案フェーズ外(BASIC_DESIGN)で要件を触る = 改訂 → 稟議が要る
    p = project(phase="BASIC_DESIGN")
    payload = p.payload(agent_type="jtbc:jtbc-kacho", tool_name="Edit",
                        tool_input={"file_path": ".jtbc/requirements/requirements.md"})
    r = run_hook("ringi_guard", payload)
    assert r.blocked and "[ringi_guard]" in r.stderr


def test_ringi_guard_allows_with_approved_cr(project):
    from conftest import run_hook
    p = project(phase="BASIC_DESIGN")
    cr = (
        "---\n"
        "status: APPROVED\n"
        "type: requirement\n"
        "---\n"
        "対象: .jtbc/requirements/requirements.md\n"
    )
    p.write_doc(".jtbc/changes/approved/CR-001.md", cr)
    payload = p.payload(agent_type="jtbc:jtbc-kacho", tool_name="Edit",
                        tool_input={"file_path": ".jtbc/requirements/requirements.md"})
    r = run_hook("ringi_guard", payload)
    assert r.passed


def test_ringi_guard_allows_approver_to_stamp(project):
    from conftest import run_hook
    # 承認者(bucho)は稟議なしで提案書へ承認印を押せる
    p = project(phase="PROPOSAL")
    payload = p.payload(agent_type="jtbc:jtbc-bucho", tool_name="Edit",
                        tool_input={"file_path": ".jtbc/proposal/proposal.md"})
    r = run_hook("ringi_guard", payload)
    assert r.passed


def test_ringi_guard_blocks_non_approver_revision(project):
    from conftest import run_hook
    # 主任(shunin)は提案書の承認者ではないのでブロックされる
    p = project(phase="PROPOSAL")
    payload = p.payload(agent_type="jtbc:jtbc-shunin", tool_name="Edit",
                        tool_input={"file_path": ".jtbc/proposal/proposal.md"})
    r = run_hook("ringi_guard", payload)
    assert r.blocked and "[ringi_guard]" in r.stderr


# ---------------------------------------------------------------------------
# state_guard: フェーズ移行の権限(PMO限定)+ 事前条件
# ---------------------------------------------------------------------------

def _proposal_ready_state(phase="PROPOSAL"):
    return {
        "mode": "jtbc", "phase": phase, "active_incidents": [], "active_wbs_task": None,
        "approvals": {"proposal_gate": {"bucho": "approved", "shacho": "approved"}},
        "client_reviews": {"proposal": {"status": "APPROVED"}},
    }


def test_state_guard_allows_pmo_when_preconditions_met(project):
    from conftest import run_hook
    p = project(**_proposal_ready_state())
    p.write_doc(".jtbc/proposal/proposal.md", "# 提案書\n実内容あり")
    new_state = _proposal_ready_state(phase="REQUIREMENTS")
    payload = p.payload(agent_type="jtbc:jtbc-pmo", tool_name="Write",
                        tool_input={"file_path": ".jtbc/state.json",
                                    "content": json.dumps(new_state, ensure_ascii=False)})
    r = run_hook("state_guard", payload)
    assert r.passed, r.stderr


def test_state_guard_blocks_non_pmo(project):
    from conftest import run_hook
    p = project(**_proposal_ready_state())
    p.write_doc(".jtbc/proposal/proposal.md", "# 提案書\n実内容あり")
    new_state = _proposal_ready_state(phase="REQUIREMENTS")
    payload = p.payload(agent_type="jtbc:jtbc-kacho", tool_name="Write",
                        tool_input={"file_path": ".jtbc/state.json",
                                    "content": json.dumps(new_state, ensure_ascii=False)})
    r = run_hook("state_guard", payload)
    assert r.blocked and "PMO" in r.stderr


def test_state_guard_blocks_when_preconditions_unmet(project):
    """承認が欠ける移行は PMO でも阻止(審査スキップの物理防止)。"""
    from conftest import run_hook
    bare = {"mode": "jtbc", "phase": "PROPOSAL", "active_incidents": [],
            "approvals": {}, "client_reviews": {}}
    p = project(**bare)
    new_state = dict(bare, phase="REQUIREMENTS")
    payload = p.payload(agent_type="jtbc:jtbc-pmo", tool_name="Write",
                        tool_input={"file_path": ".jtbc/state.json",
                                    "content": json.dumps(new_state, ensure_ascii=False)})
    r = run_hook("state_guard", payload)
    assert r.blocked and "事前条件" in r.stderr


def test_state_guard_passes_non_phase_update(project):
    """phase を変えない state.json 更新(approvals 追記等)は素通り。"""
    from conftest import run_hook
    p = project(**_proposal_ready_state())
    same = _proposal_ready_state(phase="PROPOSAL")
    payload = p.payload(agent_type="jtbc:jtbc-kacho", tool_name="Write",
                        tool_input={"file_path": ".jtbc/state.json",
                                    "content": json.dumps(same, ensure_ascii=False)})
    r = run_hook("state_guard", payload)
    assert r.passed


# ---------------------------------------------------------------------------
# approval_sync_guard: gate 記録の押印 → state.json#approvals 転記漏れ検出
# (UserPromptSubmit・非ブロッキング。検出時のみ stdout にリマインドを出す)
# ---------------------------------------------------------------------------

_STAMPED_GATE = (
    "## 承認パス\n"
    "### 部長 (jtbc-bucho) — 承認済み\n"
    "[x] 🔴 承認  部長  (jtbc-bucho)  2026-06-19\n"
    "### 社長 (jtbc-shacho) — 承認待ち\n"
    "[ ] 🔴 承認  社長  (jtbc-shacho)  YYYY-MM-DD\n"
)


def test_approval_sync_detects_untranscribed(project):
    """gate に押印済みだが approvals 未転記 → リマインドを stdout に出す。"""
    from conftest import run_hook
    p = project(phase="PROPOSAL", approvals={})
    p.write_doc(".jtbc/gates/proposal_gate.md", _STAMPED_GATE)
    r = run_hook("approval_sync_guard", p.payload())
    assert r.passed  # 非ブロッキング
    assert "承認転記リマインド" in r.stdout
    assert "proposal_gate" in r.stdout and "bucho" in r.stdout
    # 未押印(YYYY-MM-DD 雛形)の社長は通知対象にしない
    assert "shacho" not in r.stdout


def test_approval_sync_quiet_when_transcribed(project):
    """押印が approvals へ転記済みなら何も出さない。"""
    from conftest import run_hook
    p = project(phase="PROPOSAL", approvals={"proposal_gate": {"bucho": "approved"}})
    p.write_doc(".jtbc/gates/proposal_gate.md", _STAMPED_GATE)
    r = run_hook("approval_sync_guard", p.payload())
    assert r.passed and r.stdout.strip() == ""


def test_approval_sync_ignores_placeholder_only(project):
    """雛形(YYYY-MM-DD)のみで実押印が無ければ通知しない。"""
    from conftest import run_hook
    placeholder = (
        "[ ] 🔴 承認  部長  (jtbc-bucho)  YYYY-MM-DD\n"
        "[ ] 🔴 承認  社長  (jtbc-shacho)  YYYY-MM-DD\n"
    )
    p = project(phase="PROPOSAL", approvals={})
    p.write_doc(".jtbc/gates/proposal_gate.md", placeholder)
    r = run_hook("approval_sync_guard", p.payload())
    assert r.passed and r.stdout.strip() == ""


def test_approval_sync_passes_without_gates(project):
    """gates/ が無ければ素通り(非 JTBC・初期状態)。"""
    from conftest import run_hook
    p = project(phase="PROPOSAL", approvals={})
    r = run_hook("approval_sync_guard", p.payload())
    assert r.passed and r.stdout.strip() == ""
