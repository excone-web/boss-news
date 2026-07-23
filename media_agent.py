"""
Media Management Agent Module
=============================
언론사 큐레이션 대상을 관리하고, 동적으로 언론사 추가/삭제/상태검증을 수행하는 에이전트 모듈입니다.
"""

import requests
from config import MEDIA_CONFIG

class MediaManagerAgent:
    """언론사 추가, 삭제, 상태 검증 및 파이프라인 관리를 담당하는 에이전트"""
    
    def __init__(self):
        self.config = MEDIA_CONFIG

    def get_registered_media(self) -> list[dict]:
        """현재 등록된 언론사 목록 반환"""
        media_list = []
        for category, item_list in self.config.items():
            for item in item_list:
                media_list.append({
                    "name": item["name"],
                    "rss_url": item.get("rss_url"),
                    "site_url": item.get("site_url"),
                    "type": "RSS" if item.get("rss_url") else "HTML Scraper"
                })
        return media_list

    def validate_media_health(self) -> list[dict]:
        """등록된 언론사의 RSS 및 웹사이트 접속 상태 점검 에이전트 비즈니스 로직"""
        health_results = []
        headers = {"User-Agent": "Mozilla/5.0"}

        for media in self.get_registered_media():
            name = media["name"]
            url = media["rss_url"] or media["site_url"]
            try:
                res = requests.get(url, headers=headers, timeout=5)
                status = "정상 (200 OK)" if res.status_code == 200 else f"오류 (HTTP {res.status_code})"
            except Exception as e:
                status = f"접속불가 ({e.__class__.__name__})"

            health_results.append({
                "name": name,
                "type": media["type"],
                "url": url,
                "status": status
            })

        return health_results

media_agent = MediaManagerAgent()
