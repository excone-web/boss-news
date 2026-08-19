import os
from media_policy import html_media, mixed_rss, section_rss, validate_media_config

# 프로젝트 루트 디렉터리
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SQLite 데이터베이스 경로
DB_PATH = os.path.join(BASE_DIR, "news.db")

# 크롤링 설정
CRAWL_DELAY_SECONDS = 0.2  # 미디어 간 수집 요청 간격 (서버 부하 방지)

# HTTP 요청 헤더 (User-Agent)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 새 매체는 media_policy.section_rss / html_media / mixed_rss 만 사용.
# 해외 매체는 일시 중지. 복구 시 아래 해외IT 주석 블록을 MEDIA_CONFIG에 되돌린다.
MEDIA_CONFIG = {
    "주요뉴스": [
        *section_rss("매일신문", [
            ("politics", "https://www.imaeil.com/rss?cate=politics"),
            ("economy", "https://www.imaeil.com/rss?cate=economy"),
            ("society", "https://www.imaeil.com/rss?cate=society"),
            ("nations", "https://www.imaeil.com/rss?cate=nations"),
            ("opinion", "https://www.imaeil.com/rss?cate=opinion"),
        ]),
        html_media("한미일보", "https://www.hanmiilbo.kr/", allow_homepage=True),
        mixed_rss("프리진뉴스", "https://www.freezinenews.com/rss/allArticle.xml"),
        mixed_rss("트루스데일리", "https://www.truthdaily.co.kr/rss/allArticle.xml"),
        *section_rss("펜앤드마이크", [
            ("politics", "https://www.pennmike.com/rss/S1N2.xml"),
            ("society", "https://www.pennmike.com/rss/S1N4.xml"),
            ("economy", "https://www.pennmike.com/rss/S1N6.xml"),
            ("column", "https://www.pennmike.com/rss/S1N1.xml"),
        ]),
        mixed_rss("독립신문", "https://www.ainews1.co.kr/rss/allArticle.xml"),
        html_media(
            "뉴스앤포스트",
            "https://www.newsandpost.com/data/article.php?id=news",
            custom_scraper=True,
        ),
        html_media("뉴데일리", "https://www.newdaily.co.kr/", custom_scraper=True),
        # 데일리안은 입력 시각 파싱이 불안정해 수집에서 제외. 복구 시 HTML 항목을 되돌린다.
        *section_rss(
            "에포크타임스",
            [
                ("politics", "https://www.epochtimes.kr/category/politics/feed/"),
                ("economy", "https://www.epochtimes.kr/category/economics/feed/"),
                ("society", "https://www.epochtimes.kr/category/society/feed/"),
                ("international", "https://www.epochtimes.kr/category/international/feed/"),
                ("usa", "https://www.epochtimes.kr/category/usa/feed/"),
                ("china", "https://www.epochtimes.kr/category/china/feed/"),
                ("middle-east", "https://www.epochtimes.kr/category/middle-east/feed/"),
                ("opinion", "https://www.epochtimes.kr/category/opinion/feed/"),
                ("interview", "https://www.epochtimes.kr/category/interview/feed/"),
            ],
            url_contains="epochtimes.kr",
        ),
    ],
    # 해외 수집 일시 중지 (로그인/페이월). 복구 시 이 리스트를 채운다.
    "해외IT": [],
}

validate_media_config(MEDIA_CONFIG)

# 해외 피드 보관 (수집 재개 시 MEDIA_CONFIG["해외IT"]로 복구)
# Reclaim The Net  https://reclaimthenet.org/feed/
# The Federalist   https://thefederalist.com/category/technology/feed/
# National Review  https://www.nationalreview.com/science-tech/feed/

