"""수집 섹션 정책. 새 매체도 이 모듈을 통하지 않으면 전체 피드/홈을 넣지 못한다."""
import re

ALLOWED_SECTIONS = frozenset({
    "politics",
    "economy",
    "society",
    "nations",
    "international",
    "opinion",
    "column",
    "defense",
    "northkorea",
    "usa",
    "china",
    "middle-east",
    "interview",
})

# 피드·목록 URL에 있으면 수집 대상이 아님
BLOCKED_SOURCE_RE = re.compile(
    r"allArticle|clickTop|"
    r"entertain|sports?|lifestyle|/life[/?]|"
    r"culture-history|culture-brief|/culture|"
    r"/photo|/video|/vod|gallery|"
    r"shenyun|falungong|bright|permium|"
    r"연예|스포츠|라이프",
    re.I,
)

# 기사 URL 경로에 있으면 스킵 (혼합 피드 잔여분)
BLOCKED_ARTICLE_PATH_RE = re.compile(
    r"/(?:entertain(?:ment)?|sports?|lifestyle|life|culture(?:-history|-brief)?|"
    r"photo|photos|video|vod|gallery|shenyun|falungong|bright)/",
    re.I,
)

SKIP_TITLE_RE = re.compile(r"^\[(?:포토|영상|사진|오늘날씨)\]|뉴데툰|윤서인")


def is_skipped_title(title: str) -> bool:
    return bool(SKIP_TITLE_RE.search(title or ""))


def is_blocked_source_url(url: str) -> bool:
    return bool(url and BLOCKED_SOURCE_RE.search(url))


def is_blocked_article_url(url: str) -> bool:
    return bool(url and BLOCKED_ARTICLE_PATH_RE.search(url))


def is_collectible_article(title: str, url: str) -> bool:
    if is_skipped_title(title):
        return False
    if is_blocked_article_url(url):
        return False
    return True


def section_rss(name: str, feeds: list, **extra) -> list[dict]:
    """허용 섹션 RSS만 등록. (섹션키, URL) 목록."""
    entries = []
    for section, rss_url in feeds:
        if section not in ALLOWED_SECTIONS:
            raise ValueError(f"[{name}] 허용되지 않은 섹션 '{section}'")
        if is_blocked_source_url(rss_url):
            raise ValueError(f"[{name}] 차단된 피드 URL: {rss_url}")
        item = {
            "name": name,
            "rss_url": rss_url,
            "site_url": None,
            "type": "RSS",
            "section": section,
        }
        item.update(extra)
        entries.append(item)
    if not entries:
        raise ValueError(f"[{name}] 섹션 피드가 비어 있음")
    return entries


def mixed_rss(name: str, rss_url: str, **extra) -> dict:
    """섹션 RSS가 없을 때만. 제목·URL 필터가 유일한 게이트."""
    item = {
        "name": name,
        "rss_url": rss_url,
        "site_url": None,
        "type": "RSS",
        "allow_mixed_feed": True,
    }
    item.update(extra)
    return item


def html_media(
    name: str,
    site_url: str,
    section_urls: list[str] | None = None,
    custom_scraper: bool = False,
    allow_homepage: bool = False,
    **extra,
) -> dict:
    if not custom_scraper and not allow_homepage and not section_urls:
        raise ValueError(f"[{name}] HTML은 section_urls / custom_scraper / allow_homepage 중 하나 필요")
    for url in section_urls or []:
        if is_blocked_source_url(url):
            raise ValueError(f"[{name}] 차단된 섹션 URL: {url}")
    item = {
        "name": name,
        "rss_url": None,
        "site_url": site_url,
        "type": "HTML",
        "section_urls": list(section_urls or []),
        "custom_scraper": custom_scraper,
        "allow_homepage": allow_homepage,
    }
    item.update(extra)
    return item


def validate_media_config(media_config: dict) -> None:
    for bucket, media_list in media_config.items():
        for media in media_list:
            name = media.get("name") or "?"
            rss_url = media.get("rss_url")
            if rss_url and is_blocked_source_url(rss_url) and not media.get("allow_mixed_feed"):
                raise ValueError(f"[{name}] 전체/차단 피드는 allow_mixed_feed 없이 등록할 수 없음: {rss_url}")
            if media.get("type") == "HTML" and not rss_url:
                if not (
                    media.get("custom_scraper")
                    or media.get("allow_homepage")
                    or media.get("section_urls")
                ):
                    raise ValueError(f"[{name}] HTML 홈만 넣지 말 것. 섹션 URL을 지정하라")
            section = media.get("section")
            if section and section not in ALLOWED_SECTIONS:
                raise ValueError(f"[{name}/{bucket}] 허용되지 않은 섹션 '{section}'")
