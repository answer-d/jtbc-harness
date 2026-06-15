---
description: 客先レビュー(お客様確認)を実施する。社内審査会(ゲート)の前に、課長が成果物をお客様へご提示し、ご承認を賜る工程。承認されるまで対象ゲートは開催できない。引数: <gate_name>
argument-hint: "<proposal|project_plan|basic_design|detailed_design>"
---

# /jtbc:client-review

社内審査会(ゲート)の **前** に、課長(お客様窓口)が成果物をお客様(ユーザー)へご提示し、
**確認・ご承認を賜る** 工程です。これは「顧客版の根回し」であり、お客様の合意を得てから
社内の正式審査(ゲート)に進むことで、手戻りと公の場での差し戻しを防ぎます。

定義は `modes/jtbc.yaml#gates[<gate>].client_review`、接遇トーンは `jtbc-customer-relations` を正とします。
**お客様への応答は必ず丁重な敬語**で行ってください(社内口調で話さない)。

## 引数

`$ARGUMENTS` が以下のいずれか:

| gate | 客先レビュー対象 | ご提示資料 | 直前フェーズ |
|---|---|---|---|
| `proposal` | 提案内容・プロジェクト計画方針 | 00 提案書 | PROPOSAL |
| `project_plan` | 要件定義書 | 02 要件定義書 | REQUIREMENTS |
| `basic_design` | 基本設計書 | 03 基本設計書 | BASIC_DESIGN |
| `detailed_design` | 詳細設計書 | 04 詳細設計書 | DETAILED_DESIGN |

> `release` / `completion` には客先レビュー前提はありません(客先向け会議・検収で別途対応)。

## 実行手順

### 1. 前提確認
1. `.jtbc/state.json#phase` を読み、当該ゲートの `previous_phase` と一致するか確認
   - 違う場合は中止し、お客様へ現状を丁重にご案内する
2. `active_incidents` が非空なら中止(緊急対応モードを優先)
3. ご提示資料(`modes/jtbc.yaml#gates[<gate>].client_review.documents`)が存在し、
   社内で初版が整っていることを確認(不足なら起案を先に行う)

### 2. お客様へのご提示(課長が進行)
4. 課長(重要局面では部長も同席)が、成果物の要点を **お客様に分かる言葉** でご説明する
   - 技術的細部はかみ砕き、ご判断に必要な論点・選択肢・前提を簡潔にお示しする
   - 「ここまでの内容でご認識に相違がないか」「ご懸念・ご要望はないか」を明確にお伺いする
5. **ここで必ずお客様(ユーザー)の確認を取る。応答を待つ(安請け合い・自己完結で先に進めない)。**

### 3. 結果の記録
6. 客先レビュー記録(16)を `.jtbc/client_reviews/<gate>_client_review.md` に作成
   - ご説明の要点 / ご指摘事項 / ご承認結果 / 次のステップ を敬語で記す
7. `state.json#client_reviews[<gate>]` を更新:

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

8. 結果による分岐:
   - **ご承認(APPROVED)** → `status: "APPROVED"`。次に `/jtbc:gate <gate>` で社内審査会を開催できる旨をご案内
   - **ご指摘あり・要修正(REVISION_REQUESTED)** → `status: "REVISION_REQUESTED"`、`feedback` にご指摘を記録。
     担当部署(課長/主任)が成果物を修正し、再度 `/jtbc:client-review <gate>` を実施する

> **ゲートとの関係**: `/jtbc:gate <gate>` は、`state.json#client_reviews[<gate>].status == "APPROVED"`
> でない限り開催できない(`/jtbc:gate` 側で機械チェック)。お客様のご承認が社内審査の前提条件です。

## 出力例 (ご提示〜確認のお願い)

```
🤝 要件定義書 客先レビュー  (担当: 課長)

{{client_name}} 御中
お世話になっております。JTBC開発部の課長でございます。
このたびは要件定義書がまとまりましたので、社内審査に先立ち、内容のご確認をお願い申し上げます。

【ご説明の要点】
- ご要望の中核機能を 12件の機能要件(REQ-001〜012)として整理いたしました
- 性能・可用性などの非機能要件は別表(NFR)にまとめております
- ○○については、A案/B案の2案がございます。ご意向を伺えますと幸いです

恐れ入りますが、上記内容でご認識に相違がないか、また追加のご要望がございましたら
お聞かせいただけますでしょうか。ご承認をいただけましたら、社内のPJ計画審査へと進めてまいります。
```

## 出力例 (ご承認をいただいた後)

```
誠にありがとうございます。要件定義書につきまして、ご承認を賜りました。

客先レビュー記録: .jtbc/client_reviews/project_plan_client_review.md
state: client_reviews.project_plan = APPROVED

つきましては、社内のPJ計画審査(/jtbc:gate project_plan)へと進めさせていただきます。
```

## 出力例 (ご指摘をいただいた場合)

```
貴重なご指摘を賜り、誠にありがとうございます。
いただいた内容(帳票レイアウトの変更ご希望)を要件定義書へ反映のうえ、
改めてご確認をお願い申し上げます。今しばらくお時間を頂戴いたします。

state: client_reviews.project_plan = REVISION_REQUESTED
→ 課長が要件定義書(02)を修正し、再度 /jtbc:client-review project_plan を実施します。
```
