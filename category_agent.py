"""
Category Management & Robust Auto-Classification Agent
======================================================
기사의 제목 및 키워드를 과도하지 않게 명확한 7개 핵심 카테고리로 정확하게 분류합니다.
부동산, 아파트, 오피스텔 등 핵심 주제 키워드에 높은 우선순위 가중치를 부여하여 오분류를 차단합니다.
"""

KEYWORDS_MAP = {
    "정치/외교": {
        "high": ["대통령", "국회", "정당", "여당", "야당", "의원", "선거", "총리", "장관", "외교", "안보", "북한", "트럼프", "바이든", "조국", "이재명", "한동훈", "원내대표", "탄핵", "투표"],
        "normal": ["정치", "정부", "국방", "공천", "외교부", "통일부", "입법", "법안"]
    },
    "경제/부동산": {
        "high": ["아파트", "오피스텔", "부동산", "주택", "분양", "재건축", "재개발", "전세", "청약", "금리", "증시", "주식", "코스피", "코스닥", "환율", "코인", "비트코인", "매매", "물가"],
        "normal": ["경제", "금융", "은행", "재정", "무역", "상장", "기업", "수출", "수입", "실적", "투자", "자산", "임대", "건설"]
    },
    "사회/사법": {
        "high": ["검찰", "경찰", "법원", "재판", "범죄", "수사", "피의자", "구속", "판결", "사건", "사고", "음주운전", "폭행", "사기", "배임", "횡령"],
        "normal": ["사회", "노동", "복지", "교육", "노조", "파업", "근로자", "임금", "연금", "학교", "대학", "의료", "병원", "화재", "재난"]
    },
    "IT/과학": {
        "high": ["AI", "인공지능", "반도체", "IT", "과학", "로봇", "빅데이터", "플랫폼", "소프트웨어", "앱", "클라우드", "네이버", "카카오", "삼성전자", "SK하이닉스", "엔비디아", "애플", "구글", "통신"],
        "normal": ["양자", "기술", "우주", "스마트폰", "디지털"]
    },
    "문화/연예/스포츠": {
        "high": ["연예", "스포츠", "방송", "영화", "공연", "K-POP", "전시", "미술", "음악", "드라마", "골프", "축구", "야구", "가수", "배우", "올림픽"],
        "normal": ["문화", "관광", "축제", "건강", "여행", "맛집"]
    },
    "지역/사설": {
        "high": ["대구", "경북", "구미", "포항", "경산", "안동", "경주", "김천", "칠곡", "사설", "칼럼", "시론", "시선", "기고"],
        "normal": ["지자체", "시청", "도청", "구청", "군청", "시장", "도지사", "구청장", "군수", "조례", "행정"]
    }
}

def classify_article(title: str, content: str = "", raw_category: str = "") -> str:
    """기사 제목 및 내용을 분석하여 정확한 카테고리로 분류"""
    text_to_search = f"{title} {content}"

    category_scores = {cat: 0 for cat in KEYWORDS_MAP.keys()}

    for category, sub_dict in KEYWORDS_MAP.items():
        # 고우선순위 키워드 (제목 포함 시 +10점, 본문 포함 시 +5점)
        for kw in sub_dict.get("high", []):
            if kw in title:
                category_scores[category] += 10
            elif kw in text_to_search:
                category_scores[category] += 5

        # 일반 키워드 (제목 포함 시 +2점, 본문 포함 시 +1점)
        for kw in sub_dict.get("normal", []):
            if kw in title:
                category_scores[category] += 2
            elif kw in text_to_search:
                category_scores[category] += 1

    best_category = max(category_scores, key=category_scores.get)
    if category_scores[best_category] >= 2:
        return best_category

    return "일반/종합"

def reclassify_all_articles_in_db():
    """DB 내 모든 기사를 정밀 카테고리로 전수 재분류 및 업데이트"""
    import sqlite3
    from database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, category FROM articles")
    rows = cursor.fetchall()

    updated_count = 0
    for row in rows:
        article_id = row["id"]
        title = row["title"] or ""
        curr_cat = row["category"] or ""

        new_cat = classify_article(title=title, raw_category=curr_cat)
        cursor.execute("UPDATE articles SET category = ? WHERE id = ?", (new_cat, article_id))
        updated_count += 1

    conn.commit()
    conn.close()
    return updated_count
