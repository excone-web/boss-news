"""
Data Processing & Placeholder Summary Module
=============================================
MVP 단계에서는 AI 요약 API 연동을 생략하고, 추후 LLM (Gemini, OpenAI 등) 연동이
용이하도록 모듈화된 인터페이스 함수를 작성해 둡니다.
"""

def generate_summary(text: str, max_length: int = 150) -> str:
    """
    [Placeholder] 기사 본문 요약 생성 인터페이스
    
    :param text: 기사 본문 원문 텍스트
    :param max_length: 요약 최대 길이
    :return: 요약 문장 (MVP 단계에서는 placeholder 메시지 또는 단순 첫 문장 잘라내기 반환)
    """
    if not text or len(text.strip()) == 0:
        return "[요약 정보 없음]"
    
    # MVP 임시 로직: 본문의 앞부분 일부를 자르거나 placeholder를 반환
    cleaned_text = text.strip().replace("\n", " ")
    if len(cleaned_text) > max_length:
        return cleaned_text[:max_length] + "..."
    return cleaned_text

def process_unsummarized_articles():
    """
    [Future Feature] DB에서 summary가 NULL인 기사들을 불러와 요약을 생성하고 업데이트하는 프로세서
    """
    # 추후 LLM 요약 자동화 스케줄러 기능 구현 시 이 함수에 DB 조회 및 업데이트 로직 추가
    pass
