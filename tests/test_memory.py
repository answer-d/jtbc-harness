"""役職メモ(.jtbc/memory/)まわりのフックのテスト。

- memory_grant: 自メモ allow / 他役職メモ deny / lead allow / 非メモ無関与
- memory_timeline: phase 変化で追記・同 phase は冪等
- role_guard: memory パスは素通り(memory_grant に委譲)
- memory_reminder: 知識役職がメモ未記録なら通知、記録済みなら静か
"""
from __future__ import annotations

import json

from conftest import run_hook


def _decision(result):
    """memory_grant の stdout JSON から permissionDecision を取り出す(無ければ None)。"""
    out = result.stdout.strip()
    if not out:
        return None
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


# --- memory_grant --------------------------------------------------------

def test_grant_allows_own_memory():
    r = run_hook("memory_grant", {
        "tool_name": "Write",
        "tool_input": {"file_path": ".jtbc/memory/kacho/lesson.md"},
        "agent_type": "jtbc:jtbc-kacho",
    })
    assert r.passed
    assert _decision(r) == "allow"


def test_grant_denies_other_role_memory():
    r = run_hook("memory_grant", {
        "tool_name": "Write",
        "tool_input": {"file_path": ".jtbc/memory/shunin/x.md"},
        "agent_type": "jtbc:jtbc-kacho",
    })
    assert _decision(r) == "deny"


def test_grant_allows_lead_memory():
    r = run_hook("memory_grant", {
        "tool_name": "Write",
        "tool_input": {"file_path": ".jtbc/memory/eigyo/x.md"},
    })
    assert _decision(r) == "allow"


def test_grant_ignores_non_memory_paths():
    r = run_hook("memory_grant", {
        "tool_name": "Write",
        "tool_input": {"file_path": ".jtbc/proposal/proposal.md"},
        "agent_type": "jtbc:jtbc-kacho",
    })
    assert r.passed
    assert _decision(r) is None  # decision を出さない


def test_grant_ignores_non_edit_tools():
    # Read 等 Edit|Write 以外のツールには関与しない
    r = run_hook("memory_grant", {
        "tool_name": "Read",
        "tool_input": {"file_path": ".jtbc/memory/kacho/a.md"},
        "agent_type": "jtbc:jtbc-kacho",
    })
    assert r.passed
    assert _decision(r) is None


def test_grant_allows_own_memory_via_multiedit():
    r = run_hook("memory_grant", {
        "tool_name": "MultiEdit",
        "tool_input": {"file_path": ".jtbc/memory/pmo/x.md"},
        "agent_type": "jtbc:jtbc-pmo",
    })
    assert _decision(r) == "allow"


# --- role_guard が memory を素通り ---------------------------------------

def test_role_guard_defers_memory():
    # 他役職メモでも role_guard 自体はブロックしない(判定は memory_grant)
    r = run_hook("role_guard", {
        "tool_name": "Write",
        "tool_input": {"file_path": ".jtbc/memory/shunin/x.md"},
        "agent_type": "jtbc:jtbc-kacho",
    })
    assert r.passed


# --- memory_timeline -----------------------------------------------------

def test_timeline_appends_on_phase_change(project):
    p = project(phase="PROPOSAL")
    payload = p.payload(
        tool_name="Write",
        tool_input={"file_path": ".jtbc/state.json"},
        agent_type="jtbc:jtbc-pmo",
    )
    run_hook("memory_timeline", payload)
    timeline = p.root / ".jtbc" / "memory" / "_timeline.md"
    assert timeline.exists()
    assert "phase=PROPOSAL" in timeline.read_text(encoding="utf-8")


def test_timeline_idempotent_same_phase(project):
    p = project(phase="PROPOSAL")
    payload = p.payload(
        tool_name="Write",
        tool_input={"file_path": ".jtbc/state.json"},
        agent_type="jtbc:jtbc-pmo",
    )
    run_hook("memory_timeline", payload)
    run_hook("memory_timeline", payload)
    timeline = (p.root / ".jtbc" / "memory" / "_timeline.md").read_text(encoding="utf-8")
    assert timeline.count("phase=") == 1


def test_timeline_noop_for_non_state_writes(project):
    # state.json 以外への書込みではタイムラインを作らない
    p = project(phase="PROPOSAL")
    run_hook("memory_timeline", p.payload(
        tool_name="Write",
        tool_input={"file_path": ".jtbc/proposal/proposal.md"},
        agent_type="jtbc:jtbc-kacho",
    ))
    assert not (p.root / ".jtbc" / "memory" / "_timeline.md").exists()


# --- memory_reminder -----------------------------------------------------

def test_reminder_notifies_when_empty(project):
    p = project()
    r = run_hook("memory_reminder", p.payload(agent_type="jtbc:jtbc-kacho"))
    assert r.passed
    assert "memory_reminder" in r.stderr


def test_reminder_silent_when_recorded(project):
    p = project()
    p.write_doc(".jtbc/memory/kacho/lesson.md", "# x")
    r = run_hook("memory_reminder", p.payload(agent_type="jtbc:jtbc-kacho"))
    assert r.passed
    assert r.stderr.strip() == ""


def test_reminder_silent_for_non_knowledge_role(project):
    # 実装のみの担当は知識生産役職でないので促さない
    p = project()
    r = run_hook("memory_reminder", p.payload(agent_type="jtbc:jtbc-tantou"))
    assert r.passed
    assert r.stderr.strip() == ""
