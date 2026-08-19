# 📰 보수 언론사 속보 뉴스 큐레이션 (Cloudflare Pages)

매일신문, 한미일보, 프리진뉴스, 트루스데일리, 펜앤드마이크, 독립신문, 뉴스앤포스트, 에포크타임스, 뉴데일리, 데일리안 등 국내 보수 언론의 최근 96시간 속보·원문 헤드라인을 큐레이션합니다.

---

## 1. 주요 특징 및 기술 스택
- **호스팅 & 프론트엔드:** Cloudflare Pages (HTML5, Vanilla CSS, JavaScript)
- **데이터 파이프라인:** Python RSS & HTML Scraper (`scraper.py`), SQLite (`news.db` 로컬), `articles.json`
- **자동 갱신 (서버):** GitHub Actions 스케줄(+ 선택 Cloudflare Worker 트리거) → `build_data.py` → `articles.json` / `sitemap.xml` 커밋 → Pages 재배포
- **자동 갱신 (브라우저):** `app.js`가 탭 표시 중 주기적으로 `articles.json` 재조회
- **검색엔진 최적화(SEO):** Schema.org JSON-LD, Open Graph, Twitter Cards, Sitemap.xml, Naver Search Advisor 인증
- **저작권 준수:** 원문 헤드라인, 배포시간, 언론사명 및 원문 링크 전용 제공

---

## 2. 프로젝트 디렉토리 구조

```
/news_curation
├── index.html                 # Cloudflare Pages 메인 HTML
├── style.css
├── app.js                     # 필터/페이지네이션 + articles.json 주기 재조회
├── articles.json              # 최근 96시간 기사 데이터 (배포 산출물)
├── _headers                   # Cloudflare Pages 캐시 정책
├── config.py                  # 언론사·크롤러 설정
├── database.py                # SQLite CRUD
├── scraper.py                 # RSS + HTML 스크래핑
├── category_agent.py          # 기사 카테고리 분류
├── build_data.py              # 수집 + articles.json/sitemap 빌드
├── generate_sitemap.py
├── cloudflare_worker.js       # (선택) Actions workflow_dispatch 정시 트리거
├── .github/workflows/
│   └── update_news.yml        # 2시간대 주기 자동 수집·푸시
├── robots.txt
├── sitemap.xml
├── requirements.txt
└── README.md
```

> 주기 수집은 **GitHub Actions**가 담당합니다. 로컬 APScheduler 등은 사용하지 않습니다.

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
`index.html`을 브라우저로 열거나 `python -m http.server 8000` 등으로 확인합니다.

### 4) 운영 자동 갱신
- **필수:** 레포 Actions 활성화 + `update_news.yml` schedule / 수동 Run workflow
- **권장:** Cloudflare Worker 배포 + Cron + Secret `GITHUB_PAT` (Actions schedule 지연 보완)
- Pages가 `main` 푸시에 연결되어 있어야 웹에 반영됩니다.
