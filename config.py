import os

# 프로젝트 루트 디렉터리
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SQLite 데이터베이스 경로
DB_PATH = os.path.join(BASE_DIR, "news.db")

# 크롤링 설정
CRAWL_DELAY_SECONDS = 0.2  # 미디어 간 수집 요청 간격 (서버 부하 방지)

# HTTP 요청 헤더 (User-Agent)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 보수 언론사 수집 대상 (국내 Dual RSS/HTML + 해외 IT RSS)
# 해외 매체: lang="en" → 제목 한글 번역. Breitbart Tech는 tech 피드 오염으로 제외.
MEDIA_CONFIG = {
    "주요뉴스": [
        {
            "name": "매일신문",
            "rss_url": "https://www.imaeil.com/rss/",
            "site_url": "https://www.imaeil.com/",
            "type": "DUAL"
        },
        {
            "name": "한미일보",
            "rss_url": None,
            "site_url": "https://www.hanmiilbo.kr/",
            "type": "HTML"
        },
        {
            "name": "프리진뉴스",
            "rss_url": "https://www.freezinenews.com/rss/allArticle.xml",
            "site_url": "https://www.freezinenews.com/",
            "type": "DUAL"
        },
        {
            "name": "트루스데일리",
            "rss_url": "https://www.truthdaily.co.kr/rss/allArticle.xml",
            "site_url": "https://www.truthdaily.co.kr/",
            "type": "DUAL"
        },
        {
            "name": "펜앤드마이크",
            "rss_url": "https://www.pennmike.com/rss/allArticle.xml",
            "site_url": "https://www.pennmike.com/",
            "type": "DUAL"
        },
        {
            "name": "독립신문",
            "rss_url": "https://www.ainews1.co.kr/rss/allArticle.xml",
            "site_url": "https://www.ainews1.co.kr/",
            "type": "DUAL"
        }
    ],
    # 해외 보수·우익 성향 IT/테크 (RSS 전용, 제목 한글 번역)
    # 성향 참고: MBFC/AllSides 기준 Right ~ Right-Center (2026)
    "해외IT": [
        {
            "name": "Reclaim The Net",
            "rss_url": "https://reclaimthenet.org/feed/",
            "site_url": None,
            "type": "RSS",
            "lang": "en",
        },
        {
            "name": "The Federalist",
            "rss_url": "https://thefederalist.com/category/technology/feed/",
            "site_url": None,
            "type": "RSS",
            "lang": "en",
        },
        {
            "name": "National Review",
            "rss_url": "https://www.nationalreview.com/science-tech/feed/",
            "site_url": None,
            "type": "RSS",
            "lang": "en",
        },
        {
            "name": "Epoch Times",
            "rss_url": "https://feed.theepochtimes.com/tech/feed",
            "site_url": None,
            "type": "RSS",
            "lang": "en",
        },
        {
            "name": "Epoch Times",
            "rss_url": "https://feed.theepochtimes.com/science/feed",
            "site_url": None,
            "type": "RSS",
            "lang": "en",
        },
    ],
}
