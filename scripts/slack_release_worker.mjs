const GITHUB_API_URL = "https://api.github.com";

function textResponse(text, status = 200) {
  return new Response(text, {
    status,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}

function getHeader(request, name) {
  return request.headers.get(name) || request.headers.get(name.toLowerCase()) || "";
}

async function hmacSha256Hex(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return [...new Uint8Array(signature)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) {
    return false;
  }
  let result = 0;
  for (let index = 0; index < a.length; index += 1) {
    result |= a.charCodeAt(index) ^ b.charCodeAt(index);
  }
  return result === 0;
}

async function verifySlackSignature(request, body, env) {
  const timestamp = getHeader(request, "X-Slack-Request-Timestamp");
  const signature = getHeader(request, "X-Slack-Signature");
  if (!timestamp || !signature) {
    throw new Error("Missing Slack signature headers");
  }

  const requestTime = Number(timestamp);
  if (!Number.isFinite(requestTime) || Math.abs(Date.now() / 1000 - requestTime) > 60 * 5) {
    throw new Error("Slack request timestamp is too old");
  }

  const base = `v0:${timestamp}:${body}`;
  const digest = await hmacSha256Hex(env.SLACK_SIGNING_SECRET, base);
  const expected = `v0=${digest}`;
  if (!timingSafeEqual(expected, signature)) {
    throw new Error("Invalid Slack signature");
  }
}

function assertUserAllowed(userId, env) {
  if (!env.SLACK_ALLOWED_USER_IDS) {
    return;
  }
  const allowed = env.SLACK_ALLOWED_USER_IDS.split(",").map((item) => item.trim()).filter(Boolean);
  if (!allowed.includes(userId)) {
    throw new Error("이 Slack 사용자는 배포 권한이 없습니다.");
  }
}

function buildReleaseNotes(text, userName) {
  if (text === "배포해" || text === "deploy" || text === "release") {
    return `Slack 배포 요청 by ${userName}`;
  }
  return `Slack 배포 요청 by ${userName}\n\n${text}`;
}

async function triggerReleaseWorkflow(releaseNotes, env) {
  const workflowFile = env.GITHUB_RELEASE_WORKFLOW || "release.yml";
  const ref = env.GITHUB_RELEASE_REF || "main";
  const url = `${GITHUB_API_URL}/repos/${env.GITHUB_REPOSITORY}/actions/workflows/${workflowFile}/dispatches`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "Content-Type": "application/json",
      "User-Agent": "review-writer-slack-release-bot",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({
      ref,
      inputs: { release_notes: releaseNotes },
    }),
  });

  if (response.status !== 204) {
    const details = await response.text();
    throw new Error(`GitHub workflow dispatch failed: ${response.status} ${details}`);
  }
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return textResponse("Not found", 404);
    }

    try {
      const body = await request.text();
      await verifySlackSignature(request, body, env);

      const payload = new URLSearchParams(body);
      const text = (payload.get("text") || "").trim();
      const userId = payload.get("user_id") || "";
      const userName = payload.get("user_name") || userId || "unknown";

      assertUserAllowed(userId, env);

      const isReleaseCommand = text === "배포해" || text === "deploy" || text === "release" || text.startsWith("배포해 ");
      if (!isReleaseCommand) {
        return textResponse("사용법: /review-release 배포해 또는 /review-release 배포해 이번 수정 내용");
      }

      await triggerReleaseWorkflow(buildReleaseNotes(text, userName), env);
      return textResponse("Release workflow를 실행했습니다. GitHub Actions와 draft release를 확인해주세요.");
    } catch (error) {
      return textResponse(`배포 요청 처리 실패: ${error.message}`, 500);
    }
  },
};
