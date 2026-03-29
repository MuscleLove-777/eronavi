"""
設定管理モジュール
環境変数または.envファイルから設定を読み込む
マルチジャンル対応のポータルサイト「エロナビ」用
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートの.envファイルを読み込む
_project_root = Path(__file__).resolve().parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)


# ジャンル定義（検索キーワード・カテゴリ名）
GENRES = {
    "ntr": {"keywords": ["寝取られ", "NTR", "人妻NTR"], "category": "ntr", "label": "NTR"},
    "muscle": {"keywords": ["筋肉", "マッスル", "フィットネス"], "category": "muscle", "label": "筋肉"},
    "vr": {"keywords": ["VR", "アダルトVR", "8KVR"], "category": "vr", "label": "VR"},
    "jukujo": {"keywords": ["熟女", "人妻", "四十路"], "category": "jukujo", "label": "熟女"},
    "shiroto": {"keywords": ["素人", "ハメ撮り", "ナンパ"], "category": "shiroto", "label": "素人"},
    "oppai": {"keywords": ["巨乳", "美乳", "爆乳"], "category": "oppai", "label": "巨乳"},
    "cosplay": {"keywords": ["コスプレ", "アニコス", "メイド"], "category": "cosplay", "label": "コスプレ"},
    "fetish": {"keywords": ["乳首", "フェチ", "パンスト"], "category": "fetish", "label": "フェチ"},
    "chijo": {"keywords": ["痴女", "逆ナン", "M男", "女性主導", "痴女プレイ"], "category": "chijo", "label": "痴女"},
    "nakadashi": {"keywords": ["中出し", "孕ませ", "大量中出し", "生中出し", "種付け"], "category": "nakadashi", "label": "中出し"},
    "gal": {"keywords": ["ギャル", "黒ギャル", "日焼け ギャル", "パリピ", "ビッチ"], "category": "gal", "label": "ギャル"},
    "lesbian": {"keywords": ["レズ", "レズビアン", "百合", "女同士", "レズキス"], "category": "lesbian", "label": "レズ"},
    "kikaku": {"keywords": ["痴漢", "マジックミラー号", "ナンパ", "企画", "モニタリング"], "category": "kikaku", "label": "企画"},
    "goods": {"keywords": ["オナホ", "アダルトグッズ", "バイブ", "ローター", "TENGA"], "category": "goods", "label": "グッズ"},
    "doujin": {"keywords": ["同人", "CG集", "同人誌", "エロ漫画", "ASMR"], "category": "doujin", "label": "同人"},
    "sm": {"keywords": ["SM", "縛り", "拘束", "調教", "鞭"], "category": "sm", "label": "SM"},
    "ol": {"keywords": ["OL", "女教師", "秘書", "上司", "オフィス"], "category": "ol", "label": "OL"},
    "joshi": {"keywords": ["女子校生", "JK", "学園", "制服", "ロリ"], "category": "joshi", "label": "女子校生"},
    "milf": {"keywords": ["母乳", "授乳", "ママ", "妊婦", "産後"], "category": "milf", "label": "母乳"},
    "massage": {"keywords": ["マッサージ", "エステ", "オイル", "整体", "リフレ"], "category": "massage", "label": "マッサージ"},
    "swapping": {"keywords": ["スワッピング", "乱交", "複数プレイ", "3P", "4P"], "category": "swapping", "label": "乱交"},
    "chikan": {"keywords": ["痴漢", "電車", "満員電車", "バス", "通勤"], "category": "chikan", "label": "痴漢"},
    "cuckold": {"keywords": ["寝取らせ", "夫婦", "旦那公認", "夫の前", "妻貸出"], "category": "cuckold", "label": "寝取らせ"},
    "debut": {"keywords": ["デビュー", "新人", "初撮り", "AV女優デビュー", "初脱ぎ"], "category": "debut", "label": "新人"},
    "award": {"keywords": ["大賞", "ベスト", "ランキング1位", "殿堂入り", "受賞"], "category": "award", "label": "受賞作"},
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
