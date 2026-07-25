/**
 * ==============================================================================
 * 🚀 Cloudflare Worker: 보수 뉴스 큐레이션 100% 정시 자동 크롤링 트리거
 * ==============================================================================
 * - 갱신 주기: 스마트 가변 주기 (주간 2시간 / 야간 4시간)
 * - Cron 표현식: 0 1,3,5,7,9,11,13,17,21,23 * * *
 * - 재시도 프로토콜: 지수 백오프 (Exponential Backoff + Retries)
 *   (1차 실패 -> 10초 대기 -> 2차 실패 -> 30초 대기 -> 3차 실패 -> 2분 대기 -> 4차 실패 -> 5분 대기 -> 5차 최종 완료)
 * ==============================================================================
 */

export default {
  // 1. Cloudflare Cron Trigger 자동 수행
  async scheduled(event, env, ctx) {
    ctx.waitUntil(triggerWithExponentialBackoff(env));
  },
  
  // 2. 브라우저 접속으로 수동 즉시 테스트 가능
  async fetch(request, env, ctx) {
    const result = await triggerWithExponentialBackoff(env);
    return new Response(JSON.stringify(result, null, 2), {
      status: result.success ? 200 : 500,
      headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }
};

async function triggerWithExponentialBackoff(env) {
  const owner = "excone-web";
  const repo = "boss-news";
  const workflow = "update_news.yml";
  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;

  // 지수 백오프 대기 시간 (밀리초): 10초, 30초, 2분(120초), 5분(300초)
  const backoffDelaysMs = [10000, 30000, 120000, 300000];
  const maxAttempts = backoffDelaysMs.length + 1; // 총 5회 시도

  const token = env.GITHUB_PAT;
  if (!token) {
    const errMsg = "⚠️ GITHUB_PAT 환경 변수가 설정되지 않았습니다. Cloudflare Worker Settings > Variables에서 GITHUB_PAT를 추가해주세요.";
    console.error(errMsg);
    return { success: false, message: errMsg };
  }

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const nowKst = new Date().toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
      console.log(`[시도 ${attempt}/${maxAttempts}] GitHub Actions 크롤러 트리거 요청... (${nowKst})`);

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Accept": "application/vnd.github.v3+json",
          "User-Agent": "Cloudflare-Worker-News-Cron"
        },
        body: JSON.stringify({ ref: "main" })
      });

      // 204 No Content 또는 HTTP OK
      if (response.status === 204 || response.ok) {
        const successMsg = `✅ [성공] ${attempt}번째 시도만에 GitHub 뉴스 자동 크롤러 트리거 완료! (${nowKst})`;
        console.log(successMsg);
        return { success: true, attempt: attempt, time: nowKst, message: successMsg };
      }

      const errorText = await response.text();
      console.warn(`⚠️ [경고] ${attempt}번째 시도 실패 (HTTP ${response.status}): ${errorText}`);

    } catch (error) {
      console.error(`❌ [오류] ${attempt}번째 시도 중 네트워크 오류 발생: ${error.message}`);
    }

    // 다음 재시도가 남아있는 경우 지수 백오프 대기
    if (attempt <= backoffDelaysMs.length) {
      const waitMs = backoffDelaysMs[attempt - 1];
      const waitSec = waitMs / 1000;
      const waitDisplay = waitSec >= 60 ? `${waitSec / 60}분` : `${waitSec}초`;
      console.log(`⏱️ ${waitDisplay} 대기 후 ${attempt + 1}번째 재시도를 수행합니다...`);
      await new Promise(resolve => setTimeout(resolve, waitMs));
    }
  }

  const finalErrMsg = `🚨 [최종 실패] 총 ${maxAttempts}회 지수 백오프 시도(10s -> 30s -> 2m -> 5m) 후에도 GitHub API 호출 실패.`;
  console.error(finalErrMsg);
  return { success: false, message: finalErrMsg };
}
