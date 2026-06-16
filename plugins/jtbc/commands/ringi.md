---
description: 変更管理票(稟議)の起票・提出。要件/設計/技術選定/スコープ/工数の変更時に必須。引数: <new|submit|list|show> [args...]
argument-hint: "<new <type> <title> | submit <CR-NNN> | list | show <CR-NNN>>"
---

# /jtbc:ringi

変更管理票(稟議)を扱います。

## サブコマンド

### `new <type> <title>`

新しい変更管理票を起票します。

- `type`: `requirement` | `design` | `tech_stack` | `scope` | `effort`
- `title`: 簡潔な変更概要

動作:
1. 次の連番を決定 (`.jtbc/changes/{pending,approved,rejected}/CR-NNN.md` をスキャン)
2. `plugins/jtbc/templates/change_request.md` を読み、雛形を埋める:
   - CR-ID
   - type
   - title
   - 起票者(現在の role)
   - 起票日時
   - 状態: `DRAFT`
3. `.jtbc/changes/pending/CR-NNN.md` に保存
4. 表示:

```
✅ CR-NNN を起票しました (DRAFT)

ファイル: .jtbc/changes/pending/CR-NNN.md

次のステップ:
  1. CR-NNN を編集して詳細を記入
  2. /jtbc:ringi submit CR-NNN で提出
```

### `submit <CR-NNN>`

DRAFT を承認フローに乗せる。

動作:
1. CR-NNN を読む。状態が DRAFT でなければ中止
2. 必須項目(背景/変更内容/影響範囲/代替案)が埋まっているか確認
3. type に応じて承認パスを決定 (modes/jtbc.yaml の `ringi_workflow` 参照)
4. 状態を `PENDING_SHUNIN` に更新(主任が最初)
5. `.jtbc/state.json#active_ringi` に CR-NNN を追加
6. 表示:

```
📨 CR-NNN を提出しました

承認パス: 主任 → 課長 → 部長 (→ 社長)
現在: PENDING_SHUNIN

次のステップ: /jtbc:shonin shunin CR-NNN [approve|reject] "コメント"
```

### `list`

進行中の稟議一覧を表示。

動作:
1. `.jtbc/changes/pending/*.md` を Glob
2. 各ファイルから state と title と type を抽出
3. テーブルで表示:

```
進行中の稟議:

CR-001 | requirement | "ログイン2FA追加"       | PENDING_KACHO
CR-003 | scope       | "管理画面に検索追加"     | PENDING_SHUNIN
```

### `show <CR-NNN>`

稟議の全文を表示。

動作: 該当ファイルを Read して表示。

## 承認パス定義

`modes/jtbc.yaml#ringi_workflow` から決定:

| type | フロー |
|---|---|
| requirement | shunin → kacho → bucho → shacho |
| design | shunin → kacho → bucho |
| tech_stack | shunin → kacho → bucho |
| scope | kacho → bucho → shacho |
| effort | shunin → kacho → bucho |

## エラー

- `.jtbc/` 未初期化 → `/jtbc:init` を案内
- type が定義済みでない → 一覧を表示して中止
