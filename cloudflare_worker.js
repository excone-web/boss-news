/**
 * ==============================================================================
 * Cloudflare Worker: 뉴스 큐레이션 정시 자동 크롤링 트리거
 * ==============================================================================
 * - 역할: GitHub Actions workflow_dispatch 호출 (Actions schedule 지연 보완)
 * - 권장 Cron (UTC, Actions와 동일 시각대 분 맞춤):
 *     5 1,3,5,7,9,11,13,17,21,23 * * *
 * - 필수 설정 (Cloudflare Dashboard):
 *     1) 이 Worker 배포
 *     2) Triggers > Cron Triggers 에 위 표현식 등록
 *     3) Settings > Variables > Secret: GITHUB_PAT
 *        (repo 권한 있는 Fine-grained 또는 classic PAT, actions:write)
 * - 재시도: 지수 백오프 10s → 30s → 2m → 5m (최대 5회)
 * ==============================================================================
 */

const OWNER = "excone-web";
const REPO = "boss-news";
const WORKFLOW = "update_news.yml";
const BRANCH = "main";

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(triggerWithExponentialBackoff(env));
  },

  // 브라우저/헬스체크로 수동 즉시 실행: GET Worker URL
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    // /health 는 설정 상태만 확인 (트리거 없음)
    if (url.pathname === "/health") {
      return jsonResponse({
        ok: true,
        has_github_pat: Boolean(env.GITHUB_PAT),
        owner: OWNER,
        repo: REPO,
        workflow: WORKFLOW,
        branch: BRANCH
      }, 200);
    }
    const result = await triggerWithExponentialBackoff(env);
    return jsonResponse(result, result.success ? 200 : 500);
  }
};

function jsonResponse(body, status) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" }
  });
}

async function triggerWithExponentialBackoff(env) {
  const apiUrl =
    `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`;

  const backoffDelaysMs = [10000, 30000, 120000, 300000];
  const maxAttempts = backoffDelaysMs.length + 1;

  const token = env.GITHUB_PAT;
  if (!token) {
    const errMsg =
      "GITHUB_PAT 미설정. Worker Settings > Variables(Secret)에 repo+actions 권한 PAT를 추가하세요.";
    console.error(errMsg);
    return { success: false, message: errMsg };
  }

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const nowKst = new Date().toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
    try {
      console.log(`[시도 ${attempt}/${maxAttempts}] workflow_dispatch... (${nowKst})`);

      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
          "User-Agent": "Cloudflare-Worker-News-Cron"
        },
        body: JSON.stringify({ ref: BRANCH })
      });

      // 204 No Content = dispatch 성공
      if (response.status === 204 || response.ok) {
        const successMsg = `[성공] ${attempt}번째 시도 — GitHub Actions 트리거 완료 (${nowKst})`;
        console.log(successMsg);
        return { success: true, attempt, time: nowKst, message: successMsg };
      }

      const errorText = await response.text();
      console.warn(`[경고] HTTP ${response.status}: ${errorText}`);

      // 401/403/404는 재시도해도 동일 — 조기 종료
      if ([401, 403, 404].includes(response.status)) {
        return {
          success: false,
          attempt,
          time: nowKst,
          message: `인증/권한/경로 오류 HTTP ${response.status}: ${errorText}`
        };
      }
    } catch (error) {
      console.error(`[오류] 네트워크: ${error.message}`);
    }

    if (attempt <= backoffDelaysMs.length) {
      const waitMs = backoffDelaysMs[attempt - 1];
      console.log(`${waitMs / 1000}s 대기 후 재시도...`);
      await new Promise((resolve) => setTimeout(resolve, waitMs));
    }
  }

  const finalErrMsg =
    `[최종 실패] ${maxAttempts}회 지수 백오프 후에도 GitHub API 호출 실패.`;
  console.error(finalErrMsg);
  return { success: false, message: finalErrMsg };
}
