"""層3: 静的整合性 lint。

LLM もフック実行も使わず、設定・コード・宣言の「ドリフト」を機械検出する。
最重要は config/jtbc.yaml#gates ↔ state_guard.py#TRANSITIONS の一致
(この二重定義は典型的なドリフト源)。
"""
from __future__ import annotations

import json
import py_compile
import re
import sys

import pytest

from conftest import HOOKS_DIR, PLUGIN_ROOT

sys.path.insert(0, str(HOOKS_DIR))
import state_guard  # noqa: E402


def _load_yaml():
    yaml = pytest.importorskip("yaml", reason="整合性テストには PyYAML が必要")
    with (PLUGIN_ROOT / "config" / "jtbc.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# 最重要: gates(yaml) ↔ TRANSITIONS(state_guard) の一致
# ---------------------------------------------------------------------------

def test_transitions_keys_match_gate_next_phases():
    cfg = _load_yaml()
    gate_next_phases = {g["next_phase"] for g in cfg["gates"].values()}
    assert set(state_guard.TRANSITIONS) == gate_next_phases


@pytest.mark.parametrize("gate_name", [
    "proposal", "project_plan", "basic_design", "detailed_design", "release", "completion",
])
def test_each_gate_matches_transition(gate_name):
    cfg = _load_yaml()
    gate = cfg["gates"][gate_name]
    spec = state_guard.TRANSITIONS[gate["next_phase"]]

    assert spec["gate"] == gate_name
    assert spec["approvers"] == gate["approvers"], "承認者がドリフトしている"
    assert spec["docs"] == gate["required_documents"], "必要書類がドリフトしている"

    # client_review: internal_approval_first のゲートのみ必須で、値はゲート名
    if gate.get("internal_approval_first"):
        assert spec["client_review"] == gate_name
    else:
        assert spec["client_review"] is None


def test_transition_docs_have_paths():
    """TRANSITIONS が参照する全 doc キーが DOC_PATHS に定義されているか。"""
    for spec in state_guard.TRANSITIONS.values():
        for key in spec["docs"]:
            assert key in state_guard.DOC_PATHS, f"DOC_PATHS に未定義: {key}"


# ---------------------------------------------------------------------------
# hooks.json ↔ 実ファイル
# ---------------------------------------------------------------------------

def _hooks_json():
    return json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))


def _referenced_hook_files():
    refs = set()
    for events in _hooks_json()["hooks"].values():
        for matcher in events:
            for hook in matcher["hooks"]:
                m = re.search(r"/hooks/([\w.]+\.py)", hook["command"])
                if m:
                    refs.add(m.group(1))
    return refs


def test_hooks_json_references_existing_files():
    for fname in _referenced_hook_files():
        assert (HOOKS_DIR / fname).exists(), f"hooks.json が参照する {fname} が無い"


def test_every_hook_is_referenced():
    """hooks/ の全 .py が hooks.json から参照される(オーファン検出)。"""
    on_disk = {p.name for p in HOOKS_DIR.glob("*.py")}
    referenced = _referenced_hook_files()
    assert on_disk == referenced, f"未参照のフック: {on_disk - referenced}"


# ---------------------------------------------------------------------------
# 全フックが構文的に正しい
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hook_path", sorted(HOOKS_DIR.glob("*.py")), ids=lambda p: p.name)
def test_hook_compiles(hook_path):
    py_compile.compile(str(hook_path), doraise=True)


# ---------------------------------------------------------------------------
# plugin.json
# ---------------------------------------------------------------------------

def test_plugin_version_is_semver():
    meta = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert re.fullmatch(r"\d+\.\d+\.\d+", meta["version"]), meta.get("version")
