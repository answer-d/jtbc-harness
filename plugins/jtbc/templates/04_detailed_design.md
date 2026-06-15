# 詳細設計書

<!--
- 作成者: 主任 (jtbc-shunin)
- 承認者: 課長
- 更新条件: 詳細レベルの変更時 (要件/基本設計に踏み込む場合は稟議経由)
- レビュー条件: 詳細設計審査時
-->

## 1. 概要

(基本設計書のサマリと、本書の対応範囲)

## 2. コンポーネント詳細

各コンポーネントについて、以下を記述。

### 2.1 <コンポーネント名>

- **対応する基本設計章**: 3.1
- **対応する REQ-ID**: REQ-001, REQ-002
- **責務**: 
- **依存先コンポーネント**: 

#### 2.1.1 クラス/モジュール構成 (疑似コードでOK)

```
class UserService:
    repo: UserRepository
    
    def register(email: str, password: str) -> User
    def authenticate(email: str, password: str) -> Token | AuthError
```

#### 2.1.2 主要関数のシグネチャと振る舞い

| 関数名 | 入力 | 出力 | 副作用 | エラー |
|---|---|---|---|---|
| register | email, password | User | DB書込 | DuplicateEmail |

#### 2.1.3 データフロー

```
[入力] → [Validate] → [Hash] → [Persist] → [出力]
```

#### 2.1.4 エラーハンドリング方針

- 入力エラー: 4xx を返す
- システムエラー: 5xx + ログ
- 既知ビジネスエラー: 専用エラーコード

#### 2.1.5 テスト観点

- 正常系: 新規登録
- 異常系: 重複メール
- 境界: メール最大長

(以下、コンポーネントごと)

## 3. データベース設計詳細

### 3.1 テーブル定義

```
users
- id          PK
- email       UNIQUE NOT NULL
- password_hash NOT NULL
- created_at  NOT NULL
```

### 3.2 インデックス

| テーブル | インデックス | 列 | 理由 |
|---|---|---|---|
| users | idx_email | email | ログイン高速化 |

## 4. 外部API呼出し詳細

| API | 呼出し元 | 入力 | 出力 | リトライ | タイムアウト |
|---|---|---|---|---|---|
| | | | | 3回 / 指数backoff | 5s |

## 5. 並行制御

- ロック対象:
- 競合検知方法:

## 6. ロギング詳細

| 場所 | レベル | 内容 |
|---|---|---|
| 認証成功 | INFO | user_id, ip |
| 認証失敗 | WARN | email, ip, reason |

## 7. WBSとの対応

本書の各章を WBS のどのタスクが実装するかを示す:

| 詳細設計章 | WBS-ID | 担当 |
|---|---|---|
| 2.1.1 UserService.register | WBS-001 | tantou |

---
## 文書管理情報
- 文書ID: DOC-04
- バージョン: 0.1
- 作成者: 主任
- 承認者: 課長
- 作成日: {{created_at}}
- 最終更新: {{created_at}}
- 承認状態: DRAFT
- 関連稟議: -
