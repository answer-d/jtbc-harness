---
description: 稟議を承認/却下する。引数: <role> <CR-NNN> <approve|reject> [comment]
argument-hint: "<shunin|kacho|bucho|shacho> <CR-NNN> <approve|reject> [\"コメント\"]"
---

# /jtbc:shonin

進行中の稟議に対する承認/却下を行います。

## 引数

- `role`: `shunin` | `kacho` | `bucho` | `shacho`
- `CR-NNN`: 稟議ID
- 判定: `approve` | `reject`
- コメント: 任意の文字列

## 動作

1. `.jtbc/changes/pending/CR-NNN.md` を読む
2. 状態 (`PENDING_<role>`) が引数の role と一致するか確認
   - 不一致 → 「現在は <現状態> なので <その役職> が承認すべきです」と中止
3. 該当する agent (jtbc-<role>) を Task tool 経由で起動し、変更内容と影響範囲をレビューさせる
   - agent には「あなたの責務領域(`agents/jtbc-<role>.md` 参照)に照らして判断してください」と指示
4. agent の判断を稟議ファイルの `approvals` リストに追記し、本文の承認パス表に **承認印(🔴)** を押す:

```yaml
approvals:
  - role: <role>
    decision: <approve|reject>
    by: "AI-Agent (jtbc-<role>)"
    at: "<ISO datetime>"
    seal: "🔴"          # 承認印(approve時)。reject時は朱書き理由
    comment: "<agent判断 + コマンドコメント>"
```

> 稟議は誰でも起票できます(担当・外注SESも可)。ただし承認は経路上の役職のみが行えます。
> 経路を飛ばした承認は `ringi_guard.py` が阻止します(報連相の徹底)。

5. approve の場合:
   - 次の承認者に状態を進める (`PENDING_<next_role>`)
   - **最終承認者の場合(B-1: ringi_guard との整合)**:
     1. CR 本文(影響範囲/対象パス欄)に **改訂対象ドキュメントの相対パス**
        (例: `.jtbc/requirements/requirements.md`)が明記されていることを確認する。
        記載がない場合は、承認者が Edit ツールで追記してから移動する。
        ※ この記載により `ringi_guard` が当該ドキュメントの改訂を許可する。
     2. frontmatter の `status:` を **`APPROVED`** に更新する(Edit ツールで行う)。
        社長・部長・課長は Edit ツールを持つため自身で追記できる。
     3. ファイルを `.jtbc/changes/approved/CR-NNN.md` へ移動する。
     4. `state.json#active_ringi` から外す。
6. reject の場合:
   - 状態を `REJECTED` に更新、ファイルを `.jtbc/changes/rejected/CR-NNN.md` に移動
   - `state.json#active_ringi` から外す
7. 結果を表示

## 出力例 (承認)

```
📩 CR-001 を承認しました

承認者: 課長 (jtbc-kacho)
判定: APPROVED
コメント: "REQ-027 への影響は限定的。設計トレーサビリティは維持される。"

承認パス進捗: 主任 ✅ → 課長 ✅ → 部長 ⏳ → 社長 ⏳

次のステップ: /jtbc:shonin bucho CR-001 [approve|reject]
```

## 出力例 (最終承認 = 全承認完了)

```
🎉 CR-001 完全承認

承認: 主任 ✅ / 課長 ✅ / 部長 ✅ / 社長 ✅
status: APPROVED (frontmatter 更新済み)
対象ドキュメント: .jtbc/requirements/requirements.md (ringi_guard 解除済み)
ファイル: .jtbc/changes/approved/CR-001.md

この変更は実装可能になりました。
WBS に反映してください: /jtbc:role shunin で主任を呼んで影響タスクを追加
```

## 出力例 (却下)

```
❌ CR-001 却下

却下者: 部長 (jtbc-bucho)
理由: "スケジュール影響が +10人日。今四半期では対応困難。次期へ持ち越し検討"

ファイル: .jtbc/changes/rejected/CR-001.md
```

## ガード

- ringi_guard.py (hook) は、状態 PENDING_X の稟議に対し X 以外の役職が承認を入れようとしたら阻止
