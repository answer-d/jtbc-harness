# JTBC プラグインの自動テスト

## 方針 — テスト容易性は「層」で分ける

このプラグインは4層からなり、決定論的にテストできる層とできない層が分かれる。
統制の実体は**フック(物理ガード)**にあるため、テスト投資もそこへ寄せる。

| 層 | 中身 | テスト | 本リポジトリ |
|---|---|---|---|
| 1. フック (Python) | `hooks/*_guard.py` | 決定論的・最重要 | `test_hooks.py` |
| 2. 状態機械 + フック合成 | `.jtbc/` ライフサイクル | LLM 不要で再現可 | `test_lifecycle.py` |
| 3. 静的整合性 | yaml↔コード表・hooks.json | lint で機械検証 | `test_consistency.py` |
| 4. LLM 挙動 | agents/skills プロンプト | 非決定論・スポット eval | (CI 対象外) |

> なぜこの配分か: 「プロンプトでは守らせられない、物理フックで担保する」のが本プラグインの
> 設計思想。守りたい不変条件はフックが握るので、層1+3 が費用対効果の最大点。LLM 挙動(層4)は
> flaky なので合否ゲートにしない。

## 実行

```sh
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

本体フックは標準ライブラリのみで動作する。テストの追加依存は `pytest` と
(整合性テストの YAML パース用)`PyYAML` のみ。CI は `.github/workflows/test.yml`。

## 設計メモ

- **フックは「stdin JSON → exit 0/2 + stderr」の純関数**。`conftest.py` の `run_hook()` が
  実プロセスと同じ経路(サブプロセス + stdin)で起動する。stderr は壊れやすい完全一致を避け、
  フック名タグ等の**部分一致**で確認する。
- **隔離**: `team_guard` は team config を `CLAUDE_CONFIG_DIR`(無ければ `~/.claude`)配下から読む。
  テストは一時ディレクトリを `CLAUDE_CONFIG_DIR` に指すだけで実機 `~/.claude` に触れず隔離できる
  (`teams_config` フィクスチャ)。状態依存フックは一時 `.jtbc/` を作る(`project` フィクスチャ)。
- **ドリフト検出**: `config/jtbc.yaml#gates` と `state_guard.py#TRANSITIONS` は二重定義(yaml 依存を
  避けるための写し)。`test_consistency.py` が両者の一致を強制し、片方だけ直す事故を防ぐ。
- **シナリオ(層2)**: `test_lifecycle.py` は本番 `hooks.json` と同じ順で Edit/Write 系ガードを連結し
  (`WRITE_GUARDS`)、PROPOSAL→…→COMPLETED を意図したツール呼び出し列で歩かせる。各ゲートで
  「起案者は起案でき、司令塔は ringi 文書を起案できず、承認前は移行不可、PMO のみ移行可」を確認する。
  単体テストが見ない**ガードの合成**(例: 課長の phase 書込みは state_guard ではなく role_guard が先に止める)を捕捉する。
