let allArticles = [];
let filteredArticles = [];
let currentPage = 1;
let itemsPerPage = 50;
let currentCategory = "전체";
let isMaster = false;

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    setupEventListeners();
    await loadArticlesData();
}

async function loadArticlesData() {
    try {
        const response = await fetch("articles.json?t=" + new Date().getTime());
        if (response.ok) {
            allArticles = await response.json();
            document.getElementById("dbStatusBadge").innerText = `🟢 DB 정상가동 (최근 96시간 기사 ${allArticles.length.toLocaleString()}건)`;
        } else {
            console.error("articles.json 로드 실패");
            document.getElementById("dbStatusBadge").innerText = "⚠️ 기사 데이터 수집 중...";
        }
    } catch (e) {
        console.error("데이터 통신 오류:", e);
    }
    applyFilters();
}

function setupEventListeners() {
    // 사이드바 토글
    const sidebar = document.getElementById("sidebar");
    const mainContainer = document.querySelector(".main-container");
    const toggleSidebarBtn = document.getElementById("toggleSidebarBtn");
    const closeSidebarBtn = document.getElementById("closeSidebarBtn");

    toggleSidebarBtn.addEventListener("click", () => {
        sidebar.classList.toggle("collapsed");
        mainContainer.classList.toggle("expanded");
    });

    closeSidebarBtn.addEventListener("click", () => {
        sidebar.classList.add("collapsed");
        mainContainer.classList.add("expanded");
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

    // 카테고리 탭
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            currentCategory = e.target.getAttribute("data-category");

            trackGAEvent('select_category', { 'category_name': currentCategory });

            if (currentCategory === "💡 의견/피드백 보내기") {
                document.getElementById("newsListContainer").classList.add("hidden");
                document.getElementById("paginationContainer").classList.add("hidden");
                document.getElementById("categoryCaption").classList.add("hidden");
                document.getElementById("feedbackSection").classList.remove("hidden");
            } else {
                document.getElementById("newsListContainer").classList.remove("hidden");
                document.getElementById("paginationContainer").classList.remove("hidden");
                document.getElementById("categoryCaption").classList.remove("hidden");
                document.getElementById("feedbackSection").classList.add("hidden");
                applyFilters();
            }
        });
    });

    // 마스터 로그인 (비밀번호: maya1009)
    document.getElementById("masterLoginBtn").addEventListener("click", () => {
        const inputPw = document.getElementById("masterPassword").value;
        if (inputPw === "maya1009") {
            isMaster = true;
            document.getElementById("masterAuthMsg").innerText = "🔓 마스터 인증 성공!";
            document.getElementById("masterAuthMsg").style.color = "#166534";
            document.getElementById("masterFeedbackSection").classList.remove("hidden");
            renderMasterFeedbacks();
            trackGAEvent('master_login', { 'status': 'success' });
        } else {
            document.getElementById("masterAuthMsg").innerText = "비밀번호가 일치하지 않습니다.";
            document.getElementById("masterAuthMsg").style.color = "#dc2626";
        }
    });

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

function applyFilters() {
    const keyword = document.getElementById("searchInput").value.trim().toLowerCase();
    const selectedMedia = document.getElementById("mediaSelect").value;
    const sortOrder = document.querySelector("input[name='sortOrder']:checked").value;

    if (keyword) {
        trackGAEvent('search', { 'search_term': keyword });
    }

    filteredArticles = allArticles.filter(art => {
        const matchCat = (currentCategory === "전체") || (art.category === currentCategory);
        const matchMedia = (selectedMedia === "전체") || (art.media_name === selectedMedia);
        const matchKeyword = !keyword || (art.title && art.title.toLowerCase().includes(keyword));
        return matchCat && matchMedia && matchKeyword;
    });

    if (sortOrder === "popular") {
        filteredArticles.sort((a, b) => ((b.click_count || 0) * 2 + (b.like_count || 0) * 5) - ((a.click_count || 0) * 2 + (a.like_count || 0) * 5));
    } else {
        filteredArticles.sort((a, b) => (b.published_at || "").localeCompare(a.published_at || ""));
    }

    currentPage = 1;
    renderArticles();
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

    let html = "";
    pageData.forEach(item => {
        const pubDate = (item.published_at || "").substring(0, 16);
        const titleSafe = escapeHtml(item.title);
        const mediaSafe = escapeHtml(item.media_name || "언론사");
        html += `
            <div class="article-row">
                <span class="media-badge">${mediaSafe}</span>
                <a href="${item.url}" target="_blank" class="title-link" onclick="trackGAEvent('click_article', {'article_title': '${titleSafe.replace(/'/g, "\\'")}', 'media_name': '${mediaSafe}'})">${titleSafe}</a>
                <span class="date-span">🕒 ${pubDate}</span>
            </div>
        `;
    });

    newsContainer.innerHTML = html;
    renderPagination(totalPages);
}

// 100% 순수 인라인 텍스트 기반 미니멀 페이지네이션
function renderPagination(totalPages) {
    const pagContainer = document.getElementById("paginationContainer");
    if (totalPages <= 1) {
        pagContainer.innerHTML = "";
        return;
    }

    const windowSize = 15;
    let startP = Math.max(1, currentPage - Math.floor(windowSize / 2));
    let endP = Math.min(totalPages, startP + windowSize - 1);
    if (endP - startP + 1 < windowSize) {
        startP = Math.max(1, endP - windowSize + 1);
    }

    let html = "";
    
    for (let p = startP; p <= endP; p++) {
        const isActive = (p === currentPage) ? "active" : "";
        html += `<button class="page-link ${isActive}" onclick="goToPage(${p})">${p}</button> `;
    }

    if (currentPage < totalPages) {
        html += `<button class="page-link" onclick="goToPage(${currentPage + 1})">▶</button> `;
        html += `<button class="page-link" onclick="goToPage(${totalPages})">▶|</button>`;
    } else {
        html += `<button class="page-link disabled">▶</button> `;
        html += `<button class="page-link disabled">▶|</button>`;
    }

    pagContainer.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    renderArticles();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function renderMasterFeedbacks() {
    const listEl = document.getElementById("feedbackList");
    const feedbacks = JSON.parse(localStorage.getItem("user_feedbacks") || "[]");

    if (feedbacks.length === 0) {
        listEl.innerHTML = "<p>접수된 피드백이 없습니다.</p>";
        return;
    }

    let html = "";
    feedbacks.forEach(fb => {
        html += `
            <div style="padding: 12px; border-bottom: 1px solid #e2e8f0;">
                <strong>[${fb.type}]</strong> <small>${fb.date}</small> - <em>${escapeHtml(fb.user)}</em>
                <p style="margin-top: 4px; color: #475569;">${escapeHtml(fb.content)}</p>
                <button onclick="deleteFeedback(${fb.id})" style="color: #dc2626; background: none; border: none; cursor: pointer; font-size: 0.8rem;">🗑️ 피드백 삭제</button>
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
