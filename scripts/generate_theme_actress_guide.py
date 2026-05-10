"""Generate a FANZA guide article for one actress and one narrow theme.

Example:
  python scripts/generate_theme_actress_guide.py ^
    --actress "竹内有紀" ^
    --theme-label "腹筋・筋肉" ^
    --keywords "腹筋,筋肉,マッスル,トレーニング" ^
    --slug "takeuchi-yuki-abs-fanza-guide"

The script uses the DMM/FANZA ItemList API credentials from .env via config.py.
It intentionally generates a curated hub page with affiliate search/detail links,
instead of inventing product data.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from config import Config


JST = timezone(timedelta(hours=9))
AXIS_HINTS = ("腹筋", "筋肉", "マッスル", "トレーニング", "フィットネス", "汗", "スポーツ", "鍛え", "肉体美", "バリキレ")


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def yaml_list(values: list[str]) -> str:
    return "[" + ", ".join(yaml_string(v) for v in values) + "]"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9-]+", "-", value.strip().lower()).strip("-")
    return slug or f"theme-actress-{abs(hash(value)) % 100000}"


def direct_affiliate_url(cid: str) -> str:
    return f"https://www.dmm.co.jp/digital/videoa/-/detail/=/cid={cid}/?af_id={Config.AFFILIATE_ID}"


def search_affiliate_url(query: str) -> str:
    from urllib.parse import quote

    return f"https://www.dmm.co.jp/digital/videoa/-/list/search/=/searchstr={quote(query)}/?af_id={Config.AFFILIATE_ID}"


def fetch_items(query: str, hits: int) -> tuple[list[dict[str, Any]], int]:
    params = {
        "api_id": Config.API_ID,
        "affiliate_id": Config.AFFILIATE_ID,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "hits": min(hits, 100),
        "sort": "rank",
        "keyword": query,
        "output": "json",
    }
    response = requests.get(Config.API_BASE_URL, params=params, timeout=30)
    response.raise_for_status()
    result = response.json().get("result", {})
    if result.get("status") != 200:
        raise RuntimeError(f"FANZA API error for {query}: {result.get('message')}")
    return result.get("items", []), int(result.get("total_count", 0) or 0)


def parse_item(item: dict[str, Any], query: str) -> dict[str, Any]:
    info = item.get("iteminfo") or {}
    cid = item.get("content_id") or item.get("product_id") or ""
    image_data = item.get("imageURL") or {}
    prices = item.get("prices") or {}

    def names(key: str) -> list[str]:
        values = info.get(key) or []
        return [v.get("name", "") for v in values if isinstance(v, dict) and v.get("name")]

    return {
        "cid": cid,
        "title": item.get("title", ""),
        "date": item.get("date", ""),
        "price": prices.get("price", "") if isinstance(prices.get("price", ""), str) else "",
        "image": image_data.get("large") or image_data.get("small") or "",
        "actresses": names("actress"),
        "genres": names("genre"),
        "maker": (names("maker") or [""])[0],
        "series": (names("series") or [""])[0],
        "query_hits": [query],
    }


def score_item(item: dict[str, Any], actress: str, keywords: list[str]) -> int:
    title = item.get("title", "")
    text = " ".join(
        [
            title,
            " ".join(item.get("genres", [])),
            item.get("maker", ""),
            item.get("series", ""),
            " ".join(item.get("query_hits", [])),
        ]
    )
    score = 0
    if actress in title or actress in " ".join(item.get("actresses", [])):
        score += 3
    for keyword in keywords:
        if keyword in title:
            score += 4
        elif keyword in text:
            score += 2
    for hint in AXIS_HINTS:
        if hint in title:
            score += 2
        elif hint in text:
            score += 1
    return score


def collect_products(actress: str, keywords: list[str], hits: int, sleep_sec: float) -> tuple[list[dict[str, Any]], dict[str, int]]:
    products: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}
    queries = [f"{actress} {keyword}" for keyword in keywords] + [actress]

    for query in queries:
        items, total = fetch_items(query, hits)
        counts[query] = total
        for raw in items:
            parsed = parse_item(raw, query)
            cid = parsed.get("cid") or parsed.get("title")
            if not cid:
                continue
            if cid in products:
                products[cid]["query_hits"].append(query)
            else:
                products[cid] = parsed
        time.sleep(sleep_sec)

    scored = []
    for product in products.values():
        product["score"] = score_item(product, actress, keywords)
        if product["score"] > 0:
            scored.append(product)
    scored.sort(key=lambda p: (-p["score"], p.get("cid", "")))
    return scored, counts


def render_article(
    *,
    actress: str,
    theme_label: str,
    keywords: list[str],
    slug: str,
    products: list[dict[str, Any]],
    counts: dict[str, int],
    limit: int,
) -> str:
    now = datetime.now(JST)
    selected = products[:limit]
    cover = selected[0]["image"] if selected else ""
    title = f"{actress}の{theme_label}系FANZA作品まとめ【DMMアフィリ】"
    description = (
        f"{actress}の{theme_label}系FANZA作品をDMM/FANZA API確認データで厳選。"
        f"{'・'.join(keywords[:4])}の検索導線をDMMアフィリリンク付きでまとめたガイド。"
    )
    tags = [actress, *keywords[:4], "FANZA", "DMMアフィリ", "女優レビュー"]
    frontmatter = [
        "---",
        "featured: true",
        f"title: {yaml_string(title)}",
        f"date: {now.strftime('%Y-%m-%dT%H:%M:%S+09:00')}",
        f"lastmod: {now.strftime('%Y-%m-%dT%H:%M:%S+09:00')}",
        "draft: false",
        'categories: ["女優", "muscle"]',
        f"tags: {yaml_list(tags)}",
        f"keywords: {yaml_list([f'{actress} {k}' for k in keywords] + [f'FANZA {theme_label}', f'{theme_label} AV'])}",
        f"description: {yaml_string(description)}",
        "cover:",
        f"  image: {yaml_string(cover)}",
        f"  alt: {yaml_string(title)}",
        "  hidden: false",
        "---",
        "",
    ]
    lines = frontmatter
    lines += [
        f"## {actress}は「{theme_label}」検索で集める",
        "",
        f"{actress}作品は、女優名だけで探すよりも **{'・'.join(keywords)}** のような狭いテーマで絞ると、検索意図が濃い読者を集めやすくなります。",
        "",
        "本記事では、DMM/FANZA APIで確認できた作品データをもとに、テーマに合う作品を優先して整理します。",
        "",
        "<!--more-->",
        "",
        "## 集計メモ",
        "",
        "| 検索語 | API確認件数 |",
        "|---|---:|",
    ]
    for query, count in counts.items():
        lines.append(f"| {query} | {count}件 |")
    lines += [
        "",
        f"上記から重複を除き、タイトル・ジャンル・出演者に「{'」「'.join(keywords)}」などが入る作品を優先しました。",
        "",
        '<div style="display:flex;gap:12px;flex-wrap:wrap;margin:1.5em 0;">',
    ]
    for keyword in keywords[:3]:
        query = f"{actress} {keyword}"
        lines.append(
            f'  <a href="{search_affiliate_url(query)}" target="_blank" rel="nofollow sponsored" '
            'style="display:inline-block;padding:10px 18px;background:#e63946;color:#fff;text-decoration:none;border-radius:6px;font-weight:bold;">'
            f"FANZAで{query}を探す</a>"
        )
    lines += ["</div>", "", f"## {theme_label}系おすすめ作品", ""]

    for index, product in enumerate(selected, start=1):
        cid = product.get("cid", "")
        title = product.get("title", "")
        lines += [
            f"### {index}. {cid}: {title[:34]}",
            "",
        ]
        if product.get("image"):
            lines += [f"![{actress} {theme_label} {cid}]({product['image']})", ""]
        lines += [
            f"**「{title}」**",
            "",
            "| 項目 | 内容 |",
            "|---|---|",
            f"| 品番 | {cid} |",
            f"| 出演 | {', '.join(product.get('actresses', [])) or actress} |",
            f"| メーカー | {product.get('maker') or '-'} |",
            f"| ジャンル | {' / '.join(product.get('genres', [])[:6]) or '-'} |",
            f"| 価格目安 | {product.get('price') or 'リンク先で確認'} |",
            "",
            f"{theme_label}系の検索導線に使いやすい一本です。タイトル・ジャンル・出演者を確認し、FANZA側の最新情報も合わせてチェックしてください。",
            "",
            f'<a href="{direct_affiliate_url(cid)}" target="_blank" rel="nofollow sponsored" style="display:inline-block;padding:10px 24px;background:#e63946;color:#fff;text-decoration:none;border-radius:6px;font-weight:bold;">FANZAで{cid}を見る</a>',
            "",
        ]

    lines += [
        "## まとめ",
        "",
        f"{actress}の{theme_label}系は、作品単体レビューよりもテーマ別ハブに集約すると内部リンクとSNS投稿の両方で使い回しやすくなります。",
        "",
        "検索導線は次の語に集約します。",
        "",
    ]
    for keyword in keywords[:5]:
        lines.append(f"- {actress} {keyword}")
    lines += [
        "",
        "---",
        "",
        "*本記事内のリンクはFANZA/DMMアフィリエイトリンクです。価格・配信状況・セール情報はリンク先で最新情報をご確認ください。*",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate actress x theme FANZA guide article.")
    parser.add_argument("--actress", required=True, help="Actress name, e.g. 竹内有紀")
    parser.add_argument("--theme-label", required=True, help="Theme label for article title, e.g. 腹筋・筋肉")
    parser.add_argument("--keywords", required=True, help="Comma-separated theme keywords")
    parser.add_argument("--slug", default="", help="ASCII slug without date prefix")
    parser.add_argument("--limit", type=int, default=8, help="Number of products to include")
    parser.add_argument("--hits", type=int, default=50, help="API hits per query")
    parser.add_argument("--sleep", type=float, default=0.4, help="Sleep seconds between API calls")
    parser.add_argument("--dry-run", action="store_true", help="Print target path only, do not write")
    args = parser.parse_args()

    if not Config.validate():
        return 1

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not keywords:
        raise SystemExit("--keywords must contain at least one keyword")

    slug = slugify(args.slug or f"{args.actress}-{args.theme_label}-fanza-guide")
    products, counts = collect_products(args.actress, keywords, args.hits, args.sleep)
    article = render_article(
        actress=args.actress,
        theme_label=args.theme_label,
        keywords=keywords,
        slug=slug,
        products=products,
        counts=counts,
        limit=args.limit,
    )

    date_prefix = datetime.now(JST).strftime("%Y-%m-%d")
    output_path = Path(Config.CONTENT_DIR) / f"{date_prefix}-{slug}.md"
    print(f"[info] collected {len(products)} scored products")
    print(f"[info] output: {output_path}")
    if args.dry_run:
        print(article[:1000])
        return 0
    output_path.write_text(article, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
