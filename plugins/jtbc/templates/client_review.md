---
review_id: CR-REVIEW-NNN
gate: proposal | project_plan | basic_design | detailed_design
reviewed_documents: []
held_at: 
facilitator: kacho
attendees: [user, kacho]
status: PENDING | APPROVED | REVISION_REQUESTED
---

# 客先レビュー記録

<!--
- 作成者: 課長 (jtbc-kacho / お客様窓口)
- 目的: 社内審査会(ゲート)で内部承認を得た成果物を、お客様へご提示(ご査収)し、確認・ご承認を賜る
- トーン: お客様向けの記録のため、丁重な敬語で記す (customer-relations)
- 対象ゲート: 提案審査 / PJ計画審査 / 基本設計審査 / 詳細設計審査 の内部承認後
-->

## レビュー情報

- レビュー名: <対象>客先レビュー(ご査収)
- 対象ゲート: <proposal | project_plan | basic_design | detailed_design>(内部承認済み)
- ご提示資料(パス): <例) .jtbc/proposal/proposal.md / .jtbc/requirements/requirements.md 等>
- 日時: 
- 弊社出席者: 課長(窓口)〔重要局面では部長も同席〕
- お客様: {{client_name}} 御中

## 1. ご説明の要点

<!-- 課長がお客様に分かる言葉で成果物の要点をご説明した内容を記す -->

- 
- 

## 2. お客様からのご確認・ご指摘事項

| # | ご指摘・ご要望 | 弊社対応方針 | 反映先 |
|---|---|---|---|
| 1 |  |  |  |

## 3. ご承認結果

- [ ] **ご承認**(この内容で次フェーズへ進めてよい)
- [ ] **ご指摘あり・要修正**(下記ご指摘を反映し、社内で再承認のうえ再レビュー)

> 結果は `state.json#client_reviews[<gate>].status` に記録する。
> APPROVED で次フェーズへ進む。REVISION_REQUESTED の場合は当該ゲートの内部承認をクリアし、
> 修正 → 内部審査(社内で自動開催・再承認)→ 客先提示(自動発火)の順で進める。

## 4. 次のステップ

<!-- APPROVED: 次フェーズへ移行 / REVISION: 修正→再・内部承認→再レビュー -->

- 

---
## 文書管理情報
- 文書ID: DOC-16 (客先レビュー記録)
- 作成者: 課長
- 作成日: {{created_at}}
- 配布先: お客様 / 社内審査会
- 承認状態: PENDING
