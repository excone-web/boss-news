import time
import requests
import feedparser
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from config import MEDIA_CONFIG, USER_AGENT, CRAWL_DELAY_SECONDS
from database import save_articles, purge_old_articles
from category_agent import classify_article

def parse_pub_date(raw_date: str) -> str:
    """RSS pubDate 및 다양한 포맷의 날짜 문자열을 YYYY-MM-DD HH:MM:SS 형태로 변환"""
    if not raw_date:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        dt = parsedate_to_datetime(raw_date)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw_date, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def is_within_hours(published_at_str: str, hours: int = 96) -> bool:
    """기사 발행시간이 최근 N시간 이내인지 확인 (기본 96시간 = 4일)"""
    if not published_at_str:
        return True
    try:
        dt = datetime.strptime(published_at_str[:19], "%Y-%m-%d %H:%M:%S")
        cutoff = datetime.now() - timedelta(hours=hours)
        return dt >= cutoff
    except Exception:
        return True

def fetch_rss_feed(rss_url: str, media_name: str, raw_category: str) -> list[dict]:
    """RSS 피드 파싱 (최근 96시간 기사 필터링 포함)"""
    articles = []
    if not rss_url:
        return articles

    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(rss_url, headers=headers, timeout=8)
        if response.status_code != 200:
            return articles

        feed = feedparser.parse(response.content)

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()

            if not title or not url:
                continue

            raw_date = entry.get("published", entry.get("updated", ""))
            published_at = parse_pub_date(raw_date)

            if not is_within_hours(published_at, hours=96):
                continue

            description = entry.get("summary", entry.get("description", ""))
            clean_body = ""
            if description:
                soup = BeautifulSoup(description, "html.parser")
                clean_body = soup.get_text(strip=True)

            assigned_category = classify_article(title=title, content=clean_body, raw_category=raw_category)

            articles.append({
                "media_name": media_name,
                "category": assigned_category,
                "title": title,
                "url": url,
                "published_at": published_at,
                "summary": None,
                "content_body": clean_body
            })

    except Exception as e:
        print(f"[{media_name}] RSS 파싱 에러 ({rss_url}): {e}")

    return articles

def fetch_hanmiilbo_detail_date(session: requests.Session, article_url: str) -> str:
    """한미일보 본문 상세페이지에서 원래 작성/업로드된 정확한 시각 추출"""
    try:
        res = session.get(article_url, timeout=3)
        if res.status_code == 200:
            m = re.search(r'20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', res.text)
            if m:
                return parse_pub_date(m.group(0))
            m2 = re.search(r'20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}', res.text)
            if m2:
                return parse_pub_date(m2.group(0))
    except Exception:
        pass
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def scrape_html_feed(site_url: str, media_name: str, raw_category: str) -> list[dict]:
    """HTML 메인 및 뉴스 목록 정밀 스크래핑 (기사 수집량 극대화)"""
    articles = []
    if not site_url:
        return articles

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    try:
        response = session.get(site_url, timeout=8)
        if response.status_code != 200:
            return articles

        soup = BeautifulSoup(response.text, "html.parser")
        seen_urls = set()

        for a_tag in soup.find_all("a"):
            href = a_tag.get("href", "").strip()
            if not href or href.startswith("javascript:") or href == "#":
                continue

            # 뉴스 기사 URL 패턴 탐지
            if any(k in href for k in ["idx=", "view", "article", "news", "read"]):
                full_url = urljoin(site_url, href)
                if full_url in seen_urls:
                    continue

                title_el = a_tag.find(class_=["title", "subject", "tit", "headline"]) or a_tag.find(["h1", "h2", "h3", "h4", "strong", "b"])
                if title_el:
                    clean_title = title_el.get_text(strip=True)
                else:
                    lines = [line.strip() for line in a_tag.get_text("\n").split("\n") if line.strip()]
                    clean_title = lines[0] if lines else ""

                if not clean_title or len(clean_title) < 6:
                    continue
                if len(clean_title) > 120:
                    clean_title = clean_title[:120] + "..."

                seen_urls.add(full_url)

                # 한미일보는 본문 정밀 파서 사용
                if "hanmiilbo" in site_url:
                    pub_date = fetch_hanmiilbo_detail_date(session, full_url)
                else:
                    parent_text = a_tag.parent.get_text() if a_tag.parent else ""
                    m = re.search(r'20\d{2}[-./]\d{2}[-./]\d{2}(\s+\d{2}:\d{2}(:\d{2})?)?', parent_text)
                    pub_date = parse_pub_date(m.group(0)) if m else parse_pub_date("")

                if not is_within_hours(pub_date, hours=96):
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
    """보수 언론사 6곳 RSS + HTML 듀얼 크롤링 (수집량 최적화)"""
    all_articles = []
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 보수 언론사 6곳 듀얼 크롤링 시작...")

    for category, media_list in MEDIA_CONFIG.items():
        for media in media_list:
            media_name = media["name"]
            rss_url = media.get("rss_url")
            site_url = media.get("site_url")

            rss_articles = []
            if rss_url:
                rss_articles = fetch_rss_feed(rss_url, media_name, category)
                all_articles.extend(rss_articles)
                print(f" -> [{media_name} (RSS)] {len(rss_articles)}건 수집")

            # RSS 수집건수가 적거나 HTML 전용 언론사인 경우 HTML 파싱 백업 실행 (기사 수집량 보장)
            if len(rss_articles) < 15 and site_url:
                html_articles = scrape_html_feed(site_url, media_name, category)
                all_articles.extend(html_articles)
                print(f" -> [{media_name} (HTML 보충)] {len(html_articles)}건 수집")

            time.sleep(CRAWL_DELAY_SECONDS)

    inserted_count = save_articles(all_articles)
    purge_old_articles(hours=96)
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 뉴스 크롤링 완료. 신규 기사 {inserted_count}건 저장됨.")
    return inserted_count

if __name__ == "__main__":
    from database import init_db
    init_db()
    run_news_crawler()
