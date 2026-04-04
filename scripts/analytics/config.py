"""
エロナビ アクセス分析 - 設定ファイル

==========================================================
セットアップ手順
==========================================================

1. Google Cloud プロジェクトを作成
   - https://console.cloud.google.com/ にアクセス
   - 新規プロジェクトを作成（例: "eronavi-analytics"）

2. API を有効化
   - Google Cloud Console > 「APIとサービス」 > 「ライブラリ」
   - 「Google Search Console API」を検索して有効化
   - 「Google Analytics Data API」を検索して有効化

3. サービスアカウントを作成し JSON 鍵をダウンロード
   - 「APIとサービス」 > 「認証情報」 > 「認証情報を作成」
   - 「サービスアカウント」を選択
   - 名前を入力して作成（例: "eronavi-analytics-sa"）
   - 「鍵」タブ > 「鍵を追加」 > 「新しい鍵を作成」 > JSON
   - ダウンロードした JSON ファイルを credentials.json として配置

4. Search Console でサービスアカウントに権限を付与
   - https://search.google.com/search-console にアクセス
   - 対象プロパティの「設定」 > 「ユーザーと権限」
   - サービスアカウントのメールアドレスを追加（閲覧権限でOK）
   - メールアドレスは JSON 鍵の "client_email" に記載

5. GA4 でサービスアカウントに権限を付与
   - https://analytics.google.com/ にアクセス
   - 「管理」 > 対象プロパティの「プロパティのアクセス管理」
   - サービスアカウントのメールアドレスを追加（閲覧者でOK）

6. credentials.json を配置
   - このスクリプトと同じディレクトリに置く
   - または環境変数 GOOGLE_APPLICATION_CREDENTIALS にパスを設定

7. config.py の GA4_PROPERTY_ID を設定
   - GA4 管理画面 > 「プロパティの詳細」でプロパティ ID を確認
   - 数字のみ（例: "123456789"）

8. パッケージのインストールと実行
   - pip install -r requirements.txt
   - python run_analytics.py

==========================================================
"""

import os
from pathlib import Path

# ---------- ディレクトリ設定 ----------

# このファイルの場所を基準にする
_SCRIPT_DIR = Path(__file__).resolve().parent

# データ保存ディレクトリ（analytics/data/）
DATA_DIR = _SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# レポート出力ディレクトリ
REPORT_OUTPUT_DIR = Path(r"c:/Users/atsus/000_ClaudeCode/051_FANZAアフィリ")

# 記事コンテンツディレクトリ
CONTENT_DIR = Path(
    r"c:/Users/atsus/000_ClaudeCode/051_FANZAアフィリ/eronavi/content/posts"
)

# ---------- サイト設定 ----------

# サイト URL
SITE_URL = "https://musclelove-777.github.io/eronavi/"

# ---------- Google Search Console 設定 ----------

# SC-Domain 形式: "sc-domain:example.com"
# URL-prefix 形式: "https://example.com/"
GSC_SITE_URL = "https://musclelove-777.github.io/eronavi/"

# ---------- Google Analytics 4 設定 ----------

# GA4 プロパティ ID（数字のみ。例: "123456789"）
# GA4 管理画面 > プロパティの詳細 で確認
GA4_PROPERTY_ID = ""  # 要設定

# ---------- 認証情報 ----------

# サービスアカウントの JSON 鍵ファイルパス
# 環境変数 GOOGLE_APPLICATION_CREDENTIALS が設定されていればそちらを優先
CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(_SCRIPT_DIR / "credentials.json"),
)
