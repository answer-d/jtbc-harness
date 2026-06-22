# 成果物・プロジェクト文書一覧

<!--
- 作成者: 課長 (jtbc-kacho。PM・owner) / 主任は事前レビュー(テスト結果・残課題)で関与
- 承認者: 部長
- 更新条件: 成果物追加/変更時
- レビュー条件: リリース判定会、完了審査

- 本書は2区分で管理する:
  (1) 納品成果物 — お客様へ引き渡す product/deliverables。
  (2) 社内プロジェクト文書 — 進捗/リスク/課題/変更/教訓などの project documents。
       社内保管・監査用であり、お客様には納品しない。
  PMBOK Guide でも product(deliverables) と project documents は別カテゴリで管理する。
  「納品物確認」(完了承認書 第4章) はこのうち (1) を対象とする。
-->

## 1. 納品成果物一覧 (客先提出物)

お客様へ引き渡す成果物。JTBCモードの場合、最低限以下を納品成果物とする:

| # | 成果物 | 種別 | 提出パス | 状態 |
|---|---|---|---|---|
| D-1 | ソースコード | source | `src/` (+ tag `v1.0.0`) | NOT_READY |
| D-2 | 提案書 | doc | `.jtbc/proposal/proposal.md` | NOT_READY |
| D-3 | 要件定義書 | doc | `.jtbc/requirements/requirements.md` | NOT_READY |
| D-4 | 基本設計書 | doc | `.jtbc/designs/basic_design.md` | NOT_READY |
| D-5 | 詳細設計書 | doc | `.jtbc/designs/detailed_design.md` | NOT_READY |
| D-6 | テスト計画書 | doc | `.jtbc/tests/test_plan.md` | NOT_READY |
| D-7 | テスト結果報告書 | report | `.jtbc/tests/test_report.md` | NOT_READY |
| D-8 | リリース記録 | record | `.jtbc/deliverables/release_note.md` | NOT_READY |

## 2. 社内プロジェクト文書 (社内保管・監査用 / 客先には納品しない)

プロジェクト運営のための管理文書。お客様への納品対象ではないが、リリース判定会・完了審査での内部統制エビデンスとして整備・保管する。

| # | 文書 | 種別 | パス | 状態 |
|---|---|---|---|---|
| P-1 | プロジェクト計画書 | doc | `.jtbc/plans/project_plan.md` | NOT_READY |
| P-2 | WBS | doc | `.jtbc/wbs/wbs.md` | NOT_READY |
| P-3 | リスク登録簿 | doc | `.jtbc/risks/risk_register.md` | NOT_READY |
| P-4 | 課題管理簿 | doc | `.jtbc/issues/issue_log.md` | NOT_READY |
| P-5 | 変更管理票一式 | doc | `.jtbc/changes/approved/CR-*.md` | NOT_READY |
| P-6 | 教訓登録簿 | doc | `.jtbc/lessons/lessons_learned.md` | NOT_READY |
| P-7 | プロジェクト完了承認書 | doc | `.jtbc/deliverables/completion_approval.md` | NOT_READY |

## 3. 状態区分

- `NOT_READY` — まだ提出可能な状態でない
- `READY` — 内容完成、承認待ち
- `APPROVED` — 承認済み、納品可
- `SUBMITTED` — 顧客/上位部署へ提出済み

## 4. 通過条件

### 4.1 リリース判定会通過に必要な状態 (納品成果物)

- 全納品成果物 (D-1〜D-8) が `READY` 以上
- D-1〜D-8 がすべて `APPROVED`

### 4.2 完了審査時点で必要な状態 (社内プロジェクト文書)

- P-6 (教訓登録簿) が `APPROVED`
- P-7 (プロジェクト完了承認書) が PJ完了審査で承認 (`APPROVED`)

<!-- 各成果物・文書のテンプレートは plugins/jtbc/templates/<id>.md として個別に管理する
     (例: リリース記録 = release_note.md)。本書に雛形を直書きしない。 -->

---
## 文書管理情報
- 文書ID: DOC-11
- バージョン: 0.1
- 作成者: 課長 (PM・owner)
- 承認者: 部長
- 作成日: {{created_at}}
- 最終更新: {{created_at}}
- 承認状態: DRAFT
- 関連稟議: -
