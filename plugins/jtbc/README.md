# jtbc plugin

Claude Code 用プラグイン本体。日本の伝統的大企業のガバナンスをAIエージェント開発に導入する。

## インストール

### Marketplace 経由(将来の公式配布想定)

リポジトリルートの `.claude-plugin/marketplace.json` 経由で配布できる。

```bash
/plugin marketplace add answer-d/jtbc-harness
/plugin install jtbc@jtbc-harness
```

### ローカル開発

```bash
mkdir -p ~/.claude/plugins
ln -s "$(pwd)/plugins/jtbc" ~/.claude/plugins/jtbc
```

## 提供物

- **Agents (7)** — `agents/jtbc-{shacho,bucho,kacho,shunin,tantou,ses,pmo}.md`
  (外注SES `jtbc-ses` は `model: haiku` の低コスト実装支援)
  - ※ **PMO `jtbc-pmo` はプロセスの門番**(PMBOK)。**フェーズ移行(`state.json#phase` 書換)を行える唯一の役職**で、
    ゲート承認・必要書類・客先承認を機械検証してから工程を進める(`state_guard` が物理担保)。受注後の
    立ち上げ・計画(PJ計画書/リスク登録簿/WBS骨子)を実作業前に主導する。成果物の品質承認(押印)はしない。
  - ※ **運用は常駐エージェントチーム(Agent Teams)が基本**。司令塔(営業)が lead、各役職が常駐 teammate。
    `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` を `settings.json` に設定して有効化する(無効なら都度起動の
    サブエージェントへ自動フォールバック)。詳細は `DESIGN.md §1.4` / `skills/governance/SKILL.md`。
  - ※ **客対の一次窓口は「営業」= メインセッション(司令塔=lead)の客対人格** で、teammate ではない
    (お客様との逐次対話は teammate に委譲できないため lead が務める)。営業は開発組織の外側に立ち、
    承認権限を持たない。重要局面では営業が課長(PM)・部長(責任者)を同席紹介する。
    定義は `config/jtbc.yaml#customer_window`。
  - ※ **承認は起案者(owner)より上位の役職のみ**(社長>部長>課長>主任>担当>SES)。下位役職は
    `reviewers`(事前レビュー・記載協力)として関与できるが承認印は押さない。詳細は `config/jtbc.yaml#gates`。
- **Commands (4)** — `commands/{init,status,hearing,client-review}.md`(お客様が直接使うのはこの4つのみ)
  - ※ 内部審査(ゲート)・変更管理(稟議)・工程内遷移・会議体・インシデント対応・役職振り分け・
    納品物整備・教訓登録などの **社内作業はコマンドではなく `governance` スキルが自動実行** する
- **Skills (8)** — `governance`(司令塔) / `document-writer` / `customer-relations`(接遇) /
  `requirements-interview`(要望ヒアリング) / `meetings`(会議体) / `incident-response`(インシデント) / `naze-naze`(なぜなぜ分析) / `role-memory`(役職メモ)
- **Hooks (11)** — `hooks/{phase,role,ringi,incident,state,team}_guard.py`(PreToolUse で権限分離・フェーズ強制・緊急対応強制・
  フェーズ移行のPMO限定・常駐teammate強制) + `hooks/memory_grant.py`(PreToolUse で `.jtbc/memory/` 書込みを自動承認) +
  `hooks/{superior_visit,approval_sync_guard}.py`(UserPromptSubmit で上長視察・承認転記漏れ通知) +
  `hooks/memory_timeline.py`(PostToolUse でフェーズ足跡を自動記録) + `hooks/memory_reminder.py`(SubagentStop でメモ記録を促す)
- **Templates (17)** — `templates/proposal.md` 〜 `completion_approval.md`, `incident_report.md`, `meeting_minutes.md`, `client_review.md`
- **Config (1)** — `config/jtbc.yaml`(組織構造・フェーズ・ゲート・稟議・会議体・インシデントの正本。JTBC専用でモード切替はない)

## state.json schema

`state/schema.json` 参照。`state/initial_state.json` が `/jtbc:init` の初期値。

## フック動作確認

```bash
# JSON を stdin に渡すと判定できる(exit 2 = ブロック)
echo '{"agent_name":"jtbc-shacho","tool_input":{"file_path":"src/app.js"},"cwd":"/path/to/proj"}' \
  | python3 hooks/role_guard.py
```
