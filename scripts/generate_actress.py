"""人気AV女優ページ自動生成スクリプト"""
import os
import requests
import re
from datetime import datetime
from config import Config

# 人気女優キーワード（API検索用）
POPULAR_ACTRESSES = [
    "三上悠亜", "橋本ありな", "河北彩花", "小花のん", "楓カレン",
    "明日花キララ", "葵つかさ", "桃乃木かな", "天使もえ", "松本いちか",
    "美乃すずめ", "架乃ゆら", "伊藤舞雪", "七沢みあ", "石原希望",
    "永瀬ゆい", "有村のぞみ", "日向うみ", "月乃さくら", "汐見夏衣",
]


def fetch_actress_works(actress_name, hits=10):
    """指定女優の作品をAPIから取得"""
    params = {
        "api_id": Config.API_ID,
        "affiliate_id": Config.AFFILIATE_ID,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "hits": min(hits, 20),
        "sort": "rank",
        "keyword": actress_name,
        "output": "json",
    }
    try:
        r = requests.get(Config.API_BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("result", {}).get("items", [])
    except Exception:
        return []


def generate_actress_page(actress_name):
    """女優専門ページを生成"""
    items = fetch_actress_works(actress_name, hits=15)
    if not items:
        print(f"[スキップ] {actress_name}: データなし")
        return None

    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    slug = re.sub(r'[^a-zA-Z0-9]', '-', actress_name).strip('-').lower()
    if not slug:
        slug = f"actress-{hash(actress_name) % 10000}"

    # 最初の作品画像をカバーに
    first_img = ""
    img_data = items[0].get("imageURL", {})
    if img_data:
        first_img = img_data.get("large", img_data.get("small", ""))

    md = f"""---
title: "{actress_name}のおすすめAV作品一覧【{today.strftime('%Y年%m月')}最新】"
date: {today.strftime("%Y-%m-%dT%H:%M:%S+09:00")}
tags: ["{actress_name}", "AV女優", "おすすめ"]
categories: ["Actress"]
draft: false
description: "{actress_name}出演のおすすめAV作品を厳選紹介。最新作からランキング上位作品まで、サンプル動画付きでチェック。"
cover:
  image: "{first_img}"
  alt: "{actress_name}のおすすめAV作品"
  hidden: false
---

## {actress_name} おすすめ作品一覧

**{today.strftime('%Y年%m月')}更新** | {actress_name}出演の人気作品を厳選

"""

    for i, item in enumerate(items):
        title = item.get("title", "")
        content_id = item.get("content_id", "")
        affiliate_url = f"https://www.dmm.co.jp/digital/videoa/-/detail/=/cid={content_id}/?af_id={Config.AFFILIATE_ID}" if content_id else ""

        image_url = ""
        img_data = item.get("imageURL", {})
        if img_data:
            image_url = img_data.get("large", img_data.get("small", ""))

        prices = item.get("prices", {})
        price = prices.get("price", "") if isinstance(prices.get("price"), str) else ""

        genres = []
        item_info = item.get("iteminfo", {})
        if item_info:
            genres = [g.get("name", "") for g in item_info.get("genre", []) if g.get("name")]

        # サンプル画像
        sample_images = []
        sample_data = item.get("sampleImageURL", {})
        if sample_data:
            sl = sample_data.get("sample_l", {})
            if sl:
                sample_images = sl.get("image", [])[:3]

        genre_text = " / ".join(genres[:4]) if genres else ""

        md += f"""### {i+1}. {title[:60]}{"…" if len(title) > 60 else ""}

<div style="display: flex; gap: 16px; margin: 1em 0; flex-wrap: wrap;">
  <div style="flex: 0 0 200px;">
    <a href="{affiliate_url}" target="_blank" rel="nofollow">
      <img src="{image_url}" alt="{actress_name}出演作品" style="width: 200px; border-radius: 8px;" loading="lazy" />
    </a>
  </div>
  <div style="flex: 1; min-width: 200px;">
"""
        if genre_text:
            md += f"    <p><strong>ジャンル:</strong> {genre_text}</p>\n"
        if price:
            md += f"    <p><strong>価格:</strong> {price}</p>\n"

        md += f"""    <a href="{affiliate_url}" target="_blank" rel="nofollow"
       style="display: inline-block; padding: 8px 20px; background: #e63946; color: #fff; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 8px;">
      詳細を見る
    </a>
  </div>
</div>

"""
        if sample_images:
            md += '<div style="display: flex; gap: 8px; margin: 0.5em 0 1.5em;">\n'
            for img in sample_images:
                md += f'  <a href="{affiliate_url}" target="_blank" rel="nofollow sponsored"><img src="{img}" style="width: 120px; border-radius: 4px;" loading="lazy" /></a>\n'
            md += '</div>\n\n'

        md += "---\n\n"

    # フッター
    md += """
### MuscleLove

<div style="display: flex; gap: 16px; flex-wrap: wrap; margin: 1.5em 0;">
  <a href="https://www.patreon.com/c/MuscleLove" rel="nofollow" target="_blank"
     style="display: inline-block; padding: 10px 24px; background: #FF424D; color: #fff; text-decoration: none; border-radius: 6px; font-weight: bold;">
    MuscleLove on Patreon
  </a>
  <a href="https://x.com/MuscleGirlLove7" rel="nofollow" target="_blank"
     style="display: inline-block; padding: 10px 24px; background: #000; color: #fff; text-decoration: none; border-radius: 6px; font-weight: bold;">
    MuscleLove on X
  </a>
  <a href="https://linktr.ee/ILoveMyCats" rel="nofollow" target="_blank"
     style="display: inline-block; padding: 10px 24px; background: #43e660; color: #fff; text-decoration: none; border-radius: 6px; font-weight: bold;">
    MuscleLove Links
  </a>
</div>

<p style="text-align: center; margin: 2em 0 0.5em; font-size: 0.9em; color: #888;">Presented by <strong>MuscleLove</strong></p>
"""

    # 保存
    output_dir = Config.CONTENT_DIR
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{date_str}-actress-{slug}.md")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[生成] {filepath}")
    return filepath


def generate_all_actress_pages():
    """人気女優20人分のページを生成"""
    import time
    for actress in POPULAR_ACTRESSES:
        generate_actress_page(actress)
        time.sleep(1)  # APIレート制限対策


if __name__ == "__main__":
    generate_all_actress_pages()
