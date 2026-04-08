"""
DMM/FANZAアフィリエイトAPIから商品データを取得するモジュール
マルチジャンル対応版（実写AV + アニメ・同人 + グッズ + 写真集・小説・物販 57ジャンル統合版）
ジャンルごとにservice/floorを切り替えてAPIを叩く
"""

import time
import random
import requests
from typing import Optional
from config import Config, GENRES


# ジャンルごとの関連キーワード（タイトル・ジャンルフィルタリング用）
GENRE_KEYWORDS = {
    "ntr": ["寝取られ", "NTR", "寝取り", "寝取らせ", "人妻", "不倫", "浮気", "背徳", "間男"],
    "muscle": ["筋肉", "マッスル", "フィットネス", "トレーニング", "腹筋", "肉体", "スパッツ", "レオタード"],
    "vr": ["VR", "バーチャル", "没入", "主観", "ハイクオリティVR", "8KVR", "4KVR"],
    "jukujo": ["熟女", "人妻", "四十路", "五十路", "三十路", "美熟女", "母", "妻", "義母"],
    "shiroto": ["素人", "ハメ撮り", "ナンパ", "個人撮影", "シロウト", "ガチ", "リアル"],
    "oppai": ["巨乳", "美乳", "爆乳", "おっぱい", "パイズリ", "Hカップ", "Gカップ"],
    "cosplay": ["コスプレ", "アニコス", "メイド", "ナース", "制服", "セーラー", "バニー"],
    "fetish": ["乳首", "フェチ", "脚", "尻", "パンスト", "ストッキング", "タイツ", "脇"],
    "chijo": ["痴女", "逆ナン", "M男", "女性主導", "痴女プレイ", "逆レ", "S女", "女王様", "強制", "誘惑"],
    "nakadashi": ["中出し", "孕ませ", "生中", "種付け", "大量中出し", "連続中出し", "膣内射精", "危険日", "受精", "生挿入"],
    "gal": ["ギャル", "黒ギャル", "日焼け", "ビッチ", "パリピ", "褐色", "ギャル系", "派手", "小麦色", "サーフ"],
    "lesbian": ["レズ", "レズビアン", "百合", "女同士", "レズキス", "レズプレイ", "貝合わせ", "ビアン", "ガールズ", "女×女"],
    "kikaku": ["痴漢", "マジックミラー", "ナンパ", "企画物", "モニタリング", "羞恥", "電車", "満員電車", "MM号", "素人ナンパ"],
    "goods": ["オナホ", "アダルトグッズ", "バイブ", "ローター", "TENGA", "ラブグッズ", "大人のおもちゃ", "エログッズ", "オナニー", "ディルド"],
    "doujin": ["同人", "CG集", "同人誌", "エロ漫画", "電子書籍", "アダルトコミック", "ASMR", "ボイス", "VTuber", "二次創作"],
    "sm": ["SM", "縛り", "拘束", "調教", "鞭", "緊縛", "ボンデージ", "奴隷", "首輪", "蝋燭"],
    "ol": ["OL", "女教師", "秘書", "オフィス", "上司", "部下", "スーツ", "タイトスカート", "社内", "受付嬢"],
    "joshi": ["女子校生", "学園", "制服", "ブルマ", "部活", "放課後", "教室", "セーラー服", "スクール", "通学"],
    "milf": ["母乳", "授乳", "ママ", "妊婦", "産後", "ミルク", "母性", "搾乳", "おっぱい", "育児"],
    "massage": ["マッサージ", "エステ", "オイル", "整体", "リフレ", "アロマ", "施術", "回春", "メンズエステ", "密着"],
    "swapping": ["スワッピング", "乱交", "複数プレイ", "3P", "4P", "大乱交", "複数", "グループ", "王様ゲーム", "合コン"],
    "chikan": ["痴漢", "電車", "満員電車", "バス", "通勤", "痴漢行為", "触る", "車内", "ラッシュ", "盗撮"],
    "cuckold": ["寝取らせ", "旦那公認", "夫の前", "妻貸出", "見せつけ", "他人棒", "夫婦", "共有", "差し出す", "目の前"],
    "debut": ["デビュー", "新人", "初撮り", "初脱ぎ", "初体験", "初出演", "新人AV", "ルーキー", "発掘", "フレッシュ"],
    "award": ["大賞", "ベスト", "ランキング", "殿堂", "受賞", "アワード", "年間", "月間", "TOP", "No.1"],
    # === アニメ・同人系（12ジャンル）===
    "anime": ["アニメ", "OVA", "エロアニメ", "アニメーション", "声優", "2Dアニメ", "原作", "コミック原作", "ゲーム原作", "シリーズ"],
    "doujin_cg": ["CG集", "イラスト", "AI", "画像集", "CG", "フルカラー", "高画質", "立ち絵", "差分", "描き下ろし"],
    "doujin_manga": ["同人誌", "漫画", "マンガ", "コミック", "成人向け", "薄い本", "二次創作", "オリジナル", "フルカラー", "描き下ろし"],
    "doujin_voice": ["ASMR", "ボイス", "音声", "バイノーラル", "耳かき", "囁き", "催眠", "シチュエーション", "ドラマCD", "CV"],
    "doujin_game": ["同人ゲーム", "RPG", "アクション", "ノベル", "シミュレーション", "ドット絵", "ゲーム", "プレイ", "エンディング", "攻略"],
    "pcgame": ["美少女ゲーム", "エロゲ", "ノベルゲーム", "ギャルゲ", "アドベンチャー", "シミュレーション", "RPG", "Windows", "DL版", "パッケージ"],
    "comic": ["コミック", "漫画", "エロ漫画", "成人向け", "アダルトコミック", "単行本", "連載", "読み切り", "フルカラー", "オリジナル"],
    "ntr_anime": ["NTR", "寝取られ", "アニメ", "OVA", "人妻", "不倫", "浮気", "堕ち", "催眠", "洗脳"],
    "tentacle": ["触手", "異種姦", "モンスター", "魔物", "クリーチャー", "異種", "怪物", "拘束", "産卵", "侵食"],
    "isekai": ["異世界", "ファンタジー", "転生", "魔法", "冒険", "勇者", "魔王", "エルフ", "ハーレム", "チート"],
    "school_anime": ["学園", "制服", "学校", "教室", "部活", "放課後", "先生", "生徒", "青春", "恋愛"],
    "bl": ["BL", "ボーイズラブ", "男の娘", "ショタ", "男子", "男×男", "腐", "イケメン", "美少年", "やおい"],
    # === アダルトグッズ系（8ジャンル）===
    "onahole": ["オナホ", "オナホール", "名器", "ホール", "挿入", "リアル", "二層構造", "吸引", "振動", "非貫通"],
    "vibrator": ["バイブ", "バイブレーター", "ローター", "電マ", "振動", "リモコン", "防水", "USB充電", "吸引", "クリ"],
    "tenga": ["TENGA", "テンガ", "EGG", "カップ", "フリップ", "エアテック", "スピナー", "ディープスロート", "使い捨て", "繰り返し"],
    "lotion": ["ローション", "潤滑", "オイル", "ジェル", "マッサージ", "温感", "冷感", "ぬるぬる", "水溶性", "シリコン"],
    "cosplay_goods": ["コスプレ", "ランジェリー", "コスチューム", "セクシー", "下着", "ベビードール", "メイド服", "ナース", "制服", "網タイツ"],
    "sm_goods": ["SM", "拘束", "手錠", "目隠し", "首輪", "鞭", "ロープ", "ボンデージ", "ボールギャグ", "調教"],
    "couple": ["カップル", "ペア", "二人用", "リモート", "遠隔", "ワイヤレス", "パートナー", "夫婦", "プレゼント", "初心者"],
    "new_goods": ["新商品", "新作", "話題", "人気", "おすすめ", "ランキング", "売れ筋", "限定", "コラボ", "最新"],
    # === 新規追加ジャンル（12ジャンル）===
    "amateur_video": ["素人投稿", "個人撮影", "スマホ", "自撮り", "投稿動画", "リアル", "ガチ", "流出", "プライベート", "隠し撮り"],
    "nikkatsu": ["日活", "ロマンポルノ", "昭和", "名作", "レトロ", "ピンク映画", "にっかつ", "クラシック", "70年代", "80年代"],
    "subscription": ["見放題", "月額", "チャンネル", "サブスク", "定額", "プレミアム", "デラックス", "unlimited", "配信", "ストリーミング"],
    "vr_channel": ["VRch", "月額VR", "VR見放題", "VRサブスク", "VR定額", "VRチャンネル", "バーチャル", "没入", "360度", "主観"],
    "dvd": ["DVD", "Blu-ray", "ブルーレイ", "限定版", "特典", "BOX", "コレクション", "パッケージ", "ディスク", "初回"],
    "figure": ["フィギュア", "抱き枕", "タペストリー", "ポスター", "キャラグッズ", "アクリル", "等身大", "スケール", "PVC", "造形"],
    "novel": ["官能小説", "エロ小説", "ノベル", "官能", "小説", "読み物", "文庫", "書き下ろし", "連載", "短編"],
    "photobook": ["写真集", "グラビア", "ヌード", "セミヌード", "撮り下ろし", "デジタル写真集", "フォトブック", "水着", "ビキニ", "ポートレート"],
    "tl": ["TL", "ティーンズラブ", "女性向け", "恋愛", "胸キュン", "イケメン", "溺愛", "俺様", "御曹司", "シンデレラ"],
    "tl_doujin": ["TL同人", "女性向け同人", "乙女", "夢小説", "乙女ゲーム", "恋愛", "女性向け", "BLじゃない", "純愛", "ラブ"],
    "bl_book": ["BLコミック", "ボーイズラブ漫画", "BL小説", "BL", "ボーイズラブ", "腐女子", "攻め受け", "BL新刊", "商業BL", "BL文庫"],
    "anime_dvd": ["アニメDVD", "OVA", "エロアニメ", "Blu-ray", "アダルトアニメ", "パッケージ", "限定版", "特装版", "コレクション", "シリーズ"],
}


def fetch_products(
    keyword: str = "",
    hits: int = Config.DEFAULT_HITS,
    service: str = Config.DEFAULT_SERVICE,
    floor: str = "",
    sort: str = Config.DEFAULT_SORT,
    genre: str = "",
) -> list[dict]:
    """
    DMM Affiliate API v3から商品一覧を取得する

    Args:
        keyword: 検索キーワード
        hits: 取得件数（最大100）
        service: サービス種別（digital, mono等）
        floor: フロアID
        sort: ソート順（date, rank, price等）
        genre: ジャンルキー（ntr, muscle, vr等）

    Returns:
        商品情報の辞書リスト
    """
    if not Config.validate():
        return []

    # ジャンルからservice/floorを決定（引数での指定を優先）
    genre_info = GENRES.get(genre, {}) if genre else {}
    if not service or service == Config.DEFAULT_SERVICE:
        service = genre_info.get("service", Config.DEFAULT_SERVICE)
    if not floor:
        floor = genre_info.get("floor", "videoa")

    # キーワード未指定時はジャンルからランダムに選択
    if not keyword:
        if genre and genre in GENRES:
            keyword = random.choice(GENRES[genre]["keywords"])
        else:
            # ランダムなジャンルから選択
            random_genre = random.choice(list(GENRES.values()))
            keyword = random.choice(random_genre["keywords"])

    # APIリクエストパラメータの構築
    params = {
        "api_id": Config.API_ID,
        "affiliate_id": Config.AFFILIATE_ID,
        "site": "FANZA",
        "service": service,
        "hits": min(hits, 100),
        "sort": sort,
        "keyword": keyword,
        "output": "json",
    }

    if floor:
        params["floor"] = floor

    print(f"[取得中] キーワード「{keyword}」(service={service}, floor={floor}) で{hits}件の商品を検索...")

    try:
        response = requests.get(Config.API_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        print("[エラー] APIリクエストがタイムアウトしました")
        return []
    except requests.exceptions.ConnectionError:
        print("[エラー] APIサーバーに接続できません")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"[エラー] APIがHTTPエラーを返しました: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[エラー] リクエスト中に予期せぬエラーが発生: {e}")
        return []

    try:
        data = response.json()
    except ValueError:
        print("[エラー] APIレスポンスのJSONパースに失敗しました")
        return []

    result = data.get("result", {})
    status = result.get("status", 0)
    if status != 200:
        message = result.get("message", "不明なエラー")
        print(f"[エラー] API応答エラー: {message}")
        return []

    items = result.get("items", [])
    if not items:
        print(f"[情報] キーワード「{keyword}」に該当する商品が見つかりませんでした")
        return []

    # フィルタリング用キーワードを決定
    relevant_kws = GENRE_KEYWORDS.get(genre, []) if genre else []

    products = []
    for item in items:
        product = _parse_item(item, service, floor)
        if product:
            if relevant_kws:
                if _is_relevant(product, keyword, relevant_kws):
                    products.append(product)
                else:
                    print(f"[除外] 関連度低: {product['title'][:40]}...")
            else:
                products.append(product)

    print(f"[完了] {len(products)}件の関連商品データを取得しました")
    return products


def _is_relevant(product: dict, keyword: str, relevant_keywords: list[str]) -> bool:
    """
    商品がテーマに関連するかチェックする
    """
    title = product.get("title", "").lower()
    genres = " ".join(product.get("genres", [])).lower()
    check_text = f"{title} {genres}"

    if keyword.lower() in check_text:
        return True

    for kw in relevant_keywords:
        if kw.lower() in check_text:
            return True

    return False


def _patch_af_id(url: str, affiliate_id: str) -> str:
    """URL内の空af_idやaf_id欠落をaffiliate_idで補う（収益保護）"""
    if not url or not affiliate_id:
        return url
    import re
    if re.search(r"af_id=([&#]|$)", url):
        url = re.sub(r"af_id=([&#]|$)", f"af_id={affiliate_id}\\1", url)
    elif "af_id=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}af_id={affiliate_id}"
    return url


def _build_affiliate_url(item: dict, affiliate_id: str, service: str = "", floor: str = "") -> str:
    """商品のアフィリエイトURLを構築する（全ジャンル対応）"""
    if not affiliate_id:
        raise RuntimeError("AFFILIATE_ID が空です。環境変数を設定してください（収益ゼロ防止）")

    # monthly（月額サブスク系）はAPIのaffiliateURLをそのまま使う
    if service == "monthly":
        affiliate_url = item.get("affiliateURL", "")
        if affiliate_url:
            return _patch_af_id(affiliate_url, affiliate_id)
        direct_url = item.get("URL", "")
        if direct_url:
            separator = "&" if "?" in direct_url else "?"
            return f"{direct_url}{separator}af_id={affiliate_id}"
        return ""

    # FANZAのアフィリエイトURLをそのまま使う（アニメ・同人含む全ジャンル対応）
    affiliate_url = item.get("affiliateURL", "")
    if affiliate_url:
        return _patch_af_id(affiliate_url, affiliate_id)

    content_id = item.get("content_id", "")
    direct_url = item.get("URL", "")

    if direct_url:
        separator = "&" if "?" in direct_url else "?"
        return f"{direct_url}{separator}af_id={affiliate_id}"

    if content_id:
        # mono系（DVD, フィギュア, アニメDVD, グッズ）
        if service == "mono":
            base_url = f"https://www.dmm.co.jp/mono/{floor}/-/detail/=/cid={content_id}/"
            return f"{base_url}?af_id={affiliate_id}"
        # ebook系（官能小説, 写真集, TL, BL書籍, コミック）
        if service == "ebook":
            return f"https://book.dmm.co.jp/detail/{content_id}/?af_id={affiliate_id}"
        # digital/videoc（素人動画）
        if service == "digital" and floor == "videoc":
            base_url = f"https://www.dmm.co.jp/digital/videoc/-/detail/=/cid={content_id}/"
            return f"{base_url}?af_id={affiliate_id}"
        # デフォルト（実写AV等）
        base_url = f"https://www.dmm.co.jp/digital/videoa/-/detail/=/cid={content_id}/"
        return f"{base_url}?af_id={affiliate_id}"

    return ""


def _parse_item(item: dict, service: str = "", floor: str = "") -> Optional[dict]:
    """APIレスポンスの1商品をパースして整形する"""
    try:
        image_url = ""
        image_data = item.get("imageURL", {})
        if image_data:
            image_url = image_data.get("large", image_data.get("small", ""))

        # NOW PRINTING画像（仮画像）の商品は除外
        if not image_url or "nowprinting" in image_url.lower() or "now_printing" in image_url.lower():
            return None

        prices = item.get("prices", {})
        price = ""
        if prices:
            price_info = prices.get("price", prices.get("deliveries", {}).get("delivery", [{}]))
            if isinstance(price_info, str):
                price = price_info
            elif isinstance(price_info, list) and price_info:
                price = price_info[0].get("price", "")

        genres = []
        item_info = item.get("iteminfo", {})
        if item_info:
            genre_list = item_info.get("genre", [])
            genres = [g.get("name", "") for g in genre_list if g.get("name")]

        actresses = []
        if item_info:
            actress_list = item_info.get("actress", [])
            actresses = [a.get("name", "") for a in actress_list if a.get("name")]

        sample_images = []
        sample_image_data = item.get("sampleImageURL", {})
        if sample_image_data:
            sample_l = sample_image_data.get("sample_l", {})
            if sample_l:
                sample_images = sample_l.get("image", [])
            else:
                sample_s = sample_image_data.get("sample_s", {})
                if sample_s:
                    small_images = sample_s.get("image", [])
                    import re as _re
                    for img in small_images:
                        large_img = _re.sub(r'(\w+)-(\d+\.jpg)$', r'\1jp-\2', img)
                        sample_images.append(large_img)

        sample_movie_url = ""
        sample_movie_data = item.get("sampleMovieURL", {})
        if sample_movie_data:
            size_560 = sample_movie_data.get("size_560_360", "")
            if size_560:
                sample_movie_url = size_560

        # レビュー情報の取得
        review = item.get("review", {})
        review_average = review.get("average", 0) if review else 0
        review_count = review.get("count", 0) if review else 0

        # セール判定
        list_price = ""
        sale_price = ""
        is_on_sale = False
        if prices:
            lp = prices.get("list_price", "")
            sp = prices.get("price", "")
            if lp and sp and lp != sp:
                list_price = lp
                sale_price = sp
                is_on_sale = True

        return {
            "title": item.get("title", "タイトル不明"),
            "description": item.get("title", ""),
            "image_url": image_url,
            "affiliate_url": _build_affiliate_url(item, Config.AFFILIATE_ID, service, floor),
            "price": price,
            "date": item.get("date", ""),
            "content_id": item.get("content_id", ""),
            "product_id": item.get("product_id", ""),
            "genres": genres,
            "actresses": actresses,
            "maker": item_info.get("maker", [{}])[0].get("name", "") if item_info.get("maker") else "",
            "series": item_info.get("series", [{}])[0].get("name", "") if item_info.get("series") else "",
            "sample_images": sample_images,
            "sample_movie_url": sample_movie_url,
            "review_average": float(review_average) if review_average else 0,
            "review_count": int(review_count) if review_count else 0,
            "is_on_sale": is_on_sale,
            "list_price": list_price,
            "sale_price": sale_price,
        }
    except (KeyError, IndexError, TypeError) as e:
        print(f"[警告] 商品データのパースに失敗しました: {e}")
        return None


def fetch_multiple_keywords(
    keywords: Optional[list[str]] = None,
    hits_per_keyword: int = 3,
    genre: str = "",
) -> list[dict]:
    """複数キーワードで商品を一括取得する"""
    if keywords is None:
        if genre and genre in GENRES:
            keywords = GENRES[genre]["keywords"]
        else:
            keywords = []
            for g in GENRES.values():
                keywords.extend(g["keywords"])

    all_products = []
    seen_ids = set()

    for kw in keywords:
        products = fetch_products(keyword=kw, hits=hits_per_keyword, genre=genre)
        for p in products:
            pid = p.get("content_id", "")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_products.append(p)
        time.sleep(1)

    print(f"[合計] {len(all_products)}件のユニークな商品を取得しました")
    return all_products


if __name__ == "__main__":
    products = fetch_products(keyword="寝取られ", hits=3, genre="ntr")
    for p in products:
        print(f"  - {p['title']} ({p['price']})")
