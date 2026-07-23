"""
APScheduler Background Scheduler Module
=======================================
주기적인 뉴스 자동 수집(2~4시간 간격)을 담당합니다.
Streamlit 실행 시 중복 실행되지 않도록 싱글톤 패턴 및 백그라운드 구동을 지원합니다.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config import CRAWL_INTERVAL_HOURS
from database import init_db
from scraper import run_news_crawler

_scheduler = None

def init_scheduler() -> BackgroundScheduler:
    """스케줄러 싱글톤 초기화 및 작업 등록"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    # DB 테이블 존재 여부 확인
    init_db()

    _scheduler = BackgroundScheduler(daemon=True)
    
    # 2시간(기본값) 간격으로 뉴스 자동 수집 등록
    _scheduler.add_job(
        func=run_news_crawler,
        trigger=IntervalTrigger(hours=CRAWL_INTERVAL_HOURS),
        id="news_crawler_job",
        name="주기적 뉴스 RSS 자동 수집",
        replace_existing=True
    )
    
    _scheduler.start()
    print(f"[Scheduler] 백그라운드 뉴스 수집 스케줄러 시작됨 ({CRAWL_INTERVAL_HOURS}시간 간격)")
    return _scheduler

def trigger_manual_crawl() -> int:
    """수동으로 수집 프로세스를 실행"""
    init_db()
    return run_news_crawler()

def stop_scheduler():
    """스케줄러 종료"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Scheduler] 백그라운드 스케줄러 종료됨")
        _scheduler = None

if __name__ == "__main__":
    import time
    scheduler = init_scheduler()
    # 즉시 1회 실행 테스트
    trigger_manual_crawl()
    print("스케줄러 테스트 실행 중... Ctrl+C로 종료")
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        stop_scheduler()
