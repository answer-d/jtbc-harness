---
description: 客先レビュー(お客様確認)を実施する。社内の内部承認(ゲート)を得た成果物を、営業(窓口)がお客様へご提示し、ご承認を賜る工程。重要局面では課長を同席紹介する。ご承認をもって次フェーズへ進む。引数: <gate_name>
argument-hint: "<proposal|project_plan|basic_design|detailed_design>"
---

# /jtbc:client-review

**社内の内部審査(自動開催)で内部承認を得た** 成果物を、**営業(客対窓口=メインセッション)** が
お客様(ユーザー)へ **正式にご提示** し、**ご確認・ご承認を賜る** 工程です。
技術説明が要る重要局面では、営業が裏方の課長(PM)を同席紹介し、その説明を客前で取り次ぎます。

> **この工程は通常、内部審査の通過に続けて司令塔が自動で発火します**(お客様の操作は不要)。
> このコマンドは、**手動で再提示** したいときの入口として残しています。
> **順序が重要**: 内部承認前の文書をお客様に出してはいけません。必ず内部審査(自動開催)で
> 上位承認を得てから提示します。
> 流れ: ①課長が起案(裏方) → ②内部審査(自動・内部承認)→ ③営業が客先提示(自動・ご承認)→ ④次フェーズへ

定義は `config/jtbc.yaml#gates[<gate>]`(`internal_approval_first: true`)、接遇トーンは
`customer-relations` を正とします。**お客様への応答は必ず丁重な敬語**で行ってください。

## 引数

`$ARGUMENTS` が以下のいずれか:

| gate | ご提示する成果物 | ご提示資料(パス) | このフェーズ |
|---|---|---|---|
| `proposal` | ご提案内容 | `.jtbc/proposal/proposal.md` | PROPOSAL |
| `project_plan` | 要件定義書 | `.jtbc/requirements/requirements.md` | REQUIREMENTS |
| `basic_design` | 基本設計書 | `.jtbc/designs/basic_design.md` | BASIC_DESIGN |
| `detailed_design` | 詳細設計書 | `.jtbc/designs/detailed_design.md` | DETAILED_DESIGN |

> `release` / `completion` には客先レビューはありません(客先向け会議・検収で別途対応)。

## 実行手順

### 1. 前提確認(内部承認が先)
1. `.jtbc/state.json#phase` を読み、当該ゲートの `previous_phase` と一致するか確認
   - 違う場合は中止し、お客様へ現状を丁重にご案内する
2. **内部承認チェック(最重要)**: `config/jtbc.yaml#gates[<gate>].approvers` の **全員** が
   `state.json#approvals["<gate>_gate"][<role>] == "approved"` であることを機械的に確認する
   - 未承認(=社内審査が未了)の場合は **中止**し、
     「お客様へご提示する前に、社内の内部審査(自動開催)で承認を得る必要があります」と内部向けに案内する
   - **内部承認前の成果物をお客様へ提示してはならない**
3. `active_incidents` が非空なら中止(緊急対応モードを優先)
4. ご提示資料が存在し、フォーマット(テンプレート)に沿って記載が整っていることを確認

### 2. お客様へのご提示(営業が進行・必要に応じ課長同席)
5. **成果物のパスを明示** し、フォーマットに沿った正式文書として「ご査収ください」とご提示する
   - **簡略化したサマリだけで済ませない。** お客様が原本をご確認できるよう、必ずファイルパスを示す
   - そのうえで、ご判断に必要な要点・選択肢・前提を **お客様に分かる言葉** で補足説明する
   - 「ご認識に相違がないか」「ご懸念・ご要望はないか」を明確にお伺いする
6. **ここで必ずお客様(ユーザー)の確認を取り、応答を待つ(安請け合い・自己完結で先に進めない)。**

### 3. 結果の記録と遷移
7. 客先レビュー記録を `.jtbc/client_reviews/<gate>_client_review.md` に作成
   (ご提示資料のパス / ご説明の要点 / ご指摘事項 / ご承認結果 / 次のステップ を敬語で記す)
8. `state.json#client_reviews[<gate>]` を更新:

```json
{
  "client_reviews": {
    "<gate>": {
      "status": "APPROVED",
      "reviewed_at": "<today>",
      "record": ".jtbc/client_reviews/<gate>_client_review.md",
      "feedback": []
    }
  }
}
```

9. 結果による分岐:
   - **ご承認(APPROVED)** → `status: "APPROVED"`。
     **`state.json#phase` を当該ゲートの `next_phase` へ進め、次フェーズへ移行する。**
     - **特に `proposal` のご承認は、お客様がご提案をお受け入れくださった = ご発注の確定(受注)** を
       意味する。このタイミングで初めて **受注の御礼** を `customer-relations` トーンで申し上げる
       (`/jtbc:init` や内部承認の段階では御礼を述べない)。
   - **ご指摘あり・要修正(REVISION_REQUESTED)** → `status: "REVISION_REQUESTED"`、`feedback` に記録。
     成果物が変わるため **当該ゲートの内部承認は無効化** する(`approvals["<gate>_gate"]` をクリア)。
     担当部署(課長/主任)が成果物を修正し、**再度 内部審査(自動開催)→ 客先提示(自動発火)** の順で進める。

> **phase 遷移の所在**: `internal_approval_first` のゲートでは、phase を進めるのは **内部審査ではなく
> 本工程(client-review APPROVED 時)**。内部審査(自動開催)は phase を進めない。

## 出力例 (ご提示〜ご査収のお願い)

```
🤝 要件定義書 客先レビュー  (進行: 営業 / 社内承認済み・課長同席)

{{client_name}} 御中
お世話になっております。JTBC で本件の窓口を担当しております営業の◯◯でございます。
このたび要件定義書につきまして社内の承認手続きを完了いたしましたので、正式にご提示申し上げます。
ご査収のほど、よろしくお願い申し上げます。

【ご提示資料】
  要件定義書: .jtbc/requirements/requirements.md  ← 原本をご確認いただけます

【ご説明の要点】
- ご要望の中核機能を 12件の機能要件(REQ-001〜012)として整理いたしました
- 性能・可用性などの非機能要件は別表(NFR)にまとめております
- ○○については A案 / B案の2案がございます。ご意向を伺えますと幸いです

恐れ入りますが、上記内容でご認識に相違がないか、また追加のご要望がございましたら
お聞かせいただけますでしょうか。ご承認をいただけましたら、次工程(基本設計)へと進めてまいります。
```

## 出力例 (ご承認をいただいた後)

```
誠にありがとうございます。要件定義書につきまして、ご承認を賜りました。

客先レビュー記録: .jtbc/client_reviews/project_plan_client_review.md
state: client_reviews.project_plan = APPROVED
phase: 要件定義 (REQUIREMENTS) → 基本設計 (BASIC_DESIGN) に更新しました。

つきましては、基本設計工程へと進めさせていただきます。
```

## 出力例 (提案ご承認 = 受注の御礼)  ※ `proposal` のご承認時のみ

```
{{client_name}} 御中

このたびはご提案の内容をご承認賜り、誠にありがとうございます。
数ある開発会社の中から弊社をお選びいただきましたことを、心より御礼申し上げます。
ご提示の条件にて、本プロジェクトを進めさせていただきます。

ご提示資料: .jtbc/proposal/proposal.md(ご承認いただいた提案書の原本)
客先レビュー記録: .jtbc/client_reviews/proposal_client_review.md
state: client_reviews.proposal = APPROVED
phase: 提案 (PROPOSAL) → 要件定義 (REQUIREMENTS) に更新しました。

つきましては、次のステップとして要件定義へと進めてまいります。
今後ともどうぞよろしくお願い申し上げます。
```

## 出力例 (ご指摘をいただいた場合)

```
貴重なご指摘を賜り、誠にありがとうございます。
いただいた内容(帳票レイアウトの変更ご希望)を要件定義書へ反映のうえ、
社内で改めて承認手続きを行い、再度ご確認をお願い申し上げます。今しばらくお時間を頂戴いたします。

state: client_reviews.project_plan = REVISION_REQUESTED
内部承認(approvals.project_plan_gate)はクリアしました(再承認が必要です)。
→ 課長が要件定義書を修正 → 内部審査(自動開催・再承認)→ 客先提示(自動発火)の順で進めます。
```
