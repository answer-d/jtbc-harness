---
cr_id: CR-NNN
type: requirement | design | tech_stack | scope | effort
title: 
status: DRAFT | PENDING_SHUNIN | PENDING_KACHO | PENDING_BUCHO | PENDING_SHACHO | APPROVED | REJECTED
created_by: 
created_at: 
approvals: []
---

# 変更管理票 (稟議)

<!--
- 作成者: 起票者 (任意 role)
- 承認者: type により異なる(下記「8. 承認パス」参照)
- 更新条件: 起票時、承認/差し戻し時
- レビュー条件: 起票毎
-->

## 1. 変更概要 (一文で)

<!-- 何を、どう変えたいか -->

## 2. 変更種別

- [ ] 要件変更 (requirement)
- [ ] 設計変更 (design)
- [ ] 技術選定変更 (tech_stack)
- [ ] スコープ変更 (scope)
- [ ] 工数追加 (effort)

## 3. 背景・動機

<!-- なぜこの変更が必要か。発生した事象、検知の経緯 -->

## 4. 変更内容詳細

### 4.1 変更前
<!-- 現状の要件/設計/タスク -->

### 4.2 変更後
<!-- 変更後の要件/設計/タスク -->

## 5. 影響範囲分析 (← 主任が記入)

- **影響する REQ-ID**:
- **影響する設計章 (03/04)**:
- **影響するファイル**:
- **影響する既存テスト**:
- **工数増分** (人日):
- **スケジュール影響** (日):
- **推奨される実装順序**:
- **改訂対象ドキュメント(フルパス)**:
  <!-- ringi_guard が照合し、承認後の改訂を解錠するパス。
       該当するものをすべて列挙すること。
       例:
         - .jtbc/requirements/02_requirements.md
         - .jtbc/designs/03_basic_design.md
         - .jtbc/designs/04_detailed_design.md
       ここに記載した相対パスと approved/ 配下の CR の frontmatter が一致した場合のみ、
       ringi_guard は当該ドキュメントの改訂を許可する。 -->
  -

## 6. 代替案

| 案 | 概要 | メリット | デメリット |
|---|---|---|---|
| A (本案) | | | |
| B | 現状維持 | | |
| C | | | |

## 7. リスク

- 変更を実施した場合のリスク:
- 変更を実施しない場合のリスク:

## 8. 承認パス

<!-- type ごとの承認経路 (ringi_workflow より):
  - requirement : 主任 → 課長 → 部長 → 社長
  - design      : 主任 → 課長 → 部長
  - tech_stack  : 主任 → 課長 → 部長
  - scope       : 課長 → 部長 → 社長
  - effort      : 主任 → 課長 → 部長

  本 CR の frontmatter の type に該当する経路の行のみを使うこと。
  その type で不要な承認段は「N/A」と記入する。
-->

| 段 | 役職 | 状態 | 承認者 | 日時 | コメント |
|---|---|---|---|---|---|
| 1 | 主任 (jtbc-shunin) | PENDING / N/A | - | - | - |
| 2 | 課長 (jtbc-kacho) | WAIT / N/A | - | - | - |
| 3 | 部長 (jtbc-bucho) | WAIT / N/A | - | - | - |
| 4 | 社長 (jtbc-shacho) | WAIT / N/A | - | - | - |

<!-- status が APPROVED になると ringi_guard によるドキュメント改訂ロックが解除される。 -->

## 9. 承認後の更新タスク (主任)

- [ ] 要件定義書 (02) の改訂 (REQ-IDレベル)
- [ ] 基本設計書 (03) の改訂
- [ ] 詳細設計書 (04) の改訂
- [ ] WBS (05) へのタスク追加
- [ ] テスト計画書 (09) の改訂

---
## 文書管理情報
- 文書ID: CR-NNN
- バージョン: 0.1
- 作成者: <role>
- 承認者: <type に応じた承認経路 (requirement:主任→課長→部長→社長 / design・tech_stack・effort:主任→課長→部長 / scope:課長→部長→社長)>
- 作成日: {{created_at}}
- 最終更新: {{created_at}}
- 承認状態: DRAFT
- 関連 REQ-ID: 
- 関連 WBS-ID:
