# 매체 수집 규칙

새 언론사를 넣을 때 사용자가 섹션을 다시 말하지 않아도 아래를 적용한다.

## 수집하는 섹션만
정치, 경제, 사회, 국제/외교/북한/국방, 칼럼/오피니언.

## 넣지 말 것
연예, 스포츠, 라이프, 문화, 포토/영상/VOD, 지역 홍보, 날씨 단신, 션윈/파룬궁, 홈 전체 RSS(`allArticle`, `/rss/` 무카테), 홈 HTML 전체.

## 등록 방법 (`config.py` + `media_policy.py`)
1. 섹션 RSS가 있으면 **반드시** `section_rss("이름", [("politics", url), ...])`. 키는 `ALLOWED_SECTIONS`만.
2. HTML이면 `html_media(..., section_urls=[정치/경제/사회/... 목록 URL])`. 전용 파서가 있을 때만 `custom_scraper=True`.
3. 섹션 피드가 **정말 없을 때만** `mixed_rss(...)`. 제목·URL 필터가 게이트다.
4. 홈만 긁는 `site_url` 단독 추가는 금지. `validate_media_config`가 import 시 막는다.
5. 데일리안처럼 시각 파싱이 반복 실패하면 수집하지 않는다.

기사 단위 필터(`is_collectible_article`)는 RSS/HTML 공통으로 이미 돈다. 새 스크래퍼를 짜도 저장 전에 이 함수를 통과시켜야 한다.
