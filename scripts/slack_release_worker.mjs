const GITHUB_API_URL = "https://api.github.com";
const CODEX_TASK_LABEL = "codex-task";

function textResponse(text, status = 200) {
  return new Response(text, {
    status,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}

function slackResponse(text, { inChannel = false, status = 200 } = {}) {
  return new Response(JSON.stringify({
    response_type: inChannel ? "in_channel" : "ephemeral",
    text,
  }), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
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

function truncateForSlack(text, maxLength = 900) {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 3)}...`;
}

function githubHeaders(env) {
  return {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${env.GITHUB_TOKEN}`,
    "Content-Type": "application/json",
    "User-Agent": "review-writer-slack-ops-bot",
    "X-GitHub-Api-Version": "2022-11-28",
  };
}

async function triggerReleaseWorkflow(releaseNotes, env) {
  const workflowFile = env.GITHUB_RELEASE_WORKFLOW || "release.yml";
  const ref = env.GITHUB_RELEASE_REF || "main";
  const url = `${GITHUB_API_URL}/repos/${env.GITHUB_REPOSITORY}/actions/workflows/${workflowFile}/dispatches`;
  const response = await fetch(url, {
    method: "POST",
    headers: githubHeaders(env),
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

function repoParts(env) {
  const [owner, name] = env.GITHUB_REPOSITORY.split("/");
  if (!owner || !name) {
    throw new Error("GITHUB_REPOSITORY must be owner/repo");
  }
  return { owner, name };
}

function buildTaskTitle(text) {
  const normalized = text.replace(/\s+/g, " ").trim();
  const cleaned = normalized.replace(/^(작업|수정|버그|기능|task)\s*[:：-]?\s*/i, "");
  return `[Slack Task] ${cleaned.slice(0, 80) || "Review Writer 작업 요청"}`;
}

function buildTaskBody(text, userName) {
  return [
    "## Slack 작업 요청",
    "",
    text,
    "",
    "## 요청자",
    "",
    `Slack: ${userName}`,
    "",
    "## Coding agent 작업 규칙",
    "",
    "- 작업 시작 전 `Index.md`와 `docs/release-process.md`를 먼저 확인합니다.",
    "- 변경 유형에 맞게 `version.py` bump 필요 여부를 판단합니다.",
    "- 코드 변경 시 관련 문서와 `Index.md`를 함께 업데이트합니다.",
    "- 테스트 또는 최소 검증 결과를 PR 본문에 기록합니다.",
    "- 완료 후 PR을 만들고 리뷰어 확인을 요청합니다.",
  ].join("\n");
}

async function ensureCodexTaskLabel(env) {
  const { owner, name } = repoParts(env);
  const url = `${GITHUB_API_URL}/repos/${owner}/${name}/labels/${encodeURIComponent(CODEX_TASK_LABEL)}`;
  const existing = await fetch(url, { headers: githubHeaders(env) });
  if (existing.status === 200) {
    return;
  }
  if (existing.status !== 404) {
    const details = await existing.text();
    throw new Error(`GitHub label lookup failed: ${existing.status} ${details}`);
  }

  const create = await fetch(`${GITHUB_API_URL}/repos/${owner}/${name}/labels`, {
    method: "POST",
    headers: githubHeaders(env),
    body: JSON.stringify({
      name: CODEX_TASK_LABEL,
      color: "2563eb",
      description: "Local Codex runner task queue",
    }),
  });
  if (![200, 201].includes(create.status)) {
    const details = await create.text();
    throw new Error(`GitHub label create failed: ${create.status} ${details}`);
  }
}

async function createTaskIssue(title, body, env) {
  await ensureCodexTaskLabel(env);

  const { owner, name } = repoParts(env);
  const response = await fetch(`${GITHUB_API_URL}/repos/${owner}/${name}/issues`, {
    method: "POST",
    headers: githubHeaders(env),
    body: JSON.stringify({
      title,
      body,
      labels: [CODEX_TASK_LABEL],
    }),
  });
  const data = await response.json();
  if (![200, 201].includes(response.status)) {
    throw new Error(`GitHub issue create failed: ${response.status} ${JSON.stringify(data)}`);
  }
  return data;
}

async function createCodingTask(text, userName, env) {
  if (!text) {
    throw new Error("작업 요청 내용이 비어 있습니다.");
  }
  const title = buildTaskTitle(text);
  const body = buildTaskBody(text, userName);
  return createTaskIssue(title, body, env);
}

function isTaskCommand(command, text) {
  return command.endsWith("/review-task") || text.startsWith("작업 ") || text.startsWith("수정 ");
}

function isReleaseCommand(command, text) {
  if (!command.endsWith("/review-release")) {
    return false;
  }

  const normalizedText = text.replace(/\s+/g, " ").trim().toLowerCase();
  return normalizedText === ""
    || normalizedText === "배포"
    || normalizedText === "배포해"
    || normalizedText === "배포 해"
    || normalizedText === "deploy"
    || normalizedText === "release"
    || normalizedText.startsWith("배포 ")
    || normalizedText.startsWith("배포해 ")
    || normalizedText.startsWith("deploy ")
    || normalizedText.startsWith("release ");
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
      const command = payload.get("command") || "";
      const userId = payload.get("user_id") || "";
      const userName = payload.get("user_name") || userId || "unknown";

      assertUserAllowed(userId, env);

      if (isTaskCommand(command, text)) {
        const taskText = command.endsWith("/review-task") ? text : text.replace(/^(작업|수정)\s+/, "");
        const issue = await createCodingTask(taskText, userName, env);
        const issueUrl = issue.html_url || `https://github.com/${env.GITHUB_REPOSITORY}/issues/${issue.number}`;
        return slackResponse([
          "Codex 작업 대기 Issue를 생성했습니다.",
          "",
          `요청자: ${userName}`,
          `요청 내용: ${truncateForSlack(taskText)}`,
          `Issue: ${issueUrl}`,
          "",
          `다음 단계: Local Codex Runner가 켜져 있으면 Issue #${issue.number}를 자동 처리합니다.`,
        ].join("\n"), { inChannel: true });
      }

      if (isReleaseCommand(command, text)) {
        await triggerReleaseWorkflow(buildReleaseNotes(text, userName), env);
        return slackResponse([
          "Release workflow를 실행했습니다.",
          "",
          `요청자: ${userName}`,
          `요청 내용: ${truncateForSlack(text)}`,
          "GitHub Actions와 draft release를 확인해주세요.",
        ].join("\n"), { inChannel: true });
      }

      return slackResponse([
        "사용법:",
        "/review-task README에 테스트용 주석 한 줄 추가",
        "/review-release 배포해",
      ].join("\n"));
    } catch (error) {
      return slackResponse(`요청 처리 실패: ${error.message}`, { status: 500 });
    }
  },
};
