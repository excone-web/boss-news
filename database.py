import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH

def get_connection():
    """SQLite 커넥션 생성 (WAL 모드 및 timeout 설정 포함)"""
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    """데이터베이스 테이블 생성 및 미디어명 업데이트 (AI뉴스 -> 독립신문)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        media_name TEXT,
        category TEXT,
        title TEXT,
        url TEXT UNIQUE,
        published_at TEXT,
        summary TEXT,
        click_count INTEGER DEFAULT 0,
        like_count INTEGER DEFAULT 0,
        scraped_at TEXT
    );
    """)

    try:
        cursor.execute("ALTER TABLE articles ADD COLUMN like_count INTEGER DEFAULT 0;")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feedback_type TEXT,
        user_name TEXT,
        content TEXT,
        created_at TEXT
    );
    """)

    # 기존 DB 내 'AI뉴스' 미디어명을 '독립신문'으로 일괄 변경
    cursor.execute("UPDATE articles SET media_name = '독립신문' WHERE media_name = 'AI뉴스';")

    conn.commit()
    conn.close()

def save_articles(articles: list[dict]) -> int:
    if not articles:
        return 0

    conn = get_connection()
    cursor = conn.cursor()
    inserted_count = 0
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in articles:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO articles (
                    media_name, category, title, url, published_at, summary, click_count, like_count, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)
            """, (
                item.get("media_name"),
                item.get("category"),
                item.get("title"),
                item.get("url"),
                item.get("published_at"),
                item.get("summary"),
                scraped_at
            ))
            if cursor.rowcount > 0:
                inserted_count += 1
        except sqlite3.Error as e:
            print(f"[DB Error] 기사 저장 중 오류 발생: {e}")
            continue

    conn.commit()
    conn.close()
    return inserted_count

def purge_old_articles(hours: int = 96) -> int:
    """96시간(4일)이 지난 오래된 기사 자동 삭제기능"""
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("DELETE FROM articles WHERE published_at < ?", (cutoff,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def get_articles(
    category: str = None,
    search_keyword: str = None,
    media_name: str = None,
    sort_by: str = "latest",
    limit: int = 1000
) -> list[dict]:
    """최근 96시간 이내 기사 목록 조회"""
    conn = get_connection()
    cursor = conn.cursor()

    # 최근 96시간 기준 시간
    cutoff = (datetime.now() - timedelta(hours=96)).strftime("%Y-%m-%d %H:%M:%S")

    query = "SELECT * FROM articles WHERE 1=1 AND (published_at >= ? OR published_at IS NULL OR published_at = '')"
    params = [cutoff]

    if category and category != "전체":
        query += " AND category = ?"
        params.append(category)

    if media_name and media_name != "전체":
        query += " AND media_name = ?"
        params.append(media_name)

    if search_keyword:
        query += " AND title LIKE ?"
        params.append(f"%{search_keyword}%")

    if sort_by == "popular":
        query += " ORDER BY (click_count * 2 + like_count * 5) DESC, published_at DESC"
    else:
        query += " ORDER BY published_at DESC, id DESC"

    query += " LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def increment_click_count(article_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE articles SET click_count = click_count + 1 WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()

def save_feedback(feedback_type: str, user_name: str, content: str) -> bool:
    if not content or not content.strip():
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO feedbacks (feedback_type, user_name, content, created_at) VALUES (?, ?, ?, ?)",
        (feedback_type, user_name or "익명 사용자", content.strip(), created_at)
    )
    conn.commit()
    conn.close()
    return True

def get_feedbacks(limit: int = 100) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM feedbacks ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_feedback(feedback_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM feedbacks WHERE id = ?", (feedback_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_categories() -> list[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM articles WHERE category IS NOT NULL AND category != ''")
    rows = cursor.fetchall()
    conn.close()
    return [row["category"] for row in rows]

def get_media_names() -> list[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT media_name FROM articles WHERE media_name IS NOT NULL AND media_name != ''")
    rows = cursor.fetchall()
    conn.close()
    return [row["media_name"] for row in rows]

def get_db_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total_count, MAX(scraped_at) as last_scraped FROM articles")
    row = cursor.fetchone()
    conn.close()
    return {
        "total_count": row["total_count"] if row else 0,
        "last_scraped": row["last_scraped"] if row and row["last_scraped"] else "수집 이력 없음"
    }
