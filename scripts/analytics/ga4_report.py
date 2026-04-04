#!/usr/bin/env python3
"""
GA4 Data API レポート取得スクリプト

Google Analytics 4 の Data API を使って各種レポートを取得し、
JSON形式で保存する。

============================================================
セットアップ手順:
============================================================

1. Google Cloud Console (https://console.cloud.google.com/) でプロジェクトを作成

2. 「Google Analytics Data API」を有効化
   - APIs & Services > Library > "Google Analytics Data API" を検索して有効化

3. サービスアカウントを作成
   - APIs & Services > Credentials > Create Credentials > Service Account
   - 適当な名前を付けて作成
   - Keys タブで JSON キーを作成・ダウンロード

4. GA4 プロパティでサービスアカウントに権限を付与
   - GA4 管理画面 > プロパティ > プロパティアクセス管理
   - サービスアカウントのメールアドレス（xxx@xxx.iam.gserviceaccount.com）を
     「閲覧者」権限で追加

5. 環境変数を設定
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

6. パッケージインストール
   pip install google-analytics-data

7. GA4プロパティIDを確認
   - GA4 管理画面 > プロパティ設定 > プロパティID（数字のみ）
   - 測定ID (G-XXXXXXX) ではなく、数値のプロパティIDが必要
   - 例: 測定ID "G-CSFVD34MKK" に対応する数値プロパティIDを使う

============================================================
使用例:
============================================================

  # 環境変数で認証（デフォルトのプロパティID使用）
  python ga4_report.py

  # プロパティIDを指定
  python ga4_report.py --property-id 123456789

  # 鍵ファイルを引数で指定
  python ga4_report.py --credentials /path/to/key.json

  # 他のスクリプトから呼び出し
  from analytics.ga4_report import fetch_ga4_report
  result = fetch_ga4_report(property_id="123456789")
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        FilterExpression,
        Filter,
        Metric,
        OrderBy,
        RunReportRequest,
    )
except ImportError:
    print("エラー: google-analytics-data パッケージがインストールされていません。")
    print("  pip install google-analytics-data")
    sys.exit(1)


# デフォルトのプロパティID（数値IDに置き換えること）
# 測定ID G-CSFVD34MKK に対応する数値プロパティIDを設定する
DEFAULT_PROPERTY_ID = "000000000"

# データ保存先（このスクリプトからの相対パス）
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"


def _get_client(credentials_path: str | None = None) -> BetaAnalyticsDataClient:
    """GA4 Data API クライアントを生成する。"""
    if credentials_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    elif not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        raise RuntimeError(
            "認証情報が設定されていません。\n"
            "環境変数 GOOGLE_APPLICATION_CREDENTIALS にサービスアカウント鍵ファイルの"
            "パスを設定するか、--credentials 引数で指定してください。"
        )
    return BetaAnalyticsDataClient()


def _run_report(
    client: BetaAnalyticsDataClient,
    property_id: str,
    dimensions: list[str],
    metrics: list[str],
    date_ranges: list[dict],
    order_by_metric: str | None = None,
    limit: int = 0,
    dimension_filter: FilterExpression | None = None,
) -> list[dict]:
    """汎用レポート実行ヘルパー。"""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(**dr) for dr in date_ranges],
        limit=limit if limit > 0 else 0,
        dimension_filter=dimension_filter,
    )
    if order_by_metric:
        request.order_bys = [
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name=order_by_metric),
                desc=True,
            )
        ]

    response = client.run_report(request)

    rows = []
    for row in response.rows:
        entry = {}
        for i, dim in enumerate(dimensions):
            entry[dim] = row.dimension_values[i].value
        for i, met in enumerate(metrics):
            val = row.metric_values[i].value
            # 数値に変換を試みる
            try:
                entry[met] = int(val)
            except ValueError:
                try:
                    entry[met] = float(val)
                except ValueError:
                    entry[met] = val
        rows.append(entry)
    return rows


# ------------------------------------------------------------------
# 個別レポート取得関数
# ------------------------------------------------------------------

def fetch_summary(client: BetaAnalyticsDataClient, property_id: str) -> dict:
    """サマリー: アクティブユーザー、セッション、PV、平均エンゲージメント時間。"""
    metrics = [
        "activeUsers",
        "sessions",
        "screenPageViews",
        "averageSessionDuration",
    ]
    result = {}
    for label, start in [("7days", "7daysAgo"), ("28days", "28daysAgo")]:
        rows = _run_report(
            client,
            property_id,
            dimensions=[],
            metrics=metrics,
            date_ranges=[{"start_date": start, "end_date": "today"}],
        )
        if rows:
            result[label] = rows[0]
        else:
            result[label] = {m: 0 for m in metrics}
    return result


def fetch_top_pages(client: BetaAnalyticsDataClient, property_id: str) -> list[dict]:
    """ページ別 PV 上位50ページ（過去28日）。"""
    return _run_report(
        client,
        property_id,
        dimensions=["pagePath", "pageTitle"],
        metrics=["screenPageViews", "activeUsers"],
        date_ranges=[{"start_date": "28daysAgo", "end_date": "today"}],
        order_by_metric="screenPageViews",
        limit=50,
    )


def fetch_traffic_sources(client: BetaAnalyticsDataClient, property_id: str) -> list[dict]:
    """流入元別（チャネルグループ）の内訳（過去28日）。"""
    return _run_report(
        client,
        property_id,
        dimensions=["sessionDefaultChannelGroup"],
        metrics=["sessions", "activeUsers", "screenPageViews"],
        date_ranges=[{"start_date": "28daysAgo", "end_date": "today"}],
        order_by_metric="sessions",
    )


def fetch_device_breakdown(client: BetaAnalyticsDataClient, property_id: str) -> list[dict]:
    """デバイス別の内訳（過去28日）。"""
    return _run_report(
        client,
        property_id,
        dimensions=["deviceCategory"],
        metrics=["sessions", "activeUsers", "screenPageViews"],
        date_ranges=[{"start_date": "28daysAgo", "end_date": "today"}],
        order_by_metric="sessions",
    )


def fetch_daily_trend(client: BetaAnalyticsDataClient, property_id: str) -> list[dict]:
    """日別推移: 過去28日のアクティブユーザー・PV。"""
    rows = _run_report(
        client,
        property_id,
        dimensions=["date"],
        metrics=["activeUsers", "screenPageViews"],
        date_ranges=[{"start_date": "28daysAgo", "end_date": "today"}],
    )
    # 日付昇順にソート
    rows.sort(key=lambda r: r["date"])
    return rows


def fetch_category_breakdown(client: BetaAnalyticsDataClient, property_id: str) -> list[dict]:
    """カテゴリ別: /categories/ 配下のページパスを集計（過去28日）。"""
    dim_filter = FilterExpression(
        filter=Filter(
            field_name="pagePath",
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.CONTAINS,
                value="/categories/",
            ),
        )
    )
    rows = _run_report(
        client,
        property_id,
        dimensions=["pagePath"],
        metrics=["screenPageViews", "activeUsers"],
        date_ranges=[{"start_date": "28daysAgo", "end_date": "today"}],
        order_by_metric="screenPageViews",
        limit=50,
        dimension_filter=dim_filter,
    )

    # パスからカテゴリ名を抽出して再集計
    category_totals: dict[str, dict] = {}
    for row in rows:
        path = row["pagePath"]
        # /categories/xxx/... から xxx 部分を抽出
        parts = path.strip("/").split("/")
        try:
            idx = parts.index("categories")
            category = parts[idx + 1] if idx + 1 < len(parts) else "unknown"
        except (ValueError, IndexError):
            category = "unknown"

        if category not in category_totals:
            category_totals[category] = {"category": category, "screenPageViews": 0, "activeUsers": 0}
        category_totals[category]["screenPageViews"] += row["screenPageViews"]
        category_totals[category]["activeUsers"] += row["activeUsers"]

    result = sorted(category_totals.values(), key=lambda x: x["screenPageViews"], reverse=True)
    return result


# ------------------------------------------------------------------
# メインの取得関数
# ------------------------------------------------------------------

def fetch_ga4_report(
    property_id: str = DEFAULT_PROPERTY_ID,
    credentials_path: str | None = None,
) -> dict:
    """
    GA4 の全レポートを取得して辞書で返す。

    Args:
        property_id: GA4 の数値プロパティID
        credentials_path: サービスアカウント鍵ファイルのパス（省略時は環境変数を使用）

    Returns:
        各レポートをまとめた辞書
    """
    client = _get_client(credentials_path)

    print("GA4 レポートを取得中...")

    print("  - サマリー...")
    summary = fetch_summary(client, property_id)

    print("  - ページ別 PV...")
    top_pages = fetch_top_pages(client, property_id)

    print("  - 流入元別...")
    traffic_sources = fetch_traffic_sources(client, property_id)

    print("  - デバイス別...")
    device_breakdown = fetch_device_breakdown(client, property_id)

    print("  - 日別推移...")
    daily_trend = fetch_daily_trend(client, property_id)

    print("  - カテゴリ別...")
    category_breakdown = fetch_category_breakdown(client, property_id)

    report = {
        "generated_at": datetime.now().isoformat(),
        "property_id": property_id,
        "summary": summary,
        "top_pages": top_pages,
        "traffic_sources": traffic_sources,
        "device_breakdown": device_breakdown,
        "daily_trend": daily_trend,
        "category_breakdown": category_breakdown,
    }

    print("取得完了。")
    return report


def save_report(report: dict) -> Path:
    """レポートを JSON ファイルとして保存する。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = DATA_DIR / f"ga4_report_{date_str}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return filepath


def print_summary(report: dict) -> None:
    """コンソールにサマリーを表示する。"""
    print("\n" + "=" * 60)
    print("GA4 レポート サマリー")
    print(f"生成日時: {report['generated_at']}")
    print(f"プロパティID: {report['property_id']}")
    print("=" * 60)

    # サマリー
    for period_label, period_key in [("過去7日", "7days"), ("過去28日", "28days")]:
        s = report["summary"].get(period_key, {})
        print(f"\n--- {period_label} ---")
        print(f"  アクティブユーザー: {s.get('activeUsers', 'N/A'):>10,}")
        print(f"  セッション数:       {s.get('sessions', 'N/A'):>10,}")
        print(f"  ページビュー数:     {s.get('screenPageViews', 'N/A'):>10,}")
        avg_dur = s.get("averageSessionDuration", 0)
        if isinstance(avg_dur, (int, float)):
            minutes = int(avg_dur) // 60
            seconds = int(avg_dur) % 60
            print(f"  平均エンゲージメント: {minutes}分{seconds}秒")
        else:
            print(f"  平均エンゲージメント: {avg_dur}")

    # 流入元
    print("\n--- 流入元別（過去28日）---")
    for row in report.get("traffic_sources", []):
        ch = row.get("sessionDefaultChannelGroup", "?")
        sess = row.get("sessions", 0)
        print(f"  {ch:<25} {sess:>8,} sessions")

    # デバイス
    print("\n--- デバイス別（過去28日）---")
    for row in report.get("device_breakdown", []):
        dev = row.get("deviceCategory", "?")
        sess = row.get("sessions", 0)
        print(f"  {dev:<15} {sess:>8,} sessions")

    # トップページ（上位10件のみ表示）
    print("\n--- PV上位ページ（過去28日・上位10件）---")
    for i, row in enumerate(report.get("top_pages", [])[:10], 1):
        path = row.get("pagePath", "?")
        pv = row.get("screenPageViews", 0)
        print(f"  {i:>2}. {pv:>8,} PV  {path}")

    # カテゴリ上位
    cats = report.get("category_breakdown", [])
    if cats:
        print("\n--- カテゴリ別（過去28日・上位10件）---")
        for row in cats[:10]:
            cat = row.get("category", "?")
            pv = row.get("screenPageViews", 0)
            print(f"  {cat:<30} {pv:>8,} PV")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="GA4 Data API からレポートを取得する"
    )
    parser.add_argument(
        "--property-id",
        default=os.environ.get("GA4_PROPERTY_ID", DEFAULT_PROPERTY_ID),
        help="GA4 の数値プロパティID（環境変数 GA4_PROPERTY_ID でも指定可）",
    )
    parser.add_argument(
        "--credentials",
        default=None,
        help="サービスアカウント鍵ファイルのパス（省略時は GOOGLE_APPLICATION_CREDENTIALS を使用）",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="JSON ファイルへの保存をスキップする",
    )
    args = parser.parse_args()

    try:
        report = fetch_ga4_report(
            property_id=args.property_id,
            credentials_path=args.credentials,
        )
    except RuntimeError as e:
        print(f"\nエラー: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAPI呼び出しエラー: {e}", file=sys.stderr)
        sys.exit(1)

    print_summary(report)

    if not args.no_save:
        filepath = save_report(report)
        print(f"\nレポートを保存しました: {filepath}")

    return report


if __name__ == "__main__":
    main()
