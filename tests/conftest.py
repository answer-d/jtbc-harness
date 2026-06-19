"""JTBC フックテストの共通フィクスチャ・ヘルパ。

依存は標準ライブラリのみ(整合性テストの YAML パースのみ任意で PyYAML を使う)。
各フックは「stdin に JSON → exit 0/2 + stderr」の純関数なので、サブプロセスで
実プロセスと同じ経路で起動して検証する。
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugins" / "jtbc"
HOOKS_DIR = PLUGIN_ROOT / "hooks"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "e2e: 実機 claude を起動する層4テスト(既定で skip。JTBC_E2E=1 で有効化)",
    )


@dataclass
class HookResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def blocked(self) -> bool:
        return self.exit_code == 2

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


def run_hook(hook: str, payload: dict, env: dict | None = None) -> HookResult:
    """フック <hook>.py を payload(JSON)を stdin に与えて起動し、結果を返す。

    env は os.environ への追加分(CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS など)。
    """
    hook_path = HOOKS_DIR / f"{hook}.py"
    assert hook_path.exists(), f"hook not found: {hook_path}"
    import os

    proc_env = dict(os.environ)
    # テスト間の汚染を避けるため、フックが見る環境変数は明示分のみに正規化する
    for key in ("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "CLAUDE_CONFIG_DIR", "JTBC_HOOK_DEBUG"):
        proc_env.pop(key, None)
    if env:
        proc_env.update(env)

    proc = subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=proc_env,
    )
    return HookResult(proc.returncode, proc.stdout, proc.stderr)


@pytest.fixture
def project(tmp_path: Path):
    """一時 .jtbc/ プロジェクトを作るヘルパ。

    使い方:
        p = project(phase="REQUIREMENTS", approvals={...})
        p.write_doc(".jtbc/proposal/proposal.md", "本文")
        payload = p.payload(tool_name="Write", file_path=".jtbc/state.json", ...)
    """

    class Project:
        def __init__(self, root: Path):
            self.root = root
            (root / ".jtbc").mkdir(parents=True, exist_ok=True)

        def set_state(self, **fields) -> "Project":
            state = {
                "mode": "jtbc",
                "phase": "PROPOSAL",
                "active_incidents": [],
                "active_wbs_task": None,
                "approvals": {},
                "client_reviews": {},
            }
            state.update(fields)
            (self.root / ".jtbc" / "state.json").write_text(
                json.dumps(state, ensure_ascii=False), encoding="utf-8"
            )
            return self

        def write_doc(self, rel: str, content: str) -> "Project":
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return self

        def payload(self, **fields) -> dict:
            base = {"cwd": str(self.root), "tool_input": {}}
            base.update(fields)
            return base

    def _make(**state_fields) -> Project:
        p = Project(tmp_path)
        p.set_state(**state_fields)
        return p

    return _make


@pytest.fixture
def teams_config(tmp_path: Path):
    """CLAUDE_CONFIG_DIR 用の teams/session-*/config.json を作るヘルパ。

    返り値は (config_dir, build) で、build(session_id, members) が config を書き、
    フックへ渡す env(CLAUDE_CONFIG_DIR + teams 有効)を返す。
    """
    config_dir = tmp_path / "claude_config"

    def _build(session_id: str, members: list[dict]) -> dict:
        sess_dir = config_dir / "teams" / f"session-{session_id[:8]}"
        sess_dir.mkdir(parents=True, exist_ok=True)
        config = {
            "name": f"session-{session_id[:8]}",
            "leadSessionId": session_id,
            "members": members,
        }
        (sess_dir / "config.json").write_text(
            json.dumps(config, ensure_ascii=False), encoding="utf-8"
        )
        return {
            "CLAUDE_CONFIG_DIR": str(config_dir),
            "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
        }

    return _build
