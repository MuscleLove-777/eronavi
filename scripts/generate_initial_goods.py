"""
グッズ8ジャンルの初期記事を生成するスクリプト
各ジャンル2本ずつ = 16本
"""

import sys
import time
from pathlib import Path

# scriptsディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Config, GENRES
from fetch_products import fetch_products
from generate_articles import generate_articles

GOODS_GENRES = [
    "onahole", "vibrator", "tenga", "lotion",
    "cosplay_goods", "sm_goods", "couple", "new_goods",
]

ARTICLES_PER_GENRE = 2


def main():
    print("[開始] グッズ8ジャンル初期記事生成\n")

    if not Config.validate():
        sys.exit(1)

    total_files = []

    for genre_key in GOODS_GENRES:
        genre_info = GENRES.get(genre_key, {})
        label = genre_info.get("label", genre_key)
        keywords = genre_info.get("keywords", [])
        service = genre_info.get("service", "mono")
        floor = genre_info.get("floor", "goods")

        print(f"\n{'='*40}")
        print(f"  ジャンル: {label} ({genre_key})")
        print(f"{'='*40}")

        all_products = []
        seen_ids = set()

        for kw in keywords:
            products = fetch_products(
                keyword=kw,
                hits=10,
                service=service,
                floor=floor,
                genre=genre_key,
            )
            for p in products:
                pid = p.get("content_id", "")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    all_products.append(p)
            time.sleep(1)

        # 必要件数に絞る
        all_products = all_products[:ARTICLES_PER_GENRE]

        if not all_products:
            print(f"[{label}] 取得できた商品がないため、スキップ")
            continue

        files = generate_articles(all_products, genre=genre_key)
        total_files.extend(files)
        print(f"[{label}] {len(files)}件の記事を生成")

    print(f"\n{'='*60}")
    print(f"  合計: {len(total_files)}件の記事を生成しました")
    print(f"{'='*60}")

    for f in total_files:
        print(f"  - {Path(f).name}")


if __name__ == "__main__":
    main()
