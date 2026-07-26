import json
import os
from datetime import datetime, timedelta, timezone
import database
import scraper
from generate_sitemap import generate_sitemap

KST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "articles.json")


def now_kst_str() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


def seed_db_from_articles_json() -> int:
    """
    CI는 news.db를 커밋하지 않으므로 빈 DB로 시작한다.
    체크아웃된 articles.json을 먼저 적재해 이전 수집분을 유지한 뒤 크롤을 이어간다.
    """
    if not os.path.isfile(JSON_PATH):
        return 0
    try:
        with open(JSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
        articles = data if isinstance(data, list) else (data.get("articles") or [])
        if not articles:
            return 0
        seeded = database.save_articles(articles)
        print(f"[Seed] articles.json → DB 적재 완료 (신규 insert {seeded}건 / 파일 {len(articles)}건)")
        return seeded
    except Exception as e:
        print(f"[Seed Warning] articles.json 적재 실패(무시 후 크롤 계속): {e}")
        return 0


def build_static_articles_json():
    """DB에 수집된 최근 96시간 기사를 articles.json 및 sitemap.xml 생성"""
    database.init_db()

    # 0. 이전 배포 데이터 시드 (Actions 등 ephemeral runner 대응)
    seed_db_from_articles_json()

    # 1. 뉴스 크롤링 실행
    try:
        scraper.run_news_crawler()
    except Exception as e:
        print(f"[Build Error] 뉴스 크롤링 중 오류: {e}")

    # 2. 최근 96시간 기사 조회
    conn = database.get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now(KST) - timedelta(hours=96)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        SELECT id, media_name, category, title, url, published_at, click_count, like_count
        FROM articles
        WHERE published_at >= ? OR published_at IS NULL OR published_at = ''
        ORDER BY published_at DESC, id DESC
    """, (cutoff,))

    rows = cursor.fetchall()
    conn.close()

    articles = [dict(row) for row in rows]

    build_time = now_kst_str()
    export_data = {
        "updated_at": build_time,
        "interval_hours": 2,
        "total_count": len(articles),
        "articles": articles
    }

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"[{build_time} KST] articles.json 생성 완료! 총 {len(articles)}건 저장됨.")

    # 3. Sitemap.xml 자동 생성
    try:
        generate_sitemap()
    except Exception as e:
        print(f"[Build Error] sitemap.xml 생성 실패: {e}")

    return len(articles)

if __name__ == "__main__":
    build_static_articles_json()

