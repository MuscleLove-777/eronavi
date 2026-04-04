#!/usr/bin/env python3
"""
エロナビ アクセス分析 - メイン実行スクリプト

全分析ツールを一括実行、または個別実行するためのスクリプト。

使い方:
    全実行:   python run_analytics.py
    個別実行: python run_analytics.py --gsc        # Search Console のみ
              python run_analytics.py --ga4        # GA4 のみ
              python run_analytics.py --health     # サイトヘルスチェックのみ
              python run_analytics.py --report     # レポート生成のみ
    複数指定: python run_analytics.py --gsc --ga4  # GSC + GA4
"""

import argparse
import sys
import time
from pathlib import Path

# スクリプトのディレクトリをパスに追加
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))


def run_search_console():
    """Search Console データを取得する。"""
    print("=" * 60)
    print("[1/4] Search Console データ取得")
    print("=" * 60)
    try:
        from search_console import main as gsc_main
        gsc_main()
        print("[OK] Search Console データ取得完了\n")
    except Exception as e:
        print(f"[ERROR] Search Console データ取得に失敗: {e}\n")


def run_ga4():
    """GA4 データを取得する。"""
    print("=" * 60)
    print("[2/4] GA4 データ取得")
    print("=" * 60)
    try:
        from ga4_report import main as ga4_main
        ga4_main()
        print("[OK] GA4 データ取得完了\n")
    except Exception as e:
        print(f"[ERROR] GA4 データ取得に失敗: {e}\n")


def run_site_health():
    """サイトヘルスチェックを実行する。"""
    print("=" * 60)
    print("[3/4] サイトヘルスチェック")
    print("=" * 60)
    try:
        from site_health import main as health_main
        health_main()
        print("[OK] サイトヘルスチェック完了\n")
    except Exception as e:
        print(f"[ERROR] サイトヘルスチェックに失敗: {e}\n")


def run_report():
    """パワーポイントレポートを生成する。"""
    print("=" * 60)
    print("[4/4] レポート生成")
    print("=" * 60)
    try:
        from generate_report import main as report_main
        report_main()
        print("[OK] レポート生成完了\n")
    except Exception as e:
        print(f"[ERROR] レポート生成に失敗: {e}\n")


def parse_args():
    """コマンドライン引数を解析する。"""
    parser = argparse.ArgumentParser(
        description="エロナビ アクセス分析ツール - 一括実行スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python run_analytics.py              # 全ステップ実行
  python run_analytics.py --gsc        # Search Console のみ
  python run_analytics.py --ga4        # GA4 のみ
  python run_analytics.py --health     # サイトヘルスチェックのみ
  python run_analytics.py --report     # レポート生成のみ
  python run_analytics.py --gsc --ga4  # 複数指定も可能
        """,
    )
    parser.add_argument(
        "--gsc", action="store_true",
        help="Search Console データ取得を実行",
    )
    parser.add_argument(
        "--ga4", action="store_true",
        help="GA4 データ取得を実行",
    )
    parser.add_argument(
        "--health", action="store_true",
        help="サイトヘルスチェックを実行",
    )
    parser.add_argument(
        "--report", action="store_true",
        help="パワーポイントレポート生成を実行",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # 個別指定がなければ全実行
    run_all = not any([args.gsc, args.ga4, args.health, args.report])

    print("=" * 60)
    print("  エロナビ アクセス分析 開始")
    print("=" * 60)
    start = time.time()

    if run_all or args.gsc:
        run_search_console()

    if run_all or args.ga4:
        run_ga4()

    if run_all or args.health:
        run_site_health()

    if run_all or args.report:
        run_report()

    elapsed = time.time() - start
    print("=" * 60)
    print(f"  全処理完了 (所要時間: {elapsed:.1f}秒)")
    print("=" * 60)


if __name__ == "__main__":
    main()
