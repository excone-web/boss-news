import time
import requests
import feedparser
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from config import MEDIA_CONFIG, USER_AGENT, CRAWL_DELAY_SECONDS
from media_policy import is_collectible_article, is_skipped_title
from database import save_articles, purge_old_articles, purge_duplicate_articles, get_existing_urls
from category_agent import classify_article
from translate import translate_title_to_ko, reset_translate_budget

KST = timezone(timedelta(hours=9))

def parse_pub_date(raw_date: str) -> str:
    """RSS pubDate 및 다양한 포맷의 날짜 문자열을 한국 표준시(KST) YYYY-MM-DD HH:MM:SS 형태로 변환"""
    if not raw_date:
        return ""

    try:
        dt = parsedate_to_datetime(raw_date)
        if dt.tzinfo is not None:
            dt = dt.astimezone(KST)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", 
        "%Y%m%dT%H%M%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y/%m/%d %H:%M:%S"
    ):
        try:
            dt = datetime.strptime(raw_date, fmt)
            if dt.tzinfo is not None:
                dt = dt.astimezone(KST)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    for fmt in ("%Y/%m/%d", "%Y.%m.%d", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw_date, fmt)
            return dt.strftime("%Y-%m-%d") + " 12:00:00"
        except ValueError:
            continue

    return ""


def parse_epoch_kr_ko_datetime(html: str) -> str:
    """에포크타임스 본문 '2026년 08월 16일 오전 11:18' 시각."""
    m = re.search(
        r'(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(오전|오후)\s*(\d{1,2}):(\d{2})',
        html or "",
    )
    if not m:
        return ""
    year, month, day, ampm, hour, minute = m.groups()
    hour_i = int(hour)
    if ampm == "오후" and hour_i < 12:
        hour_i += 12
    if ampm == "오전" and hour_i == 12:
        hour_i = 0
    return f"{year}-{int(month):02d}-{int(day):02d} {hour_i:02d}:{minute}:00"


def decode_html_bytes(raw: bytes, content_type: str = "") -> str:
    """헤더 charset이 없어도 UTF-8/EUC-KR 본문을 깨지지 않게 디코드."""
    m = re.search(r"charset=([^\s;]+)", content_type or "", re.I)
    header_enc = (m.group(1).strip("\"'") if m else "").lower()
    for enc in (header_enc, "utf-8", "euc-kr", "cp949"):
        if not enc:
            continue
        try:
            text = raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
        if re.search(r"[가-힣]", text):
            return text
        if enc == header_enc and header_enc not in ("iso-8859-1", "latin-1", "windows-1252"):
            return text
    return raw.decode("utf-8", errors="replace")


def extract_html_title(html: str) -> str:
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        return BeautifulSoup(m.group(1), "html.parser").get_text(strip=True)
    m = re.search(r"<title>([^<]+)</title>", html, re.I)
    if m:
        return BeautifulSoup(m.group(1), "html.parser").get_text(strip=True).split(" | ")[0].split(" - ")[0].strip()
    return ""


def now_kst() -> datetime:
    """GitHub Actions(UTC)에서도 발행시각(KST)과 동일 기준으로 비교하기 위함"""
    return datetime.now(KST).replace(tzinfo=None)


def is_within_hours(published_at_str: str, hours: int = 96) -> bool:
    """기사 발행시간(KST 문자열)이 최근 N시간 이내인지 검증. 미래 시각 과다 배제."""
    if not published_at_str:
        return True
    try:
        # published_at 은 parse_pub_date 기준 KST naive 문자열
        dt = datetime.strptime(published_at_str[:19], "%Y-%m-%d %H:%M:%S")
        now = now_kst()
        cutoff = now - timedelta(hours=hours)
        # CI가 UTC 이면 datetime.now() 사용 시 저녁 KST 기사가 '미래'로 전부 탈락함
        if dt > now + timedelta(minutes=15):
            return False
        return dt >= cutoff
    except Exception:
        return True

INVALID_SECTION_TITLES = {
    "많이 본 뉴스", "방송·미디어", "엔터테인먼트", "오피니언", "카테고리", "메뉴", "전체",
    "정치", "경제", "사회", "IT/과학", "문화", "지역", "사설", "칼럼", "포토", "영상",
    "PDF", "구독", "로그인", "회원가입", "마이페이지", "제보", "회사소개", "주요뉴스",
    "실시간 뉴스", "최신기사", "인기기사", "전체기사", "분야별 뉴스", "공지사항", "이벤트"
}

def is_valid_article_title(title: str) -> bool:
    clean = title.strip()
    if not clean or len(clean) < 8:
        return False
    if clean in INVALID_SECTION_TITLES:
        return False
    if is_skipped_title(clean):
        return False
    # 기사 제목은 2개 이상의 단어로 이루어지므로 띄어쓰기 필수
    if " " not in clean:
        return False
    return True

def normalize_title(title: str) -> str:
    """중복 방지를 위한 제목 공백/특수문자 정규화 키 생성"""
    return re.sub(r'[\s\W]+', '', title).lower()

def fetch_rss_feed(
    rss_url: str,
    media_name: str,
    raw_category: str,
    lang: str = None,
    url_contains: str = None,
    known_urls: set = None,
    default_category: str = None,
) -> list[dict]:
    """RSS 피드 파싱 (중복 방지 및 최근 96시간 기사 필터링)

    lang="en": 제목을 한글로 번역 (국내 매체는 기본값 None → 무번역).
    url_contains: URL에 해당 부분 문자열이 없으면 스킵 (섹션 피드 오염 방어).
    known_urls: 이미 DB에 있는 URL은 번역 스킵.
    default_category: 키워드 미매칭 시 카테고리. 없으면 영문은 IT/과학.
    """
    articles = []
    if not rss_url:
        return articles

    headers = {"User-Agent": USER_AGENT}
    known_urls = known_urls if known_urls is not None else set()
    if not default_category:
        default_category = "IT/과학" if lang == "en" else None

    try:
        response = requests.get(rss_url, headers=headers, timeout=8)
        if response.status_code != 200:
            return articles

        feed = feedparser.parse(response.content)
        seen_keys = set()

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()

            if not title or not url or not is_valid_article_title(title):
                continue
            if not is_collectible_article(title, url):
                continue

            if url_contains and url_contains not in url:
                continue

            # in-feed 중복은 원제 기준 (번역 전)
            norm_key = (media_name, normalize_title(title))
            if norm_key in seen_keys:
                continue
            seen_keys.add(norm_key)

            raw_date = entry.get("published", entry.get("updated", entry.get("pubDate", "")))
            published_at = parse_pub_date(raw_date)
            if not published_at:
                published_at = now_kst().strftime("%Y-%m-%d %H:%M:%S")

            if not is_within_hours(published_at, hours=96):
                continue

            description = entry.get("summary", entry.get("description", ""))
            clean_body = ""
            if description:
                # 긴 content:encoded 대신 summary만 사용 (해외 피드 본문 과다 방지)
                soup = BeautifulSoup(description, "html.parser")
                clean_body = soup.get_text(strip=True)
                if len(clean_body) > 500:
                    clean_body = clean_body[:500]

            # 분류는 원제 기준
            assigned_category = classify_article(
                title=title,
                content=clean_body,
                raw_category=raw_category,
                default_category=default_category,
            )

            display_title = title
            if lang == "en" and url not in known_urls:
                try:
                    display_title = translate_title_to_ko(title)
                except Exception as te:
                    print(f"[{media_name}] 번역 예외(원문 유지): {te}")
                    display_title = title

            articles.append({
                "media_name": media_name,
                "category": assigned_category,
                "title": display_title,
                "url": url,
                "published_at": published_at,
                "summary": None,
                "content_body": clean_body
            })

    except Exception as e:
        print(f"[{media_name}] RSS 파싱 에러 ({rss_url}): {e}")

    return articles

def canonicalize_newsandpost_url(full_url: str) -> str:
    """목록 쿼리스트링을 제거하고 id=news&category=&no= 만 남긴다."""
    no_m = re.search(r'[?&]no=(\d+)', full_url, re.I)
    if not no_m:
        return full_url
    cat_m = re.search(r'[?&]category=(\d+)', full_url, re.I)
    no = no_m.group(1)
    if cat_m:
        return f"https://www.newsandpost.com/data/read.php?id=news&category={cat_m.group(1)}&no={no}"
    return f"https://www.newsandpost.com/data/read.php?id=news&no={no}"


def fetch_newsandpost_detail_date(session: requests.Session, article_url: str) -> str:
    """본문의 '기사입력: YYYY-MM-DD HH:MM:SS' 시각을 추출"""
    try:
        res = session.get(article_url, timeout=3)
        if res.status_code != 200:
            return ""
        m = re.search(r'기사입력:\s*(20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', res.text)
        if m:
            return parse_pub_date(m.group(1))
        m2 = re.search(r'기사입력:\s*(20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2})', res.text)
        if m2:
            return parse_pub_date(m2.group(1))
    except Exception:
        pass
    return ""


def fetch_hanmiilbo_detail_date(session: requests.Session, article_url: str) -> str:
    """한미일보 본문 상세페이지에서 원래 승인/입력된 정확한 시각 추출"""
    try:
        res = session.get(article_url, timeout=3)
        if res.status_code == 200:
            m = re.search(r'(?:승인|입력|등록|작성)?\s*(20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', res.text)
            if m:
                return parse_pub_date(m.group(1))
            m2 = re.search(r'(?:승인|입력|등록|작성)?\s*(20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2})', res.text)
            if m2:
                return parse_pub_date(m2.group(1))
    except Exception:
        pass
    return ""

NEWSANDPOST_NEWS_LIST = "https://www.newsandpost.com/data/article.php?id=news"
NEWSANDPOST_MAX_PAGES = 8
NEWSANDPOST_PAGE_CAP = 100

NEWDAILY_ARTICLE_RE = re.compile(r"/site/data/html/20\d{2}/\d{2}/\d{2}/\d+\.html", re.I)
NEWDAILY_REGIONAL_HOSTS = (
    "tk.newdaily.co.kr",
    "gg.newdaily.co.kr",
    "gj.newdaily.co.kr",
    "cc.newdaily.co.kr",
    "pk.newdaily.co.kr",
    "ic.newdaily.co.kr",
    "gw.newdaily.co.kr",
)
NEWDAILY_SECTIONS = (
    ("정치", "https://www.newdaily.co.kr/news/section_list_all.html?catid=2"),
    ("사회", "https://www.newdaily.co.kr/news/section_list_all.html?catid=3"),
    ("북한", "https://www.newdaily.co.kr/news/section_list_all.html?catid=4"),
    ("외교국방", "https://www.newdaily.co.kr/news/section_list_all.html?catid=X"),
    ("칼럼", "https://www.newdaily.co.kr/news/section_list_all.html?catid=F"),
    ("경제", "https://biz.newdaily.co.kr/news/section_list_all.html?catid=all"),
)
NEWDAILY_MAX_PAGES = 4
NEWDAILY_CAP = 150


def _newsandpost_article_from_link(a_tag, seen_urls: set, seen_titles: set):
    href = a_tag.get("href", "").strip()
    if not href:
        return None
    href_lower = href.lower()
    if not re.search(r'read\.php\?[^#]*\bid=news\b', href_lower):
        return None
    if not re.search(r'(?:[?&])no=\d+', href_lower):
        return None

    full_url = canonicalize_newsandpost_url(urljoin(NEWSANDPOST_NEWS_LIST, href))
    if full_url in seen_urls:
        return None

    title_el = a_tag.find(class_=["title", "subject", "tit", "headline"]) or a_tag.find(["h1", "h2", "h3", "h4", "strong", "b"])
    if title_el:
        clean_title = title_el.get_text(strip=True)
    else:
        lines = [line.strip() for line in a_tag.get_text("\n").split("\n") if line.strip()]
        clean_title = lines[0] if lines else ""

    if not is_valid_article_title(clean_title):
        return None
    if len(clean_title) > 120:
        clean_title = clean_title[:120] + "..."

    norm_key = normalize_title(clean_title)
    if norm_key in seen_titles:
        return None

    pub_date = ""
    date_node = a_tag.find_next(string=re.compile(r'20\d{2}/\d{2}/\d{2}'))
    if date_node:
        m_np = re.search(r'20\d{2}/\d{2}/\d{2}', str(date_node))
        pub_date = parse_pub_date(m_np.group(0)) if m_np else ""
    if not pub_date:
        pub_date = now_kst().strftime("%Y-%m-%d %H:%M:%S")

    seen_urls.add(full_url)
    seen_titles.add(norm_key)
    return {
        "title": clean_title,
        "url": full_url,
        "published_at": pub_date,
    }


def scrape_newsandpost_news(raw_category: str) -> list[dict]:
    """뉴스앤포스트 뉴스 게시판을 96시간이 끊길 때까지 페이지 순회."""
    articles = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    seen_urls = set()
    seen_titles = set()
    media_name = "뉴스앤포스트"

    for page in range(1, NEWSANDPOST_MAX_PAGES + 1):
        list_url = f"{NEWSANDPOST_NEWS_LIST}&page={page}"
        try:
            response = session.get(list_url, timeout=8)
        except Exception as e:
            print(f"[{media_name}] 목록 요청 실패 (page={page}): {e}")
            break
        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.text, "html.parser")
        page_kept = 0
        page_listed = 0

        for a_tag in soup.find_all("a"):
            parsed = _newsandpost_article_from_link(a_tag, seen_urls, seen_titles)
            if not parsed:
                continue
            page_listed += 1
            if not is_within_hours(parsed["published_at"], hours=96):
                continue

            detail_date = fetch_newsandpost_detail_date(session, parsed["url"])
            if detail_date:
                parsed["published_at"] = detail_date
                if not is_within_hours(parsed["published_at"], hours=96):
                    continue

            if not is_collectible_article(parsed["title"], parsed["url"]):
                continue

            assigned_category = classify_article(title=parsed["title"], raw_category=raw_category)
            articles.append({
                "media_name": media_name,
                "category": assigned_category,
                "title": parsed["title"],
                "url": parsed["url"],
                "published_at": parsed["published_at"],
                "summary": None,
                "content_body": ""
            })
            page_kept += 1
            if len(articles) >= NEWSANDPOST_PAGE_CAP:
                print(f"[{media_name}] page={page} 수집 {len(articles)}건 (상한)")
                return articles

        print(f"[{media_name}] page={page} kept={page_kept} listed={page_listed} total={len(articles)}")
        if page_listed == 0 or page_kept == 0:
            break
        time.sleep(CRAWL_DELAY_SECONDS)

    return articles


def newdaily_url_day(url: str) -> str:
    m = re.search(r"/site/data/html/(20\d{2})/(\d{2})/(\d{2})/", url or "")
    if not m:
        return ""
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)} 12:00:00"


def is_newdaily_skip_title(title: str) -> bool:
    return is_skipped_title(title)


def fetch_newdaily_detail(session: requests.Session, url: str, title: str) -> tuple[str, str]:
    """본문 og:title + 입력 시각."""
    clean_title = title
    pub_date = ""
    try:
        detail_res = session.get(url, timeout=3)
        if detail_res.status_code != 200:
            return clean_title, pub_date
        detail_html = decode_html_bytes(detail_res.content, detail_res.headers.get("Content-Type", ""))
        detail_title = extract_html_title(detail_html)
        if is_valid_article_title(detail_title) and not is_newdaily_skip_title(detail_title):
            clean_title = detail_title[:120] + "..." if len(detail_title) > 120 else detail_title
        m_det = re.search(
            r'(?:article:published_time|og:regdate|pubdate)["\']?\s*content=["\']?([^"\'\s>]+)',
            detail_html,
            re.I,
        )
        if m_det:
            pub_date = parse_pub_date(m_det.group(1))
        if not pub_date:
            m_body = re.search(
                r"(?:승인|입력|등록|작성)?\s*(20\d{2}[-./]\d{2}[-./]\d{2}\s+\d{2}:\d{2}(:\d{2})?)",
                detail_html,
            )
            if m_body:
                pub_date = parse_pub_date(m_body.group(1))
    except Exception:
        pass
    return clean_title, pub_date


def scrape_newdaily_sections(raw_category: str) -> list[dict]:
    """뉴데일리 정치·사회·북한·외교국방·칼럼·경제 섹션만 96시간 수집."""
    articles = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    seen_urls = set()
    seen_titles = set()
    media_name = "뉴데일리"

    for section_name, list_url in NEWDAILY_SECTIONS:
        for page in range(1, NEWDAILY_MAX_PAGES + 1):
            page_url = list_url if page == 1 else f"{list_url}&pn={page}"
            try:
                response = session.get(page_url, timeout=8)
            except Exception as e:
                print(f"[{media_name}] {section_name} 목록 실패 (page={page}): {e}")
                break
            if response.status_code != 200:
                break

            soup = BeautifulSoup(
                decode_html_bytes(response.content, response.headers.get("Content-Type", "")),
                "html.parser",
            )
            page_kept = 0
            page_listed = 0

            for a_tag in soup.find_all("a"):
                href = a_tag.get("href", "").strip()
                if not href or not NEWDAILY_ARTICLE_RE.search(href):
                    continue
                full_url = urljoin(list_url, href)
                host = full_url.split("/")[2].lower() if "://" in full_url else ""
                if host in NEWDAILY_REGIONAL_HOSTS:
                    continue
                if full_url in seen_urls:
                    continue

                title_el = a_tag.find(class_=["title", "subject", "tit", "headline"]) or a_tag.find(
                    ["h1", "h2", "h3", "h4", "strong", "b"]
                )
                if title_el:
                    clean_title = title_el.get_text(strip=True)
                else:
                    lines = [line.strip() for line in a_tag.get_text("\n").split("\n") if line.strip()]
                    clean_title = lines[0] if lines else ""

                if is_newdaily_skip_title(clean_title):
                    continue
                if not is_valid_article_title(clean_title):
                    continue
                if len(clean_title) > 120:
                    clean_title = clean_title[:120] + "..."

                url_day = newdaily_url_day(full_url)
                if url_day and not is_within_hours(url_day, hours=96):
                    continue

                page_listed += 1
                seen_urls.add(full_url)

                clean_title, pub_date = fetch_newdaily_detail(session, full_url, clean_title)
                if is_newdaily_skip_title(clean_title):
                    continue
                if not pub_date:
                    pub_date = url_day
                if not pub_date or not is_within_hours(pub_date, hours=96):
                    continue
                if not is_collectible_article(clean_title, full_url):
                    continue

                norm_key = normalize_title(clean_title)
                if norm_key in seen_titles:
                    continue
                seen_titles.add(norm_key)

                articles.append({
                    "media_name": media_name,
                    "category": classify_article(title=clean_title, raw_category=raw_category),
                    "title": clean_title,
                    "url": full_url,
                    "published_at": pub_date,
                    "summary": None,
                    "content_body": "",
                })
                page_kept += 1
                if len(articles) >= NEWDAILY_CAP:
                    print(f"[{media_name}] {section_name} page={page} 수집 {len(articles)}건 (상한)")
                    return articles

            print(
                f"[{media_name}] {section_name} page={page} kept={page_kept} listed={page_listed} total={len(articles)}"
            )
            if page_listed == 0 or page_kept == 0:
                break
            time.sleep(CRAWL_DELAY_SECONDS)
        time.sleep(CRAWL_DELAY_SECONDS)

    return articles


def scrape_html_feed(site_url: str, media_name: str, raw_category: str) -> list[dict]:
    """HTML 메인 및 뉴스 목록 정밀 스크래핑 (중복 교차 검증)"""
    articles = []
    if not site_url:
        return articles

    if "newsandpost" in site_url:
        return scrape_newsandpost_news(raw_category)

    if "newdaily.co.kr" in site_url:
        return scrape_newdaily_sections(raw_category)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    try:
        response = session.get(site_url, timeout=8)
        if response.status_code != 200:
            return articles

        soup = BeautifulSoup(decode_html_bytes(response.content, response.headers.get("Content-Type", "")), "html.parser")
        seen_urls = set()
        seen_titles = set()

        for a_tag in soup.find_all("a"):
            href = a_tag.get("href", "").strip()
            if not href or href.startswith("javascript:") or href == "#":
                continue

            href_lower = href.lower()
            is_epoch_kr = "epochtimes.kr" in site_url

            # 목록/카테고리/섹션/검색 URL 제외
            if any(ex in href_lower for ex in ["list.php", "section.php", "category", "pdf_list", "search", "tag", "member", "login", "user"]):
                continue

            if is_epoch_kr:
                if not re.search(r'/20\d{2}/\d{2}/\d+\.html', href_lower):
                    continue
            else:
                # 한미일보 기사 뷰 URL (view.php?idx=숫자) 전용 검증
                if "hanmiilbo" in site_url and not re.search(r'view\.php\?idx=\d+', href_lower):
                    continue

                if not any(k in href for k in ["idx=", "view", "article", "news", "read"]):
                    continue

            full_url = urljoin(site_url, href)
            if full_url in seen_urls:
                continue

            title_el = a_tag.find(class_=["title", "subject", "tit", "headline"]) or a_tag.find(["h1", "h2", "h3", "h4", "strong", "b"])
            if title_el:
                clean_title = title_el.get_text(strip=True)
            else:
                lines = [line.strip() for line in a_tag.get_text("\n").split("\n") if line.strip()]
                clean_title = lines[0] if lines else ""

            if not is_valid_article_title(clean_title):
                continue

            if len(clean_title) > 120:
                clean_title = clean_title[:120] + "..."

            norm_key = normalize_title(clean_title)
            if norm_key in seen_titles:
                continue

            seen_urls.add(full_url)
            seen_titles.add(norm_key)

            pub_date = ""
            if "hanmiilbo" in site_url:
                pub_date = fetch_hanmiilbo_detail_date(session, full_url)
            else:
                parent_text = a_tag.parent.get_text() if a_tag.parent else ""
                m = re.search(r'20\d{2}[-./]\d{2}[-./]\d{2}(\s+\d{2}:\d{2}(:\d{2})?)?', parent_text)
                pub_date = parse_pub_date(m.group(0)) if m else ""

            if not pub_date:
                try:
                    detail_res = session.get(full_url, timeout=3)
                    if detail_res.status_code == 200:
                        detail_html = decode_html_bytes(detail_res.content, detail_res.headers.get("Content-Type", ""))
                        m_det = re.search(r'(?:article:published_time|og:regdate|pubdate)["\']?\s*content=["\']?([^"\'\s>]+)', detail_html, re.I)
                        if m_det:
                            pub_date = parse_pub_date(m_det.group(1))
                        if not pub_date:
                            m_body = re.search(r'(?:승인|입력|등록|작성)?\s*(20\d{2}[-./]\d{2}[-./]\d{2}\s+\d{2}:\d{2}(:\d{2})?)', detail_html)
                            if m_body:
                                pub_date = parse_pub_date(m_body.group(1))
                        if not pub_date and is_epoch_kr:
                            pub_date = parse_epoch_kr_ko_datetime(detail_html)
                except Exception:
                    pass

            if not pub_date:
                m_url = re.search(r'(20\d{2})(\d{2})(\d{2})', full_url)
                if m_url:
                    pub_date = f"{m_url.group(1)}-{m_url.group(2)}-{m_url.group(3)} 12:00:00"

            if not pub_date:
                pub_date = now_kst().strftime("%Y-%m-%d %H:%M:%S")

            if not is_within_hours(pub_date, hours=96):
                continue
            if not is_collectible_article(clean_title, full_url):
                continue

            assigned_category = classify_article(title=clean_title, raw_category=raw_category)

            articles.append({
                "media_name": media_name,
                "category": assigned_category,
                "title": clean_title,
                "url": full_url,
                "published_at": pub_date,
                "summary": None,
                "content_body": ""
            })

            if len(articles) >= 100:
                break

    except Exception as e:
        print(f"[{media_name}] HTML 스크래핑 에러 ({site_url}): {e}")

    return articles

def run_news_crawler() -> int:
    """국내·해외 보수 언론 RSS/HTML 크롤링 및 중복 제거"""
    all_articles = []
    reset_translate_budget()
    known_urls = set()
    try:
        known_urls = get_existing_urls()
    except Exception as e:
        print(f"[Crawler Warning] known URL 조회 실패(전체 번역 가능): {e}")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 뉴스 크롤링 시작 (known_urls={len(known_urls)})...")

    for category, media_list in MEDIA_CONFIG.items():
        for media in media_list:
            media_name = media["name"]
            rss_url = media.get("rss_url")
            site_url = media.get("site_url")
            lang = media.get("lang")
            url_contains = media.get("url_contains")
            default_category = media.get("default_category")
            section_urls = media.get("section_urls") or []

            try:
                rss_articles = []
                if rss_url:
                    rss_articles = fetch_rss_feed(
                        rss_url,
                        media_name,
                        category,
                        lang=lang,
                        url_contains=url_contains,
                        known_urls=known_urls,
                        default_category=default_category,
                    )
                    all_articles.extend(rss_articles)

                html_pages = []
                if media.get("custom_scraper") or media.get("allow_homepage"):
                    if site_url:
                        html_pages.append(site_url)
                html_pages.extend(u for u in section_urls if u and u not in html_pages)

                if len(rss_articles) < 15 and html_pages:
                    for page_url in html_pages:
                        html_articles = scrape_html_feed(page_url, media_name, category)
                        all_articles.extend(html_articles)
            except Exception as e:
                print(f"[{media_name}] 매체 수집 실패(계속 진행): {e}")

            time.sleep(CRAWL_DELAY_SECONDS)

    inserted_count = save_articles(all_articles)
    purge_old_articles(hours=96)
    purge_duplicate_articles()

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 뉴스 크롤링 완료. 신규 기사 {inserted_count}건 저장됨.")
    return inserted_count

if __name__ == "__main__":
    from database import init_db
    init_db()
    run_news_crawler()
