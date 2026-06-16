---
description: 役職agentを呼び出して以降の作業を任せる。引数: <role>
argument-hint: "<shacho|bucho|kacho|shunin|tantou|ses>"
---

# /jtbc:role

指定された役職 agent に切り替えて作業を続行します。

## 引数

- `shacho` → jtbc-shacho を起動(社長: 最終意思決定・要所のみ)
- `bucho` → jtbc-bucho を起動(部長: 承認・助言・要員払い出し)
- `kacho` → jtbc-kacho を起動(課長: PM・お客様窓口)
- `shunin` → jtbc-shunin を起動(主任: PL・テックリード)
- `tantou` → jtbc-tantou を起動(担当: 実装・テスト)
- `ses` → jtbc-ses を起動(外注SES: 低コスト実装支援、指示前提)

## 動作

1. `.jtbc/state.json#phase` を読む
2. phase と role の整合をチェック(参考程度、強制はしない)。アクティブマトリクス
   (`skills/jtbc-governance/SKILL.md`)に照らし、不在の役職を呼ぼうとしたら一言添える:
   - phase=PROPOSAL で `tantou`/`ses` → 「まだ実装フェーズではありません。提案・要件が先です」
   - phase=IMPLEMENTATION で `shacho` → 「社長は実装には出てきません。要所(審査会)で登場します」

### C-2: roster ガード(増員チェック)

3. `ses` または `tantou`(2人目以降)を起動しようとする場合は、先に roster を確認する:
   - **`ses` 起動時**: `state.json#roster.ses` が 1 以上であるかを確認。
     0 の場合は起動せず、次のメッセージを表示して終了する:
     「外注SESの増員には部長承認が必要です。`/jtbc:role bucho` で部長に増員(roster 更新)をご相談ください。」
   - **`tantou` 2人目以降**: `state.json#roster.tantou` が必要数以上であるかを確認。
     不足の場合も同様に部長へ相談するよう案内する。
   - 部長が承認して `roster` を更新した後に起動できる、という流れにする。

4. Task tool で対応 subagent を起動。直近のユーザー要求を引数として渡す
5. **外注SES(ses)を呼ぶ場合**: 必ず指示元(主任/担当)とタスク(active_wbs_task)を明示する。
   指示なしの単独起動は避ける(SESは常に指示のもとで動く)

## 出力例

```
🎭 役職: 課長 (jtbc-kacho)  ── PM・お客様窓口
現フェーズ: 要件定義 (REQUIREMENTS) / このフェーズでの課長: ◎ 主担当

課長のご担当領域:
- 要件定義書・計画書の起案
- 設計レビュー、稟議の課長段、お客様窓口

ご要望をお聞かせください。(他役職へは /jtbc:role を再度実行)
```

## ガード

`role_guard.py` (hook) が各 agent のシステムプロンプトで指定されたパスのみ Write/Edit 可能にします。
違反したら hook がツール実行を block します。担当・主任・外注SESのコード編集には
`active_wbs_task` の割り当てと実装系フェーズが必要です(phase_guard / role_guard)。
