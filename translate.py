"""
영문 제목 → 한글 기계번역 (deep-translator / Google)
======================================================
API 키 불필요. 실패 시 원문을 그대로 반환해 수집 파이프라인이 중단되지 않게 한다.
"""
import re
import time

# 1회 실행당 번역 상한 (rate-limit·CI 시간 보호)
MAX_TRANSLATIONS_PER_RUN = 80
_TRANSLATE_SLEEP_SEC = 0.15

_translated_count = 0


def reset_translate_budget() -> None:
    global _translated_count
    _translated_count = 0


def has_hangul(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text or ""))


def translate_title_to_ko(title: str) -> str:
    """
    영문 제목을 한글로 번역. 예산 초과·실패·빈 결과 시 원문 반환.
    """
    global _translated_count

    text = (title or "").strip()
    if not text:
        return title or ""

    # 이미 한글이 충분하면 스킵
    if has_hangul(text):
        return text

    if _translated_count >= MAX_TRANSLATIONS_PER_RUN:
        return text

    try:
        from deep_translator import GoogleTranslator

        result = GoogleTranslator(source="en", target="ko").translate(text)
        _translated_count += 1
        time.sleep(_TRANSLATE_SLEEP_SEC)
        if result and result.strip():
            return result.strip()
    except Exception as e:
        print(f"[Translate Warning] 제목 번역 실패(원문 유지): {e}")

    return text
