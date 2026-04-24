const GITHUB_API_URL = "https://api.github.com";
const GITHUB_GRAPHQL_URL = "https://api.github.com/graphql";

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

async function githubGraphql(query, variables, env) {
  const response = await fetch(GITHUB_GRAPHQL_URL, {
    method: "POST",
    headers: {
      ...githubHeaders(env),
      "GraphQL-Features": "issues_copilot_assignment_api_support,coding_agent_model_selection",
    },
    body: JSON.stringify({ query, variables }),
  });
  const data = await response.json();
  if (!response.ok || data.errors) {
    throw new Error(`GitHub GraphQL failed: ${response.status} ${JSON.stringify(data.errors || data)}`);
  }
  return data.data;
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

async function getRepositoryContext(env) {
  const { owner, name } = repoParts(env);
  const query = `
    query RepositoryContext($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100) {
          nodes {
            login
            __typename
            ... on Bot {
              id
            }
            ... on User {
              id
            }
          }
        }
      }
    }
  `;
  const data = await githubGraphql(query, { owner, name }, env);
  const repository = data.repository;
  if (!repository) {
    throw new Error("Repository not found");
  }
  const copilot = (repository.suggestedActors.nodes || []).find((actor) => actor.login === "copilot-swe-agent");
  return { repositoryId: repository.id, copilotId: copilot?.id || null };
}

async function createIssueOnly(repositoryId, title, body, env) {
  const mutation = `
    mutation CreateIssue($repositoryId: ID!, $title: String!, $body: String!) {
      createIssue(input: { repositoryId: $repositoryId, title: $title, body: $body }) {
        issue {
          number
          url
        }
      }
    }
  `;
  const data = await githubGraphql(mutation, { repositoryId, title, body }, env);
  return data.createIssue.issue;
}

async function createCopilotIssue(repositoryId, copilotId, title, body, text, env) {
  const mutation = `
    mutation CreateCopilotIssue(
      $repositoryId: ID!,
      $copilotId: ID!,
      $title: String!,
      $body: String!,
      $baseRef: String!,
      $instructions: String!
    ) {
      createIssue(input: {
        repositoryId: $repositoryId,
        title: $title,
        body: $body,
        assigneeIds: [$copilotId],
        agentAssignment: {
          targetRepositoryId: $repositoryId,
          baseRef: $baseRef,
          customInstructions: $instructions
        }
      }) {
        issue {
          number
          url
          assignees(first: 10) {
            nodes {
              login
            }
          }
        }
      }
    }
  `;
  const instructions = [
    "Review Writer repository maintenance task.",
    "Read Index.md first, then inspect only relevant files.",
    "Follow docs/release-process.md for version bump and PR body.",
    `User request: ${text}`,
  ].join("\n");
  const data = await githubGraphql(
    mutation,
    {
      repositoryId,
      copilotId,
      title,
      body,
      baseRef: env.GITHUB_TASK_BASE_REF || "main",
      instructions,
    },
    env,
  );
  return data.createIssue.issue;
}

async function createCodingTask(text, userName, env) {
  if (!text) {
    throw new Error("작업 요청 내용이 비어 있습니다.");
  }
  const { repositoryId, copilotId } = await getRepositoryContext(env);
  const title = buildTaskTitle(text);
  const body = buildTaskBody(text, userName);
  const shouldAssignCopilot = env.COPILOT_ASSIGNMENT_ENABLED !== "false" && Boolean(copilotId);

  if (!shouldAssignCopilot) {
    const issue = await createIssueOnly(repositoryId, title, body, env);
    return { issue, assignedToCopilot: false };
  }

  const issue = await createCopilotIssue(repositoryId, copilotId, title, body, text, env);
  return { issue, assignedToCopilot: true };
}

function isTaskCommand(command, text) {
  return command.endsWith("/review-task") || text.startsWith("작업 ") || text.startsWith("수정 ");
}

function isReleaseCommand(command, text) {
  return command.endsWith("/review-release")
    && (text === "배포해" || text === "deploy" || text === "release" || text.startsWith("배포해 "));
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
        const result = await createCodingTask(taskText, userName, env);
        const assignmentText = result.assignedToCopilot
          ? "Copilot coding agent에 배정했습니다."
          : "Copilot 배정은 건너뛰고 Issue만 생성했습니다.";
        return textResponse(`작업 Issue를 생성했습니다. ${assignmentText}\n${result.issue.url}`);
      }

      if (isReleaseCommand(command, text)) {
        await triggerReleaseWorkflow(buildReleaseNotes(text, userName), env);
        return textResponse("Release workflow를 실행했습니다. GitHub Actions와 draft release를 확인해주세요.");
      }

      return textResponse([
        "사용법:",
        "/review-task README에 테스트용 주석 한 줄 추가",
        "/review-release 배포해",
      ].join("\n"));
    } catch (error) {
      return textResponse(`요청 처리 실패: ${error.message}`, 500);
    }
  },
};
