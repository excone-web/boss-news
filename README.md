# 📰 언론사 뉴스 헤드라인 및 요약 큐레이션 시스템 (MVP)

속보 중심의 언론사 주요 뉴스를 자동 수집하고 카테고리별로 큐레이팅하여 최신 정보와 원문 링크를 고밀도 텍스트 UI로 제공하는 웹 서비스입니다.

---

## 1. 주요 특징
* **저작권 준수:** 헤드라인, 발행시간, 언론사명 및 원문 링크 위주의 정보 제공
* **자동 스케줄링:** APScheduler 기반 2시간 간격 자동 RSS 수집 (서버 부하 및 차단 방지)
* **스마트 중복 제거:** SQLite `UNIQUE(url)` 제약조건 및 `INSERT OR IGNORE` 기반 중복 방지
* **검색 & 필터링:** 카테고리(정치, 경제, 사회), 키워드 검색, 언론사별 필터, 최신순/인기순 정렬
* **미래 확장성:** `processor.py`에 요약 생성 인터페이스(`summary` 컬럼 및 placeholder 함수) 준비

---

## 2. 프로젝트 디렉토리 구조

```
/news_curation
├── config.py              # 언론사·카테고리 매핑 및 스케줄러/크롤러 설정
├── database.py            # SQLite 연결, 테이블 생성, CRUD, 중복 방지 저장 로직
├── scraper.py             # RSS + BeautifulSoup 스크래핑 로직 (Polite crawling)
├── processor.py           # 요약 placeholder 함수 (추후 LLM 연동용 인터페이스)
├── scheduler.py           # APScheduler 백그라운드 구동 로직
├── app.py                 # Streamlit 대시보드 UI
├── requirements.txt       # 의존성 패키지 목록
└── README.md              # 실행 가이드 문서
```

---

## 3. 실행 방법

### 1) 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

### 2) 데이터베이스 초기화 및 최초 뉴스 수집 (선택)
```bash
python scraper.py
```

### 3) Streamlit 웹 애플리케이션 실행
```bash
streamlit run app.py
```

실행 후 웹 브라우저에서 `http://localhost:8501`로 접속할 수 있습니다.

---

## 4. 데이터베이스 스키마

```sql
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_name TEXT,
    category TEXT,
    title TEXT,
    url TEXT UNIQUE,
    published_at TEXT,
    summary TEXT,           -- MVP에서는 NULL 또는 placeholder
    click_count INTEGER DEFAULT 0,
    scraped_at TEXT
);
```

---

## 5. 추후 확장 계획
* **AI 요약 생성:** `processor.py`의 `generate_summary()` 함수에 OpenAI / Gemini API를 연결하여 자동으로 3줄 요약을 생성하도록 구현 예정
* **카테고리/언론사 추가:** `config.py` 파일의 `MEDIA_CONFIG` 수정을 통해 추가 코드 작성 없이 간편하게 확장 가능
