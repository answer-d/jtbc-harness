---
name: jtbc-document-writer
description: JTBC のドキュメント雛形を `.jtbc/` 配下に挿入する補助スキル。/jtbc:init や各 agent、各コマンドがテンプレを生成する際に呼ばれる。プレースホルダ ({{project_name}}, {{client_name}}, {{created_at}} 等) を実値で埋める。提案書(00)・障害報告書(14)・議事録(15)を含む全テンプレートに対応。
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
| 00_proposal | .jtbc/proposal/00_proposal.md |
| 01_project_plan | .jtbc/plans/01_project_plan.md |
| 02_requirements | .jtbc/requirements/02_requirements.md |
| 03_basic_design | .jtbc/designs/03_basic_design.md |
| 04_detailed_design | .jtbc/designs/04_detailed_design.md |
| 05_wbs | .jtbc/wbs/05_wbs.md |
| 06_risk_register | .jtbc/risks/06_risk_register.md |
| 07_issue_log | .jtbc/issues/07_issue_log.md |
| 08_change_request | .jtbc/changes/pending/CR-NNN.md (NNN は自動採番) |
| 09_test_plan | .jtbc/tests/09_test_plan.md |
| 10_test_report | .jtbc/tests/10_test_report.md |
| 11_deliverables_list | .jtbc/deliverables/11_deliverables_list.md |
| 12_lessons_learned | .jtbc/lessons/12_lessons_learned.md |
| 13_completion_approval | .jtbc/deliverables/13_completion_approval.md |
| 14_incident_report | .jtbc/incidents/INC-NNN.md (NNN は自動採番) |
| 15_meeting_minutes | .jtbc/minutes/MTG-NNN_<type>.md (NNN は自動採番) |

## 採番ルール

- CR-NNN / INC-NNN / MTG-NNN / L-NNN / WBS-NNN は、対応ディレクトリ内の既存最大番号+1 で採番(3桁ゼロ埋め)
