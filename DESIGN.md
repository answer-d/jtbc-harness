# JTBC — Japanese Traditional Big Company

AIエージェントによるソフトウェア開発に、日本の伝統的大企業の組織構造・承認プロセス・会議体・インシデント対応を導入する Claude Code Plugin。

半分ジョークです。

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

役職は **フェーズ単位のエージェントチーム(Agent Teams)** として運用する。司令塔(=営業)が **lead**(セッションを通して継続)、各フェーズの実働役職が **teammate** として独立コンテキストを持って報連相し、**ゲート通過で畳む**(継続はディスク上の役職メモが担う)。`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` が無効な環境では、同じ役職定義を **都度起動のサブエージェント** として使うフォールバックで動く(ガバナンスは同一)。詳細は §1.4。

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
│  Orchestrator (governance skill = 司令塔)                │
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
                              主任 (PL/TL) ───→ 担当
                                                 │
                                                 ▼
                                    ┌───────────────────────────────────────┐
                                    │ Hooks                                 │
                                    │ PreToolUse (6):                       │
                                    │ - phase_guard   (フェーズ強制)         │
                                    │ - role_guard    (権限分離)             │
                                    │ - ringi_guard   (稟議承認強制)         │
                                    │ - incident_guard(緊急対応モード強制)   │
                                    │ - state_guard   (phase移行をPMOに限定) │
                                    │ - team_guard    (常駐teammate強制)     │
                                    │ UserPromptSubmit (2):                 │
                                    │ - superior_visit  (上長視察 確率発火)  │
                                    │ - approval_sync_guard(承認転記漏れ通知)│
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
| **Teammates / Subagents (6)** | 5役職(社長〜担当)+ PMO(プロセスの門番)。teams 有効環境では常駐 teammate、無効環境ではサブエージェントとして同一定義を再利用 | `agents/*.md` (tools: 指定) |
| **Slash Commands (4)** | ユーザー操作の入口(init/status/hearing/client-review。社内作業は governance が自動実行) | `commands/*.md` |
| **Skills (8)** | ガバナンス制御・接遇・要望ヒアリング・会議・インシデント・なぜなぜ・雛形挿入・役職メモ | `skills/*/SKILL.md` |
| **Hooks (11)** | ツール実行時の権限分離・フェーズ強制・緊急対応強制・フェーズ移行のPMO限定・役職メモ書込みの自動承認 / ユーザー入力時の上長視察注入・承認転記漏れ通知 / フェーズ足跡の自動記録・メモ記録の促し | `hooks/hooks.json` + `*.py` |
| **State** | プロジェクト現状 | `.jtbc/state.json` |
| **Templates (17)** | ドキュメント雛形 | `templates/*.md` |
| **Config (1)** | 組織文化プロファイル (JTBC専用) | `config/jtbc.yaml` |
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
  "roster": {"shacho":1,"bucho":1,"kacho":1,"shunin":1,"tantou":2},
  "approvals": { "proposal_gate": {"kacho":"approved","bucho":"approved","shacho":"approved","at":"2026-06-14"} },
  "client_reviews": { "proposal": {"status":"APPROVED","reviewed_at":"2026-06-14","record":".jtbc/client_reviews/proposal_client_review.md","feedback":[]} },
  "deliverables": {}
}
```

### 1.4 役職の運用: フェーズ単位エージェントチーム (Agent Teams)

役職は **フェーズ単位の teammate** として運用する。各フェーズの開始でそのフェーズの実働役職を起こし、
**ゲート通過時に畳む**。継続(記憶)はディスク上の役職メモ(`.jtbc/memory/<役職>/`)が担い、役職は
フェーズ毎にインスタンスを作り直す。これにより「同時に生きている teammate = 現フェーズのチーム」に
限定され、idle 居座りが積み上がらない。

> **なぜ常駐(セッション全体)でなくフェーズ単位か**: in_process teammate は `Done` でも自然終了せず、
> 確実な解散は lead からの `shutdown_request` のみ(公式機能。`TaskStop` は in_process に効かない)。
> Agent Teams は「チーム=セッション・スコープ」で、個別 teammate の graceful shutdown も公式サポート
> される(`agent-teams.md`)。そこで PJ 全体を1チームで抱える代わりに、解散点を **頻繁で明確なフェーズ
> ゲート** に置く。lead(営業=単一の客窓口)はセッションを通して継続し、実働ロールだけをフェーズ毎に
> 入れ替える。teardown の実挙動は E2E 2回で確認済み(idle ~1s / busy 数〜十数秒)。

- **lead = 司令塔(営業) = Human Gateway**: メインセッションがチームの lead(生涯固定)。**お客様との
  対話(ヒアリング・ご提示・ご承認・ご報告)はすべて lead が直接担う**。各役職の spawn とオーケストレーションも担う。
- **【最重要】Human Gateway: お客様窓口は lead 一本**: teammate にお客様対応を渡さない(teammate は逐次対話を
  保持できず idle で止まる/中継が壊れるため。実機で確認済みの不安定さ)。**裏方 teammate がお客様の判断を
  要する点に当たったら、お客様に直接聞かず lead へ質問を上げ、lead が複数論点を束ねてまとめてお客様へ確認** する
  (往復を最小化)。teams は **裏方の並行作業**(起案・審査・並行承認・設計)に使い、対お客様の窓口は1つに固定する。
- **teammates = 5役職(裏方)**: 社長/部長/課長/主任/担当 を、`agents/jtbc-*.md` の定義名を指定して
  teammate として spawn。teammate は定義の `tools`/`model`/人格を継承する。
- **フェーズ単位の常駐(寿命=フェーズ)**: 各フェーズ開始でそのフェーズの実働役職を spawn し、フェーズ内は
  生かして SendMessage で回し、**ゲート通過で畳む**。次フェーズで必要になれば改めて spawn し、前フェーズの
  引き継ぎメモを読ませて cold start を埋める。実働は 提案/要件/基本設計=課長、詳細設計=主任(+課長レビュー)、
  実装・テスト=主任+担当。承認者(部長/社長)・PMO は **用が生じた時点で都度起こして畳む**
  (構成表と手順は `skills/governance/SKILL.md`「フェーズ・ライフサイクル」を正とする)。
- **フェーズ境界の解散手順**: ゲート通過時、lead は各実働役職へ ① 引き継ぎメモ(`.jtbc/memory/<役職>/`)を
  書かせ → ② `shutdown_request` を送り → ③ `~/.claude/teams/session-*/config.json#members` から消えるまで
  ポーリング確認 → ④ PMO が `state.json#phase` を進めて畳む → ⑤ 次フェーズの役職を spawn。`TaskStop` は
  in_process teammate に効かないため使わない。
- **報連相 = mailbox**: teammate 同士は **誰とでも** 直接メッセージできる(ハーネスは宛先を制限しない)。
  やり取り自体は縛らず、PM 規律として **指示・承認・エスカレーション(意思決定)は指揮系統**(社長⇄部長⇄課長⇄主任⇄担当)
  **を尊重** する点のみを課す。情報共有・確認の横連携は妨げない。lead が意思決定系統の乱れ(勝手な承認・指示の飛ばし)を是正。
- **入れ子チーム禁止**: teammate は部下を spawn できない。社長〜担当と PMO はすべて lead が spawn する
  (階層は spawn 木ではなくメッセージ規律で表現)。
- **物理ガバナンスは無改修で有効**: teammate は別インスタンスだが、PreToolUse payload に
  `agent_type`(= frontmatter name, 例 `jtbc-kacho`)が乗り、`role_guard` 等の exit 2 ブロックも届く
  (実機確認済み)。**チーム化してもガバナンスの効き方は変わらない**。
- **フォールバック**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 無効時は、同じ役職定義を `Agent` ツールの
  都度起動(一発実行)で使う。常駐による記憶継続のみ失われ、起案/承認/振り分け/ガバナンスは同一。
- **寿命**: teammate はセッション内のみ。`/resume` では復元されないため、再開時に lead が現 phase に
  応じて必要役職を再 spawn する。

実行ロジックの正本は `skills/governance/SKILL.md`「役職の運用」。

### 1.5 役職メモ (永続記憶 / Per-Role Memory)

エージェントの作業記憶は **揮発的**(サブエージェントは役目を終えると消え、常駐 teammate も
セッション終了・`/resume` で失われる)。そこで各役職は自分の知見を `.jtbc/memory/<役職>/` に
書き出して永続化する。コールドスタートの新インスタンスでも起動時に読み直せば文脈を再構築でき、
組織としての継続性が保たれる(プロジェクトの正本は `state.json` と正式文書。メモはそこに載らない
**役職固有の非自明な作業知** だけを持つ — 重複させない)。

- **起動時に読む(リハイドレート)**: 役職は最初に `.jtbc/memory/<役職>/INDEX.md` を読み、過去の決定・前提・つまずきを思い出す。
- **要所で確認なく書く**: 決定・理由・前提・つまずき等を得たら即 `.jtbc/memory/<役職>/<slug>.md` に記録。
  書込み許可は `memory_grant` フックが **自動承認** するため、ユーザーは settings.json を触らない
  (プラグインは権限ルールを配布できないが、権限判定フックは配布できる Claude Code の仕様を利用)。
- **フェーズ足跡は自動**: `memory_timeline`(PostToolUse)が phase 変更を `_timeline.md` に冪等追記。
- **書き忘れの促し**: `memory_reminder`(SubagentStop)が知識役職のメモ未記録を通知(非ブロッキング)。
- **権限分離**: 各役職は自分の `.jtbc/memory/<役職>/` のみ書ける(他役職メモは `memory_grant` が deny)。

正本は `skills/role-memory/SKILL.md`。

---

## 2. Claude Code Plugin 構成案

### 2.1 Plugin manifest

```json
{
  "name": "jtbc",
  "displayName": "JTBC — Japanese Traditional Big Company",
  "version": "0.4.0"
}
```

> `agents/` `commands/` `skills/` `hooks/hooks.json` は規約ディレクトリとして
> **自動検出**されるため、manifest にパスキーは書かない(明示すると hooks の二重ロード等の
> 検証エラーになる)。

### 2.2 Plugin が提供するもの

- **Teammates / Subagents (6)**: 社長 / 部長 / 課長 / 主任 / 担当 + **PMO**(プロセスの門番。フェーズ移行の唯一の実行者)。teams 有効時は常駐 teammate、無効時はサブエージェント。定義は同一 `agents/jtbc-*.md`
- **Slash Commands (4)**: init / status / hearing / client-review
  - ※ お客様(発注者)が直接操作するのはこの4つだけ。**社内作業はすべて司令塔(governance)が自動実行** する:
    内部審査(ゲート)・変更管理(稟議)・工程内遷移・会議体・インシデント対応・役職振り分け・納品物整備・教訓登録。
    (旧 gate / ringi / shonin / phase / meeting / noubi / kyokun / role / mode コマンドは撤去済み)
  - client-review は通常、内部承認に続けて自動発火する(手動再提示用にコマンドを残置)。
- **Skills (8)**: governance(司令塔) / document-writer / customer-relations(接遇) / requirements-interview(要望ヒアリング) / meetings(会議体) / incident-response(インシデント) / naze-naze(なぜなぜ分析) / memory(役職メモ)
- **Hooks (11)**: PreToolUse 7種 (memory_grant / phase_guard / role_guard / ringi_guard / incident_guard / state_guard / team_guard) + UserPromptSubmit 2種 (superior_visit / approval_sync_guard) + PostToolUse 1種 (memory_timeline) + SubagentStop 1種 (memory_reminder)
  - `memory_grant`: `.jtbc/memory/<役職>/` への書込みを **自動承認**(permissionDecision: allow)し、ユーザーが settings.json に許可を書かずとも役職が確認なしでメモを残せる(バックグラウンド・エージェントの自動拒否も回避)。他役職のメモへの書込みは deny。詳細は `skills/role-memory/SKILL.md`
  - `memory_timeline`: `state.json#phase` 変更時に `.jtbc/memory/_timeline.md` へ「実時刻・役職・新フェーズ」を冪等に追記(決定論的タイムライン)
  - `memory_reminder`: 知識生産役職(課長/主任/部長/PMO)がメモ未記録のまま応答を終えたとき、随時記録を促す(通知のみ・非ブロッキング)
  - `team_guard`: teams 有効環境(`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`)で jtbc 役職を一発実行(`subagent_type` のみ・`run_in_background` 無し)で spawn しようとすると物理ブロックし、常駐 teammate 起動へ誘導(司令塔の「一発実行への退化」を物理担保。teams 無効環境では素通り)
  - `incident_guard`: `active_incidents` 非空の間、`.jtbc/(proposal|requirements|designs|plans|wbs)/` への Edit/Write を物理ブロック(緊急対応モード強制)
  - `state_guard`: `.jtbc/state.json` の `phase` 変更を **(A)権限: PMO(`jtbc-pmo`)以外は物理ブロック** + **(B)プロセス: 移行先ゲートの事前条件(ゲート承認者全員 approved・客先承認 APPROVED・必要書類が雛形でなく記入済み)を満たさなければ PMO であってもブロック**。審査スキップ・客先承認スキップ・空テンプレのまま前進を物理的に防ぐ(approvals 等 phase 以外の更新は素通り)
  - `superior_visit`: 各ユーザー入力時に社長(確率0.005)/部長(確率0.03)の上長視察を確率発火し文脈へ注入(COMPLETED・緊急対応中は発火しない)
  - `approval_sync_guard`: 各ユーザー入力時に gate 記録(`.jtbc/gates/<gate>_gate.md`)の押印(🔴・実日付)を走査し、承認の正本 `state.json#approvals` へ未転記の承認があればリード/PMO へ転記を促す(非ブロッキング。承認者役職は state.json を直接書けない=role_guard が物理担保するため、転記漏れは司令塔の認知漏れになりやすく、これを物理検出で補う)
- **Templates (17)**: 提案書〜完了承認書 + 障害報告書 + 議事録 + 客先レビュー記録
- **Modes (1)**: jtbc.yaml (JTBC専用)

### 2.3 Claude Code が読む順序

1. プラグイン有効化時に `plugin.json` を読む
2. ユーザー入力時に `governance` skill が dispatch を判断(接遇トーンを適用)
3. role判定後、対応する役職を動かす(teams 有効時は常駐 teammate へ SendMessage / 初回は spawn。無効時はサブエージェントを都度起動)
4. teammate / subagent がツールを呼ぶたびに PreToolUse hook が `agent_type` で役職を識別し `.jtbc/state.json` と照合
5. 違反したら hook が exit 2 でツール実行を阻止(teammate にも届く)

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
    │   └── jtbc-pmo.md      (PMO / プロセスの門番)
    ├── commands/         ← お客様が直接使う4つのみ(社内作業は governance が自動実行)
    │   └── init.md    status.md  hearing.md  client-review.md
    ├── skills/
    │   ├── governance/SKILL.md
    │   ├── document-writer/SKILL.md
    │   ├── customer-relations/SKILL.md
    │   ├── requirements-interview/SKILL.md
    │   ├── meetings/SKILL.md
    │   ├── incident-response/SKILL.md
    │   ├── naze-naze/SKILL.md
    │   └── memory/SKILL.md      (役職メモ / 永続記憶)
    ├── hooks/
    │   ├── hooks.json
    │   ├── memory_grant.py      (PreToolUse: .jtbc/memory/書込みを自動承認・他役職メモはdeny)
    │   ├── phase_guard.py       (PreToolUse: フェーズ強制)
    │   ├── role_guard.py        (PreToolUse: 権限分離)
    │   ├── ringi_guard.py       (PreToolUse: 稟議承認強制)
    │   ├── incident_guard.py    (PreToolUse: 緊急対応モード強制)
    │   ├── state_guard.py       (PreToolUse: phase移行をPMOに限定)
    │   ├── team_guard.py        (PreToolUse: teams有効時の一発実行を阻止・常駐teammate強制)
    │   ├── superior_visit.py    (UserPromptSubmit: 上長視察 確率発火)
    │   ├── approval_sync_guard.py (UserPromptSubmit: 承認転記漏れをリード/PMOへ通知)
    │   ├── memory_timeline.py   (PostToolUse: phase変更を_timeline.mdへ自動記録)
    │   └── memory_reminder.py   (SubagentStop: 知識役職にメモ記録を促す・通知のみ)
    ├── templates/
    │   ├── proposal.md          (提案書)
    │   ├── project_plan.md … completion_approval.md
    │   ├── incident_report.md   (障害報告書)
    │   └── meeting_minutes.md   (議事録)
    ├── config/jtbc.yaml
    └── state/{schema.json, initial_state.json}
```

`.jtbc/` は **プラグインを使う先のプロジェクト** に生成される:

```
<user-project>/.jtbc/
├── state.json
├── proposal/        提案書           ├── tests/            テスト計画/結果
├── plans/           計画書           ├── deliverables/     納品一覧/完了承認書
├── requirements/    要件定義書       ├── lessons/          教訓登録簿
├── designs/         基本/詳細設計書  ├── incidents/        障害報告書
├── wbs/             WBS              ├── minutes/          議事録
├── risks/           リスク登録簿     ├── client_reviews/   客先レビュー記録
├── issues/          課題管理簿       ├── gates/
├── changes/{pending,approved,rejected}/  稟議  └── org/organization.md
```

---

## 4. 状態遷移図

### 4.1 プロジェクト全体ステートマシン

```
 提案 (PROPOSAL)
   │ ① 内部審査(自動)proposal       … 課長◎ 部長○ 社長○ (内部承認=上位承認/この案件を受けるか)
   │ ② 客先提示(自動)proposal       … 内部承認済みの提案書をお客様へ提示・ご承認(=受注)で次へ
   ▼
 要件定義 (REQUIREMENTS)
   │ ① 内部審査(自動)project_plan   … 課長◎ 部長○ 主任○ (内部承認/要件+計画の妥当性)
   │ ② 客先提示(自動)project_plan   … 内部承認済みの要件定義書をお客様へ提示・ご承認で次へ
   ▼
 基本設計 (BASIC_DESIGN)
   │ ① 内部審査(自動)basic_design   … 課長◎ 部長○ (内部承認)
   │ ② 客先提示(自動)basic_design   … 内部承認済みの基本設計書をお客様へ提示・ご承認で次へ
   ▼
 詳細設計 (DETAILED_DESIGN)
   │ ① 内部審査(自動)detailed_design … 課長○ 主任◎ 部長○ (内部承認)
   │ ② 客先提示(自動)detailed_design … 内部承認済みの詳細設計書をお客様へ提示・ご承認で次へ
   ▼
 実装 (IMPLEMENTATION)
   │ 工程内遷移(自動)       … 主任が完了確認したら司令塔が自動で進める (審査会なし)
   ▼
 単体テスト (UNIT_TEST)
   │ 工程内遷移(自動)
   ▼
 総合テスト (INTEGRATION_TEST)
   │ 内部審査(自動)release     … 課長◎ 主任○ 部長○ 社長○ (リリース判定会)
   ▼
 リリース済 (RELEASED)
   │ 内部審査(自動)completion  … 課長◎ 部長○ 社長○ (PJ完了審査・教訓3件)
   ▼
 完了 (COMPLETED)
```

> 内部審査(ゲート)はお客様の操作ではなく **司令塔(governance)が自動開催** する。
> internal_approval_first ゲートでは、内部承認の通過に続けて **客先提示が自動発火** する。
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
- フェーズゲート・稟議の **承認者**。**追加要員(担当)の払い出し権限** を持つ
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
- 担当への **業務分担をコントロール・割り振り**(担当が複数なら配分)。**自分でも実装可能**
- 内部定例のファシリ。実装系工程の進行(完了確認で司令塔が自動遷移)

### 5.5 担当 (jtbc-tantou) — `tools: Read, Write, Edit, Grep, Glob, Bash`
- 課長・主任の指示のもと、特定WBSタスクの実装・テスト・雑用
- 要件/設計/スコープ変更は単独で行わず稟議
- active_wbs_task の "触ってよいファイル" 以外は触らない
- 増員(2人目以降)は部長承認で払い出す(主任が配分)

### 5.6 PMO (jtbc-pmo) — `tools: Read, Write, Edit, Grep, Glob`
- **プロセスの門番**。ライン職(社長〜担当)とは直交する **部長直下のスタッフ職**(PMBOK)
- **フェーズ移行(`state.json#phase` の書き換え)を行える唯一の役職**。ゲート承認の充足・必要書類の
  整備・客先承認・方針(バッファ20%/教訓3件等)を機械検証してから工程を進める(`state_guard` が物理担保)
- **受注後の立ち上げ・計画を主導**: プロジェクト計画書・リスク登録簿・WBS骨子を **実作業の前に** 整える
  (「雛形だけ置いて中身は後で」を許さない)。リスク/課題/スケジュールを継続監視
- **成果物の品質承認(🔴 押印)はしない**(品質承認はゲート承認者=部長/社長)。PMO が見るのはプロセス適合
- 提案/要件/設計の起案・改訂はしない(課長/主任の領域)。コードも書かない

---

## 6. 各ドキュメントのテンプレート

17種類を `templates/` に配置。各テンプレ末尾に文書管理情報(作成者/承認者/状態)を持つ。

| ファイル | ドキュメント | 作成者 | 承認(審査) |
|---|---|---|---|
| `proposal.md` | 提案書 | 課長 | 提案審査(課長→部長→社長) |
| `project_plan.md` | プロジェクト計画書 | 課長 | PJ計画審査(部長) |
| `requirements.md` | 要件定義書 | 課長 | PJ計画審査(部長+課長) |
| `basic_design.md` | 基本設計書 | 課長 | 基本設計審査(課長+部長) |
| `detailed_design.md` | 詳細設計書 | 主任 | 詳細設計審査(課長) |
| `wbs.md` | WBS | 主任 | 詳細設計審査 |
| `risk_register.md` | リスク登録簿 | 課長 | 部長レビュー |
| `issue_log.md` | 課題管理簿 | 課長/主任 | 基本設計審査 |
| `change_request.md` | 変更管理票(稟議) | 起票者(誰でも) | type別経路 |
| `test_plan.md` | テスト計画書 | 主任 | 詳細設計審査 |
| `test_report.md` | テスト結果報告書 | 担当 | リリース判定会 |
| `deliverables_list.md` | 納品一覧 | 課長/主任 | リリース判定会 |
| `lessons_learned.md` | 教訓登録簿 | 担当+主任 | PJ完了審査(課長+部長) |
| `completion_approval.md` | プロジェクト完了承認書 | 課長 | PJ完了審査(課長→部長→社長) |
| `incident_report.md` | 障害報告書 | 課長 | ユーザー提出(部長確認) |
| `meeting_minutes.md` | 議事録 | ファシリテーター | 出席者/お客様 |
| `client_review.md` | 客先レビュー記録 | 課長 | お客様確認(社内審査の前提) |

---

## 7. 承認フロー (稟議)

変更管理(稟議)は **お客様の操作ではなく、司令塔(governance)が起票〜承認まで自動処理** する
(旧 `/jtbc:ringi` / `/jtbc:shonin` コマンドは撤去済み。お客様には結果だけを丁重にご報告する)。

| 変更種別 | 起票 | 承認経路 |
|---|---|---|
| 要件変更 | 担当/課長 | 主任 → 課長 → 部長 → 社長 |
| 設計変更 | 主任/課長 | 主任 → 課長 → 部長 |
| 技術選定変更 | 主任/担当 | 主任 → 課長 → 部長 |
| スコープ変更 | 課長/部長 | 課長 → 部長 → 社長 |
| 工数追加 | 担当/主任 | 主任 → 課長 → 部長 |

hook(`ringi_guard.py`)が、稟議未承認の要件/設計書の直接改訂を物理的に阻止する。
実行ロジックの正本は `skills/governance/SKILL.md`「変更管理(稟議)の自動処理」。

---

## 8. フェーズゲート設計

6つの審査会(`config/jtbc.yaml#gates` を正とする)。各ゲートは「必要書類 + 承認者 + チェックリスト」。
**発動はユーザー操作ではなく、司令塔(governance)が発火条件を満たしたときに自動開催する**
(旧 `/jtbc:gate` コマンドは撤去済み)。実行ロジックの正本は `skills/governance/SKILL.md`。

| gate | 前→次 | 必要書類 | 承認者 | 客先提示 |
|---|---|---|---|---|
| proposal (提案審査) | 提案→要件定義 | 提案書 | 課長,部長,社長 | 内部承認後に提示 |
| project_plan (PJ計画審査) | 要件定義→基本設計 | 計画書,要件定義書,リスク登録簿 | 課長,部長,主任 | 内部承認後に提示 |
| basic_design (基本設計審査) | 基本設計→詳細設計 | 基本設計書,課題管理簿 | 課長,部長 | 内部承認後に提示 |
| detailed_design (詳細設計審査) | 詳細設計→実装 | 詳細設計書,WBS,テスト計画書 | 課長,主任,部長 | 内部承認後に提示 |
| release (リリース判定会) | 総合テスト→リリース済 | テスト結果報告書,納品一覧 | 課長,主任,部長,社長 | — |
| completion (PJ完了審査) | リリース済→完了 | 教訓登録簿,完了承認書 | 課長,部長,社長 | — |

- **内部承認 → 客先提示の順序(重要)**: 提案/要件/基本設計/詳細設計の各ゲートは `internal_approval_first: true`。
  まず **内部審査(自動開催)** で **上位承認(内部承認)** を得て、**続けて自動発火する客先提示** で
  内部承認済みの成果物をお客様へ提示(パス明示・「ご査収ください」)し、ご承認を賜る。
  **内部承認前の文書をお客様に出してはならない。ユーザーに審査を操作させない。**
- **phase 遷移の所在**: `internal_approval_first` のゲートでは内部審査は phase を進めず(`previous_phase` のまま据え置き)、
  **客先提示のご承認(APPROVED)で `next_phase` へ進む**。`release`/`completion` は内部審査の承認で直接進む。
- **【重要】phase 遷移の実行者は PMO**: `state.json#phase` を書けるのは **PMO(`jtbc-pmo`)のみ**(`state_guard` が物理担保)。
  PMO が「承認の充足・必要書類の整備・客先承認・方針適合」を PMBOK 観点で検証してから phase を更新する。
  特に **project_plan ゲートは計画書・要件定義書・リスク登録簿が実内容で埋まっていること** を PMO が確認し、
  受注後の計画整備を飛ばして基本設計へ進む逸脱を防ぐ。司令塔/課長は phase を進められない。
- **客先レビューのご指摘時**: 成果物を修正し、当該ゲートの内部承認(`approvals`)をクリア。再度 内部審査(自動)→ 客先提示(自動)の順。
- **根回し**: 審査会の前に、owner(課長/主任)が承認者へ事前説明し論点を潰す(任意・推奨)
- **承認印**: 承認は 🔴 のハンコ表現で文書へ押印する
- **工程内遷移**: 実装→単体→総合テストはゲート無し。主任が完了確認したら司令塔が自動で進める
- hook(`phase_guard.py`)が、実装系フェーズ以外での `src/` 書込みを阻止する
- **承認の正本と機械チェック(C-3)**: 承認の正本は `state.json#approvals["<gate>_gate"]`。gate 記録 `.jtbc/gates/<gate>_gate.md` は参照用。phase を `next_phase` へ進める前に `config/jtbc.yaml#gates[<gate>].approvers` の全員が `approved` かを機械チェックし、1人でも未承認なら遷移しない(ハンコの実効化)
- **No-Go 時の処理(A-3)**: ゲート否決(No-Go)の場合は phase を `previous_phase`(審査前のフェーズ)に戻し、`active_gate=null` として差し戻し理由を gate 記録 .md に残す

---

## 9. 会議体

伝統的大企業らしく、会議がプロセスに組み込まれている(`meetings` skill。司令塔が自動開催)。
すべて議事録を残す。

### 9.1 定例 (recurring)

| 会議 | ファシリ | 参加者 | 頻度 |
|---|---|---|---|
| プロジェクト内部定例 | 主任 | 課長・担当 | 高 |
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

社内規程違反・作業中の事故を検知したら発動(`incident-response` skill。お客様の申告/検知を起点に司令塔が自動起動)。

```
検知 → ① ユーザーへ緊急一報 → ② 封じ込め → ③ 定期状況報告(部長/課長)
     → ④ なぜなぜ分析(naze-naze) → ⑤ 恒久対応・再発防止策
     → ⑥ 障害報告書をユーザーへ提出 → ⑦ 教訓登録 + クローズ
```

- **社内規程(抜粋)**: RULE-01 WBS外編集禁止 / RULE-02 稟議なし要件設計変更禁止 / RULE-03 ゲート未通過実装禁止 / RULE-04 承認経路飛ばし禁止 / RULE-05 テスト未済リリース禁止 / RULE-06 役職権限逸脱禁止 / RULE-07 PMO以外のフェーズ移行(state.json#phase書換)禁止
- severity が high/critical なら部長(+社長)が前に出てお詫び
- 根本原因は **なぜなぜ分析(5 Whys)** で究明し、対策は 仕組み > 手順 > 教育 の順
- `state.json#active_incidents` が空でない間は緊急対応モード
- **緊急対応モードの物理強制(B-3)**: `incident_guard.py`(PreToolUse hook)が `active_incidents` 非空の間は `.jtbc/(proposal|requirements|designs|plans|wbs)/` への Edit/Write を物理ブロックする。src・tests・incidents・issues 等は引き続き許可

---

## 11. 顧客接遇 (おもてなし)

ユーザーは「JTBCに開発を発注したお客様」。ユーザー向け応答は受注ベンダーの窓口として丁重な敬語で行う(`customer-relations` skill)。

- 窓口は原則 **課長**、重要局面は **部長**、決裁は **社長**。担当・主任は原則前面に出ない
- 受注御礼(提案ご承認時)、進捗ご報告、ご要望の受領、お詫び(インシデント時)に定型トーンを用意
- 安請け合いしない。スコープ・納期の約束は社内手続き(稟議・審査)を経てから
- **要望ヒアリングは1問ずつ・推奨案つき**(`requirements-interview` / `/jtbc:hearing`、grill-me 方式)
- **見積りは実測可能な値で表す(嘘をつかない)**: 費用は架空の「○○万円」ではなく **概算トークン数**
  (本プラグインにおける実質コスト)、期間/工数は「○○週間」ではなく **概算プロンプト数=やり取りの
  往復回数** で表す
- **成果物の客先提示は内部承認の後**。提示はパスを示し「ご査収ください」と正式文書として連携する

### 例: 受注御礼

> {{client_name}} 御中
> 平素は格別のご高配を賜り、厚く御礼申し上げます。
> この度は…正式にご発注いただき誠にありがとうございます。… 何卒よろしくお願い申し上げます。

---

## 12. 伝統的施策 (様式美)

| 施策 | 内容 | 実装箇所 |
|---|---|---|
| **要望ヒアリング** | 課長が1問ずつ・推奨案つきで要望を引き出し共通理解を得る(grill-me 方式) | requirements-interview skill / hearing command |
| **客先レビュー(ご査収)** | 社内の内部承認を得た成果物を、パス明示で「ご査収ください」とお客様へ提示し承認を賜る(内部承認後に自動発火) | governance skill / client-review command(手動再提示用) / client_review template |
| **根回し** | 審査会(自動開催)前に owner が承認者へ事前説明し論点を潰す | governance skill |
| **報連相** | 指揮系統を飛ばさない。悪い報告ほど早く | governance skill / 各agent |
| **承認印(ハンコ)** | 承認は 🔴 の押印表現で文書に残す | governance skill / 各テンプレ |
| **議事録** | すべての会議で議事録を残す | meetings skill / meeting_minutes template |
| **接遇・敬語** | お客様への丁重な応対 | customer-relations skill |
| **なぜなぜ分析** | インシデント・教訓の真因を5 Whysで究明 | naze-naze skill |
| **持ち帰り** | 即答せず社内手続きを経て回答 | customer-relations / agents |

---

## 13. Company Mode

本プラグインは **JTBC 専用**(かつての startup モードは廃止)。
`config/jtbc.yaml` が唯一の実体。mode 切替(set)は無く、`state.json#mode` に常に `"jtbc"` を保持する
(かつての `/jtbc:mode` 確認コマンドは撤去。情報は本ドキュメント参照)。

将来の拡張余地(未実装): `agile`(PO/SM/Dev)、`oss`(maintainer/contributor/reviewer)、`gov`(統括/設計/実装/監査)。
mode yaml と対応する役職 agent を追加すれば新文化を足せるアーキテクチャは残してある。

---

## 14. Marketplace 配布

リポジトリルートの `.claude-plugin/marketplace.json` により、Claude Code のプラグインマーケットプレイスとして登録できる(将来の公式配布を見据えた構成)。

```bash
# ユーザー側の利用イメージ
/plugin marketplace add answer-d/jtbc-harness
/plugin install jtbc@jtbc-harness
```

ローカル開発では `plugins/jtbc/` をプラグイン読込先に配置すればよい(README参照)。

---

## 15. MVP 実装計画 / 検収条件

### 含むもの (実装済)
- plugin.json / marketplace.json
- 6 agents(5役職 + PMO)/ 4 commands / 8 skills / 11 hooks(本実装) / 17 templates / 1 mode / state schema

### 検収シナリオ (MVPが「動いた」と言える基準)

```
1. /jtbc:init で 依頼内容を確認(無ければ狙いを仮定せず1問伺う)→ .jtbc/ 一式 + 体制図が生成される(受注御礼はまだ述べない)
2. 課長がヒアリング項目(決定木)を起案 → 営業がそれを1問ずつ代弁して引き出す → 共通理解を得て課長が提案書を起案
   (費用=トークン数 / 期間=往復回数 で見積る。架空の万円・週は使わない)
3. (自動)提案審査で 部長→社長 が内部承認(=上位承認)→ (自動)客先提示で
   内部承認済みの提案書を「ご査収ください」と提示 → お客様ご承認 → **受注御礼(フル定型)** で
   PMO が要件定義へ phase を進める
   ※ お客様は審査を操作しない。審査は自動開催され、承認依頼だけがお客様へ上がる
3.5 (受注後キックオフ)PMO を spawn → 実作業の前に プロジェクト計画書・リスク登録簿・WBS骨子を整備
   (空のまま先へ進まない。PMBOK 的な立ち上げ・計画)
4. 課長が要件定義書、PMO/課長が計画書・リスク登録簿を作成 → (自動)PJ計画審査(計画書+要件+リスクが必須)→
   (自動)客先提示でお客様承認 → PMO が基本設計へ phase を進める
5. 課長が基本設計 → (自動)基本設計審査 → (自動)客先提示でお客様承認
6. 主任が詳細設計・WBS・テスト計画 → (自動)詳細設計審査 → (自動)客先提示でお客様承認
7. 主任が担当へタスクを割り振り、実装(役職振り分けは司令塔が自動)
8. (自動)工程内遷移で 実装→単体テスト→総合テスト と進む(主任の完了確認を起点に司令塔が自動遷移)
9. 実装中に要件変更ニーズ発覚 → (自動)変更管理(稟議)を起票し 主任→課長→部長→社長 が自動承認 → 結果をご報告
10. 作業中の事故発生 → (自動)インシデント対応(緊急報告 → なぜなぜ分析 → 障害報告書 → 収束)
11. (自動)会議体を開催(内部定例 / 客先定例 / 状況報告)
12. (自動)リリース判定会(納品一覧を自動整備のうえ判定)
13. (自動)教訓を3件登録(なぜなぜ由来)
14. (自動)PJ完了審査 → 完了
```

### 段階的拡張 (Phase 2+)
- hook で WBS の "触ってよいファイル" と active_wbs_task を厳密照合
- 会議頻度のスケジューリング
- 教訓の組織横断ナレッジ化(`~/.jtbc/_org/`)、監査レポート自動生成

---

## 付録A: 暴走防止の効き方

| 暴走パターン | JTBCでの抑止 |
|---|---|
| 「ついでにリファクタ」 | 担当は active_wbs_task 外を触れない(role_guard) |
| スコープクリープ | 要件変更は稟議必須、主任が影響範囲分析 |
| 設計無視の実装 | 実装フェーズ突入には詳細設計審査通過が必要(phase_guard) |
| 一人で全部やる | tool分離 + role分離。社長/部長/課長はsrc書込不可(role_guard/phase_guard)。担当はガバナンス文書不可 |
| 教訓が残らない | PJ完了審査の前提が教訓3件のAPPROVED |
| 事故の握りつぶし | インシデント対応で必ずユーザー報告+障害報告書 |
| その場しのぎの謝罪 | なぜなぜ分析で真因に対する再発防止策を義務化 |

## 付録B: JTBCの限界 (正直なところ)

- **遅い**。本当に遅い。小さな変更にもプロセスが乗る(それが抑止力でもありコストでもある)
- agentの「人格」が崩れることがある(hookで物理強制するが、プロンプトだけでは100%抑止不可)
- **稟議疲れ・会議疲れ**。実プロジェクトでやると人間が滅入る(本物のJTBCがそうであるように)
- **チーム(Agent Teams)は実験機能**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 依存で、`/resume` 非対応・
  task status のラグ・shutdown が遅い等の既知の制約を抱える(research preview)。配布プラグインとして
  teams を必須にせず、無効環境はサブエージェントへフォールバックする。split panes は tmux/iTerm2 が必要
  (in-process はどの端末でも可)。
- **チームのコスト**: 各役職の常駐は各々が別インスタンス=別コンテキストで、トークン消費が大きい。
  遅延常駐(出番が来た役職だけ起こす)で緩和するが、本質的に重い。
- **Read制御の限界(B-2)**: PreToolUse の matcher は Edit / Write / MultiEdit のみ。**ファイル読み取り(Read/Grep/Glob)は hook で制御できない**ため、社長の src 閲覧や担当のガバナンス文書閲覧はプロンプト規範に依存する(物理強制は書込み系のみ)

逆に言えば、この「遅さ」「重さ」「様式」こそが暴走への抑止力であり、AIエージェントに対する **意図的なフリクション** である。
