---
description: 現在のJTBCプロジェクトの状態(フェーズ/承認状況/稟議/WBS/インシデント/体制)を表示する。お客様向けの進捗ご報告にも使う。
---

# /jtbc:status

`.jtbc/state.json` を読んで現状を一覧表示します。
お客様向けにご報告する場合は `customer-relations` の敬語トーンに整えます。

## 実行手順

1. `.jtbc/state.json` を Read(無ければ `/jtbc:init` を案内)
2. 以下をまとめて表示:

```
JTBCプロジェクト状況

案件: <project_name> (<project_code>)   お客様: <client_name>
現フェーズ: <phase の日本語名>
体制: 課長/主任/担当(<n>)   ※承認・エスカレーション: 部長/社長 / 増員枠: 外注SES(<m>)

進行中の審査: <active_gate or "なし">
進行中の稟議: <active_ringi 一覧 or "なし">
進行中のWBSタスク: <active_wbs_task or "なし">
対応中のインシデント: <active_incidents 一覧 or "なし">

内部承認(ゲート)状況 ※客先提示の前提:
  - 提案審査:        [x] 課長 / [x] 部長 / [x] 社長  → 客先提示可
  - PJ計画審査:      [x] 課長 / [ ] 部長 / [ ] 主任
  - 基本設計審査:    [ ] ...
  ...

客先提示(ご査収)状況 ※内部承認の後に実施・ご承認で次フェーズへ:
  - 提案:        <APPROVED / PENDING / REVISION_REQUESTED / 未実施>
  - 要件定義書:  <...>
  - 基本設計書:  <...>
  - 詳細設計書:  <...>

次のアクション:
  → <推奨される次のコマンド>
```

3. フェーズに応じた推奨アクション(**内部承認 → 客先提示** の順):

| 現フェーズ | 推奨アクション |
|---|---|
| 提案 (PROPOSAL) | `/jtbc:hearing` で要望整理 → 課長が提案書起案 → `/jtbc:gate proposal`(内部承認)→ `/jtbc:client-review proposal`(客先提示) |
| 要件定義 (REQUIREMENTS) | 課長が要件定義書・計画書 → `/jtbc:gate project_plan`(内部承認)→ `/jtbc:client-review project_plan`(客先提示) |
| 基本設計 (BASIC_DESIGN) | 課長が基本設計 → `/jtbc:gate basic_design`(内部承認)→ `/jtbc:client-review basic_design`(客先提示) |
| 詳細設計 (DETAILED_DESIGN) | 主任が詳細設計・WBS → `/jtbc:gate detailed_design`(内部承認)→ `/jtbc:client-review detailed_design`(客先提示) |
| 実装 (IMPLEMENTATION) | 主任が担当/SESへ割り振り、実装 → 完了後 `/jtbc:phase next` |
| 単体テスト (UNIT_TEST) | 担当が単体テスト → `/jtbc:phase next` |
| 総合テスト (INTEGRATION_TEST) | 主任が総合テスト → `/jtbc:gate release` |
| リリース済 (RELEASED) | 教訓整理 → `/jtbc:gate completion` |
| *_REVIEW | 審査会開催中。承認者の押印を待つ |

## インシデント発生中の表示

`active_incidents` が空でない場合は最上部に警告を出す:

```
⚠️ 緊急対応中: INC-001 「<title>」(severity: high)
　 詳細は /jtbc:incident status INC-001
```

## エラーハンドリング

- `.jtbc/state.json` 不在 → `/jtbc:init` を案内
