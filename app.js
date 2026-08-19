let allArticles = [];
let filteredArticles = [];
let currentPage = 1;
let itemsPerPage = 50;
let currentCategory = "전체";
let isMaster = false;

// 탭을 연 채로도 서버 갱신을 반영 (데이터 수집 주기 2h보다 짧게 폴링)
const CLIENT_REFRESH_MS = 5 * 60 * 1000;
// Actions가 main에 푸시한 JSON을 직접 읽음 → Pages 배포 지연/스킵과 무관하게 데이터 갱신
const ARTICLES_DATA_URLS = [
    "https://raw.githubusercontent.com/excone-web/boss-news/main/articles.json",
    "articles.json"
];
// 수집 중지 매체 — 잔여 articles.json도 화면에 올리지 않음
const DISABLED_OVERSEAS_MEDIA = new Set([
    "Reclaim The Net",
    "The Federalist",
    "National Review",
    "Epoch Times",
    "데일리안"
]);
const MEDIA_NAME_ALIASES = {
    "에포크타임스": ["에포크타임스", "에포크타임즈"]
};
const SKIP_TOPIC_RE = /\[(?:포토|영상|사진|오늘날씨)\]|뉴데툰|윤서인|라이온즈|랜더스|프로야구|프로축구|연주회|합창단|예술제|클래식|국악|걸그룹|K팝|K-POP|아이돌|뮤지컬/i;

function isOfftopicArticle(art) {
    if (!art) return true;
    if (DISABLED_OVERSEAS_MEDIA.has(art.media_name)) return true;
    if (art.category === "문화/연예/스포츠") return true;
    return SKIP_TOPIC_RE.test(art.title || "");
}

function mediaNameMatches(articleName, selectedMedia) {
    if (selectedMedia === "전체") return true;
    if (articleName === selectedMedia) return true;
    const aliases = MEDIA_NAME_ALIASES[selectedMedia];
    return !!(aliases && aliases.includes(articleName));
}
let refreshTimer = null;
let isLoadingArticles = false;

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    if (window.innerWidth <= 768) {
        itemsPerPage = 20;
        const selectEl = document.getElementById("itemsPerPage");
        if (selectEl) selectEl.value = "20";
    }
    if (sessionStorage.getItem("bossNews_isMaster") === "true") {
        isMaster = true;
        const loginForm = document.getElementById("masterLoginForm");
        const loggedMenu = document.getElementById("masterLoggedMenu");
        if (loginForm) loginForm.classList.add("hidden");
        if (loggedMenu) loggedMenu.classList.remove("hidden");
    }
    setupEventListeners();
    await loadArticlesData(false);
    startAutoRefresh();
}

let lastUpdatedAt = "";
let crawlIntervalHours = 2;

function updateStatusBadge(articleCount) {
    const line1 = `🟢 DB 정상가동 ( 최근 96시간 기사 ${articleCount.toLocaleString()}건 )`;
    const line2 = lastUpdatedAt
        ? `최근 갱신: ${lastUpdatedAt} · ${crawlIntervalHours}시간 주기 갱신`
        : `${crawlIntervalHours}시간 주기 갱신`;
    const badge = document.getElementById("dbStatusBadge");
    if (badge) {
        badge.innerHTML = `<span class="badge-line1">${line1}</span><span class="badge-line2">${line2}</span>`;
    }
}

/**
 * @param {boolean} isBackground  true면 백그라운드 재조회 (페이지/필터 유지, 변경 시에만 목록 갱신)
 */
async function loadArticlesData(isBackground = false) {
    if (isLoadingArticles) return;
    isLoadingArticles = true;

    try {
        const cacheKey = Date.now();
        let data = null;

        const fetched = [];
        await Promise.all(ARTICLES_DATA_URLS.map(async (baseUrl) => {
            try {
                const sep = baseUrl.includes("?") ? "&" : "?";
                const response = await fetch(baseUrl + sep + "v=" + cacheKey, {
                    cache: "no-cache"
                });
                if (!response.ok) return;
                fetched.push(await response.json());
            } catch (fetchErr) {
                console.warn("articles 소스 실패:", baseUrl, fetchErr);
            }
        }));
        if (fetched.length) {
            fetched.sort((a, b) => {
                const ta = (!Array.isArray(a) && a.updated_at) || "";
                const tb = (!Array.isArray(b) && b.updated_at) || "";
                return tb.localeCompare(ta);
            });
            data = fetched[0];
        }

        if (!data) {
            console.error("articles.json 로드 실패 (모든 소스)");
            if (!isBackground) {
                document.getElementById("dbStatusBadge").innerHTML =
                    `<span class="badge-line1">⚠️ 기사 데이터 수집 중...</span>`;
            }
            return;
        }

        let nextArticles;
        let nextUpdatedAt = lastUpdatedAt;
        let nextInterval = crawlIntervalHours;

        if (Array.isArray(data)) {
            nextArticles = data;
        } else {
            nextArticles = data.articles || [];
            nextUpdatedAt = data.updated_at || "";
            nextInterval = data.interval_hours || 2;
        }
        nextArticles = nextArticles.filter(art => !isOfftopicArticle(art));

        if (!nextUpdatedAt && nextArticles.length > 0) {
            nextUpdatedAt = (nextArticles[0].published_at || "").substring(0, 16);
        }

        const dataChanged =
            !isBackground ||
            nextUpdatedAt !== lastUpdatedAt ||
            nextArticles.length !== allArticles.length;

        if (!dataChanged) {
            return;
        }

        allArticles = nextArticles;
        lastUpdatedAt = nextUpdatedAt;
        crawlIntervalHours = nextInterval;
        updateStatusBadge(allArticles.length);

        if (isBackground) {
            applyFilters(false);
        } else {
            applyFilters(false);
            const restored = restoreAppState();
            if (!restored) {
                applyFilters(true);
            }
        }
    } catch (e) {
        console.error("데이터 통신 오류:", e);
    } finally {
        isLoadingArticles = false;
    }
}

function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(() => {
        if (document.visibilityState === "visible") {
            loadArticlesData(true);
        }
    }, CLIENT_REFRESH_MS);

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            loadArticlesData(true);
        }
    });
}

function saveAppState() {
    const state = {
        category: currentCategory,
        page: currentPage,
        media: document.getElementById("mediaSelect") ? document.getElementById("mediaSelect").value : "전체",
        search: document.getElementById("searchInput") ? document.getElementById("searchInput").value : "",
        sort: document.querySelector("input[name='sortOrder']:checked") ? document.querySelector("input[name='sortOrder']:checked").value : "latest",
        scrollTop: window.scrollY || document.documentElement.scrollTop || 0
    };
    sessionStorage.setItem("bossNews_appState", JSON.stringify(state));
}

function restoreAppState() {
    const raw = sessionStorage.getItem("bossNews_appState");
    if (!raw) return false;
    try {
        const state = JSON.parse(raw);
        sessionStorage.removeItem("bossNews_appState");

        if (state.category) {
            const tab = document.querySelector(`.tab-btn[data-category="${state.category}"]`);
            currentCategory = tab ? state.category : "전체";
            document.querySelectorAll(".tab-btn").forEach(b => {
                b.classList.toggle("active", b.getAttribute("data-category") === currentCategory);
            });
        }
        if (state.media && document.getElementById("mediaSelect")) {
            document.getElementById("mediaSelect").value = state.media;
        }
        if (state.search && document.getElementById("searchInput")) {
            document.getElementById("searchInput").value = state.search;
        }
        if (state.sort) {
            const radio = document.querySelector(`input[name='sortOrder'][value='${state.sort}']`);
            if (radio) radio.checked = true;
        }

        applyFilters(false);

        if (state.page) {
            currentPage = state.page;
            renderArticles();
        }

        if (state.scrollTop) {
            setTimeout(() => {
                window.scrollTo({ top: state.scrollTop, behavior: 'instant' });
            }, 80);
        }
        return true;
    } catch (e) {
        console.error("상태 복원 중 오류:", e);
        return false;
    }
}

function handleArticleClick(e, titleStr, mediaStr) {
    trackGAEvent('click_article', {'article_title': titleStr, 'media_name': mediaStr});
    if (window.innerWidth <= 768) {
        saveAppState();
    }
}

function setupEventListeners() {
    // 사이드바 토글 및 오버레이 관리
    const sidebar = document.getElementById("sidebar");
    const mainContainer = document.querySelector(".main-container");
    const toggleSidebarBtn = document.getElementById("toggleSidebarBtn");
    const closeSidebarBtn = document.getElementById("closeSidebarBtn");
    const sidebarOverlay = document.getElementById("sidebarOverlay");

    function openSidebar() {
        sidebar.classList.remove("collapsed");
        if (window.innerWidth <= 768) {
            sidebarOverlay.classList.add("active");
        } else {
            mainContainer.classList.remove("expanded");
        }
    }

    function closeSidebar() {
        sidebar.classList.add("collapsed");
        sidebarOverlay.classList.remove("active");
        if (window.innerWidth > 768) {
            mainContainer.classList.add("expanded");
        }
    }

    toggleSidebarBtn.addEventListener("click", () => {
        if (sidebar.classList.contains("collapsed")) {
            openSidebar();
        } else {
            closeSidebar();
        }
    });

    closeSidebarBtn.addEventListener("click", closeSidebar);
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener("click", closeSidebar);
    }

    // 모바일 접속 시 사이드바 기본 접힘 상태 적용
    if (window.innerWidth <= 768) {
        closeSidebar();
    }

    window.addEventListener("resize", () => {
        if (window.innerWidth <= 768) {
            mainContainer.style.marginLeft = "0";
            mainContainer.style.width = "100%";
        } else {
            mainContainer.style.marginLeft = "";
            mainContainer.style.width = "";
            sidebarOverlay.classList.remove("active");
        }
    });

    // 필터 변경
    document.getElementById("searchInput").addEventListener("input", applyFilters);
    document.getElementById("mediaSelect").addEventListener("change", applyFilters);
    document.getElementById("itemsPerPage").addEventListener("change", (e) => {
        itemsPerPage = parseInt(e.target.value, 10);
        currentPage = 1;
        renderArticles();
    });

    document.querySelectorAll("input[name='sortOrder']").forEach(radio => {
        radio.addEventListener("change", applyFilters);
    });

    // 사이드바 의견/피드백 보내기 버튼
    const openFeedbackBtn = document.getElementById("openFeedbackBtn");
    if (openFeedbackBtn) {
        openFeedbackBtn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.getElementById("newsListContainer").classList.add("hidden");
            document.getElementById("paginationContainer").classList.add("hidden");
            document.getElementById("categoryCaption").classList.add("hidden");
            document.getElementById("masterFeedbackSection").classList.add("hidden");
            document.getElementById("feedbackSection").classList.remove("hidden");

            trackGAEvent('select_category', { 'category_name': '의견/피드백 보내기' });

            if (window.innerWidth <= 768) {
                closeSidebar();
            }
        });
    }

    // 카테고리 탭
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            currentCategory = e.target.getAttribute("data-category");

            trackGAEvent('select_category', { 'category_name': currentCategory });

            document.getElementById("newsListContainer").classList.remove("hidden");
            document.getElementById("paginationContainer").classList.remove("hidden");
            document.getElementById("categoryCaption").classList.remove("hidden");
            document.getElementById("feedbackSection").classList.add("hidden");
            document.getElementById("masterFeedbackSection").classList.add("hidden");
            applyFilters();
        });
    });

    // 비밀번호 SHA-256 암호화 해시 함수 (소스코드 내 평문 노출 방지)
    async function hashPassword(str) {
        const encoder = new TextEncoder();
        const data = encoder.encode(str);
        const hashBuffer = await crypto.subtle.digest("SHA-256", data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    // 마스터 비밀번호 SHA-256 해시값 (maya1009 의 해시값)
    const MASTER_HASH = "5af81d6e446fdde8ffe170867ccb6327e2c1a30d0d647df249720a8edcac31d8";

    // 마스터 로그인 처리
    const masterLoginBtn = document.getElementById("masterLoginBtn");
    const masterPwInput = document.getElementById("masterPassword");
    
    async function handleMasterLogin() {
        const inputPw = masterPwInput.value;
        const authError = document.getElementById("masterAuthErrorMsg");
        const hashedInput = await hashPassword(inputPw);

        if (hashedInput === MASTER_HASH) {
            isMaster = true;
            sessionStorage.setItem("bossNews_isMaster", "true");
            if (authError) authError.innerText = "";
            document.getElementById("masterLoginForm").classList.add("hidden");
            document.getElementById("masterLoggedMenu").classList.remove("hidden");
            masterPwInput.value = "";
            showMasterFeedbackView();
            trackGAEvent('master_login', { 'status': 'success' });
        } else {
            if (authError) {
                authError.innerText = "비밀번호가 일치하지 않습니다.";
                authError.style.color = "#dc2626";
            }
        }
    }

    if (masterLoginBtn) {
        masterLoginBtn.addEventListener("click", handleMasterLogin);
    }
    if (masterPwInput) {
        masterPwInput.addEventListener("keyup", (e) => {
            if (e.key === "Enter") handleMasterLogin();
        });
    }

    // 마스터 전용 메뉴 버튼 이벤트
    const openMasterFeedbackBtn = document.getElementById("openMasterFeedbackBtn");
    if (openMasterFeedbackBtn) {
        openMasterFeedbackBtn.addEventListener("click", () => {
            showMasterFeedbackView();
        });
    }

    const closeMasterFeedbackBtn = document.getElementById("closeMasterFeedbackBtn");
    if (closeMasterFeedbackBtn) {
        closeMasterFeedbackBtn.addEventListener("click", () => {
            document.getElementById("masterFeedbackSection").classList.add("hidden");
            document.getElementById("newsListContainer").classList.remove("hidden");
            document.getElementById("paginationContainer").classList.remove("hidden");
            document.getElementById("categoryCaption").classList.remove("hidden");
            const activeTab = document.querySelector(".tab-btn[data-category='" + currentCategory + "']");
            if (activeTab) activeTab.classList.add("active");
            applyFilters();
        });
    }

    const masterLogoutBtn = document.getElementById("masterLogoutBtn");
    if (masterLogoutBtn) {
        masterLogoutBtn.addEventListener("click", () => {
            isMaster = false;
            sessionStorage.removeItem("bossNews_isMaster");
            document.getElementById("masterLoggedMenu").classList.add("hidden");
            document.getElementById("masterLoginForm").classList.remove("hidden");
            document.getElementById("masterFeedbackSection").classList.add("hidden");
            document.getElementById("newsListContainer").classList.remove("hidden");
            document.getElementById("paginationContainer").classList.remove("hidden");
            document.getElementById("categoryCaption").classList.remove("hidden");
            const activeTab = document.querySelector(".tab-btn[data-category='" + currentCategory + "']");
            if (activeTab) activeTab.classList.add("active");
            applyFilters();
        });
    }

    // 피드백 폼 제출
    document.getElementById("feedbackForm").addEventListener("submit", (e) => {
        e.preventDefault();
        const fType = document.getElementById("feedbackType").value;
        const fUser = document.getElementById("feedbackUser").value || "익명 사용자";
        const fContent = document.getElementById("feedbackContent").value;

        if (!fContent.trim()) {
            alert("피드백 내용을 입력해주세요.");
            return;
        }

        const feedbacks = JSON.parse(localStorage.getItem("user_feedbacks") || "[]");
        feedbacks.unshift({
            id: Date.now(),
            type: fType,
            user: fUser,
            content: fContent,
            date: new Date().toLocaleString("ko-KR")
        });
        localStorage.setItem("user_feedbacks", JSON.stringify(feedbacks));

        document.getElementById("feedbackContent").value = "";
        document.getElementById("feedbackSubmitMsg").innerText = "소중한 의견이 성공적으로 접수되었습니다! 감사합니다.";
        trackGAEvent('submit_feedback', { 'feedback_type': fType });
        if (isMaster) renderMasterFeedbacks();
    });
}

function trackGAEvent(eventName, params) {
    if (typeof window.gtag === 'function') {
        window.gtag('event', eventName, params);
    }
}

function applyFilters(resetPage = true) {
    const keyword = document.getElementById("searchInput").value.trim().toLowerCase();
    const selectedMedia = document.getElementById("mediaSelect").value;
    const sortOrder = document.querySelector("input[name='sortOrder']:checked").value;

    if (keyword) {
        trackGAEvent('search', { 'search_term': keyword });
    }

    filteredArticles = allArticles.filter(art => {
        let matchCat;
        if (isOfftopicArticle(art)) {
            return false;
        }
        if (currentCategory === "전체") {
            matchCat = true;
        } else {
            matchCat = art.category === currentCategory;
        }
        const matchMedia = mediaNameMatches(art.media_name, selectedMedia);
        const matchKeyword = !keyword || (art.title && art.title.toLowerCase().includes(keyword));
        return matchCat && matchMedia && matchKeyword;
    });

    if (sortOrder === "popular") {
        filteredArticles.sort((a, b) => ((b.click_count || 0) * 2 + (b.like_count || 0) * 5) - ((a.click_count || 0) * 2 + (a.like_count || 0) * 5));
    } else {
        filteredArticles.sort((a, b) => (b.published_at || "").localeCompare(a.published_at || ""));
    }

    if (resetPage) {
        currentPage = 1;
    }
    renderArticles();
}

function formatDateSmart(pubDateStr) {
    if (!pubDateStr) return "";
    const clean = pubDateStr.substring(0, 16); // "2026-07-25 13:21"
    const parts = clean.split(" ");
    if (parts.length < 2) return clean;

    const datePart = parts[0]; // "2026-07-25"
    const timePart = parts[1]; // "13:21"

    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const todayStr = `${year}-${month}-${day}`;

    if (datePart === todayStr) {
        return timePart; // 오늘 기사는 "13:21"
    } else {
        const monthDay = datePart.substring(5).replace("-", "."); // "07.24"
        return `${monthDay} ${timePart}`; // 이전 기사는 "07.24 13:21"
    }
}

function renderArticles() {
    const newsContainer = document.getElementById("newsListContainer");
    const captionEl = document.getElementById("categoryCaption");
    const totalCount = filteredArticles.length;
    const totalPages = Math.max(1, Math.ceil(totalCount / itemsPerPage));

    captionEl.innerHTML = `<strong>[${currentCategory}]</strong> 최근 96시간 기사 총 <strong>${totalCount.toLocaleString()}</strong> 개 (페이지: <strong>${currentPage} / ${totalPages}</strong>)`;

    if (totalCount === 0) {
        newsContainer.innerHTML = `<div style="padding: 20px; background: #fffbeb; border: 1px solid #fef3c7; color: #b45309; border-radius: 6px;">해당 조건에 일치하는 최근 96시간 이내 수집 기사가 없습니다.</div>`;
        renderPagination(1);
        return;
    }

    const startIdx = (currentPage - 1) * itemsPerPage;
    const pageData = filteredArticles.slice(startIdx, startIdx + itemsPerPage);

    const isMobile = window.innerWidth <= 768;
    const linkTarget = isMobile ? "_self" : "_blank";

    let html = "";
    pageData.forEach(item => {
        const fullDate = (item.published_at || "").substring(0, 16);
        const smartDate = formatDateSmart(item.published_at);
        const titleSafe = escapeHtml(item.title);
        const mediaSafe = escapeHtml(item.media_name || "언론사");
        const titleEscapedForJs = titleSafe.replace(/'/g, "\\'").replace(/"/g, "&quot;");
        html += `
            <div class="article-row">
                <div class="article-row-meta">
                    <span class="media-badge">${mediaSafe}</span>
                    <span class="date-span mobile-only-date">${smartDate}</span>
                </div>
                <a href="${item.url}" target="${linkTarget}" class="title-link" title="${titleSafe}" onclick="handleArticleClick(event, '${titleEscapedForJs}', '${mediaSafe}')">${titleSafe}</a>
                <span class="date-span desktop-only-date">🕒 ${fullDate}</span>
            </div>
        `;
    });

    newsContainer.innerHTML = html;
    renderPagination(totalPages);
}

// 100% 순수 인라인 텍스트 기반 미니멀 단일 행 페이지네이션
function renderPagination(totalPages) {
    const pagContainer = document.getElementById("paginationContainer");
    if (totalPages <= 1) {
        pagContainer.innerHTML = "";
        return;
    }

    const isMobile = window.innerWidth <= 768;
    const windowSize = isMobile ? 7 : 15;
    let startP = Math.max(1, currentPage - Math.floor(windowSize / 2));
    let endP = Math.min(totalPages, startP + windowSize - 1);
    if (endP - startP + 1 < windowSize) {
        startP = Math.max(1, endP - windowSize + 1);
    }

    let html = "";

    if (currentPage > 1) {
        html += `<button class="page-link" onclick="goToPage(1)">|◀</button>`;
        html += `<button class="page-link" onclick="goToPage(${currentPage - 1})">◀</button>`;
    }

    for (let p = startP; p <= endP; p++) {
        const isActive = (p === currentPage) ? "active" : "";
        html += `<button class="page-link ${isActive}" onclick="goToPage(${p})">${p}</button>`;
    }

    if (currentPage < totalPages) {
        html += `<button class="page-link" onclick="goToPage(${currentPage + 1})">▶</button>`;
        html += `<button class="page-link" onclick="goToPage(${totalPages})">▶|</button>`;
    }

    pagContainer.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    renderArticles();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showMasterFeedbackView() {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.getElementById("newsListContainer").classList.add("hidden");
    document.getElementById("paginationContainer").classList.add("hidden");
    document.getElementById("categoryCaption").classList.add("hidden");
    document.getElementById("feedbackSection").classList.add("hidden");
    document.getElementById("masterFeedbackSection").classList.remove("hidden");
    renderMasterFeedbacks();

    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (window.innerWidth <= 768) {
        const sidebar = document.getElementById("sidebar");
        const sidebarOverlay = document.getElementById("sidebarOverlay");
        if (sidebar) sidebar.classList.add("collapsed");
        if (sidebarOverlay) sidebarOverlay.classList.remove("active");
    }
}

function renderMasterFeedbacks() {
    const listEl = document.getElementById("feedbackList");
    const feedbacks = JSON.parse(localStorage.getItem("user_feedbacks") || "[]");

    if (feedbacks.length === 0) {
        listEl.innerHTML = `
            <div style="padding: 24px; text-align: center; background: #ffffff; border-radius: 6px; border: 1px solid #e2e8f0; color: #64748b;">
                현재 접수된 피드백이 없습니다.
            </div>
        `;
        return;
    }

    let html = `<p style="margin-bottom: 12px; font-weight: 600; color: #334155;">총 <strong>${feedbacks.length}</strong> 건의 접수된 피드백이 있습니다.</p>`;
    feedbacks.forEach(fb => {
        const typeBg = fb.type === "버그 신고" ? "#fef2f2" : "#f0fdf4";
        const typeColor = fb.type === "버그 신고" ? "#991b1b" : "#166534";
        html += `
            <div style="padding: 14px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
                    <div>
                        <span style="background: ${typeBg}; color: ${typeColor}; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem;">${escapeHtml(fb.type)}</span>
                        <span style="font-size: 0.85rem; color: #64748b; margin-left: 8px;">작성자: <strong>${escapeHtml(fb.user)}</strong></span>
                    </div>
                    <span style="font-size: 0.78rem; color: #94a3b8;">${fb.date}</span>
                </div>
                <p style="margin: 8px 0; color: #1e293b; line-height: 1.5; white-space: pre-wrap; font-size: 0.92rem;">${escapeHtml(fb.content)}</p>
                <div style="text-align: right; margin-top: 6px;">
                    <button onclick="deleteFeedback(${fb.id})" style="color: #dc2626; background: #fff1f2; border: 1px solid #fecdd3; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.78rem; font-weight: 600;">🗑️ 삭제</button>
                </div>
            </div>
        `;
    });
    listEl.innerHTML = html;
}

function deleteFeedback(id) {
    let feedbacks = JSON.parse(localStorage.getItem("user_feedbacks") || "[]");
    feedbacks = feedbacks.filter(f => f.id !== id);
    localStorage.setItem("user_feedbacks", JSON.stringify(feedbacks));
    renderMasterFeedbacks();
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
