---
description: フェーズゲート審査会を実行する(提案/PJ計画/基本設計/詳細設計/リリース判定/PJ完了)。根回し→審査→承認印の流れで進む。引数: <gate_name>
argument-hint: "<proposal|project_plan|basic_design|detailed_design|release|completion>"
---

# /jtbc:gate

フェーズゲート審査会を実行します。各ゲートは「必要書類 + 承認者 + チェックリスト」の3点セット。
定義は `modes/jtbc.yaml#gates`、チェックリストは `skills/governance/SKILL.md` を正とします。

## 引数

`$ARGUMENTS` が以下のいずれか:
- `proposal` — 提案審査(この案件をお受けするか)
- `project_plan` — PJ計画審査(要件と計画の妥当性)
- `basic_design` — 基本設計審査
- `detailed_design` — 詳細設計審査
- `release` — リリース判定会
- `completion` — PJ完了審査

## ゲート定義表

| gate | 前フェーズ | 次フェーズ | 必要書類 | 承認者(◎owner先頭) | 客先提示 |
|---|---|---|---|---|---|
| proposal | PROPOSAL | REQUIREMENTS | 提案書 | 課長, 部長, 社長 | 内部承認後に提示 |
| project_plan | REQUIREMENTS | BASIC_DESIGN | 計画, 要件, リスク | 課長, 部長, 主任 | 内部承認後に提示 |
| basic_design | BASIC_DESIGN | DETAILED_DESIGN | 基本設計, 課題 | 課長, 部長 | 内部承認後に提示 |
| detailed_design | DETAILED_DESIGN | IMPLEMENTATION | 詳細設計, WBS, テスト計画 | 課長, 主任, 部長 | 内部承認後に提示 |
| release | INTEGRATION_TEST | RELEASED | テスト結果, 納品一覧 | 課長, 主任, 部長, 社長 | — |
| completion | RELEASED | COMPLETED | 教訓, 完了承認書 | 課長, 部長, 社長 | — |

> **承認と客先提示の順序(重要)**: 内部承認(このゲート)を **先に** 行い、上位承認を得てから
> 成果物をお客様へ提示する。**内部承認前の文書をお客様に出してはならない。**
> `internal_approval_first: true` のゲート(proposal/project_plan/basic_design/detailed_design)は、
> このゲートでは **phase を進めず**、承認後に `/jtbc:client-review <gate>` でお客様のご承認を得た
> 時点で `next_phase` へ進む。`release`/`completion` はお客様提示を伴わず、ゲート承認で直接 phase を進める。

## 実行手順

### A-1: 前提確認
1. `.jtbc/state.json#phase` を読み、当該ゲートの `previous_phase` と一致するか確認
   - 違う場合は中止:「現在の工程は <現phase> です。<gate> には <previous_phase> である必要があります」
   - **ゲート記録は `.jtbc/gates/<gate>_gate.md` 単一ファイルで管理する(役職名はファイル名に入れない)**
   - **承認の正本は `state.json#approvals["<gate>_gate"]` の値であり、gate記録 .md は参照用**
   - これは **社内の内部承認** の手続きである。お客様への提示・連絡はここでは行わない。

### A-2: 書類チェック・根回し
2. 必要書類の存在と APPROVED 状態を機械的にチェック(不足は不足リストを出して中止)
3. **根回しフェーズ(伝統的施策)**: owner(課長/主任)が各承認者へ事前に要点と想定論点を共有し、
   懸念があれば審査会前に資料を是正する。公の場での差し戻しを避けるための事前調整(任意だが推奨)

### A-3: 審査会の開催と可否判定
4. `state.json#phase` を `review_phase`(例: `PROPOSAL_REVIEW`)に更新し、審査会を開催
5. `.jtbc/gates/<gate>_gate.md` にチェックリスト(全項目 `[ ]`)を生成

### C-3: 承認印(ハンコ)の機械チェック
6. 承認者 agent を順に起動。各自が担当チェック項目を `[x]`/`[ ]` で埋め、**承認印** を残す:
   - **state.json の更新**: `state.json#approvals["<gate>_gate"][<role>]` を `"approved"` に設定
   - **gate記録への押印**: `.jtbc/gates/<gate>_gate.md` の承認欄に 🔴 を記入(Edit ツールで追記)

```
🔴 承認  課長  (jtbc-kacho)  2026-06-14
```

7. **承認の機械チェック**:
   `modes/jtbc.yaml#gates[<gate>].approvers` に列挙された **全承認者** について
   `state.json#approvals["<gate>_gate"][<role>] == "approved"` であることを確認する。
   **1人でも未承認なら以下の遷移を行わない**。
8. 全員承認が確認できたら、ゲート種別で分岐する:
   - **`internal_approval_first: true`(proposal/project_plan/basic_design/detailed_design)**:
     これは内部承認のみ。**phase は `previous_phase` のまま据え置く**(進めない)。
     `active_gate` を `null` に更新し、approvals を確定する。
     → 出力で「社内承認(上位承認)が完了し、**客先提示が可能** になりました」と伝え、
     `/jtbc:client-review <gate>` でお客様へご提示するよう案内する(**ここでお客様へは連絡しない**)。
   - **client_review を持たないゲート(release/completion)**:
     `state.json#phase` を `next_phase` へ、`active_gate` を `null` に更新する。
9. **1人でも No-Go の場合 → `state.json#phase` を `previous_phase` に戻す(review_phase のまま据え置かない)、
   `active_gate` を `null` に設定し、**当該ゲートの approvals をクリア**し、差し戻し理由を表示する**

## チェックリスト雛形

各ゲートの固定チェックリストは `skills/governance/SKILL.md` の「ゲートチェックリスト一覧」を参照。

例(proposal_gate):
```markdown
# 提案審査 チェックリスト
- [ ] お客様のご要望が正しく理解・明文化されている (課長)
- [ ] ビジネス価値・収益寄与が説明できる (社長)
- [ ] 概算体制と概算見積が提示されている (課長/部長)
- [ ] 規制・ブランドリスクが許容範囲 (社長)
- [ ] 体制を確保できる見込みがある (部長)

## 承認(押印)
- 🔴 承認  課長  ____________  (____-__-__)
- 🔴 承認  部長  ____________  (____-__-__)
- 🔴 承認  社長  ____________  (____-__-__)
```

## 出力 (通過: internal_approval_first ゲート)

```
🎯 提案審査(社内・内部承認)を開催します

[根回し] 課長が部長・社長へ事前共有 … 論点合意済み
必要書類チェック:
  ✅ 提案書 (.jtbc/proposal/proposal.md)
審査チェックリスト: 5/5 OK
承認(上位承認):
  🔴 課長 / 🔴 部長 / 🔴 社長

✅ 社内承認が完了しました。提案書の客先提示が可能になりました。
phase: 提案 (PROPOSAL) のまま(客先のご承認をもって要件定義へ進みます)。
次のステップ: /jtbc:client-review proposal で、内部承認済みの提案書をお客様へご提示します。
※ お客様への連絡は client-review で行います(この段階ではまだ連絡しません)。
```

## 出力 (通過: release/completion ゲート)

```
🎯 リリース判定会 を開催します

承認: 🔴 課長 / 🔴 主任 / 🔴 部長 / 🔴 社長
phase: 総合テスト → リリース済 に更新しました。
```

## 出力 (差し戻し)

```
🎯 PJ計画審査

❌ スケジュールバッファが 12% (規定 20% 未満) — 部長差し戻し
→ 計画書のバッファを見直し、再度 /jtbc:gate project_plan を実行してください。

差し戻し理由: スケジュールバッファ不足(12%、規定 20% 以上)
phase: REQUIREMENTS_REVIEW → 要件定義 (REQUIREMENTS) に戻しました。
active_gate: null
```
