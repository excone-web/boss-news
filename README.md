# 📰 보수 언론사 속보 뉴스 큐레이션 (Cloudflare Pages)

매일신문, 한미일보, 프리진뉴스, 트루스데일리, 펜앤드마이크, 독립신문의 최근 96시간 실시간 속보 및 원문 헤드라인을 큐레이션하여 파스텔 모던 텍스트 UI로 제공하는 웹 서비스입니다.

---

## 1. 주요 특징 및 기술 스택
- **호스팅 & 프론트엔드:** Cloudflare Pages (HTML5, Vanilla CSS, JavaScript)
- **데이터 파이프라인:** Python RSS & HTML Scraper (`scraper.py`), SQLite (`news.db`), `articles.json`
- **자동 갱신:** `build_data.py` 실행 시 96시간 이내 최신 기사 수집 ➔ `articles.json` 및 `sitemap.xml` 자동 갱신
- **검색엔진 최적화(SEO):** Schema.org JSON-LD, Open Graph, Twitter Cards, Sitemap.xml, Naver Search Advisor 인증
- **저작권 준수:** 원문 헤드라인, 배포시간, 언론사명 및 원문 링크 전용 제공

---

## 2. 프로젝트 디렉토리 구조

```
/news_curation
├── index.html                 # Cloudflare Pages 메인 HTML 화면
├── style.css                  # 모던 디자인 CSS
├── app.js                     # 프론트엔드 필터링 및 articles.json 데이터 바인딩
├── articles.json              # 최근 96시간 큐레이션 기사 데이터셋
├── config.py                  # 언론사 카테고리 매핑 및 크롤러 설정
├── database.py                # SQLite 연결, 테이블 생성, CRUD, 중복 검증
├── scraper.py                 # RSS + HTML 정밀 스크래핑 로직
├── scheduler.py               # 백그라운드 주기적 수집 스케줄러
├── build_data.py              # 데이터 수집 및 articles.json/sitemap.xml 빌드
├── generate_sitemap.py        # sitemap.xml 자동 생성 스크립트
├── robots.txt                 # 검색엔진 크롤링 지침
├── sitemap.xml                # SEO 사이트맵
├── naverc008d57c...html       # 네이버 서치어드바이저 소유 확인
├── requirements.txt           # Python 크롤링 의존성 라이브러리 목록
└── README.md                  # 실행 및 운영 안내 문서
```

---

## 3. 실행 및 데이터 빌드 방법

### 1) 크롤링 패키지 설치
```bash
pip install -r requirements.txt
```

### 2) 뉴스 수집 및 articles.json / sitemap.xml 빌드
```bash
python build_data.py
```

### 3) 로컬 웹 테스트
`index.html` 파일을 웹 브라우저로 직접 열거나 로컬 웹 서버(예: `python -m http.server 8000`)로 실행하여 확인할 수 있습니다.
