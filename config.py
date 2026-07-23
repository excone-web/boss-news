import os

# 프로젝트 루트 디렉터리
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SQLite 데이터베이스 경로
DB_PATH = os.path.join(BASE_DIR, "news.db")

# 크롤링 설정
CRAWL_INTERVAL_HOURS = 2  # 2시간 주기로 백그라운드 자동 수집
CRAWL_DELAY_SECONDS = 0.2 # 미디어 간 수집 요청 간격 (서버 부하 방지)

# HTTP 요청 헤더 (User-Agent)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 보수 언론사 6곳 카테고리별 수집 대상 목록 (Dual RSS & HTML 스크래핑 설정)
MEDIA_CONFIG = {
    "주요뉴스": [
        {
            "name": "매일신문",
            "rss_url": "https://www.imaeil.com/rss/imaeil_news.xml",
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
    ]
}
