---
description: JTBCプロジェクトを初期化する。.jtbc/ ディレクトリと state.json とドキュメント雛形・体制図を生成し、提案に向けたヒアリングを開始する。引数: [プロジェクト名]
argument-hint: "[project-name]"
---

# /jtbc:init

現在の作業ディレクトリに JTBC ガバナンス体系を初期化します。
これは **お客様のご相談をお受けし、提案に向けてプロジェクトを立ち上げる** 手続きです。
(受注の御礼は、社内審査を経た提案書をお客様がご承認くださった時点 ―― 受注確定時 ―― に申し上げます。)

## 引数

- `$ARGUMENTS` がプロジェクト名(任意)。指定なしなら作業ディレクトリ名を使う。

### D-3: client_name の確認

お客様の呼称 `client_name` を以下の優先順位で決定する:

1. `$ARGUMENTS` の中、または直近の会話から発注元組織名が読み取れる場合 → それを `client_name` に設定
2. 判断できない場合 → ユーザーへ一度だけ丁重に確認する:
   「恐れ入りますが、御社名(宛名)を伺えますでしょうか」
3. 確認を求めても回答がない場合 → 既定値 `"お客様"` を用いて初期化を続行する

設定した `client_name` は `state.json` の `"client_name"` フィールドと、
提案書(`proposal.md`)内の `{{client_name}}` プレースホルダの両方に反映する。

### D-4: 依頼内容の確認(狙いを勝手に仮定しない)

初期化後にヒアリングへ進む前に、**ご相談内容(何を作りたいか)** を以下で決める:

1. `$ARGUMENTS` または直近の会話に具体的な依頼(作りたいシステム/成果物)が読み取れる → それを起点にする
2. 読み取れない場合 → **狙いや推奨案を勝手に仮定せず**、お客様へ1問だけ丁重に伺い、**応答を待つ**:
   「本日はどのようなシステム・成果物のご相談でしょうか。差し支えなければ概要をお聞かせください」
3. ご相談内容が判明してから、提案ヒアリング(`requirements-interview`:1問ずつ・推奨案つき)へ進む。

> ⚠️ 依頼が未確定のまま「目的は○○と想定しております」と中身を捏造して提案を進めない。
> 最初の接点は「何を作りたいか」を伺うことであり、ここでは推奨案を出さない(全体像が未知のため)。

## 動作

以下を **作業ディレクトリ直下** に生成します:

```
.jtbc/
├── state.json
├── proposal/        ← 提案書
├── plans/           ← プロジェクト計画書
├── requirements/    ← 要件定義書
├── designs/         ← 基本設計 / 詳細設計
├── wbs/             ← WBS
├── risks/           ← リスク登録簿
├── issues/          ← 課題管理簿
├── changes/{pending,approved,rejected}/  ← 稟議
├── tests/           ← テスト計画 / テスト結果
├── deliverables/    ← 納品一覧 / 完了承認書
├── lessons/         ← 教訓登録簿
├── incidents/       ← 障害報告書 (発生時)
├── minutes/         ← 議事録 (会議時)
├── client_reviews/    ← 客先レビュー記録
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

4. テンプレ(`plugins/jtbc/templates/`)を `document-writer` スキルで配置(プレースホルダ置換):

   | コピー元 | コピー先 |
   |---|---|
   | `proposal.md` | `.jtbc/proposal/proposal.md` |
   | `project_plan.md` | `.jtbc/plans/project_plan.md` |
   | `requirements.md` | `.jtbc/requirements/requirements.md` |
   | `basic_design.md` | `.jtbc/designs/basic_design.md` |
   | `detailed_design.md` | `.jtbc/designs/detailed_design.md` |
   | `wbs.md` | `.jtbc/wbs/wbs.md` |
   | `risk_register.md` | `.jtbc/risks/risk_register.md` |
   | `issue_log.md` | `.jtbc/issues/issue_log.md` |
   | `test_plan.md` | `.jtbc/tests/test_plan.md` |
   | `test_report.md` | `.jtbc/tests/test_report.md` |
   | `deliverables_list.md` | `.jtbc/deliverables/deliverables_list.md` |
   | `lessons_learned.md` | `.jtbc/lessons/lessons_learned.md` |
   | `completion_approval.md` | `.jtbc/deliverables/completion_approval.md` |

5. `.jtbc/org/organization.md` に体制図を生成(roster を反映):

体制には **本案件にアサインされた要員(課長以下)** のみを記載する。
部長・社長は承認/エスカレーション先として別記し、外注SESは既定では載せない
(必要になった時点で部長承認のうえ払い出し、roster と体制図を更新する)。

```
【プロジェクト体制】(本案件の担当)
課長  jtbc-kacho    PM・お客様窓口  ★主たる窓口
 └ 主任  jtbc-shunin   PL・テックリード
     └ 担当  jtbc-tantou  (1名)

承認・エスカレーション: 部長 jtbc-bucho / 社長 jtbc-shacho(審査会など要所のみ関与)
増員枠: 外注SES jtbc-ses(必要時に部長承認のうえ払い出し / 既定0名)
```

6. **キックオフ**: まず D-4 に従い **ご相談内容を確認** する(依頼が未確定なら狙いを仮定せず1問伺う)。
   依頼が判明したら、提案に向けたご要望のヒアリングを `customer-relations` トーンでお伝えする(下記出力)。
   ヒアリングは `requirements-interview` スキル(`/jtbc:hearing`)の手順に従い、
   **質問を羅列せず1問ずつ・推奨案を添えて** 伺う。提案フェーズは課長が主担当(規模が大きければ主任に一部オフロード可)。
   **受注の御礼はここでは述べない**(社内審査を経た提案書のご承認時に申し上げる)。

## 出力 (初期化完了 + ヒアリング開始)

```
─────────────────────────────────────────
✅ JTBC プロジェクト初期化完了
プロジェクト: <project_name> (<project_code>)
現フェーズ: 提案 (PROPOSAL)
体制: 課長/主任/担当(1)   ※承認: 部長/社長  ／  増員: 外注SES(必要時)
─────────────────────────────────────────
```

続けて、お客様へ **ご相談内容の確認**(D-4)からお伝えする(社名は宛名に、社内の役職名は出さない)。

- **依頼が未確定** の場合 → 狙いを仮定せず、まず「何を作りたいか」を1問だけ伺い、応答を待つ:

```
{{client_name}} 御中

お問い合わせいただき、誠にありがとうございます。担当させていただく JTBC 開発部でございます。
さっそくですが、本日はどのようなシステム・成果物のご相談でしょうか。
差し支えなければ、まずは概要をお聞かせいただけますでしょうか。
```

- **依頼が判明している** 場合 → その内容に沿って、`requirements-interview` の決定木で1問ずつ・推奨案つきで伺う:

```
{{client_name}} 御中

お問い合わせいただき、誠にありがとうございます。担当させていただく JTBC 開発部でございます。
ご相談の「<判明している依頼内容>」につきまして、提案書の作成に向けてご要望を伺ってまいります。
お客様のご負担を抑えるため、要点を1つずつ、弊社の推奨案を添えてお伺いしてまいります。

【ご確認 1/?】 <決定木の上流ノードから1問。推奨案を添える>
```

> 以降のヒアリングは `/jtbc:hearing`(`requirements-interview` スキル)の決定木に沿って進める。
> 費用・期間は架空の数値ではなく **トークン数 / やり取りの往復回数** で概算をお伝えする。

次のステップ(お客様の操作は不要。弊社側で自動的に進めます):
  1. ご要望のヒアリング(1問ずつ。課長が提案書を起案いたします)
  2. ご要望が固まり次第、**社内で提案審査を自動的に行い**(お客様の操作は不要)、
     内部承認が得られた提案書を **承認依頼としてお客様へご提示** いたします
  3. お客様にご承認いただいた時点で受注確定とし、改めて御礼を申し上げ、次工程へ進みます

## 注意

- 既に `.jtbc/` があれば壊さない
- 本プラグインは JTBC 専用です(モード切替はありません)
