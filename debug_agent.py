import sqlite3
import os
import sys
import py_compile
from config import DB_PATH

class DebugAgent:
    """
    디버깅 전문 에이전트
    - 데이터베이스 무결성(Pragma Quick Check) 점검
    - 에이전트 모듈 및 app.py 코드 구문 검증
    - 크롤러 수집 데이터 상태 정밀 진단
    """
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def check_database_integrity(self) -> dict:
        """SQLite DB 무결성 및 테이블 검증"""
        if not os.path.exists(self.db_path):
            return {"status": "FAIL", "error": "데이터베이스 파일이 존재하지 않습니다."}

        try:
            conn = sqlite3.connect(self.db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute("PRAGMA quick_check;")
            res = cursor.fetchone()
            if not res or res[0] != "ok":
                return {"status": "FAIL", "error": f"DB 무결성 오류: {res}"}

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT COUNT(*) FROM articles;")
            art_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM feedbacks;")
            fb_count = cursor.fetchone()[0]

            conn.close()
            return {
                "status": "PASS",
                "tables": tables,
                "article_count": art_count,
                "feedback_count": fb_count,
                "detail": "ok"
            }
        except Exception as e:
            return {"status": "FAIL", "error": str(e)}

    def check_agent_modules(self) -> dict:
        """주요 에이전트 모듈 및 app.py 구문 검증"""
        results = {}
        # 1. app.py 구문 검사
        try:
            py_compile.compile("app.py", doraise=True)
            results["app.py"] = "PASS (compile ok)"
        except Exception as e:
            results["app.py"] = f"FAIL ({e})"

        # 2. category_agent 테스트
        try:
            from category_agent import classify_article
            cat = classify_article("대통령 국회 연설", raw_category="주요뉴스")
            results["category_agent"] = f"PASS (category: {cat})"
        except Exception as e:
            results["category_agent"] = f"FAIL ({e})"

        # 3. media_agent 테스트
        try:
            from media_agent import media_agent
            media_list = media_agent.get_registered_media()
            results["media_agent"] = f"PASS (media count: {len(media_list)})"
        except Exception as e:
            results["media_agent"] = f"FAIL ({e})"

        return results

    def run_full_diagnostics(self) -> dict:
        """종합 진단 실행"""
        db_res = self.check_database_integrity()
        agent_res = self.check_agent_modules()
        
        is_clean = (db_res.get("status") == "PASS") and all("PASS" in v for v in agent_res.values())
        
        return {
            "is_clean": is_clean,
            "db_health": db_res,
            "agent_health": agent_res
        }

debug_agent = DebugAgent()

if __name__ == "__main__":
    print("=== Debugging Agent Self Diagnostics ===")
    diag = debug_agent.run_full_diagnostics()
    print("Status:", "CLEAN" if diag["is_clean"] else "FAIL")
    print("DB:", diag["db_health"])
    print("Agents:", diag["agent_health"])
