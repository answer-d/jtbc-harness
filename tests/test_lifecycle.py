"""層2: ライフサイクル シナリオテスト。

LLM を使わず、PROPOSAL → … → COMPLETED を「意図したツール呼び出し列」で歩かせ、
各ステップで本番と同じ PreToolUse ガード連鎖が正しく許可/ブロックするかを検証する。
単体テスト(層1)が見ない「ガードの合成」と「工程順序の物理的な強制」を確認する。
"""
from __future__ import annotations

import json

from conftest import run_hook

# 本番 hooks.json の Edit|Write 系 exit-2 ガードと同じ順序。いずれかが exit 2 なら tool call はブロックされる。
# memory_grant は同じ matcher に居るが permissionDecision(stdout)方式で exit 2 を使わないため含めない。
# このリストと hooks.json のドリフトは test_consistency.test_lifecycle_write_guards_in_sync_with_hooks_json が検出する。
WRITE_GUARDS = ["phase_guard", "role_guard", "ringi_guard", "incident_guard", "state_guard"]


def first_blocker(payload):
    """ガード連鎖を順に通し、最初にブロックしたフック名と stderr を返す(無ければ None)。"""
    for g in WRITE_GUARDS:
        r = run_hook(g, payload)
        if r.blocked:
            return g, r.stderr
    return None, ""


def _filled(rel: str) -> str:
    # 雛形プレースホルダ({{)も DOC_STUBS のスタブも含まない「実内容」。
    return f"# {rel}\n\n実内容が記載されています。トレーサビリティ確保済み。\n"


class Sim:
    """一時 .jtbc/ プロジェクトを進める最小ドライバ。"""

    def __init__(self, root):
        self.root = root
        (root / ".jtbc").mkdir(parents=True, exist_ok=True)
        self.state = {
            "mode": "jtbc", "phase": "PROPOSAL",
            "active_incidents": [], "active_wbs_task": None,
            "approvals": {}, "client_reviews": {},
        }
        self._save()

    def _save(self):
        (self.root / ".jtbc" / "state.json").write_text(
            json.dumps(self.state, ensure_ascii=False), encoding="utf-8")

    def payload(self, role, tool_name, file_path, content=None):
        ti = {"file_path": file_path}
        if content is not None:
            ti["content"] = content
        p = {"cwd": str(self.root), "tool_name": tool_name, "tool_input": ti}
        if role:
            p["agent_type"] = f"jtbc:{role}"
        return p

    def write_doc(self, role, rel, content=None):
        """role が rel を書く操作をガード連鎖に通し、許可なら実ファイルを作る。"""
        content = content if content is not None else _filled(rel)
        blocker, err = first_blocker(self.payload(role, "Write", rel, content))
        if blocker is None:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return blocker, err

    def update_state(self, role, **changes):
        """state.json 更新(approvals/client_reviews/phase)をガード連鎖に通す。"""
        new_state = json.loads(json.dumps(self.state))
        for k, v in changes.items():
            if isinstance(v, dict) and isinstance(new_state.get(k), dict):
                new_state[k] = {**new_state[k], **v}
            else:
                new_state[k] = v
        blocker, err = first_blocker(
            self.payload(role, "Write", ".jtbc/state.json",
                         json.dumps(new_state, ensure_ascii=False)))
        if blocker is None:
            self.state = new_state
            self._save()
        return blocker, err


# 内部承認を要するゲート(client_review を伴う設計系)の定義。
GATES = [
    dict(name="proposal", phase="PROPOSAL", next="REQUIREMENTS", owner="jtbc-kacho",
         ringi_docs=[".jtbc/proposal/proposal.md"], other_docs=[],
         approvers=["bucho", "shacho"], client="proposal"),
    dict(name="project_plan", phase="REQUIREMENTS", next="BASIC_DESIGN", owner="jtbc-kacho",
         ringi_docs=[".jtbc/requirements/requirements.md"],
         other_docs=[".jtbc/plans/project_plan.md", ".jtbc/risks/risk_register.md"],
         approvers=["bucho"], client="project_plan"),
    dict(name="basic_design", phase="BASIC_DESIGN", next="DETAILED_DESIGN", owner="jtbc-kacho",
         ringi_docs=[".jtbc/designs/basic_design.md"],
         other_docs=[".jtbc/issues/issue_log.md"], approvers=["bucho"], client="basic_design"),
    dict(name="detailed_design", phase="DETAILED_DESIGN", next="IMPLEMENTATION", owner="jtbc-shunin",
         ringi_docs=[".jtbc/designs/detailed_design.md"],
         other_docs=[".jtbc/wbs/wbs.md", ".jtbc/tests/test_plan.md"],
         approvers=["kacho", "bucho"], client="detailed_design"),
]


def test_full_lifecycle_walks_proposal_to_completed(tmp_path):
    sim = Sim(tmp_path)

    # --- 開始直後に PMO が phase を進めようとしても、承認も書類も無いので阻止される ---
    blocker, err = sim.update_state("jtbc-pmo", phase="REQUIREMENTS")
    assert blocker == "state_guard" and "事前条件" in err

    for gate in GATES:
        assert sim.state["phase"] == gate["phase"], f"前提フェーズずれ: {gate['name']}"

        # 司令塔(メインセッション)は ringi 対象の起案文書を直接書けない(役割分離の物理担保)
        target = gate["ringi_docs"][0]
        blocker, _ = sim.write_doc(None, target)
        assert blocker == "ringi_guard", f"{gate['name']}: 司令塔の起案は ringi_guard で阻止される想定"

        # 起案者ロールは当該フェーズで起案できる
        for rel in gate["ringi_docs"]:
            blocker, err = sim.write_doc(gate["owner"], rel)
            assert blocker is None, f"{gate['name']}: 起案者 {gate['owner']} が {rel} を書けない ({blocker}: {err})"

        # その他の必要書類(PM 文書)は司令塔/PMO が整備(非 ringi)
        for rel in gate["other_docs"]:
            blocker, err = sim.write_doc(None, rel)
            assert blocker is None, f"{gate['name']}: {rel} の整備がブロックされた ({blocker})"

        # まだ承認前 — PMO でも phase を進められない
        blocker, err = sim.update_state("jtbc-pmo", phase=gate["next"])
        assert blocker == "state_guard" and "事前条件" in err, f"{gate['name']}: 承認前移行が通った"

        # 内部承認を記録(正本 state.json#approvals を司令塔が更新。phase 不変なので通る)
        approval = {f"{gate['name']}_gate": {r: "approved" for r in gate["approvers"]}}
        blocker, err = sim.update_state(None, approvals=approval)
        assert blocker is None, f"{gate['name']}: 承認記録がブロックされた ({blocker})"

        # 客先承認を記録
        blocker, err = sim.update_state(None, client_reviews={gate["client"]: {"status": "APPROVED"}})
        assert blocker is None

        # 非 PMO は条件が揃っても phase を進められない。
        # ・司令塔(agent_type なし)は role_guard を通過するが state_guard の PMO 限定で止まる
        # ・課長など他ロールは そもそも role_guard が state.json 書込みを許さず手前で止まる
        blocker, err = sim.update_state(None, phase=gate["next"])
        assert blocker == "state_guard" and "PMO" in err, f"{gate['name']}: 司令塔の移行が通った"
        blocker, _ = sim.update_state("jtbc-kacho", phase=gate["next"])
        assert blocker == "role_guard", f"{gate['name']}: 課長の state.json 書込みが role_guard で止まらない"

        # 条件充足 + PMO で初めて phase が進む
        blocker, err = sim.update_state("jtbc-pmo", phase=gate["next"])
        assert blocker is None, f"{gate['name']}: 条件充足でも PMO 移行が通らない ({blocker}: {err})"
        assert sim.state["phase"] == gate["next"]

    # --- ここで IMPLEMENTATION。実装系フェーズでのみソースコードを書ける ---
    assert sim.state["phase"] == "IMPLEMENTATION"
    blocker, err = sim.update_state("jtbc-pmo", active_wbs_task="T-001")
    assert blocker is None
    blocker, err = sim.write_doc("jtbc-tantou", "src/main.py", "print('hi')\n")
    assert blocker is None, f"実装フェーズで担当が src を書けない ({blocker}: {err})"

    # 工程内遷移(ゲート無し)も PMO のみが進める
    blocker, err = sim.update_state("jtbc-pmo", phase="UNIT_TEST")
    assert blocker is None
    blocker, err = sim.update_state("jtbc-pmo", phase="INTEGRATION_TEST")
    assert blocker is None

    # --- リリース判定(client_review 無し。内部承認で進む) ---
    sim.write_doc("jtbc-tantou", ".jtbc/tests/test_report.md")
    sim.write_doc(None, ".jtbc/deliverables/deliverables_list.md")
    sim.update_state(None, approvals={"release_gate": {"bucho": "approved", "shacho": "approved"}})
    blocker, err = sim.update_state("jtbc-pmo", phase="RELEASED")
    assert blocker is None, f"リリース移行が通らない ({blocker}: {err})"

    # --- 完了審査 ---
    sim.write_doc(None, ".jtbc/lessons/lessons_learned.md")
    sim.write_doc(None, ".jtbc/deliverables/completion_approval.md")
    sim.update_state(None, approvals={"completion_gate": {"bucho": "approved", "shacho": "approved"}})
    blocker, err = sim.update_state("jtbc-pmo", phase="COMPLETED")
    assert blocker is None, f"完了移行が通らない ({blocker}: {err})"
    assert sim.state["phase"] == "COMPLETED"


def test_source_code_write_blocked_before_implementation(tmp_path):
    """実装フェーズ前は、担当でもソースコードを書けない(phase_guard)。"""
    sim = Sim(tmp_path)  # PROPOSAL
    sim.update_state("jtbc-pmo", active_wbs_task="T-001")  # WBS があっても phase が手前なら不可
    blocker, err = sim.write_doc("jtbc-tantou", "src/main.py", "x=1\n")
    assert blocker == "phase_guard"


def _ready_for_proposal_gate(sim):
    """PROPOSAL→REQUIREMENTS の事前条件を、client 承認の形だけ未確定にして揃える。"""
    sim.write_doc("jtbc-kacho", ".jtbc/proposal/proposal.md")
    sim.update_state(None, approvals={"proposal_gate": {"bucho": "approved", "shacho": "approved"}})


def test_state_guard_fails_closed_on_malformed_client_reviews(tmp_path):
    """client_reviews を正本 dict でなく素の文字列で書いても、門番はクラッシュ fail-open せず
    fail-closed でブロックする(E2E 2026-06-21 で発見した堅牢性ギャップの回帰)。"""
    sim = Sim(tmp_path)  # PROPOSAL
    _ready_for_proposal_gate(sim)

    # client_reviews.proposal を dict でなく素の文字列 "APPROVED" にする(正本スキーマ違反)。
    # 旧実装では cr.get() が AttributeError → exit 1 → ハーネス fail-open で遷移が素通りした。
    sim.update_state(None, client_reviews={"proposal": "APPROVED"})
    blocker, err = sim.update_state("jtbc-pmo", phase="REQUIREMENTS")
    assert blocker == "state_guard" and "事前条件" in err, f"不正形状の client_reviews で素通りした ({blocker}: {err})"
    assert "形状が不正" in err and "proposal" in err
    assert sim.state["phase"] == "PROPOSAL", "ブロックされたのに phase が進んでいる"


def test_state_guard_fails_closed_on_malformed_approvals(tmp_path):
    """approvals のゲート値が dict でない不正形状でも、門番は fail-closed でブロックする。"""
    sim = Sim(tmp_path)  # PROPOSAL
    sim.write_doc("jtbc-kacho", ".jtbc/proposal/proposal.md")
    # proposal_gate を承認状態 dict ではなく素の文字列にする
    sim.update_state(None, approvals={"proposal_gate": "approved"})
    sim.update_state(None, client_reviews={"proposal": {"status": "APPROVED"}})
    blocker, err = sim.update_state("jtbc-pmo", phase="REQUIREMENTS")
    assert blocker == "state_guard" and "形状が不正" in err, f"不正形状の approvals で素通りした ({blocker}: {err})"
    assert sim.state["phase"] == "PROPOSAL"


def test_incident_freezes_forward_docs(tmp_path):
    """緊急対応中は前進系ガバナンス文書の編集が凍結される(incident_guard)。"""
    sim = Sim(tmp_path)
    sim.state["phase"] = "BASIC_DESIGN"
    sim._save()
    # 平常時は起案できる
    blocker, _ = sim.write_doc("jtbc-kacho", ".jtbc/designs/basic_design.md")
    assert blocker is None
    # インシデント発生中はブロック
    sim.update_state(None, active_incidents=["INC-001"])
    blocker, err = sim.write_doc("jtbc-kacho", ".jtbc/designs/basic_design.md")
    assert blocker == "incident_guard"
