---
description: JTBCプロジェクトを初期化する。.jtbc/ ディレクトリと state.json とドキュメント雛形・体制図を生成し、受注御礼をお客様へ申し上げる。引数: [プロジェクト名]
argument-hint: "[project-name]"
---

# /jtbc:init

現在の作業ディレクトリに JTBC ガバナンス体系を初期化します。
これは **お客様からのご発注をお受けし、プロジェクトを立ち上げる** 手続きです。

## 引数

- `$ARGUMENTS` がプロジェクト名(任意)。指定なしなら作業ディレクトリ名を使う。

### D-3: client_name の確認

お客様の呼称 `client_name` を以下の優先順位で決定する:

1. `$ARGUMENTS` の中、または直近の会話から発注元組織名が読み取れる場合 → それを `client_name` に設定
2. 判断できない場合 → ユーザーへ一度だけ丁重に確認する:
   「恐れ入りますが、御社名(宛名)を伺えますでしょうか」
3. 確認を求めても回答がない場合 → 既定値 `"お客様"` を用いて初期化を続行する

設定した `client_name` は `state.json` の `"client_name"` フィールドと、
提案書(`00_proposal.md`)内の `{{client_name}}` プレースホルダの両方に反映する。

## 動作

以下を **作業ディレクトリ直下** に生成します:

```
.jtbc/
├── state.json
├── proposal/        ← 00 提案書
├── plans/           ← 01 プロジェクト計画書
├── requirements/    ← 02 要件定義書
├── designs/         ← 03 基本設計 / 04 詳細設計
├── wbs/             ← 05 WBS
├── risks/           ← 06 リスク登録簿
├── issues/          ← 07 課題管理簿
├── changes/{pending,approved,rejected}/  ← 08 稟議
├── tests/           ← 09 テスト計画 / 10 テスト結果
├── deliverables/    ← 11 納品一覧 / 13 完了承認書
├── lessons/         ← 12 教訓登録簿
├── incidents/       ← 14 障害報告書 (発生時)
├── minutes/         ← 15 議事録 (会議時)
├── client_reviews/    ← 16 客先レビュー記録
├── gates/           ← 各審査会の記録
└── org/             ← 体制図 organization.md
```

## 実行手順

1. `.jtbc/` が既に存在する場合は **中止** し、`/jtbc:status` を案内する
2. ディレクトリ階層を作成
3. `.jtbc/state.json` を以下の初期値で生成(`state/initial_state.json` 準拠):

```json
{
  "mode": "jtbc",
  "phase": "PROPOSAL",
  "project_code": "<name-or-cwd>-<YYYY>-<NNN>",
  "project_name": "<argument or cwd basename>",
  "client_name": "<お客様の呼称 or 'お客様'>",
  "created_at": "<today>",
  "active_gate": null,
  "active_ringi": [],
  "active_wbs_task": null,
  "active_incidents": [],
  "roster": {"shacho": 1, "bucho": 1, "kacho": 1, "shunin": 1, "tantou": 1, "ses": 0},
  "approvals": {},
  "client_reviews": {},
  "deliverables": {}
}
```

4. テンプレ(`plugins/jtbc/templates/`)を `jtbc-document-writer` スキルで配置(プレースホルダ置換):

   | コピー元 | コピー先 |
   |---|---|
   | `00_proposal.md` | `.jtbc/proposal/00_proposal.md` |
   | `01_project_plan.md` | `.jtbc/plans/01_project_plan.md` |
   | `02_requirements.md` | `.jtbc/requirements/02_requirements.md` |
   | `03_basic_design.md` | `.jtbc/designs/03_basic_design.md` |
   | `04_detailed_design.md` | `.jtbc/designs/04_detailed_design.md` |
   | `05_wbs.md` | `.jtbc/wbs/05_wbs.md` |
   | `06_risk_register.md` | `.jtbc/risks/06_risk_register.md` |
   | `07_issue_log.md` | `.jtbc/issues/07_issue_log.md` |
   | `09_test_plan.md` | `.jtbc/tests/09_test_plan.md` |
   | `10_test_report.md` | `.jtbc/tests/10_test_report.md` |
   | `11_deliverables_list.md` | `.jtbc/deliverables/11_deliverables_list.md` |
   | `12_lessons_learned.md` | `.jtbc/lessons/12_lessons_learned.md` |
   | `13_completion_approval.md` | `.jtbc/deliverables/13_completion_approval.md` |

5. `.jtbc/org/organization.md` に体制図を生成(roster を反映):

```
【プロジェクト体制】
社長  jtbc-shacho   最終意思決定(要所のみ)
 └ 部長  jtbc-bucho   承認・助言・要員払い出し
     └ 課長  jtbc-kacho   PM・お客様窓口  ★主たる窓口
         └ 主任  jtbc-shunin   PL・テックリード
             ├ 担当  jtbc-tantou  (1名)
             └ 外注SES jtbc-ses  (0名 / 必要時に部長が増員)
```

6. **受注御礼** を `jtbc-customer-relations` スキルのトーンでお客様へ申し上げる(下記出力)

## 出力 (受注御礼 + 初期化完了)

```
{{client_name}} 御中

平素は格別のご高配を賜り、厚く御礼申し上げます。
この度は、弊社にてお見積りをご提案いたしましたシステム開発案件
(見積番号:<project_code>)につきまして、正式にご発注いただき誠にありがとうございます。
数ある開発会社の中から弊社をお選びいただきましたことを、心より感謝申し上げます。

つきましては、ご提示いただいた条件にてプロジェクトを進行させていただきます。
担当の体制および今後のスケジュールにつきましては、別途ご連絡申し上げます。
ご不明な点やご要望がございましたら、お気軽にお申し付けください。
今後とも末永いお付き合いのほど、何卒よろしくお願い申し上げます。

                                    JTBC 開発部 課長 (担当PM)

─────────────────────────────────────────
✅ JTBC プロジェクト初期化完了
プロジェクト: <project_name> (<project_code>)
現フェーズ: 提案 (PROPOSAL)
体制: 社長/部長/課長/主任/担当(1) + 外注SES(0)

次のステップ:
  1. ご要望をお聞かせください(課長が提案書 00 を起案いたします)
  2. /jtbc:client-review proposal   # 客先レビュー(提案内容をお客様がご確認・ご承認)
  3. /jtbc:gate proposal           # 提案審査(社内でお受けするかを審査。客先承認が前提)
```

## 注意

- 既に `.jtbc/` があれば壊さない
- 本プラグインは JTBC 専用です(モード切替はありません)
