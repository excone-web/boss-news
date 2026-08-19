import unittest

from media_policy import (
    html_media,
    is_blocked_article_url,
    is_blocked_source_url,
    is_collectible_article,
    is_skipped_title,
    mixed_rss,
    section_rss,
    validate_media_config,
)
from config import MEDIA_CONFIG


class MediaPolicyTest(unittest.TestCase):
    def test_current_config_validates(self):
        validate_media_config(MEDIA_CONFIG)

    def test_section_rss_rejects_sports(self):
        with self.assertRaises(ValueError):
            section_rss("X", [("sports", "https://example.com/rss/politics.xml")])

    def test_section_rss_rejects_all_article_url(self):
        with self.assertRaises(ValueError):
            section_rss("X", [("politics", "https://example.com/rss/allArticle.xml")])

    def test_html_home_only_rejected(self):
        with self.assertRaises(ValueError):
            html_media("X", "https://example.com/")

    def test_mixed_rss_allowed_for_no_section_feed(self):
        item = mixed_rss("프리진뉴스", "https://www.freezinenews.com/rss/allArticle.xml")
        self.assertTrue(item["allow_mixed_feed"])
        validate_media_config({"주요뉴스": [item]})

    def test_skip_titles(self):
        self.assertTrue(is_skipped_title("[포토] 왕이"))
        self.assertTrue(is_skipped_title("[오늘날씨] 전국 비"))
        self.assertTrue(is_skipped_title("'보스 역투에다 타선 폭발' 삼성 라이온즈, SSG 랜더스 대파"))
        self.assertTrue(is_skipped_title("평균연령 73세 백세합창단 제4회 정기연주회 개최"))
        self.assertTrue(is_skipped_title("경계 허무는 ‘2026 하슬라국제예술제’"))
        self.assertFalse(is_skipped_title("李 대통령 만날 기회 안 줘"))

    def test_skip_culture_category(self):
        self.assertFalse(is_collectible_article("아무 제목입니다", "https://ex.com/n/1", "문화/연예/스포츠"))

    def test_blocked_article_path(self):
        self.assertTrue(is_blocked_article_url("https://www.imaeil.com/sport/view/1"))
        self.assertTrue(is_blocked_article_url("https://ex.com/entertainment/a.html"))
        self.assertFalse(is_blocked_article_url("https://www.imaeil.com/page/view/2026081918140282605"))

    def test_collectible(self):
        self.assertFalse(is_collectible_article("[영상] 걸그룹", "https://ex.com/news/1"))
        self.assertTrue(is_collectible_article("한미훈련 축소", "https://ex.com/news/1"))

    def test_blocked_source_detects_culture_feed(self):
        self.assertTrue(is_blocked_source_url("https://www.epochtimes.kr/category/shenyun/feed/"))
        self.assertFalse(is_blocked_source_url("https://www.epochtimes.kr/category/politics/feed/"))


if __name__ == "__main__":
    unittest.main()
