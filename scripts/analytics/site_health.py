"""
エロナビ サイトヘルスチェッカー
================================
sitemap.xmlの解析、全URLのHTTPステータスチェック、
ローカル記事との整合性確認を行う。
"""

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

import requests

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
SITE_URL = "https://musclelove-777.github.io/eronavi/"
SITEMAP_URL = SITE_URL + "sitemap.xml"
DEFAULT_CONTENT_DIR = r"c:\Users\atsus\000_ClaudeCode\051_FANZAアフィリ\eronavi\content\posts"
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
MAX_WORKERS = 10
TIMEOUT = 5  # 秒


# ---------------------------------------------------------------------------
# Sitemap 取得・パース
# ---------------------------------------------------------------------------
def fetch_sitemap(sitemap_url: str = SITEMAP_URL) -> list[str]:
    """sitemap.xml を取得し、全 <loc> URL をリストで返す。"""
    resp = requests.get(sitemap_url, timeout=TIMEOUT)
    resp.raise_for_status()

    root = ElementTree.fromstring(resp.content)
    # 名前空間を自動検出
    ns = ""
    m = re.match(r"\{(.+?)\}", root.tag)
    if m:
        ns = m.group(1)

    urls: list[str] = []
    ns_map = {"ns": ns} if ns else {}

    # sitemapindex の場合は子 sitemap を再帰取得
    if root.tag.endswith("sitemapindex"):
        for sitemap_el in root.findall("ns:sitemap/ns:loc", ns_map) if ns else root.findall("sitemap/loc"):
            child_url = sitemap_el.text.strip() if sitemap_el.text else ""
            if child_url:
                urls.extend(fetch_sitemap(child_url))
    else:
        tag = "ns:url/ns:loc" if ns else "url/loc"
        for loc in root.findall(tag, ns_map):
            if loc.text:
                urls.append(loc.text.strip())

    return urls


# ---------------------------------------------------------------------------
# HTTP ステータスチェック (並列)
# ---------------------------------------------------------------------------
def _check_single_url(url: str) -> dict:
    """1 URL のステータスを返す。"""
    try:
        resp = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        return {
            "url": url,
            "status": resp.status_code,
            "ok": resp.status_code < 400,
            "redirect": resp.history[0].status_code if resp.history else None,
        }
    except requests.RequestException as exc:
        return {
            "url": url,
            "status": None,
            "ok": False,
            "error": str(exc),
        }


def check_urls(urls: list[str], max_workers: int = MAX_WORKERS) -> list[dict]:
    """URL リストを並列でヘッドリクエストし、結果リストを返す。"""
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_check_single_url, u): u for u in urls}
        for fut in as_completed(futures):
            results.append(fut.result())
    return results


# ---------------------------------------------------------------------------
# URL 分類・集計
# ---------------------------------------------------------------------------
def classify_urls(urls: list[str]) -> dict:
    """URL をカテゴリ別・日付別に集計する。"""
    categories: Counter = Counter()
    dates: Counter = Counter()
    page_types: Counter = Counter()

    for url in urls:
        path = url.replace(SITE_URL, "").strip("/")
        parts = path.split("/")

        if not path:
            page_types["top"] += 1
        elif path.startswith("posts/"):
            page_types["post"] += 1
            # Hugo slug: posts/YYYY-MM-DD-xxx/
            slug = parts[1] if len(parts) > 1 else ""
            date_match = re.match(r"(\d{4}-\d{2}-\d{2})", slug)
            if date_match:
                dates[date_match.group(1)] += 1
        elif path.startswith("categories/"):
            page_types["category_page"] += 1
            if len(parts) > 1 and parts[1]:
                categories[parts[1]] += 1
        elif path.startswith("tags/"):
            page_types["tag_page"] += 1
        elif path.startswith("page/"):
            page_types["pagination"] += 1
        else:
            page_types["other"] += 1

    return {
        "categories": dict(categories.most_common()),
        "dates": dict(sorted(dates.items())),
        "page_types": dict(page_types.most_common()),
    }


# ---------------------------------------------------------------------------
# ローカル Markdown スキャン
# ---------------------------------------------------------------------------
def scan_local_posts(content_dir: str = DEFAULT_CONTENT_DIR) -> dict:
    """ローカルの Markdown ファイルを走査し、フロントマターから集計する。"""
    content_path = Path(content_dir)
    if not content_path.is_dir():
        return {"error": f"Directory not found: {content_dir}", "total": 0}

    md_files = list(content_path.glob("*.md"))
    total = len(md_files)
    categories: Counter = Counter()
    dates: Counter = Counter()
    drafts = 0

    for fp in md_files:
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # フロントマター抽出 (---...---)
        fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not fm_match:
            continue
        fm = fm_match.group(1)

        # draft
        if re.search(r"^draft:\s*true", fm, re.MULTILINE | re.IGNORECASE):
            drafts += 1

        # categories
        cat_match = re.search(r'^categories:\s*\[(.+?)\]', fm, re.MULTILINE)
        if cat_match:
            for cat in re.findall(r'"([^"]+)"', cat_match.group(1)):
                categories[cat] += 1

        # date from filename (YYYY-MM-DD-...)
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", fp.name)
        if date_match:
            dates[date_match.group(1)] += 1

    return {
        "total": total,
        "drafts": drafts,
        "published": total - drafts,
        "categories": dict(categories.most_common()),
        "dates": dict(sorted(dates.items())),
    }


# ---------------------------------------------------------------------------
# メインロジック
# ---------------------------------------------------------------------------
def run_health_check(
    sitemap_url: str = SITEMAP_URL,
    content_dir: str = DEFAULT_CONTENT_DIR,
    max_workers: int = MAX_WORKERS,
) -> dict:
    """サイトヘルスチェックを実行し、結果辞書を返す。"""
    now = datetime.now()
    report: dict = {
        "timestamp": now.isoformat(),
        "site_url": SITE_URL,
        "sitemap_url": sitemap_url,
    }

    # 1. Sitemap 取得
    print("[1/5] Sitemap を取得中 ...")
    try:
        urls = fetch_sitemap(sitemap_url)
        report["sitemap"] = {
            "status": "ok",
            "total_urls": len(urls),
        }
    except Exception as exc:
        print(f"  ERROR: Sitemap 取得失敗 - {exc}")
        report["sitemap"] = {"status": "error", "message": str(exc), "total_urls": 0}
        urls = []

    # 2. URL 分類
    print("[2/5] URL を分類中 ...")
    classification = classify_urls(urls)
    report["classification"] = classification

    # 3. HTTP ステータスチェック
    print(f"[3/5] {len(urls)} 件の URL をチェック中 (並列 {max_workers}) ...")
    start = time.time()
    url_results = check_urls(urls, max_workers) if urls else []
    elapsed = time.time() - start

    ok_count = sum(1 for r in url_results if r["ok"])
    error_count = len(url_results) - ok_count
    status_counter: Counter = Counter()
    for r in url_results:
        status_counter[r.get("status", "error")] += 1

    report["http_check"] = {
        "total": len(url_results),
        "ok": ok_count,
        "errors": error_count,
        "elapsed_sec": round(elapsed, 2),
        "status_codes": dict(status_counter.most_common()),
        "error_urls": [r for r in url_results if not r["ok"]],
    }

    # 4. ローカル記事スキャン
    print("[4/5] ローカル記事をスキャン中 ...")
    local = scan_local_posts(content_dir)
    report["local_posts"] = local

    # 5. 公開記事 vs sitemap 比較
    print("[5/5] 公開記事と sitemap を比較中 ...")
    sitemap_post_count = classification["page_types"].get("post", 0)
    local_published = local.get("published", 0)
    diff = local_published - sitemap_post_count
    report["comparison"] = {
        "sitemap_posts": sitemap_post_count,
        "local_published": local_published,
        "difference": diff,
        "note": (
            "一致" if diff == 0
            else f"ローカルが {abs(diff)} 件{'多い' if diff > 0 else '少ない'}"
        ),
    }

    # Google Indexing 簡易 (sitemap URL 数で代替)
    report["indexing_estimate"] = {
        "sitemap_url_count": len(urls),
        "note": "sitemap.xml に含まれる URL 数 = 検索エンジンにインデックス登録可能な最大数",
    }

    return report


# ---------------------------------------------------------------------------
# 保存・表示
# ---------------------------------------------------------------------------
def save_report(report: dict) -> Path:
    """レポートを JSON ファイルに保存して保存パスを返す。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = DATA_DIR / f"site_health_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return out_path


def print_summary(report: dict) -> None:
    """コンソールにサマリーを表示する。"""
    sep = "=" * 60
    print(f"\n{sep}")
    print("  エロナビ サイトヘルスレポート")
    print(f"  {report.get('timestamp', '')}")
    print(sep)

    # Sitemap
    sm = report.get("sitemap", {})
    print(f"\n[Sitemap]")
    print(f"  ステータス : {sm.get('status', '?')}")
    print(f"  URL 総数   : {sm.get('total_urls', 0)}")

    # HTTP チェック
    hc = report.get("http_check", {})
    print(f"\n[HTTP ステータスチェック]")
    print(f"  チェック数 : {hc.get('total', 0)}")
    print(f"  正常 (2xx) : {hc.get('ok', 0)}")
    print(f"  異常       : {hc.get('errors', 0)}")
    print(f"  所要時間   : {hc.get('elapsed_sec', 0)} 秒")
    if hc.get("status_codes"):
        print(f"  ステータス別 : {hc['status_codes']}")
    errors = hc.get("error_urls", [])
    if errors:
        print(f"\n  --- エラー URL ({len(errors)} 件) ---")
        for e in errors[:20]:
            status = e.get("status") or e.get("error", "?")
            print(f"    {status} : {e['url']}")
        if len(errors) > 20:
            print(f"    ... 他 {len(errors) - 20} 件")

    # ページ分類
    cl = report.get("classification", {})
    pt = cl.get("page_types", {})
    print(f"\n[ページ種別]")
    for k, v in pt.items():
        print(f"  {k:20s} : {v}")

    # カテゴリ上位
    cats = cl.get("categories", {})
    if cats:
        print(f"\n[カテゴリ (上位10)]")
        for k, v in list(cats.items())[:10]:
            print(f"  {k:20s} : {v}")

    # ローカル記事
    lp = report.get("local_posts", {})
    print(f"\n[ローカル記事]")
    print(f"  総数       : {lp.get('total', 0)}")
    print(f"  公開       : {lp.get('published', 0)}")
    print(f"  下書き     : {lp.get('drafts', 0)}")

    # 比較
    comp = report.get("comparison", {})
    print(f"\n[Sitemap vs ローカル]")
    print(f"  Sitemap 記事数   : {comp.get('sitemap_posts', 0)}")
    print(f"  ローカル公開数   : {comp.get('local_published', 0)}")
    print(f"  差分             : {comp.get('note', '?')}")

    # インデックス推定
    idx = report.get("indexing_estimate", {})
    print(f"\n[インデックス推定]")
    print(f"  Sitemap URL 数   : {idx.get('sitemap_url_count', 0)}")

    print(f"\n{sep}\n")


# ---------------------------------------------------------------------------
# CLI エントリポイント
# ---------------------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="エロナビ サイトヘルスチェッカー")
    parser.add_argument(
        "--content-dir",
        default=DEFAULT_CONTENT_DIR,
        help=f"ローカル記事ディレクトリ (default: {DEFAULT_CONTENT_DIR})",
    )
    parser.add_argument(
        "--sitemap-url",
        default=SITEMAP_URL,
        help=f"Sitemap URL (default: {SITEMAP_URL})",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"並列スレッド数 (default: {MAX_WORKERS})",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="JSON ファイルへの保存をスキップ",
    )
    args = parser.parse_args()

    report = run_health_check(
        sitemap_url=args.sitemap_url,
        content_dir=args.content_dir,
        max_workers=args.workers,
    )

    print_summary(report)

    if not args.no_save:
        path = save_report(report)
        print(f"レポート保存先: {path}")


if __name__ == "__main__":
    main()
