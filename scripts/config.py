"""
設定管理モジュール
環境変数または.envファイルから設定を読み込む
マルチジャンル対応のポータルサイト「エロナビ」用（実写AV + アニメ・同人 37ジャンル統合版）
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートの.envファイルを読み込む
_project_root = Path(__file__).resolve().parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)


# ジャンル定義（検索キーワード・カテゴリ名・service/floor）
# 既存25ジャンル（実写AV系）: service="digital", floor="videoa"
# アニメ系12ジャンル: service/floorはジャンルごとに異なる
GENRES = {
    # === 実写AV系（25ジャンル）===
    "ntr": {"keywords": ["寝取られ", "NTR", "人妻NTR"], "category": "ntr", "label": "NTR", "service": "digital", "floor": "videoa"},
    "muscle": {"keywords": ["筋肉", "マッスル", "フィットネス"], "category": "muscle", "label": "筋肉", "service": "digital", "floor": "videoa"},
    "vr": {"keywords": ["VR", "アダルトVR", "8KVR"], "category": "vr", "label": "VR", "service": "digital", "floor": "videoa"},
    "jukujo": {"keywords": ["熟女", "人妻", "四十路"], "category": "jukujo", "label": "熟女", "service": "digital", "floor": "videoa"},
    "shiroto": {"keywords": ["素人", "ハメ撮り", "ナンパ"], "category": "shiroto", "label": "素人", "service": "digital", "floor": "videoa"},
    "oppai": {"keywords": ["巨乳", "美乳", "爆乳"], "category": "oppai", "label": "巨乳", "service": "digital", "floor": "videoa"},
    "cosplay": {"keywords": ["コスプレ", "アニコス", "メイド"], "category": "cosplay", "label": "コスプレ", "service": "digital", "floor": "videoa"},
    "fetish": {"keywords": ["乳首", "フェチ", "パンスト"], "category": "fetish", "label": "フェチ", "service": "digital", "floor": "videoa"},
    "chijo": {"keywords": ["痴女", "逆ナン", "M男", "女性主導", "痴女プレイ"], "category": "chijo", "label": "痴女", "service": "digital", "floor": "videoa"},
    "nakadashi": {"keywords": ["中出し", "孕ませ", "大量中出し", "生中出し", "種付け"], "category": "nakadashi", "label": "中出し", "service": "digital", "floor": "videoa"},
    "gal": {"keywords": ["ギャル", "黒ギャル", "日焼け ギャル", "パリピ", "ビッチ"], "category": "gal", "label": "ギャル", "service": "digital", "floor": "videoa"},
    "lesbian": {"keywords": ["レズ", "レズビアン", "百合", "女同士", "レズキス"], "category": "lesbian", "label": "レズ", "service": "digital", "floor": "videoa"},
    "kikaku": {"keywords": ["痴漢", "マジックミラー号", "ナンパ", "企画", "モニタリング"], "category": "kikaku", "label": "企画", "service": "digital", "floor": "videoa"},
    "goods": {"keywords": ["オナホ", "アダルトグッズ", "バイブ", "ローター", "TENGA"], "category": "goods", "label": "グッズ", "service": "digital", "floor": "videoa"},
    "doujin": {"keywords": ["同人", "CG集", "同人誌", "エロ漫画", "ASMR"], "category": "doujin", "label": "同人", "service": "digital", "floor": "videoa"},
    "sm": {"keywords": ["SM", "縛り", "拘束", "調教", "鞭"], "category": "sm", "label": "SM", "service": "digital", "floor": "videoa"},
    "ol": {"keywords": ["OL", "女教師", "秘書", "上司", "オフィス"], "category": "ol", "label": "OL", "service": "digital", "floor": "videoa"},
    "joshi": {"keywords": ["女子校生", "JK", "学園", "制服", "ロリ"], "category": "joshi", "label": "女子校生", "service": "digital", "floor": "videoa"},
    "milf": {"keywords": ["母乳", "授乳", "ママ", "妊婦", "産後"], "category": "milf", "label": "母乳", "service": "digital", "floor": "videoa"},
    "massage": {"keywords": ["マッサージ", "エステ", "オイル", "整体", "リフレ"], "category": "massage", "label": "マッサージ", "service": "digital", "floor": "videoa"},
    "swapping": {"keywords": ["スワッピング", "乱交", "複数プレイ", "3P", "4P"], "category": "swapping", "label": "乱交", "service": "digital", "floor": "videoa"},
    "chikan": {"keywords": ["痴漢", "電車", "満員電車", "バス", "通勤"], "category": "chikan", "label": "痴漢", "service": "digital", "floor": "videoa"},
    "cuckold": {"keywords": ["寝取らせ", "夫婦", "旦那公認", "夫の前", "妻貸出"], "category": "cuckold", "label": "寝取らせ", "service": "digital", "floor": "videoa"},
    "debut": {"keywords": ["デビュー", "新人", "初撮り", "AV女優デビュー", "初脱ぎ"], "category": "debut", "label": "新人", "service": "digital", "floor": "videoa"},
    "award": {"keywords": ["大賞", "ベスト", "ランキング1位", "殿堂入り", "受賞"], "category": "award", "label": "受賞作", "service": "digital", "floor": "videoa"},
    # === アニメ・同人系（12ジャンル）===
    "anime": {"keywords": ["アニメ", "OVA", "エロアニメ"], "category": "Anime", "label": "エロアニメ", "service": "digital", "floor": "anime"},
    "doujin_cg": {"keywords": ["CG集", "イラスト集", "AI CG"], "category": "DoujinCG", "label": "同人CG", "service": "doujin", "floor": "digital_doujin"},
    "doujin_manga": {"keywords": ["同人誌", "エロ漫画", "成人向け漫画"], "category": "DoujinManga", "label": "同人漫画", "service": "doujin", "floor": "digital_doujin"},
    "doujin_voice": {"keywords": ["ASMR", "ボイス", "音声作品"], "category": "Voice", "label": "ASMR", "service": "doujin", "floor": "digital_doujin"},
    "doujin_game": {"keywords": ["同人ゲーム", "RPG", "アクション"], "category": "DoujinGame", "label": "同人ゲーム", "service": "doujin", "floor": "digital_doujin"},
    "pcgame": {"keywords": ["美少女ゲーム", "エロゲ", "ノベルゲーム"], "category": "PCGame", "label": "エロゲ", "service": "pcgame", "floor": "digital_pcgame"},
    "comic": {"keywords": ["アダルトコミック", "エロ漫画", "成人向け"], "category": "Comic", "label": "コミック", "service": "ebook", "floor": "comic"},
    "ntr_anime": {"keywords": ["NTR アニメ", "寝取られ アニメ"], "category": "NTRAnime", "label": "NTRアニメ", "service": "digital", "floor": "anime"},
    "tentacle": {"keywords": ["触手", "異種姦", "モンスター"], "category": "Tentacle", "label": "触手", "service": "doujin", "floor": "digital_doujin"},
    "isekai": {"keywords": ["異世界", "ファンタジー", "転生"], "category": "Isekai", "label": "異世界", "service": "doujin", "floor": "digital_doujin"},
    "school_anime": {"keywords": ["学園", "制服", "学園モノ"], "category": "SchoolAnime", "label": "学園アニメ", "service": "digital", "floor": "anime"},
    "bl": {"keywords": ["BL", "ボーイズラブ", "男の娘"], "category": "BL", "label": "BL", "service": "doujin", "floor": "digital_doujin_bl"},
}


class Config:
    """アプリケーション設定クラス"""

    # DMM API認証情報
    API_ID: str = os.getenv("API_ID", "")
    AFFILIATE_ID: str = os.getenv("AFFILIATE_ID", "")
    SITE_NAME: str = os.getenv("SITE_NAME", "eronavi")

    # APIエンドポイント
    API_BASE_URL: str = "https://api.dmm.com/affiliate/v3/ItemList"

    # Hugo出力設定
    CONTENT_DIR: str = str(_project_root / "content" / "posts")

    # 記事生成のデフォルト設定
    DEFAULT_HITS: int = 5
    DEFAULT_SERVICE: str = "digital"
    DEFAULT_SORT: str = "date"

    @classmethod
    def validate(cls) -> bool:
        """必須設定が存在するか検証する"""
        missing = []
        if not cls.API_ID:
            missing.append("API_ID")
        if not cls.AFFILIATE_ID:
            missing.append("AFFILIATE_ID")
        if missing:
            print(f"[エラー] 以下の環境変数が未設定です: {', '.join(missing)}")
            print("  .envファイルを作成するか、環境変数を設定してください。")
            return False
        return True
