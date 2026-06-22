# 納品一覧

<!--
- 作成者: 課長 (jtbc-kacho。PM・owner) / 主任は事前レビュー(テスト結果・残課題)で関与
- 承認者: 部長
- 更新条件: 納品物追加/変更時
- レビュー条件: リリース判定会、完了審査
-->

## 1. 納品物一覧 (mode別最低限)

JTBCモードの場合、最低限以下を納品物とする:

| # | 納品物 | 種別 | 提出パス | 状態 |
|---|---|---|---|---|
| 1 | ソースコード | source | `src/` (+ tag `v1.0.0`) | NOT_READY |
| 2 | 提案書 | doc | `.jtbc/proposal/proposal.md` | NOT_READY |
| 3 | プロジェクト計画書 | doc | `.jtbc/plans/project_plan.md` | NOT_READY |
| 4 | 要件定義書 | doc | `.jtbc/requirements/requirements.md` | NOT_READY |
| 5 | 基本設計書 | doc | `.jtbc/designs/basic_design.md` | NOT_READY |
| 6 | 詳細設計書 | doc | `.jtbc/designs/detailed_design.md` | NOT_READY |
| 7 | WBS | doc | `.jtbc/wbs/wbs.md` | NOT_READY |
| 8 | リスク登録簿 | doc | `.jtbc/risks/risk_register.md` | NOT_READY |
| 9 | 課題管理簿 | doc | `.jtbc/issues/issue_log.md` | NOT_READY |
| 10 | 変更管理票一式 | doc | `.jtbc/changes/approved/CR-*.md` | NOT_READY |
| 11 | テスト計画書 | doc | `.jtbc/tests/test_plan.md` | NOT_READY |
| 12 | テスト結果報告書 | report | `.jtbc/tests/test_report.md` | NOT_READY |
| 13 | リリース記録 | record | `.jtbc/deliverables/release_note.md` | NOT_READY |
| 14 | 教訓登録簿 | doc | `.jtbc/lessons/lessons_learned.md` | NOT_READY |
| 15 | プロジェクト完了承認書 | doc | `.jtbc/deliverables/completion_approval.md` | NOT_READY |

## 2. 状態区分

- `NOT_READY` — まだ提出可能な状態でない
- `READY` — 内容完成、承認待ち
- `APPROVED` — 承認済み、納品可
- `SUBMITTED` — 顧客/上位部署へ提出済み

## 3. 納品条件 (リリース判定会通過に必要な状態)

- 全納品物が `READY` 以上
- 1, 2, 4, 5, 6, 11, 12, 13 は `APPROVED`
- 14 は完了審査時点で `APPROVED`

## 4. リリース記録雛形 (release_note.md)

```markdown
# リリース記録 v<version>

- リリース日時:
- リリース担当:
- 承認者: 部長 (リリース判定会 承認者。※承認は起案者=課長より上位のみ)
- 起案/リリース実施: 課長 (PM・owner) / 主任は事前レビュー(テスト結果・残課題)で関与
- リリース対象:
  - 機能: REQ-001, REQ-002, ...
  - 修正: ISSUE-007, ...
- 影響範囲:
- ロールバック手順:
- 監視項目:
```

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
