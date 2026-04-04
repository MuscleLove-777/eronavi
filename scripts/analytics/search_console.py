#!/usr/bin/env python3
"""
Google Search Console API データ取得スクリプト

対象サイト: https://musclelove-777.github.io/eronavi/

=== セットアップ手順 ===

1. Google Cloud Console (https://console.cloud.google.com/) でプロジェクトを作成

2. Search Console API を有効化
   - 「APIとサービス」→「ライブラリ」→「Google Search Console API」→ 有効にする

3. サービスアカウントを作成
   - 「APIとサービス」→「認証情報」→「認証情報を作成」→「サービスアカウント」
   - 名前を付けて作成
   - 「鍵」タブ →「鍵を追加」→「新しい鍵を作成」→ JSON を選択 → ダウンロード

4. Search Console にサービスアカウントを追加
   - Google Search Console (https://search.google.com/search-console) を開く
   - 対象プロパティの「設定」→「ユーザーと権限」→「ユーザーを追加」
   - サービスアカウントのメールアドレス（xxx@xxx.iam.gserviceaccount.com）を
     「フル」権限で追加

5. Python パッケージをインストール
   pip install google-api-python-client google-auth

6. 実行
   # 環境変数で鍵ファイルを指定
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   python search_console.py

   # または引数で指定
   python search_console.py --credentials /path/to/service-account-key.json

   # 期間を指定（デフォルトは28日）
   python search_console.py --days 7
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print("必要なパッケージがインストールされていません。")
    print("以下を実行してください:")
    print("  pip install google-api-python-client google-auth")
    sys.exit(1)


SITE_URL = "https://musclelove-777.github.io/eronavi/"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

# 保存先ディレクトリ（このスクリプトからの相対パス）
DATA_DIR = Path(__file__).resolve().parent / "data"


def get_service(credentials_path: str | None = None):
    """Search Console API のサービスオブジェクトを構築する。"""
    if credentials_path is None:
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if not credentials_path:
        raise RuntimeError(
            "認証情報が見つかりません。\n"
            "環境変数 GOOGLE_APPLICATION_CREDENTIALS に鍵ファイルのパスを設定するか、\n"
            "--credentials 引数で指定してください。"
        )

    if not Path(credentials_path).exists():
        raise FileNotFoundError(f"鍵ファイルが見つかりません: {credentials_path}")

    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    return build("searchconsole", "v1", credentials=credentials)


def fetch_query_data(service, site_url: str, days: int, row_limit: int = 100):
    """検索クエリ別データを取得する。"""
    end_date = datetime.now().date() - timedelta(days=3)  # 最新データは数日遅れ
    start_date = end_date - timedelta(days=days - 1)

    request_body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["query"],
        "rowLimit": row_limit,
        "dataState": "final",
    }

    response = (
        service.searchanalytics()
        .query(siteUrl=site_url, body=request_body)
        .execute()
    )

    rows = []
    for row in response.get("rows", []):
        rows.append(
            {
                "query": row["keys"][0],
                "clicks": row["clicks"],
                "impressions": row["impressions"],
                "ctr": round(row["ctr"], 4),
                "position": round(row["position"], 1),
            }
        )

    return {
        "period": f"{start_date.isoformat()} ~ {end_date.isoformat()}",
        "days": days,
        "total_rows": len(rows),
        "rows": rows,
    }


def fetch_page_data(service, site_url: str, days: int = 28, row_limit: int = 50):
    """ページ別データを取得する（上位50ページ）。"""
    end_date = datetime.now().date() - timedelta(days=3)
    start_date = end_date - timedelta(days=days - 1)

    request_body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["page"],
        "rowLimit": row_limit,
        "dataState": "final",
    }

    response = (
        service.searchanalytics()
        .query(siteUrl=site_url, body=request_body)
        .execute()
    )

    rows = []
    for row in response.get("rows", []):
        rows.append(
            {
                "page": row["keys"][0],
                "clicks": row["clicks"],
                "impressions": row["impressions"],
                "ctr": round(row["ctr"], 4),
                "position": round(row["position"], 1),
            }
        )

    return {
        "period": f"{start_date.isoformat()} ~ {end_date.isoformat()}",
        "total_rows": len(rows),
        "rows": rows,
    }


def fetch_device_data(service, site_url: str, days: int = 28):
    """デバイス別の内訳を取得する。"""
    end_date = datetime.now().date() - timedelta(days=3)
    start_date = end_date - timedelta(days=days - 1)

    request_body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["device"],
        "dataState": "final",
    }

    response = (
        service.searchanalytics()
        .query(siteUrl=site_url, body=request_body)
        .execute()
    )

    devices = {}
    for row in response.get("rows", []):
        device = row["keys"][0]
        devices[device] = {
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": round(row["ctr"], 4),
            "position": round(row["position"], 1),
        }

    return {
        "period": f"{start_date.isoformat()} ~ {end_date.isoformat()}",
        "devices": devices,
    }


def fetch_date_data(service, site_url: str, days: int = 28):
    """日別推移データを取得する。"""
    end_date = datetime.now().date() - timedelta(days=3)
    start_date = end_date - timedelta(days=days - 1)

    request_body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["date"],
        "dataState": "final",
    }

    response = (
        service.searchanalytics()
        .query(siteUrl=site_url, body=request_body)
        .execute()
    )

    rows = []
    for row in response.get("rows", []):
        rows.append(
            {
                "date": row["keys"][0],
                "clicks": row["clicks"],
                "impressions": row["impressions"],
                "ctr": round(row["ctr"], 4),
                "position": round(row["position"], 1),
            }
        )

    # 日付順にソート
    rows.sort(key=lambda x: x["date"])

    return {
        "period": f"{start_date.isoformat()} ~ {end_date.isoformat()}",
        "total_days": len(rows),
        "rows": rows,
    }


def fetch_all_data(
    credentials_path: str | None = None,
    site_url: str = SITE_URL,
    days: int = 28,
) -> dict:
    """
    全データを取得して辞書で返す。
    他のスクリプトから呼び出し可能。

    Args:
        credentials_path: サービスアカウント鍵ファイルのパス（省略時は環境変数を使用）
        site_url: 対象サイトURL
        days: 取得期間（日数）

    Returns:
        各種データを含む辞書
    """
    service = get_service(credentials_path)

    data = {
        "site_url": site_url,
        "fetched_at": datetime.now().isoformat(),
        "query_7d": fetch_query_data(service, site_url, days=7),
        "query_28d": fetch_query_data(service, site_url, days=28),
        "pages": fetch_page_data(service, site_url, days=days),
        "devices": fetch_device_data(service, site_url, days=days),
        "daily": fetch_date_data(service, site_url, days=days),
    }

    return data


def save_data(data: dict, output_dir: Path | None = None) -> Path:
    """データをJSON形式で保存する。"""
    if output_dir is None:
        output_dir = DATA_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"search_console_{today}.json"
    filepath = output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def print_summary(data: dict):
    """コンソールにサマリーを表示する。"""
    print("=" * 60)
    print(f"  Google Search Console レポート")
    print(f"  サイト: {data['site_url']}")
    print(f"  取得日時: {data['fetched_at']}")
    print("=" * 60)

    # --- 検索クエリ（7日間） ---
    q7 = data["query_7d"]
    print(f"\n■ 検索クエリ TOP 10（過去7日: {q7['period']}）")
    print(f"  {'クエリ':<30} {'クリック':>6} {'表示':>8} {'CTR':>7} {'順位':>5}")
    print("  " + "-" * 58)
    for row in q7["rows"][:10]:
        print(
            f"  {row['query']:<30} {row['clicks']:>6} {row['impressions']:>8}"
            f" {row['ctr']*100:>6.1f}% {row['position']:>5.1f}"
        )

    # --- 検索クエリ（28日間）合計 ---
    q28 = data["query_28d"]
    total_clicks = sum(r["clicks"] for r in q28["rows"])
    total_impressions = sum(r["impressions"] for r in q28["rows"])
    print(f"\n■ 過去28日サマリー（{q28['period']}）")
    print(f"  総クリック数: {total_clicks:,}")
    print(f"  総表示回数:   {total_impressions:,}")
    if total_impressions > 0:
        print(f"  平均CTR:      {total_clicks / total_impressions * 100:.1f}%")
    print(f"  ユニーククエリ数: {q28['total_rows']}")

    # --- ページ別 ---
    pages = data["pages"]
    print(f"\n■ ページ別 TOP 10（{pages['period']}）")
    print(f"  {'ページ':<50} {'クリック':>6} {'表示':>8}")
    print("  " + "-" * 66)
    for row in pages["rows"][:10]:
        # URLが長いので末尾部分だけ表示
        url = row["page"].replace(data["site_url"], "/")
        if len(url) > 48:
            url = "..." + url[-45:]
        print(f"  {url:<50} {row['clicks']:>6} {row['impressions']:>8}")

    # --- デバイス別 ---
    devices = data["devices"]
    device_labels = {"DESKTOP": "PC", "MOBILE": "モバイル", "TABLET": "タブレット"}
    print(f"\n■ デバイス別（{devices['period']}）")
    for device, stats in devices["devices"].items():
        label = device_labels.get(device, device)
        print(
            f"  {label:<12} クリック: {stats['clicks']:>6}"
            f"  表示: {stats['impressions']:>8}"
            f"  CTR: {stats['ctr']*100:>5.1f}%"
            f"  順位: {stats['position']:>5.1f}"
        )

    # --- 日別推移（直近7日） ---
    daily = data["daily"]
    print(f"\n■ 日別推移（直近7日）")
    print(f"  {'日付':<12} {'クリック':>6} {'表示':>8}")
    print("  " + "-" * 28)
    for row in daily["rows"][-7:]:
        print(f"  {row['date']:<12} {row['clicks']:>6} {row['impressions']:>8}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Google Search Console API からデータを取得する"
    )
    parser.add_argument(
        "--credentials",
        "-c",
        help="サービスアカウント鍵ファイルのパス（省略時は環境変数 GOOGLE_APPLICATION_CREDENTIALS を使用）",
    )
    parser.add_argument(
        "--site-url",
        default=SITE_URL,
        help=f"対象サイトURL（デフォルト: {SITE_URL}）",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=28,
        help="ページ別・デバイス別・日別データの取得期間（デフォルト: 28日）",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        help="JSON保存先ディレクトリ（デフォルト: scripts/analytics/data/）",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="JSONファイルへの保存をスキップ",
    )

    args = parser.parse_args()

    try:
        print("Google Search Console API からデータを取得中...")
        data = fetch_all_data(
            credentials_path=args.credentials,
            site_url=args.site_url,
            days=args.days,
        )

        print_summary(data)

        if not args.no_save:
            output_dir = Path(args.output_dir) if args.output_dir else None
            filepath = save_data(data, output_dir)
            print(f"\nデータを保存しました: {filepath}")

    except FileNotFoundError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"API エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
