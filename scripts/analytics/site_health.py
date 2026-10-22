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
from xml.etree.ElementTree import ParseError as XMLParseError
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
import zlib

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

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
MAX_REDIRECTS = 3
MAX_FETCH_SECONDS = 30
MAX_WIRE_BYTES = 10 * 1024 * 1024
MAX_XML_BYTES = 10 * 1024 * 1024
MAX_XML_NODES = 500_000
MAX_XML_DEPTH = 32
MAX_SITEMAPS = 100
MAX_SITEMAP_DEPTH = 4
MAX_URLS = 50_000


# ---------------------------------------------------------------------------
# Sitemap 取得・パース
# ---------------------------------------------------------------------------
def _trusted_url(value: str, base: str = SITE_URL) -> str:
    """取得先はこのサイトのHTTPS URLだけ。相対URLとfragmentを正規化する。"""
    if (not isinstance(value, str) or not value or len(value) > 2048
            or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
            or "\\" in value):
        raise ValueError("Invalid site URL")
    try:
        parsed = urlsplit(urljoin(base, value))
        expected = urlsplit(SITE_URL)
        if (parsed.scheme != "https" or parsed.hostname != expected.hostname
                or parsed.port not in (None, 443)
                or parsed.username is not None or parsed.password is not None
                or parsed.query):
            raise ValueError("Invalid site URL")
        decoded = unquote(parsed.path, encoding="utf-8", errors="strict")
        if (not decoded.startswith(expected.path) or "\\" in decoded or "%" in decoded
                or any(c in {".", ".."} for c in decoded.split("/"))
                or any(ord(c) < 32 or ord(c) == 127 for c in decoded)):
            raise ValueError("Invalid site path")
        # literal DNS名を保持し、userinfo/port/query/fragmentを取得先へ引き継がない。
        path = quote(decoded, safe="/:@-._~!$&'()*+,;=")
        return urlunsplit(("https", expected.hostname, path, "", ""))
    except (ValueError, UnicodeError):
        raise ValueError("Invalid site URL") from None


def _bounded_xml_body(response, read_budget_end: float) -> bytes:
    # raw転送を先に制限し、urllib3内部の自動展開による大きな割当を避ける。
    encoding = response.headers.get("Content-Encoding", "").strip().lower()
    if encoding not in {"", "identity", "gzip", "x-gzip"}:
        raise ValueError("Unsupported sitemap content encoding")
    length = response.headers.get("Content-Length")
    if length is not None:
        try:
            if int(length) < 0 or int(length) > MAX_WIRE_BYTES:
                raise ValueError("Sitemap wire body is too large")
        except (TypeError, ValueError):
            raise ValueError("Invalid sitemap body length") from None
    chunks = []
    size = 0
    # timeoutはsocketのread間隔。累積時間はchunk間に確認し、厳密な総時間ではない。
    for chunk in response.raw.stream(65536, decode_content=False):
        if time.monotonic() > read_budget_end:
            raise ValueError("Sitemap body timeout")
        if not chunk:
            continue
        size += len(chunk)
        if size > MAX_WIRE_BYTES:
            raise ValueError("Sitemap wire body is too large")
        chunks.append(chunk)
    body = b"".join(chunks)
    # HTTP gzipとContent-Encodingのない.xml.gzを同じ上限付きdecoderで扱う。
    if encoding in {"gzip", "x-gzip"} or body.startswith(b"\x1f\x8b"):
        try:
            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
            body = decoder.decompress(body, MAX_XML_BYTES + 1)
            if (len(body) > MAX_XML_BYTES or decoder.unconsumed_tail
                    or decoder.unused_data or not decoder.eof):
                raise ValueError("Invalid or oversized gzip sitemap")
        except zlib.error:
            raise ValueError("Invalid gzip sitemap") from None
    elif len(body) > MAX_XML_BYTES:
        raise ValueError("Sitemap body is too large")
    return body


def _site_request(method: str, url: str):
    current = _trusted_url(url)
    first_redirect = None
    started = time.monotonic()
    with requests.Session() as session:
        # 公開サイトの検査に端末の.netrc/環境proxy/認証状態を持ち込まない。
        session.trust_env = False
        for hop in range(MAX_REDIRECTS + 1):
            if time.monotonic() - started > MAX_FETCH_SECONDS:
                raise ValueError("Site request timeout")
            with session.request(method, current, timeout=TIMEOUT,
                                 allow_redirects=False, stream=True, verify=True,
                                 headers={"Accept-Encoding": "gzip, identity"}) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    if hop >= MAX_REDIRECTS or not response.headers.get("Location"):
                        raise ValueError("Invalid or excessive site redirect")
                    if first_redirect is None:
                        first_redirect = response.status_code
                    current = _trusted_url(response.headers["Location"], current)
                    continue
                if method == "GET":
                    response.raise_for_status()
                    return _bounded_xml_body(response, started + MAX_FETCH_SECONDS)
                return {"status": response.status_code,
                        "ok": response.status_code < 400,
                        "redirect": first_redirect}
    raise ValueError("Excessive site redirect")


def _parse_sitemap(body: bytes):
    try:
        root = ElementTree.fromstring(body, forbid_dtd=True,
                                      forbid_entities=True, forbid_external=True)
    except (DefusedXmlException, XMLParseError):
        raise ValueError("Invalid or unsafe sitemap XML") from None
    nodes = 0
    pending = [(root, 1)]
    while pending:
        element, depth = pending.pop()
        nodes += 1
        if nodes > MAX_XML_NODES or depth > MAX_XML_DEPTH:
            raise ValueError("Sitemap XML structure limit exceeded")
        pending.extend((child, depth + 1) for child in element)
    return root


def fetch_sitemap(sitemap_url: str = SITEMAP_URL, _state=None, _depth: int = 0) -> list[str]:
    """自サイトのsitemapを上限内で解析し、重複しないページURLを返す。"""
    url = _trusted_url(sitemap_url)
    state = _state if _state is not None else {"sitemaps": set(), "pages": set()}
    if url in state["sitemaps"]:
        return []
    if _depth > MAX_SITEMAP_DEPTH or len(state["sitemaps"]) >= MAX_SITEMAPS:
        raise ValueError("Sitemap recursion limit exceeded")
    state["sitemaps"].add(url)
    root = _parse_sitemap(_site_request("GET", url))
    namespace = ""
    if root.tag.startswith("{"):
        namespace, _, name = root.tag[1:].partition("}")
        if namespace != "http://www.sitemaps.org/schemas/sitemap/0.9":
            raise ValueError("Unsupported sitemap namespace")
    else:
        name = root.tag
    if name not in {"sitemapindex", "urlset"}:
        raise ValueError("Unsupported sitemap root")
    prefix = "{" + namespace + "}" if namespace else ""
    result = []
    child_tag = "sitemap" if name == "sitemapindex" else "url"
    for entry in root.findall(prefix + child_tag):
        loc = entry.find(prefix + "loc")
        if loc is None or not loc.text:
            continue
        child_url = _trusted_url(loc.text.strip(), url)
        if name == "sitemapindex":
            result.extend(fetch_sitemap(child_url, state, _depth + 1))
        elif child_url not in state["pages"]:
            if len(state["pages"]) >= MAX_URLS:
                raise ValueError("Sitemap URL limit exceeded")
            state["pages"].add(child_url)
            result.append(child_url)
    return result


# ---------------------------------------------------------------------------
# HTTP ステータスチェック (並列)
# ---------------------------------------------------------------------------
def _check_single_url(url: str) -> dict:
    """検査先を毎回検証し、例外・不正URLの本文をレポートへ残さない。"""
    try:
        current = _trusted_url(url)
    except ValueError:
        return {"url": "[invalid URL]", "status": None, "ok": False, "error": "invalid_url"}
    try:
        return {"url": current, **_site_request("HEAD", current)}
    except (requests.RequestException, ValueError):
        return {"url": current, "status": None, "ok": False, "error": "request_failed"}


def check_urls(urls: list[str], max_workers: int = MAX_WORKERS) -> list[dict]:
    """URL リストを上限内で並列検査する。"""
    if len(urls) > MAX_URLS or not isinstance(max_workers, int) or not 1 <= max_workers <= MAX_WORKERS:
        raise ValueError("Invalid site check limits")
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
    sitemap_url = _trusted_url(sitemap_url)
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
    except Exception:
        print("  ERROR: Sitemap 取得失敗")
        report["sitemap"] = {"status": "error", "message": "sitemap_failed", "total_urls": 0}
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
