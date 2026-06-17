---
description: 納品物の確認(納品一覧の生成/検証)。引数: <check|generate>
argument-hint: "<check | generate>"
---

# /jtbc:noubi

納品物の管理コマンド。

## サブコマンド

### `generate`

`.jtbc/deliverables/deliverables_list.md` を生成/更新します。

動作:
1. mode (`state.json#mode`) を読む
2. mode 定義 (`modes/<mode>.yaml#deliverables_minimum`) を読む
3. 必要な納品物を一覧化し、各納品物について以下を埋める:
   - 名称
   - 種別 (コード/ドキュメント/レポート/その他)
   - 提出予定パス
   - 提出状態 (NOT_READY / READY / SUBMITTED)
4. ファイルを書き出し

### `check`

リリース判定会の前に納品物の準備状況を検証します。

動作:
1. `deliverables_list.md` を Read
2. 各エントリの「提出予定パス」が実在するかチェック
3. 不足リストを表示

## 出力例 (check)

```
📦 納品物チェック

✅ ソースコード      → src/ (存在確認)
✅ 基本設計書        → .jtbc/designs/basic_design.md (APPROVED)
✅ 詳細設計書        → .jtbc/designs/detailed_design.md (APPROVED)
❌ テスト結果報告書  → .jtbc/tests/test_report.md (内容空欄)
❌ リリース記録      → .jtbc/deliverables/release_note.md (ファイル無し)
✅ 教訓登録簿        → .jtbc/lessons/lessons_learned.md (DRAFT)

不足: 2件。リリース判定会(司令塔が自動開催)前に解消してください。
```

## JTBCにおける納品の考え方

JTBCではコードのみを納品物とみなしません。最低限以下を納品対象とします
(`modes/jtbc.yaml#deliverables_minimum` を正とする):

- ソースコード
- 提案書 / プロジェクト計画書
- 要件定義書 / 基本設計書 / 詳細設計書 / WBS
- テスト計画書 / テスト結果報告書
- リリース記録
- 教訓登録簿 / プロジェクト完了承認書

リリース判定会・PJ完了審査(いずれも司令塔が自動開催)の前に
`/jtbc:noubi check` で過不足を確認してください。
