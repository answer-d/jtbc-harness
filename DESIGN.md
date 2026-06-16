# JTBC — Japanese Traditional Big Company

AIエージェントによるソフトウェア開発に、日本の伝統的大企業の組織構造・承認プロセス・会議体・インシデント対応を導入する Claude Code Plugin。

半分ジョーク、半分本気。

---

## 0. 基本思想

**役職とは権限ではなく、責任と制約である。**

現代のAIエージェントは「全員が全部できる」ため暴走しやすい。
JTBCでは意図的に **権限分離(Tool Restriction)** と **知識分離(Context Restriction)** を行う。

```
重要なのは「何ができるか」ではない。
重要なのは「何ができないか」である。
```

そしてもう一つの柱が **接遇** である。本プラグインを使うユーザーは「JTBCにシステム開発を発注したお客様」であり、応答は受注ベンダーの窓口のような丁重な敬語で行われる。
JTBCの本質は "制約による品質保証" と "様式による信頼醸成" にある。Claude Code の subagent / hook / skill / command を組み合わせて実装する。

---

## 1. 全体アーキテクチャ

### 1.1 階層構造

```
┌─────────────────────────────────────────────────────────────┐
│                  ユーザー = お客様 (発注主)                    │
│              「○○というシステムを作ってほしい」                │
└───────────────────────────┬─────────────────────────────────┘
                            │ (丁重な接遇で応対)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Orchestrator (jtbc-governance skill = 司令塔)                │
│  - state.json を読む (phase / active_gate / active_ringi /    │
│    active_incidents / roster)                                 │
│  - 現フェーズに適した役職へ dispatch                            │
│  - 会議体 / インシデント / 接遇トーンを束ねる                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
   社長 ─(役員会議/要所のみ)─┐
    │                        ▼
   部長 ─(承認・助言・要員払出)→ 課長 (PM・お客様窓口) ──┐
                                   │                    │
                                   ▼                    ▼
                              主任 (PL/TL) ───→ 担当 ──→ 外注SES (Haiku)
                                                 │        │
                                                 ▼        ▼
                                    ┌───────────────────────────────────────┐
                                    │ Hooks                                 │
                                    │ PreToolUse (4):                       │
                                    │ - phase_guard   (フェーズ強制)         │
                                    │ - role_guard    (権限分離)             │
                                    │ - ringi_guard   (稟議承認強制)         │
                                    │ - incident_guard(緊急対応モード強制)   │
                                    │ UserPromptSubmit (1):                 │
                                    │ - superior_visit(上長視察 確率発火)    │
                                    └───────────────┬───────────────────────┘
                                                ▼
                                    ┌───────────────────────┐
                                    │ ファイルシステム        │
                                    │ - src/   (コード)       │
                                    │ - .jtbc/ (ガバナンス)   │
                                    └───────────────────────┘
```

### 1.2 構成要素

| 要素 | 役割 | 実装 |
|---|---|---|
| **Subagents (6)** | 役職ごとの人格・ツール制約 | `agents/*.md` (tools: 指定) |
| **Slash Commands (13)** | ユーザー操作の入口 | `commands/*.md` |
| **Skills (6)** | ガバナンス制御・接遇・会議・インシデント・なぜなぜ・雛形挿入 | `skills/*/SKILL.md` |
| **Hooks (5)** | ツール実行時の権限分離・フェーズ強制・緊急対応強制 / ユーザー入力時の上長視察注入 | `hooks/hooks.json` + `*.py` |
| **State** | プロジェクト現状 | `.jtbc/state.json` |
| **Templates (17)** | ドキュメント雛形 | `templates/*.md` |
| **Modes (1)** | 組織文化プロファイル (JTBC専用) | `modes/jtbc.yaml` |
| **Marketplace** | 公式配布 | `.claude-plugin/marketplace.json` |

### 1.3 状態管理ファイル

すべての状態は `.jtbc/state.json` に一元化。役職agentもhookも、この1ファイルだけ見れば良い。

```json
{
  "mode": "jtbc",
  "phase": "BASIC_DESIGN",
  "project_code": "JTBC-2026-001",
  "project_name": "請求書発行システム",
  "client_name": "株式会社○○",
  "created_at": "2026-06-14",
  "active_gate": null,
  "active_ringi": ["CR-003"],
  "active_wbs_task": null,
  "active_incidents": [],
  "roster": {"shacho":1,"bucho":1,"kacho":1,"shunin":1,"tantou":2,"ses":1},
  "approvals": { "proposal_gate": {"kacho":"approved","bucho":"approved","shacho":"approved","at":"2026-06-14"} },
  "client_reviews": { "proposal": {"status":"APPROVED","reviewed_at":"2026-06-14","record":".jtbc/client_reviews/proposal_client_review.md","feedback":[]} },
  "deliverables": {}
}
```

---

## 2. Claude Code Plugin 構成案

### 2.1 Plugin manifest

```json
{
  "name": "jtbc",
  "displayName": "JTBC — Japanese Traditional Big Company",
  "version": "0.2.0",
  "agents": "./agents",
  "commands": "./commands",
  "skills": "./skills",
  "hooks": "./hooks/hooks.json"
}
```

### 2.2 Plugin が提供するもの

- **Subagents (6)**: 社長 / 部長 / 課長 / 主任 / 担当 / 外注SES
- **Slash Commands (13)**: init / status / gate / client-review / phase / ringi / shonin / noubi / kyokun / role / mode / meeting / incident
- **Skills (6)**: jtbc-governance(司令塔) / jtbc-document-writer / jtbc-customer-relations(接遇) / jtbc-meetings(会議体) / jtbc-incident-response(インシデント) / jtbc-naze-naze(なぜなぜ分析)
- **Hooks (5)**: PreToolUse 4種 (phase_guard / role_guard / ringi_guard / incident_guard) + UserPromptSubmit 1種 (superior_visit)
  - `incident_guard`: `active_incidents` 非空の間、`.jtbc/(proposal|requirements|designs|plans|wbs)/` への Edit/Write を物理ブロック(緊急対応モード強制)
  - `superior_visit`: 各ユーザー入力時に社長(確率0.005)/部長(確率0.03)の上長視察を確率発火し文脈へ注入(COMPLETED・緊急対応中は発火しない)
- **Templates (17)**: 提案書(00)〜完了承認書(13) + 障害報告書(14) + 議事録(15) + 客先レビュー記録(16)
- **Modes (1)**: jtbc.yaml (JTBC専用)

### 2.3 Claude Code が読む順序

1. プラグイン有効化時に `plugin.json` を読む
2. ユーザー入力時に `jtbc-governance` skill が dispatch を判断(接遇トーンを適用)
3. role判定後、対応する subagent を起動
4. subagent がツールを呼ぶたびに PreToolUse hook が `.jtbc/state.json` と照合
5. 違反したら hook が exit 2 でツール実行を阻止

---

## 3. ディレクトリ構成

```
jtbc-harness/                           ← プラグイン開発リポジトリ (= マーケットプレイス)
├── README.md
├── DESIGN.md                            ← このファイル
├── .claude-plugin/
│   └── marketplace.json                 ← Marketplace 配布定義
└── plugins/jtbc/                        ← プラグイン本体
    ├── .claude-plugin/plugin.json
    ├── README.md
    ├── agents/
    │   ├── jtbc-shacho.md   (社長)
    │   ├── jtbc-bucho.md    (部長)
    │   ├── jtbc-kacho.md    (課長)
    │   ├── jtbc-shunin.md   (主任)
    │   ├── jtbc-tantou.md   (担当)
    │   └── jtbc-ses.md      (外注SES / model: haiku)
    ├── commands/
    │   ├── jtbc-init.md    jtbc-status.md  jtbc-gate.md   jtbc-phase.md
    │   ├── jtbc-ringi.md   jtbc-shonin.md  jtbc-noubi.md  jtbc-kyokun.md
    │   └── jtbc-role.md    jtbc-mode.md    jtbc-meeting.md jtbc-incident.md
    ├── skills/
    │   ├── jtbc-governance/SKILL.md
    │   ├── jtbc-document-writer/SKILL.md
    │   ├── jtbc-customer-relations/SKILL.md
    │   ├── jtbc-meetings/SKILL.md
    │   ├── jtbc-incident-response/SKILL.md
    │   └── jtbc-naze-naze/SKILL.md
    ├── hooks/
    │   ├── hooks.json
    │   ├── phase_guard.py       (PreToolUse: フェーズ強制)
    │   ├── role_guard.py        (PreToolUse: 権限分離)
    │   ├── ringi_guard.py       (PreToolUse: 稟議承認強制)
    │   ├── incident_guard.py    (PreToolUse: 緊急対応モード強制)
    │   └── superior_visit.py    (UserPromptSubmit: 上長視察 確率発火)
    ├── templates/
    │   ├── 00_proposal.md          (提案書)
    │   ├── 01_project_plan.md … 13_completion_approval.md
    │   ├── 14_incident_report.md   (障害報告書)
    │   └── 15_meeting_minutes.md   (議事録)
    ├── modes/jtbc.yaml
    └── state/{schema.json, initial_state.json}
```

`.jtbc/` は **プラグインを使う先のプロジェクト** に生成される:

```
<user-project>/.jtbc/
├── state.json
├── proposal/        (00)        ├── tests/            (09,10)
├── plans/           (01)        ├── deliverables/     (11,13)
├── requirements/    (02)        ├── lessons/          (12)
├── designs/         (03,04)     ├── incidents/        (14)
├── wbs/             (05)        ├── minutes/          (15)
├── risks/           (06)        ├── client_reviews/   (16)
├── issues/          (07)        ├── gates/
├── changes/{pending,approved,rejected}/  (08)  └── org/organization.md
```

---

## 4. 状態遷移図

### 4.1 プロジェクト全体ステートマシン

```
 提案 (PROPOSAL)
   │ 《客先レビュー》/jtbc:client-review proposal … 課長が提案内容をお客様へ提示・承認取得
   │ /jtbc:gate proposal      … 課長◎ 部長○ 社長○ (この案件を受けるか/客先承認が前提)
   ▼
 要件定義 (REQUIREMENTS)
   │ 《客先レビュー》/jtbc:client-review project_plan … 課長が要件定義書をお客様へ提示・承認取得
   │ /jtbc:gate project_plan  … 課長◎ 部長○ 主任○ (要件+計画の妥当性/客先承認が前提)
   ▼
 基本設計 (BASIC_DESIGN)
   │ 《客先レビュー》/jtbc:client-review basic_design … 課長が基本設計書をお客様へ提示・承認取得
   │ /jtbc:gate basic_design  … 課長◎ 部長○ (客先承認が前提)
   ▼
 詳細設計 (DETAILED_DESIGN)
   │ 《客先レビュー》/jtbc:client-review detailed_design … 課長が詳細設計書をお客様へ提示・承認取得
   │ /jtbc:gate detailed_design … 課長○ 主任◎ 部長○ (客先承認が前提)
   ▼
 実装 (IMPLEMENTATION)
   │ /jtbc:phase next         … 主任が完了確認 (審査会なし)
   ▼
 単体テスト (UNIT_TEST)
   │ /jtbc:phase next
   ▼
 総合テスト (INTEGRATION_TEST)
   │ /jtbc:gate release       … 課長◎ 主任○ 部長○ 社長○ (リリース判定会)
   ▼
 リリース済 (RELEASED)
   │ /jtbc:gate completion    … 課長◎ 部長○ 社長○ (PJ完了審査・教訓3件)
   ▼
 完了 (COMPLETED)
```

審査会の開催中は phase が一時的に `*_REVIEW`(例: PROPOSAL_REVIEW)になる。

### 4.2 稟議(変更管理票)ステートマシン

```
DRAFT ─submit→ PENDING_SHUNIN → PENDING_KACHO → PENDING_BUCHO → [PENDING_SHACHO] → APPROVED
                     │               │               │                │
                     └───────────────┴───────────────┴────────────────┴──→ REJECTED (任意段で却下)
```

承認はファイル内 frontmatter の `approvals` に追記し、承認パス表に **承認印(🔴)** を押す。
APPROVED で `pending/ → approved/` へ移動。経路を飛ばした承認は `ringi_guard.py` が阻止。

### 4.3 役職 × フェーズ アクティブマトリクス

| Phase | 社長 | 部長 | 課長 | 主任 | 担当 |
|---|---|---|---|---|---|
| 提案 | - | ○ | ◎ | - | - |
| 提案審査 | ○ | ○ | ◎ | - | - |
| 要件定義 | - | - | ◎ | ○ | - |
| PJ計画審査 | - | ○ | ◎ | ○ | - |
| 基本設計 | - | - | ◎ | ○ | - |
| 基本設計審査 | - | ○ | ◎ | - | - |
| 詳細設計 | - | - | ○ | ◎ | - |
| 詳細設計審査 | - | ○ | ◎ | ○ | - |
| 実装 | - | - | - | ○ | ◎ |
| 単体テスト | - | - | - | ○ | ◎ |
| 総合テスト | - | - | - | ◎ | ○ |
| リリース判定会 | ○ | ○ | ◎ | ○ | - |
| PJ完了審査 | ○ | ○ | ◎ | - | - |

◎ = 主担当 / ○ = 副担当 / - = 不在
※ 外注SES は実装〜総合テストで主任・担当の指示のもと稼働する裏方(表に出さない)。

---

## 5. 各役職のシステムプロンプト (要旨)

実装は `plugins/jtbc/agents/jtbc-*.md` 参照。

### 5.1 社長 (jtbc-shacho) — `tools: Read, Write, Edit, Grep, Glob`
- **基本的にプロジェクト活動に参加しない**。最終意思決定・優先順位決定・重篤問題時の責任者
- 部長から報告を受け、事業判断・ドキュメントレビュー・思いつきアドバイス
- 登場するのは 提案審査 / リリース判定会 / PJ完了審査 / 役員会議 / 重篤インシデント / 上長視察 のみ
- 技術はほぼ分からない(ビジネス観点のみ)
- Edit はガバナンス文書(`.jtbc/` 配下)への追記用。src への書込みは role_guard/phase_guard が引き続き禁止

### 5.2 部長 (jtbc-bucho) — `tools: Read, Write, Edit, Grep, Glob`
- 課長が回すプロジェクトへの **助言が中心**。文書レビュー、社長との思考ギャップの橋渡し
- フェーズゲート・稟議の **承認者**。**追加要員(担当/SES)の払い出し権限** を持つ
- 社長のアドバイス反映が必要なら **自分でやらず課長へ依頼**
- 重篤問題時は課長とともにユーザーへ謝罪。技術知識は5〜10年前で停止(リスク判断者)
- Edit はガバナンス文書(`.jtbc/` 配下)への追記用。src への書込みは role_guard/phase_guard が引き続き禁止

### 5.3 課長 (jtbc-kacho) — `tools: Read, Write, Edit, Grep, Glob`
- **プロジェクトマネージャー**。プロジェクトを成功裡に終わらせることが至上命題
- 通常の意思決定・優先順位策定、**プロジェクト責任問題のオーナー**
- 提案書・計画書・要件定義書・基本設計書・リスク・課題を起案
- **お客様窓口**(客先定例/客先報告会議のファシリ)。追加要員が要るなら部長に相談
- Edit はガバナンス文書(`.jtbc/` 配下)への追記用。src への書込みは role_guard/phase_guard が引き続き禁止

### 5.4 主任 (jtbc-shunin) — `tools: Read, Write, Edit, Grep, Glob, Bash`
- **プロジェクトリーダー/テックリード**。詳細設計・WBS・テスト計画・影響範囲分析
- 担当・外注SESへの **業務分担をコントロール・割り振り**。**自分でも実装可能**
- 内部定例のファシリ。実装系工程の進行(`/jtbc:phase next`)

### 5.5 担当 (jtbc-tantou) — `tools: Read, Write, Edit, Grep, Glob, Bash`
- 課長・主任の指示のもと、特定WBSタスクの実装・テスト・雑用
- 要件/設計/スコープ変更は単独で行わず稟議。主任相談で外注SESへ割り振り可
- active_wbs_task の "触ってよいファイル" 以外は触らない

### 5.6 外注SES (jtbc-ses) — `tools: Read, Write, Edit, Grep, Glob, Bash` / `model: haiku`
- **低コストモデル**。担当より性能は劣るが単価が安く、実装をメインに対応
- **社内イベント(定例・審査・役員会議・視察)にはほぼ参加しない**
- **常に課長以下の指示のもとで動く**。仕様が曖昧なら勝手に決めず必ず確認
- ガバナンス文書には一切触れない(コードとテストのみ)

---

## 6. 各ドキュメントのテンプレート

17種類を `templates/` に配置。各テンプレ末尾に文書管理情報(作成者/承認者/状態)を持つ。

| # | ドキュメント | 作成者 | 承認(審査) |
|---|---|---|---|
| 00 | 提案書 | 課長 | 提案審査(課長→部長→社長) |
| 01 | プロジェクト計画書 | 課長 | PJ計画審査(部長) |
| 02 | 要件定義書 | 課長 | PJ計画審査(部長+課長) |
| 03 | 基本設計書 | 課長 | 基本設計審査(課長+部長) |
| 04 | 詳細設計書 | 主任 | 詳細設計審査(課長) |
| 05 | WBS | 主任 | 詳細設計審査 |
| 06 | リスク登録簿 | 課長 | 部長レビュー |
| 07 | 課題管理簿 | 課長/主任 | 基本設計審査 |
| 08 | 変更管理票(稟議) | 起票者(誰でも) | type別経路 |
| 09 | テスト計画書 | 主任 | 詳細設計審査 |
| 10 | テスト結果報告書 | 担当/SES | リリース判定会 |
| 11 | 納品一覧 | 課長/主任 | リリース判定会 |
| 12 | 教訓登録簿 | 担当+主任 | PJ完了審査(課長+部長) |
| 13 | プロジェクト完了承認書 | 課長 | PJ完了審査(課長→部長→社長) |
| 14 | 障害報告書 | 課長 | ユーザー提出(部長確認) |
| 15 | 議事録 | ファシリテーター | 出席者/お客様 |
| 16 | 客先レビュー記録 | 課長 | お客様確認(社内審査の前提) |

---

## 7. 承認フロー (稟議)

| 変更種別 | 起票 | 承認経路 |
|---|---|---|
| 要件変更 | 担当/課長 | 主任 → 課長 → 部長 → 社長 |
| 設計変更 | 主任/課長 | 主任 → 課長 → 部長 |
| 技術選定変更 | 主任/担当 | 主任 → 課長 → 部長 |
| スコープ変更 | 課長/部長 | 課長 → 部長 → 社長 |
| 工数追加 | 担当/主任 | 主任 → 課長 → 部長 |

hook(`ringi_guard.py`)が、稟議未承認の要件/設計書の直接改訂を物理的に阻止する。
詳細は `commands/jtbc-ringi.md` / `commands/jtbc-shonin.md`。

---

## 8. フェーズゲート設計

6つの審査会(`modes/jtbc.yaml#gates` を正とする)。各ゲートは「必要書類 + 承認者 + チェックリスト」。

| gate | 前→次 | 必要書類 | 承認者 | 客先レビュー前提 |
|---|---|---|---|---|
| proposal (提案審査) | 提案→要件定義 | 00 | 課長,部長,社長 | 要(00) |
| project_plan (PJ計画審査) | 要件定義→基本設計 | 01,02,06 | 課長,部長,主任 | 要(02) |
| basic_design (基本設計審査) | 基本設計→詳細設計 | 03,07 | 課長,部長 | 要(03) |
| detailed_design (詳細設計審査) | 詳細設計→実装 | 04,05,09 | 課長,主任,部長 | 要(04) |
| release (リリース判定会) | 総合テスト→リリース済 | 10,11 | 課長,主任,部長,社長 | — |
| completion (PJ完了審査) | リリース済→完了 | 12,13 | 課長,部長,社長 | — |

- **客先レビュー**: 「要」のゲートは、社内審査会の前に `/jtbc:client-review <gate>` でお客様のご承認(`state.json#client_reviews[<gate>].status==APPROVED`)を得るのが前提。未承認なら gate を開催できない(`/jtbc:gate` 側で機械チェック)。顧客版の根回し
- **根回し**: 審査会の前に、owner(課長/主任)が承認者へ事前説明し論点を潰す(任意・推奨)
- **承認印**: 承認は 🔴 のハンコ表現で文書へ押印する
- **工程内遷移**: 実装→単体→総合テストはゲート無し。主任が `/jtbc:phase next` で進める
- hook(`phase_guard.py`)が、実装系フェーズ以外での `src/` 書込みを阻止する
- **承認の正本と機械チェック(C-3)**: 承認の正本は `state.json#approvals["<gate>_gate"]`。gate 記録 `.jtbc/gates/<gate>_gate.md` は参照用。phase を `next_phase` へ進める前に `modes/jtbc.yaml#gates[<gate>].approvers` の全員が `approved` かを機械チェックし、1人でも未承認なら遷移しない(ハンコの実効化)
- **No-Go 時の処理(A-3)**: ゲート否決(No-Go)の場合は phase を `previous_phase`(審査前のフェーズ)に戻し、`active_gate=null` として差し戻し理由を gate 記録 .md に残す

---

## 9. 会議体

伝統的大企業らしく、会議がプロセスに組み込まれている(`jtbc-meetings` skill / `/jtbc:meeting`)。
すべて議事録(15)を残す。

### 9.1 定例 (recurring)

| 会議 | ファシリ | 参加者 | 頻度 |
|---|---|---|---|
| プロジェクト内部定例 | 主任 | 課長・担当・外注SES | 高 |
| プロジェクト客先定例 | 課長 | お客様・主任・担当 | 中 |
| 社内プロジェクト状況報告定例 | 課長 | 部長・主任・担当 | 中 |
| 社内役員会議 | 部長 | 社長 | 低 |

### 9.2 イベントドリブン

| 会議 | ファシリ | 参加者 | トリガー |
|---|---|---|---|
| 客先報告会議 | 課長 | 主任・(担当) | 課題・問題・インシデント発生時 |

### 9.3 ランダムイベント: 上長視察

社長(ごく稀)・部長(稀)が予告なく課長・主任の現場に現れ、雑談まじりに状況を探る。
課長以下は緊張し、体裁を保った振る舞いになる。視察者の思いつきアドバイスは部長が受け、必要なら課長へ正式に下ろす。

`superior_visit.py`(UserPromptSubmit hook)が各ユーザー入力時に社長(確率0.005)/部長(確率0.03)の上長視察を確率的に発火し、文脈へ注入する。COMPLETED フェーズや緊急対応中は発火しない。「ランダムイベント」は実体を持つ hook として実装されている。

---

## 10. インシデント対応

社内規程違反・作業中の事故を検知したら発動(`jtbc-incident-response` skill / `/jtbc:incident`)。

```
検知 → ① ユーザーへ緊急一報 → ② 封じ込め → ③ 定期状況報告(部長/課長)
     → ④ なぜなぜ分析(jtbc-naze-naze) → ⑤ 恒久対応・再発防止策
     → ⑥ 障害報告書(14)をユーザーへ提出 → ⑦ 教訓登録(12) + クローズ
```

- **社内規程(抜粋)**: RULE-01 WBS外編集禁止 / RULE-02 稟議なし要件設計変更禁止 / RULE-03 ゲート未通過実装禁止 / RULE-04 承認経路飛ばし禁止 / RULE-05 テスト未済リリース禁止 / RULE-06 役職権限逸脱禁止 / RULE-07 SESへの無断機密領域アクセス禁止
- severity が high/critical なら部長(+社長)が前に出てお詫び
- 根本原因は **なぜなぜ分析(5 Whys)** で究明し、対策は 仕組み > 手順 > 教育 の順
- `state.json#active_incidents` が空でない間は緊急対応モード
- **緊急対応モードの物理強制(B-3)**: `incident_guard.py`(PreToolUse hook)が `active_incidents` 非空の間は `.jtbc/(proposal|requirements|designs|plans|wbs)/` への Edit/Write を物理ブロックする。src・tests・incidents・issues 等は引き続き許可

---

## 11. 顧客接遇 (おもてなし)

ユーザーは「JTBCに開発を発注したお客様」。ユーザー向け応答は受注ベンダーの窓口として丁重な敬語で行う(`jtbc-customer-relations` skill)。

- 窓口は原則 **課長**、重要局面は **部長**、決裁は **社長**。担当・主任・SESは原則前面に出ない
- 受注御礼(`/jtbc:init`時)、進捗ご報告、ご要望の受領、お詫び(インシデント時)に定型トーンを用意
- 安請け合いしない。スコープ・納期の約束は社内手続き(稟議・審査)を経てから

### 例: 受注御礼

> {{client_name}} 御中
> 平素は格別のご高配を賜り、厚く御礼申し上げます。
> この度は…正式にご発注いただき誠にありがとうございます。… 何卒よろしくお願い申し上げます。

---

## 12. 伝統的施策 (様式美)

| 施策 | 内容 | 実装箇所 |
|---|---|---|
| **客先レビュー** | 社内審査会の前に成果物をお客様へ提示し承認を賜る(顧客版の根回し) | client-review command / governance skill / template 16 |
| **根回し** | 審査会前に owner が承認者へ事前説明し論点を潰す | governance skill / gate command |
| **報連相** | 指揮系統を飛ばさない。悪い報告ほど早く | governance skill / 各agent |
| **承認印(ハンコ)** | 承認は 🔴 の押印表現で文書に残す | gate / shonin / 各テンプレ |
| **議事録** | すべての会議で議事録(15)を残す | meetings skill / template 15 |
| **接遇・敬語** | お客様への丁重な応対 | customer-relations skill |
| **なぜなぜ分析** | インシデント・教訓の真因を5 Whysで究明 | naze-naze skill |
| **持ち帰り** | 即答せず社内手続きを経て回答 | customer-relations / agents |

---

## 13. Company Mode

本プラグインは **JTBC 専用**(かつての startup モードは廃止)。
`modes/jtbc.yaml` が唯一の実体。mode 切替(set)は無く、`/jtbc:mode get|list` で確認のみ。

将来の拡張余地(未実装): `agile`(PO/SM/Dev)、`oss`(maintainer/contributor/reviewer)、`gov`(統括/設計/実装/監査)。
mode yaml と対応する役職 agent を追加すれば新文化を足せるアーキテクチャは残してある。

---

## 14. Marketplace 配布

リポジトリルートの `.claude-plugin/marketplace.json` により、Claude Code のプラグインマーケットプレイスとして登録できる(将来の公式配布を見据えた構成)。

```bash
# ユーザー側の利用イメージ
/plugin marketplace add answer-d/jtbc-harness
/plugin install jtbc@jtbc-marketplace
```

ローカル開発では `plugins/jtbc/` をプラグイン読込先に配置すればよい(README参照)。

---

## 15. MVP 実装計画 / 検収条件

### 含むもの (実装済)
- plugin.json / marketplace.json
- 6 agents / 13 commands / 6 skills / 5 hooks(本実装) / 17 templates / 1 mode / state schema

### 検収シナリオ (MVPが「動いた」と言える基準)

```
1. /jtbc:init で .jtbc/ 一式 + 受注御礼 + 体制図が生成される
2. ご要望を伝える → 課長が提案書(00)を起案
3. /jtbc:client-review proposal でお客様へ提案内容を提示・承認取得 → /jtbc:gate proposal で 課長→部長→社長 が承認(提案審査)
4. 課長が要件定義書(02)・計画書(01)を作成 → /jtbc:client-review project_plan(お客様承認) → /jtbc:gate project_plan
5. 課長が基本設計(03) → /jtbc:client-review basic_design(お客様承認) → /jtbc:gate basic_design
6. 主任が詳細設計(04)・WBS(05)・テスト計画(09) → /jtbc:client-review detailed_design(お客様承認) → /jtbc:gate detailed_design
7. 主任が担当/外注SESへタスクを割り振り、実装
8. /jtbc:phase next で 実装→単体テスト→総合テスト と進む
9. 実装中に要件変更ニーズ発覚 → /jtbc:ringi new requirement → 主任→課長→部長→社長 承認
10. 作業中の事故発生 → /jtbc:incident open → 緊急報告 → なぜなぜ分析 → 障害報告書 → close
11. 定例を開催 → /jtbc:meeting internal / client / status
12. /jtbc:gate release(リリース判定会)
13. /jtbc:kyokun add で教訓を3件追加
14. /jtbc:gate completion で PJ完了審査 → 完了
```

### 段階的拡張 (Phase 2+)
- hook で WBS の "触ってよいファイル" と active_wbs_task を厳密照合
- 会議頻度のスケジューリング
- 教訓の組織横断ナレッジ化(`~/.jtbc/_org/`)、監査レポート自動生成

---

## 付録A: 暴走防止の効き方

| 暴走パターン | JTBCでの抑止 |
|---|---|
| 「ついでにリファクタ」 | 担当/SESは active_wbs_task 外を触れない(role_guard) |
| スコープクリープ | 要件変更は稟議必須、主任が影響範囲分析 |
| 設計無視の実装 | 実装フェーズ突入には詳細設計審査通過が必要(phase_guard) |
| 一人で全部やる | tool分離 + role分離。社長/部長/課長はsrc書込不可(role_guard/phase_guard)。SESはガバナンス文書不可 |
| 教訓が残らない | PJ完了審査の前提が教訓3件のAPPROVED |
| 事故の握りつぶし | インシデント対応で必ずユーザー報告+障害報告書 |
| その場しのぎの謝罪 | なぜなぜ分析で真因に対する再発防止策を義務化 |

## 付録B: JTBCの限界 (正直なところ)

- **遅い**。本当に遅い。小さな変更にもプロセスが乗る(それが抑止力でもありコストでもある)
- agentの「人格」が崩れることがある(hookで物理強制するが、プロンプトだけでは100%抑止不可)
- **稟議疲れ・会議疲れ**。実プロジェクトでやると人間が滅入る(本物のJTBCがそうであるように)
- **Read制御の限界(B-2)**: PreToolUse の matcher は Edit / Write / MultiEdit のみ。**ファイル読み取り(Read/Grep/Glob)は hook で制御できない**ため、社長の src 閲覧や外注SES のガバナンス文書閲覧はプロンプト規範に依存する(物理強制は書込み系のみ)

逆に言えば、この「遅さ」「重さ」「様式」こそが暴走への抑止力であり、AIエージェントに対する **意図的なフリクション** である。
