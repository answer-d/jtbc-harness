"""層4(E2E): 実機 `claude -p` で /jtbc:init を完走させ、生成物を検証する。

層1〜3(フック/ライフサイクル/整合性)は LLM 不要で決定論的に回せるが、
「プラグインを実際に Claude Code に読ませて /jtbc:init が期待どおり動くか」だけは
実機を起動しないと分からない。本テストはそこだけを担う。

非決定論なので **既定では走らせない**(`pytest tests/` や CI を汚さない)。
明示オプトイン時のみ実行する:

    JTBC_E2E=1 python -m pytest tests/test_e2e_init.py -v -s

要件:
  - `claude` CLI が PATH にあること(無ければ skip)
  - 実機 API を消費する(課金あり)。1 回の init で概ね数分 / 数十円規模。

判定は **決定論的な観測点のみ**(LLM の口調や文面は合否にしない):
  - 終了コード/JSON result がエラーでない
  - `.jtbc/state.json` が生成され、JSON として妥当で phase=PROPOSAL / mode=jtbc
  - init.md が宣言する `.jtbc/` サブディレクトリが生成されている
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT

# このモジュール全体を opt-in に縛る二重ゲート:
#   1. JTBC_E2E=1 が無ければ丸ごと skip(通常の pytest 実行・CI を汚さない)
#   2. claude CLI が無ければ skip
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.environ.get("JTBC_E2E") != "1",
        reason="実機 E2E は既定で無効。JTBC_E2E=1 で明示的に有効化する",
    ),
    pytest.mark.skipif(
        shutil.which("claude") is None,
        reason="claude CLI が PATH に無い",
    ),
]

# .jtbc/ 直下のサブディレクトリ(DESIGN.md §3 と commands/init.md「動作」節が一致して定める正準セット)。
EXPECTED_SUBDIRS = [
    "proposal", "requirements", "designs", "plans", "risks",
    "issues", "tests", "deliverables", "lessons", "incidents",
    "wbs", "changes", "client_reviews", "gates", "org", "minutes",
]

# init を完走させるのに十分な上限(複数ファイル生成 + サブエージェント呼び出しを見込む)。
E2E_TIMEOUT_S = int(os.environ.get("JTBC_E2E_TIMEOUT", "600"))


@dataclass
class SessionResult:
    workdir: Path
    exit_code: int
    result: dict | None  # --output-format json のパース結果(失敗時 None)
    raw_stdout: str
    raw_stderr: str

    def state(self) -> dict:
        return json.loads((self.workdir / ".jtbc" / "state.json").read_text(encoding="utf-8"))


def run_jtbc_session(prompt: str, workdir: Path, timeout: int = E2E_TIMEOUT_S) -> SessionResult:
    """隔離 workdir で headless の `claude -p <prompt>` を起動し、結果を返す。

    入れ子実行の干渉対策:
      - stdin を DEVNULL に塞ぐ(継承待ちハングの主因)。
      - --plugin-dir でこのリポジトリのプラグインだけを読ませる。
      - bypassPermissions で許可プロンプト待ちのハングを避ける(workdir は隔離済み)。
    """
    cmd = [
        "claude", "-p", prompt,
        "--plugin-dir", str(PLUGIN_ROOT),
        "--permission-mode", "bypassPermissions",
        "--output-format", "json",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(workdir),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    try:
        result = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        result = None
    return SessionResult(workdir, proc.returncode, result, proc.stdout, proc.stderr)


@pytest.fixture
def session(tmp_path: Path):
    return lambda prompt: run_jtbc_session(prompt, tmp_path)


def test_init_generates_jtbc_skeleton(session):
    """/jtbc:init が .jtbc/ 一式と PROPOSAL 状態を生成する。"""
    res = session(
        "/jtbc:init 社内からの問い合わせを受け付けて担当者に振り分ける小さなWebツールを作りたい"
    )

    # --- セッションがエラー終了していない ---
    assert res.exit_code == 0, f"claude 非ゼロ終了: {res.raw_stderr[:500]}"
    assert res.result is not None, f"JSON 出力をパースできない: {res.raw_stdout[:500]}"
    assert res.result.get("is_error") is False, f"result がエラー: {res.result}"

    # --- 正本 state.json ---
    state_path = res.workdir / ".jtbc" / "state.json"
    assert state_path.exists(), ".jtbc/state.json が生成されていない"
    state = res.state()
    assert state.get("phase") == "PROPOSAL", f"初期 phase が不正: {state.get('phase')}"
    assert state.get("mode") == "jtbc", f"mode が不正: {state.get('mode')}"

    # --- 宣言どおりのディレクトリ構造 ---
    missing = [d for d in EXPECTED_SUBDIRS if not (res.workdir / ".jtbc" / d).is_dir()]
    assert not missing, f"未生成のサブディレクトリ: {missing}"
