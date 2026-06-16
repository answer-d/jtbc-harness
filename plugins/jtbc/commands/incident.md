---
description: インシデント(社内ルール違反/作業中の事故)の起票・状況報告・解決・クローズ。まずお客様へ緊急報告し、なぜなぜ分析で真因を究明、障害報告書を提出する。引数: <open|status|report|resolve|close>
argument-hint: "<open <severity> \"事象\" | status <INC> | report <INC> | resolve <INC> | close <INC> | list>"
---

# /jtbc:incident

インシデント対応コマンド。プロセスの本体は `jtbc-incident-response` スキル、
根本原因分析は `jtbc-naze-naze` スキルに従います。

## サブコマンド

### `open <severity> "<事象>"`

インシデントを起票し、**ただちにお客様へ緊急一報** します。

- `severity`: `low` | `medium` | `high` | `critical`
- 動作:
  1. `INC-NNN` を採番、`incident_report` を `.jtbc/incidents/INC-NNN.md` に生成
  2. `state.json#active_incidents` に `INC-NNN` を追加(= 緊急対応モード突入)
  3. 原因に関係する通常作業を停止
  4. お客様へ第一報(`jtbc-customer-relations` のお詫びトーン、severity に応じ課長 or 部長名義):

```
【ご報告】<事象>
この度は<事象>が発生し、ご迷惑をおかけしておりますことを深くお詫び申し上げます。
- 現在の状況: <わかっている事実>
- 暫定対応: <実施中/予定>
- 影響: <お客様影響の有無・範囲>
原因究明と復旧に全力で対応しております。進展あり次第、改めてご報告申し上げます。
```

### `status <INC-NNN>`

解決までの **定期状況報告**。部長/課長がお客様へ続報を申し上げ、報告書のタイムラインを更新。

### `report <INC-NNN>`

**なぜなぜ分析**(`jtbc-naze-naze`)で真因を究明し、障害報告書の第5〜7章を完成させる。
再発防止策は 仕組み > 手順 > 教育 の順で立てる。重篤時は部長+課長連名のお詫びを添える。

### `resolve <INC-NNN>`

恒久対応が完了し収束したことを記録(status を RESOLVED に)。報告書の収束時刻を埋める。

### `close <INC-NNN>`

障害報告書をお客様へ正式提出し、クローズ。

- 動作:
  1. 報告書の status を CLOSED に
  2. 教訓登録簿へ `L-NNN` を登録(`/jtbc:kyokun add` 連携)
  3. `state.json#active_incidents` から `INC-NNN` を除外(緊急対応モード解除)
  4. お客様へ最終ご報告(顛末+再発防止策)を提出

### `list`

`.jtbc/incidents/*.md` から INC一覧(ID/severity/status/title)を表示。

## 何がインシデントか (トリガー)

`jtbc-incident-response` スキルの社内規程(RULE-01〜07)違反、または作業中の事故
(デグレ・データ消失・誤デプロイ・ビルド破壊・機密コミット・暴走 等)。
hook がすり抜けた疑い、人為的バイパスも対象。

## 対応の鉄則

1. **隠さない・止める・すぐ報告**(担当/SESは主任経由、緊急時は直接も可)
2. お客様への第一報は **事実を簡潔に、わかった範囲で即座に**
3. 犯人探しでなく **仕組みの是正**(なぜなぜ分析)
4. severity=critical は社長まで報告。部長+課長でお詫びに立つ
