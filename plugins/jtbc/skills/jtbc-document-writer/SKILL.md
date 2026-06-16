---
name: jtbc-document-writer
description: JTBC のドキュメント雛形を `.jtbc/` 配下に挿入する補助スキル。/jtbc:init や各 agent、各コマンドがテンプレを生成する際に呼ばれる。プレースホルダ ({{project_name}}, {{client_name}}, {{created_at}} 等) を実値で埋める。提案書・障害報告書・議事録を含む全テンプレートに対応。
---

# JTBC ドキュメントライター

`plugins/jtbc/templates/*.md` の雛形を読み、プレースホルダを実値に置換した上で
`.jtbc/` の所定パスに書き込む補助スキル。

## プレースホルダ

| プレースホルダ | 実値 |
|---|---|
| `{{project_name}}` | state.json#project_name |
| `{{project_code}}` | state.json#project_code |
| `{{client_name}}` | state.json#client_name (発注主=お客様の呼称) |
| `{{created_at}}` | state.json#created_at |
| `{{today}}` | 実行日 (YYYY-MM-DD) |
| `{{role}}` | 現在の役職 (agent名) |

## 動作

入力: `(template_id, destination_path, overrides?)`

1. `plugins/jtbc/templates/<template_id>.md` を Read
2. プレースホルダを state.json と overrides で置換
3. destination_path に Write
4. ファイルパスを呼出元に返す

## テンプレID → デフォルト destination

| テンプレID | destination |
|---|---|
| proposal | .jtbc/proposal/proposal.md |
| project_plan | .jtbc/plans/project_plan.md |
| requirements | .jtbc/requirements/requirements.md |
| basic_design | .jtbc/designs/basic_design.md |
| detailed_design | .jtbc/designs/detailed_design.md |
| wbs | .jtbc/wbs/wbs.md |
| risk_register | .jtbc/risks/risk_register.md |
| issue_log | .jtbc/issues/issue_log.md |
| change_request | .jtbc/changes/pending/CR-NNN.md (NNN は自動採番) |
| test_plan | .jtbc/tests/test_plan.md |
| test_report | .jtbc/tests/test_report.md |
| deliverables_list | .jtbc/deliverables/deliverables_list.md |
| lessons_learned | .jtbc/lessons/lessons_learned.md |
| completion_approval | .jtbc/deliverables/completion_approval.md |
| incident_report | .jtbc/incidents/INC-NNN.md (NNN は自動採番) |
| meeting_minutes | .jtbc/minutes/MTG-NNN_<type>.md (NNN は自動採番) |

## 採番ルール

- CR-NNN / INC-NNN / MTG-NNN / L-NNN / WBS-NNN は、対応ディレクトリ内の既存最大番号+1 で採番(3桁ゼロ埋め)
