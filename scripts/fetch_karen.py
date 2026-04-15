"""楓カレンの作品をFANZA APIから取得"""
import os, sys, json, requests
sys.path.insert(0, os.path.dirname(__file__))
from config import Config

def fetch(keyword="楓カレン", hits=100, sort="date", offset=1):
    params = {
        "api_id": Config.API_ID,
        "affiliate_id": Config.AFFILIATE_ID,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "hits": hits,
        "offset": offset,
        "sort": sort,
        "keyword": keyword,
        "output": "json",
    }
    r = requests.get(Config.API_BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("result", {}).get("items", [])

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "date"
    items = []
    seen = set()
    for off in (1, 101, 201):
        batch = fetch(sort=mode, hits=100, offset=off)
        if not batch:
            break
        for it in batch:
            cid = it.get("content_id","")
            if cid and cid not in seen:
                seen.add(cid)
                items.append(it)
    out = []
    for it in items:
        actresses = [a.get("name","") for a in it.get("iteminfo",{}).get("actress",[])]
        if "楓カレン" not in actresses:
            continue
        image = it.get("imageURL",{}).get("large","") or it.get("imageURL",{}).get("small","")
        if "nowprinting" in image.lower() or not image:
            continue
        genres = [g.get("name","") for g in it.get("iteminfo",{}).get("genre",[])]
        maker = (it.get("iteminfo",{}).get("maker") or [{}])[0].get("name","")
        series = (it.get("iteminfo",{}).get("series") or [{}])[0].get("name","")
        prices = it.get("prices",{})
        price = prices.get("price","")
        out.append({
            "cid": it.get("content_id",""),
            "title": it.get("title",""),
            "date": it.get("date",""),
            "image": image,
            "genres": genres[:6],
            "maker": maker,
            "series": series,
            "price": price,
            "url": it.get("affiliateURL",""),
        })
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/karen_out.json"
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(out)} items to {outpath}")
