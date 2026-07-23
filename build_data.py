import json
import sqlite3
import os
from datetime import datetime, timedelta
import database
import scraper
from generate_sitemap import generate_sitemap

def build_static_articles_json():
    """DB에 수집된 최근 96시간 기사를 articles.json 및 sitemap.xml 생성"""
    database.init_db()
    
    # 1. 뉴스 크롤링 실행
    try:
        scraper.run_news_crawler()
    except Exception as e:
        print(f"[Build Error] 뉴스 크롤링 중 오류: {e}")

    # 2. 최근 96시간 기사 조회
    conn = database.get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=96)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        SELECT id, media_name, category, title, url, published_at, click_count, like_count
        FROM articles
        WHERE published_at >= ? OR published_at IS NULL OR published_at = ''
        ORDER BY published_at DESC, id DESC
    """, (cutoff,))

    rows = cursor.fetchall()
    conn.close()

    articles = [dict(row) for row in rows]

    # JSON 저장
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "articles.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] articles.json 생성 완료! 총 {len(articles)}건 저장됨.")

    # 3. Sitemap.xml 자동 생성
    try:
        generate_sitemap()
    except Exception as e:
        print(f"[Build Error] sitemap.xml 생성 실패: {e}")

    return len(articles)

if __name__ == "__main__":
    build_static_articles_json()

