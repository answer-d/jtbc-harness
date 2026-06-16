---
description: ゲート審査会を伴わない工程内遷移(実装→単体テスト→総合テスト)を進める。主任が完了を確認して進める。引数: <next|show>
argument-hint: "<next | show>"
---

# /jtbc:phase

審査会(ゲート)を挟まない **工程内の前進** を扱います。
ゲートを伴う遷移は `/jtbc:gate` を使ってください。

> 対象は `modes/jtbc.yaml#linear_transitions` に定義された辺のみ:
> - 実装 (IMPLEMENTATION) → 単体テスト (UNIT_TEST)
> - 単体テスト (UNIT_TEST) → 総合テスト (INTEGRATION_TEST)

## サブコマンド

### `show`

現フェーズと、ここから取り得る前進(linear か gate か)を表示。

### `next`

現フェーズの線形遷移を1つ進める。

動作:
1. `state.json#phase` を読む
2. `linear_transitions` に `from == 現phase` の辺があるか確認
   - 無い(= ゲートが必要)→ 中止し、対応する `/jtbc:gate <name>` を案内
3. **主任(owner)** が当該工程の完了を確認(下記の完了条件)。未達なら中止
4. 内部定例での合意を前提に、`state.json#phase` を `to` へ更新
5. 結果を表示

## 完了条件(主任が確認)

| 遷移 | 完了条件 |
|---|---|
| 実装 → 単体テスト | WBS の実装タスクが全て DONE、ビルドが通る |
| 単体テスト → 総合テスト | 単体テストが全 PASS(or 残課題化)、カバレッジ目標達成 |

総合テスト完了後は `/jtbc:gate release`(リリース判定会)へ進みます。

## 出力例

```
⏭️  工程を進めます: 実装 → 単体テスト

主任確認:
  ✅ WBS実装タスク 24/24 DONE
  ✅ ビルド成功

phase: IMPLEMENTATION → UNIT_TEST に更新しました。
次のステップ: 担当が単体テストを実施。完了後 /jtbc:phase next で総合テストへ。
```

## ガード

- `phase_guard.py` はソースコードへの書込みを 実装/単体テスト/総合テスト の各フェーズで許可します。
  したがって本コマンドで工程を進めてもコード編集権限は維持されます。
