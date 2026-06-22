---
cr_id: CR-NNN
type: [requirement]   # 複数可。改訂対象(5章)を覆うように指定。例 [requirement, design]
title: 
status: DRAFT | PENDING_KACHO | PENDING_BUCHO | PENDING_SHACHO | APPROVED | REJECTED
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

- 本書だけ冒頭に YAML frontmatter を持つ(他の設計/計画文書は持たない)のは意匠ではなく機能要件:
  ringi_guard.py が frontmatter の status / type と、本文「5. 改訂対象ドキュメント」のパスを
  機械照合し、3条件(status:APPROVED ∧ 本文に対象パス ∧ そのパスが要求する種別 ∈ type) を
  満たした時のみ当該ドキュメントの改訂ロックを解除する(type は複数可のリスト)。
  よって frontmatter は人間用ではなくガード用の正本。
  末尾「文書管理情報」は人間可読のサマリで、両者は矛盾させないこと。
-->

## 1. 変更概要 (一文で)

<!-- 何を、どう変えたいか -->

## 2. 変更種別

<!-- 諸元: PMBOK Guide「統合変更管理プロセス (Perform Integrated Change Control)」の
     変更要求4分類。「何のための変更か」を示す人間の分類(機械処理には使わない)。
     どのベースラインを変えるか(= frontmatter type)は本章では持たない。
     type は frontmatter にのみ記し、「5. 改訂対象ドキュメント」から導出する(重複記入しない)。 -->

- [ ] 是正処置 (corrective action) — 計画とのズレを実績側で計画に合わせ直す
- [ ] 予防処置 (preventive action) — 将来のズレを未然に防ぐ
- [ ] 欠陥修正 (defect repair) — 成果物の不適合(欠陥)を直す
- [ ] 更新 (update) — ベースライン/計画/文書そのものを正式に変更する

## 3. 背景・動機

<!-- なぜこの変更が必要か。発生した事象、検知の経緯 -->

## 4. 変更内容詳細

### 4.1 変更前
<!-- 現状の要件/設計/タスク -->

### 4.2 変更後
<!-- 変更後の要件/設計/タスク -->

## 5. 影響範囲分析

- **影響する REQ-ID**:
- **影響する設計章 (03/04)**:
- **影響するファイル**:
- **影響する既存テスト**:
- **工数増分** (人日):
- **スケジュール影響** (日):
- **推奨される実装順序**:
- **改訂対象ドキュメント(フルパス)**:
  <!-- 本書で最も重要な欄。これが変更範囲の「正本」であり、2.2 変更対象(type)も
       8章 承認パスもここから導出される(起票時の予想ではなく具体パスを正とする)。
       該当するものをすべて漏れなく列挙すること。漏れた文書は承認後も解錠されない。
       例:
         - .jtbc/requirements/requirements.md
         - .jtbc/designs/basic_design.md
         - .jtbc/designs/detailed_design.md
       承認後、ringi_guard は「APPROVED ∧ ここにパス記載 ∧ そのパスが要求する種別が
       frontmatter type に含まれる」をすべて満たす場合のみ当該文書の改訂を許可する。
       type が対象を覆っていない/不足している場合は、起票時に ringi_consistency が
       ブロックし、解錠時にも ringi_guard が不足種別を名指しでブロックする。

       ▼ ここに挙げたパスから frontmatter type を導出する(導出表):
         | 改訂対象ドキュメント                 | type        |
         |--------------------------------------|-------------|
         | .jtbc/requirements/requirements.md   | requirement |
         | .jtbc/designs/basic_design.md        | design      |
         | .jtbc/designs/detailed_design.md     | design      |
       ドキュメントを伴わない変更は対象パスが無いので type を直接指定する:
         技術選定そのもの=tech_stack / スコープ=scope / 工数・コスト=effort
       複数に跨れば type も複数(例 [requirement, design])。承認パス(8章)はその和集合。 -->
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

<!-- type ごとの承認経路 (ringi_workflow より / 起案者は承認者に含めない):
  - requirement : 課長 → 部長 → 社長   (起案者: 主任)
  - design      : 課長 → 部長          (起案者: 主任)
  - tech_stack  : 課長 → 部長          (起案者: 主任)
  - scope       : 部長 → 社長          (起案者: 課長)
  - effort      : 課長 → 部長          (起案者: 主任)

  type が複数あるとき(横断変更)は、各 type の経路の **和集合**(重複排除・最上位まで)を使う。
  例) type: [requirement, design] → 課長 → 部長 → 社長(requirement 側が最も厳しいため)。
  本 CR の type に現れない承認段(および起案者の段)は「N/A」と記入する。
  起案者(created_by)は自分の起票を承認しない(自己レビュー禁止)。
-->

| 段 | 役職 | 状態 | 承認者 | 日時 | コメント |
|---|---|---|---|---|---|
| 1 | 課長 (jtbc-kacho) | PENDING / N/A | - | - | - |
| 2 | 部長 (jtbc-bucho) | WAIT / N/A | - | - | - |
| 3 | 社長 (jtbc-shacho) | WAIT / N/A | - | - | - |

<!-- status が APPROVED になると ringi_guard によるドキュメント改訂ロックが解除される。 -->

## 9. 承認後の反映方針

<!-- 本書は変更要求管理(統合変更管理)の文書であり、タスク管理文書ではない。
     よって誰がいつ何を実施するかのタスクは本書に列挙しない。
     - 何を改訂するか(対象文書): 「5. 影響範囲分析 / 改訂対象ドキュメント」に列挙済み(ringi_guard の解錠対象)。
     - 誰が改訂するか(オーナー): 各ドキュメント自身のヘッダ「作成者/承認者」に従う
       (例: 要件定義書=課長、基本設計書=課長、詳細設計書=主任)。本書で起票者役職に固定しない。
     - いつ実施するか(タスク・進捗): WBS で管理する。本 CR から WBS-ID を起こして紐づける。 -->

- 改訂対象文書: 「5. 影響範囲分析」を正とする
- 各文書の改訂オーナー: 当該文書のヘッダに従う(本書で代行者を固定しない)
- 実施タスク・進捗: WBS で起票・管理(下記「関連 WBS-ID」に採番を記録)

---
## 文書管理情報
- 文書ID: CR-NNN
- バージョン: 0.1
- 起案者(created_by): <role> ※起案者は承認しない
- 承認者: <type に応じた承認経路 (requirement:課長→部長→社長 / design・tech_stack・effort:課長→部長 / scope:部長→社長)>
- 作成日: {{created_at}}
- 最終更新: {{created_at}}
- 承認状態: DRAFT
- 関連 REQ-ID: 
- 関連 WBS-ID:
