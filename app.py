import streamlit as st
import pandas as pd
import hashlib
import math
import time
from datetime import datetime

import database
from scheduler import init_scheduler, trigger_manual_crawl
from media_agent import media_agent
from category_agent import reclassify_all_articles_in_db

init_db = database.init_db
get_articles = database.get_articles
increment_click_count = database.increment_click_count
save_feedback = database.save_feedback
get_feedbacks = database.get_feedbacks
delete_feedback = getattr(database, 'delete_feedback', lambda fid: False)
get_categories = database.get_categories
get_media_names = database.get_media_names
get_db_stats = database.get_db_stats

MASTER_SALT = "antigravity_master_salt_2026"
MASTER_HASH = "6a340cb2c9d559cdebee6b639254b2cb59586693b0d61d3b7d4057e7dd412cf1"

def verify_master_password(password_input: str) -> bool:
    if not password_input:
        return False
    hashed = hashlib.sha256((password_input + MASTER_SALT).encode('utf-8')).hexdigest()
    return hashed == MASTER_HASH

# 1. 페이지 기본 설정 및 디자인 CSS
st.set_page_config(
    page_title="보수 언론사 속보 뉴스 큐레이션",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }

    /* 메인 여백 콤팩트화 */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
    }

    /* 우측 상단 툴바 및 Manage app 버튼만 숨김 (좌측 상단 사이드바 열기/접기 버튼은 100% 보존) */
    div[data-testid="stToolbar"],
    div[data-testid="stAppViewerToolbar"],
    .stAppViewerToolbar,
    [data-testid="manage-app-button"],
    #MainMenu,
    footer {
        display: none !important;
        visibility: hidden !important;
    }
    
    div[data-testid="stMarkdownContainer"],
    div[data-testid="stMarkdownContainer"] > div,
    div[data-testid="element-container"] {
        width: 100% !important;
    }
    
    .header-box {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        color: #ffffff;
        padding: 20px 24px;
        border-radius: 10px;
        margin-bottom: 16px;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        display: block !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .header-title {
        font-size: 1.55rem;
        font-weight: 700;
        margin: 0;
    }
    .header-desc {
        font-size: 0.88rem;
        color: #94a3b8;
        margin-top: 6px;
    }

    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        align-items: center !important;
        padding-top: 1px !important;
        padding-bottom: 1px !important;
        margin-bottom: -5px !important;
    }
    div[data-testid="stColumn"] {
        display: flex !important;
        align-items: center !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }

    .media-badge {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: #eff6ff;
        color: #1d4ed8;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        white-space: nowrap;
        height: 24px;
        line-height: 1 !important;
        margin: 0 !important;
    }

    .title-link {
        font-size: 0.95rem;
        font-weight: 600;
        text-decoration: none !important;
        color: #334155 !important;
        line-height: 1.4 !important;
        display: inline-block !important;
        vertical-align: middle !important;
        transition: color 0.15s ease;
    }
    .title-link:hover {
        color: #2563eb !important;
        text-decoration: none !important;
    }
    
    .date-span {
        font-size: 0.82rem;
        color: #64748b;
        display: inline-flex;
        align-items: center;
        height: 24px;
        white-space: nowrap;
    }

    /* 100% 정밀 타겟팅: 메인 하단 컬럼 페이지네이션 버튼 테두리/배경 완전 제거 */
    div[data-testid="stColumn"] button,
    div[data-testid="column"] button,
    div[data-testid="stHorizontalBlock"] div.stButton > button,
    button[data-testid*="stBaseButton"] {
        background: transparent !important;
        background-color: transparent !important;
        border: 0px none transparent !important;
        border-radius: 0px !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 0 4px !important;
        margin: 0 !important;
        min-height: 24px !important;
        height: 24px !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        color: #1d4ed8 !important;
    }

    div[data-testid="stColumn"] button[kind="primary"],
    div[data-testid="stColumn"] button[data-testid*="stBaseButton-primary"],
    button[data-testid*="stBaseButton-primary"] {
        color: #dc2626 !important; /* 선택된 페이지: 빨간색 강조 */
        font-weight: 700 !important;
        text-decoration: underline !important;
        background: transparent !important;
        background-color: transparent !important;
        border: 0px none transparent !important;
        box-shadow: none !important;
    }

    div[data-testid="stColumn"] button:hover {
        color: #2563eb !important;
        background: transparent !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# 2. 백그라운드 서비스 및 세션 상태 초기화
@st.cache_resource
def start_background_services():
    init_db()
    init_scheduler()
    
    stats = get_db_stats()
    if stats.get("total_count", 0) == 0:
        try:
            from scraper import run_news_crawler
            run_news_crawler()
        except Exception as e:
            print(f"[Auto Crawl Startup Error] {e}")
            
    return True

start_background_services()

if 'is_master' not in st.session_state:
    st.session_state['is_master'] = False

if 'last_manual_crawl' not in st.session_state:
    st.session_state['last_manual_crawl'] = 0.0

# 3. 사이드바 구성
with st.sidebar:
    st.title("📰 검색 및 뉴스 필터")
    
    search_keyword = st.text_input("🔍 키워드 검색", placeholder="예: 국회, 대통령, 부동산, AI...")
    
    db_media_list = get_media_names()
    media_options = ["전체"] + db_media_list
    selected_media = st.selectbox("🏢 언론사 선택", options=media_options, index=0)
    
    sort_option = st.radio(
        "📊 정렬 방식",
        options=["최신순 (발행시간)", "인기순 (조회수)"],
        index=0
    )
    sort_by = "popular" if "인기" in sort_option else "latest"
    
    items_per_page = st.selectbox("📄 페이지당 기사 수", options=[20, 50, 100, 200], index=1)
    
    st.divider()

    # 마스터 로그인
    if not st.session_state['is_master']:
        st.subheader("🔑 마스터 로그인")
        pw_input = st.text_input("마스터 비밀번호", type="password", placeholder="비밀번호 입력")
        if st.button("로그인", type="primary", use_container_width=True):
            if verify_master_password(pw_input):
                st.session_state['is_master'] = True
                st.success("🔓 마스터 인증 성공!")
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")
    else:
        st.success("🔓 **마스터 전용 시스템 관리**")
        if st.button("🚪 마스터 로그아웃", use_container_width=True):
            st.session_state['is_master'] = False
            st.rerun()

        st.divider()
        
        stats = get_db_stats()
        st.info(f"📊 **DB 현황 (최근 96시간)**\n- 총 기사: `{stats['total_count']:,} 건`\n- 최근 수집: `{stats['last_scraped']}`")

        # 3분 쿨다운 과부하 방지
        CRAWL_COOLDOWN_SECONDS = 180
        if st.button("🔄 실시간 뉴스 즉시 수집", type="primary", use_container_width=True):
            now = time.time()
            elapsed = now - st.session_state['last_manual_crawl']
            if elapsed < CRAWL_COOLDOWN_SECONDS:
                remaining = int(CRAWL_COOLDOWN_SECONDS - elapsed)
                st.warning(f"⚠️ 수집 요청은 3분에 1회만 가능합니다. ({remaining}초 후 가능)")
            else:
                with st.spinner("보수 언론사 6곳 최근 96시간 기사 수집 중..."):
                    new_count = trigger_manual_crawl()
                    st.session_state['last_manual_crawl'] = time.time()
                    st.success(f"수집 완료! (신규 기사 {new_count}건)")
                    st.rerun()

        with st.expander("🏢 보수 언론사 6곳 관리", expanded=False):
            registered_media = media_agent.get_registered_media()
            for m in registered_media:
                st.markdown(f"- **{m['name']}** (`{m['type']}`)")
                
            if st.button("🔌 헬스체크 검증"):
                health = media_agent.validate_media_health()
                for h in health:
                    st.caption(f"{h['name']}: {h['status']}")

        if st.button("🏷️ 정밀 카테고리 재분류"):
            with st.spinner("카테고리 분류 에이전트 작동 중..."):
                count = reclassify_all_articles_in_db()
                st.success(f"{count}건 기사 재분류 완료!")
                st.rerun()

        # 마스터 전용 피드백 관리
        st.divider()
        st.subheader("📋 접수된 피드백 관리 (마스터 전용)")
        feedbacks = get_feedbacks(100)
        if not feedbacks:
            st.caption("접수된 피드백이 없습니다.")
        else:
            for fb in feedbacks:
                st.markdown(f"**[{fb['feedback_type']}]** `{fb['created_at']}` - *{fb['user_name']}*")
                st.caption(fb['content'])
                if st.button("🗑️ 피드백 삭제", key=f"del_fb_{fb['id']}", help="해당 피드백을 완전 삭제합니다"):
                    delete_feedback(fb['id'])
                    st.success("피드백이 정상적으로 삭제되었습니다.")
                    st.rerun()
                st.divider()

# 4. 메인 화면 - 헤더
st.markdown("""
<div class="header-box">
    <div class="header-title">📰 보수 언론사 속보 뉴스 큐레이션 (최근 96시간)</div>
    <div class="header-desc">매일신문 · 한미일보 · 프리진뉴스 · 트루스데일리 · 펜앤드마이크 · 독립신문의 최근 96시간 속보 및 원문 링크를 제공합니다.</div>
</div>
""", unsafe_allow_html=True)

# 5. 메인 카테고리 탭
db_categories = get_categories()
preferred_order = [
    "정치/외교", "경제/부동산", "사회/사법", "IT/과학", 
    "문화/연예/스포츠", "지역/사설", "일반/종합"
]
sorted_categories = [c for c in preferred_order if c in db_categories] + [c for c in db_categories if c not in preferred_order]

category_tabs = ["전체"] + sorted_categories + ["💡 의견/피드백 보내기"]
selected_tab = st.tabs(category_tabs)

for idx, tab_name in enumerate(category_tabs):
    with selected_tab[idx]:
        if tab_name == "💡 의견/피드백 보내기":
            st.markdown("### 💡 서비스 피드백 및 의견 보내기")
            st.write("서비스 관련 버그 신고, 언론사 추가 요청, 개선 제안사항을 남겨주시면 마스터가 확인 후 조치합니다.")
            
            with st.form("user_feedback_form"):
                f_type = st.selectbox("의견 유형", ["버그 신고", "기능 제안", "언론사 추가 요청", "기타 의견"])
                f_user = st.text_input("작성자 (선택)", placeholder="성함 또는 닉네임")
                f_body = st.text_area("피드백 내용", placeholder="내용을 구체적으로 입력해주세요...")
                submitted = st.form_submit_button("의견 제출하기", type="primary")
                if submitted:
                    if save_feedback(f_type, f_user, f_body):
                        st.success("소중한 의견이 마스터에게 성공적으로 접수되었습니다! 감사합니다.")
                    else:
                        st.error("내용을 입력해주세요.")

        else:
            all_articles = get_articles(
                category=tab_name,
                search_keyword=search_keyword,
                media_name=selected_media,
                sort_by=sort_by,
                limit=2000
            )
            
            total_count = len(all_articles)
            total_pages = math.ceil(total_count / items_per_page) if total_count > 0 else 1

            page_key = f"page_num_{idx}"
            if page_key not in st.session_state:
                st.session_state[page_key] = 1
                
            curr_page = st.session_state[page_key]
            if curr_page > total_pages:
                curr_page = total_pages
                st.session_state[page_key] = total_pages

            st.caption(f"**[{tab_name}]** 최근 96시간 기사 총 **{total_count}** 개 (페이지: **{curr_page} / {total_pages}**)")

            if not all_articles:
                st.warning("해당 조건에 일치하는 최근 96시간 이내 수집 기사가 없습니다.")
            else:
                start_idx = (curr_page - 1) * items_per_page
                end_idx = start_idx + items_per_page
                page_articles = all_articles[start_idx:end_idx]

                for item in page_articles:
                    article_id = item["id"]
                    media_name = item["media_name"] or "언론사"
                    title = item["title"]
                    url = item["url"]
                    published_at = item["published_at"] or ""
                    formatted_date = published_at[:16] if len(published_at) >= 16 else published_at
                    
                    cols = st.columns([1.1, 8.9, 2.0])
                    
                    with cols[0]:
                        st.markdown(f"<span class='media-badge'>{media_name}</span>", unsafe_allow_html=True)
                    
                    with cols[1]:
                        st.markdown(f"<a href='{url}' target='_blank' class='title-link' onclick='fetch(\"/?click_id={article_id}\")'>{title}</a>", unsafe_allow_html=True)
                    
                    with cols[2]:
                        st.markdown(f"<span class='date-span'>🕒 {formatted_date}</span>", unsafe_allow_html=True)

                # 순수 텍스트 링크 기반 미니멀 페이지네이션
                if total_pages > 1:
                    st.divider()
                    
                    window_size = 15
                    start_p = max(1, curr_page - (window_size // 2))
                    end_p = min(total_pages, start_p + window_size - 1)
                    if end_p - start_p + 1 < window_size:
                        start_p = max(1, end_p - window_size + 1)
                        
                    page_numbers = list(range(start_p, end_p + 1))
                    
                    p_cols = st.columns([2.0] + [0.5] * len(page_numbers) + [0.5, 0.5, 2.0])
                    
                    with p_cols[0]:
                        st.write("")

                    col_idx = 1
                    for p_num in page_numbers:
                        with p_cols[col_idx]:
                            is_curr = (p_num == curr_page)
                            btn_style = "primary" if is_curr else "secondary"
                            if st.button(str(p_num), key=f"t_num_{idx}_{p_num}", type=btn_style, use_container_width=True):
                                st.session_state[page_key] = p_num
                                st.rerun()
                        col_idx += 1

                    with p_cols[col_idx]:
                        if st.button("▶", key=f"t_next_{idx}", disabled=(curr_page >= total_pages), use_container_width=True):
                            st.session_state[page_key] += 1
                            st.rerun()
                    col_idx += 1

                    with p_cols[col_idx]:
                        if st.button("▶|", key=f"t_last_{idx}", disabled=(curr_page >= total_pages), use_container_width=True):
                            st.session_state[page_key] = total_pages
                            st.rerun()

query_params = st.query_params
if "click_id" in query_params:
    try:
        c_id = int(query_params["click_id"])
        increment_click_count(c_id)
    except Exception:
        pass
