"""
低品質テンプレ記事に noindex: true を追加するスクリプト

残す基準:
- ranking-daily-* (ランキング記事)
- VR品番の個別記事 (crvr, sivr, kavr, dsvr, vrkm, 3dsvr, wavr, nhvr, mdvr, kiwvr, urvrsp, prvr, juvr, savr, ebvr)
- actress-* (女優ページ) → noindex対象（テンプレ）

noindex対象:
- 上記以外の個別作品記事すべて
"""

import os
import re
import glob

POSTS_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "posts")

# VR品番プレフィックス（ファイル名の日付以降の部分でマッチ）
VR_PREFIXES = [
    "crvr", "sivr", "kavr", "dsvr", "vrkm", "3dsvr", "wavr",
    "nhvr", "mdvr", "kiwvr", "urvrsp", "prvr", "juvr", "savr", "ebvr",
    "ipvr", "bibivr", "dovr", "exvr", "gopj", "maxvr", "mxvr",
    "atvr", "avopvr", "bikmvr", "cbikmvr", "fsvss", "hnvr",
]

def get_slug(filename):
    """ファイル名から日付部分を除去してslugを返す"""
    # 2026-03-29-xxxxx.md -> xxxxx
    m = re.match(r"\d{4}-\d{2}-\d{2}-(.*?)\.md$", filename)
    return m.group(1) if m else filename

def should_keep(filename):
    """残す記事ならTrue"""
    slug = get_slug(filename)

    # ランキング記事は残す
    if slug.startswith("ranking-daily-") or slug.startswith("ranking-"):
        return True

    # VR品番記事は残す
    slug_lower = slug.lower()
    for prefix in VR_PREFIXES:
        if slug_lower.startswith(prefix):
            return True

    return False

def add_noindex(filepath):
    """frontmatterに noindex: true を追加"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 既に noindex がある場合はスキップ
    if "noindex:" in content:
        return False

    # frontmatter の最後の --- の直前に追加
    # YAML frontmatter: ---\n...\n---
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False

    # parts[0] = "" (before first ---)
    # parts[1] = frontmatter content
    # parts[2] = body
    fm = parts[1].rstrip()
    new_content = f"---{fm}\nnoindex: true\n---{parts[2]}"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True

def main():
    files = sorted(glob.glob(os.path.join(POSTS_DIR, "*.md")))
    print(f"Total posts found: {len(files)}")

    keep_ranking = []
    keep_vr = []
    noindex_list = []

    for filepath in files:
        filename = os.path.basename(filepath)
        slug = get_slug(filename)

        if slug.startswith("ranking-daily-") or slug.startswith("ranking-"):
            keep_ranking.append(filename)
        elif should_keep(filename):
            keep_vr.append(filename)
        else:
            noindex_list.append(filepath)

    # noindex追加
    modified = 0
    for filepath in noindex_list:
        if add_noindex(filepath):
            modified += 1

    kept_total = len(keep_ranking) + len(keep_vr)

    print(f"\n=== Results ===")
    print(f"Ranking articles (KEEP): {len(keep_ranking)}")
    print(f"VR articles (KEEP):      {len(keep_vr)}")
    print(f"Total KEEP:              {kept_total}")
    print(f"noindex applied:         {modified}")
    print(f"Already had noindex:     {len(noindex_list) - modified}")
    print(f"Total noindex target:    {len(noindex_list)}")

    # 残す記事リストをファイル出力
    with open(os.path.join(os.path.dirname(__file__), "kept_articles.txt"), "w", encoding="utf-8") as f:
        f.write("=== Ranking Articles ===\n")
        for fn in keep_ranking:
            f.write(f"  {fn}\n")
        f.write(f"\n=== VR Articles ===\n")
        for fn in keep_vr:
            f.write(f"  {fn}\n")

    print(f"\nKept articles list saved to scripts/kept_articles.txt")

if __name__ == "__main__":
    main()
