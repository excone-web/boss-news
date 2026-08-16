import os

# 프로젝트 루트 디렉터리
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SQLite 데이터베이스 경로
DB_PATH = os.path.join(BASE_DIR, "news.db")

# 크롤링 설정
CRAWL_DELAY_SECONDS = 0.2  # 미디어 간 수집 요청 간격 (서버 부하 방지)

# HTTP 요청 헤더 (User-Agent)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 보수 언론사 수집 대상 (국내 Dual RSS/HTML)
# 해외 매체는 일시 중지. 복구 시 아래 해외IT 주석 블록을 MEDIA_CONFIG에 되돌린다.
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
        },
        {
            "name": "뉴스앤포스트",
            "rss_url": None,
            "site_url": "https://www.newsandpost.com/data/article.php?id=news",
            "type": "HTML"
        },
        *[
            {
                "name": "에포크타임스",
                "rss_url": rss_url,
                "site_url": ("https://www.epochtimes.kr/" if i == 0 else None),
                "type": "DUAL" if i == 0 else "RSS",
                "url_contains": "epochtimes.kr",
            }
            for i, rss_url in enumerate((
                "https://www.epochtimes.kr/feed/",
                "https://www.epochtimes.kr/category/politics/feed/",
                "https://www.epochtimes.kr/category/economics/feed/",
                "https://www.epochtimes.kr/category/society/feed/",
                "https://www.epochtimes.kr/category/international/feed/",
                "https://www.epochtimes.kr/category/usa/feed/",
                "https://www.epochtimes.kr/category/china/feed/",
                "https://www.epochtimes.kr/category/middle-east/feed/",
                "https://www.epochtimes.kr/category/culture-history/feed/",
                "https://www.epochtimes.kr/category/nature-science/feed/",
                "https://www.epochtimes.kr/category/opinion/feed/",
                "https://www.epochtimes.kr/category/interview/feed/",
                "https://www.epochtimes.kr/category/permium/feed/",
                "https://www.epochtimes.kr/category/culture-brief/feed/",
                "https://www.epochtimes.kr/category/bright/feed/",
                "https://www.epochtimes.kr/category/shenyun/feed/",
                "https://www.epochtimes.kr/category/falungong-founder/feed/",
            ))
        ],
    ],
    # 해외 수집 일시 중지 (로그인/페이월). 복구 시 이 리스트를 채운다.
    "해외IT": [],
}

# 해외 피드 보관 (수집 재개 시 MEDIA_CONFIG["해외IT"]로 복구)
# Reclaim The Net  https://reclaimthenet.org/feed/
# The Federalist   https://thefederalist.com/category/technology/feed/
# National Review  https://www.nationalreview.com/science-tech/feed/

