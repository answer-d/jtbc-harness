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

- **Agents (6)** — `agents/jtbc-{shacho,bucho,kacho,shunin,tantou,ses}.md`
  (外注SES `jtbc-ses` は `model: haiku` の低コスト実装支援)
- **Commands (13)** — `commands/{init,status,client-review,hearing,phase,ringi,shonin,noubi,kyokun,role,mode,meeting,incident}.md`
  - ※ 内部審査(ゲート)はコマンドではなく `governance` スキルが自動開催する
- **Skills (7)** — `governance`(司令塔) / `document-writer` / `customer-relations`(接遇) /
  `requirements-interview`(要望ヒアリング) / `meetings`(会議体) / `incident-response`(インシデント) / `naze-naze`(なぜなぜ分析)
- **Hooks (5)** — `hooks/{phase,role,ringi,incident}_guard.py`(PreToolUse で権限分離・フェーズ強制・緊急対応強制) +
  `hooks/superior_visit.py`(UserPromptSubmit で上長視察を確率注入)
- **Templates (17)** — `templates/proposal.md` 〜 `completion_approval.md`, `incident_report.md`, `meeting_minutes.md`, `client_review.md`
- **Modes (1)** — `modes/jtbc.yaml`(JTBC専用。startupモードは廃止)

## state.json schema

`state/schema.json` 参照。`state/initial_state.json` が `/jtbc:init` の初期値。

## フック動作確認

```bash
# JSON を stdin に渡すと判定できる(exit 2 = ブロック)
echo '{"agent_name":"jtbc-shacho","tool_input":{"file_path":"src/app.js"},"cwd":"/path/to/proj"}' \
  | python3 hooks/role_guard.py
```
