# Slack Release Webhook

이 문서는 Slack에서 작업 요청과 배포 요청을 처리하는 Cloudflare Worker 연동 구조를 설명합니다.

## 현재 Slack 연동 단계

1. GitHub Slack 앱 설치 및 계정 연결
2. Slack 채널에서 `/github subscribe SSMakers/reviewMaker pulls releases deployments workflows` 실행
3. PR, release, deployment 알림을 Slack에서 확인
4. 커스텀 Slash Command `/review-task`로 작업 Issue 생성 및 Copilot coding agent 배정
5. 커스텀 Slash Command `/review-release`로 release workflow 실행

GitHub Slack 앱은 알림과 GitHub 협업 액션에 적합합니다. 다만 한국어 자연어 명령으로 작업 Issue 생성, Copilot 배정, workflow 실행을 하려면 Slack Slash Command를 받는 별도 endpoint가 필요합니다.

## GitHub Secrets

현재 GitHub Actions 빌드에는 repository secret `ENV_FILE`이 필요합니다.

`ENV_FILE`에는 빌드된 앱에 포함될 `.env` 전체 내용을 넣습니다.

```env
API_BASE_URL=https://your-api.example.com
API_TIMEOUT_SEC=10
API_UPLOAD_TIMEOUT_SEC=60
API_CA_CERT_PATH=certs/dev_ca.crt
UPDATE_LATEST_URL=https://ssmakers.github.io/reviewMaker/latest.json
```

`UPDATE_LATEST_URL`은 공개 값이라 secret일 필요는 없지만, 현재 workflow가 `.env`를 `ENV_FILE` 하나로 만들기 때문에 여기에 함께 넣는 방식이 가장 단순합니다.

## Cloudflare Worker 설정

현재 권장 방식은 Cloudflare Workers입니다. `scripts/slack_release_worker.mjs` 내용을 Worker 코드에 넣고 배포합니다.

| Name | Required | Example |
| --- | --- | --- |
| `SLACK_SIGNING_SECRET` | Yes | Slack app의 Signing Secret |
| `GITHUB_TOKEN` | Yes | GitHub fine-grained token |
| `GITHUB_REPOSITORY` | Yes | `SSMakers/reviewMaker` |
| `GITHUB_RELEASE_WORKFLOW` | No | `release.yml` |
| `GITHUB_RELEASE_REF` | No | `main` |
| `GITHUB_TASK_BASE_REF` | No | `main` |
| `COPILOT_ASSIGNMENT_ENABLED` | No | `true` |
| `SLACK_ALLOWED_USER_IDS` | No | `U123,U456` |

Cloudflare에는 `env`라는 변수 하나를 만드는 것이 아니라, 위 이름을 각각 Secret 또는 Variable로 등록합니다.

Secret으로 등록:

- `SLACK_SIGNING_SECRET`
- `GITHUB_TOKEN`
- `SLACK_ALLOWED_USER_IDS`

Variable로 등록:

- `GITHUB_REPOSITORY`
- `GITHUB_RELEASE_WORKFLOW`
- `GITHUB_RELEASE_REF`
- `GITHUB_TASK_BASE_REF`
- `COPILOT_ASSIGNMENT_ENABLED`

GitHub token은 fine-grained personal access token을 사용합니다. repository는 `SSMakers/reviewMaker`만 선택하고, repository permission은 아래처럼 부여합니다.

- `Actions`: Read and write
- `Contents`: Read and write
- `Issues`: Read and write
- `Pull requests`: Read and write

GitHub REST API의 workflow dispatch endpoint는 fine-grained token에 `Actions` write 권한이 필요합니다. Copilot coding agent에 issue를 배정하려면 GitHub API 기준으로 `Actions`, `Contents`, `Issues`, `Pull requests` read/write 권한이 필요합니다.

## Slack App 설정

1. Slack API 페이지에서 앱 생성
2. `Slash Commands`에서 `/review-task` 생성
3. `/review-task` Request URL에 Cloudflare Worker URL 입력
4. `Slash Commands`에서 `/review-release` 생성
5. `/review-release` Request URL에 같은 Cloudflare Worker URL 입력
6. 앱을 workspace에 설치

두 명령은 같은 Worker URL을 사용합니다. Worker가 Slack payload의 `command` 값을 보고 작업 요청과 배포 요청을 구분합니다.

## 작업 요청 테스트

Slack 채널에서 아래 명령을 입력합니다.

```text
/review-task README에 테스트용 주석 한 줄 추가
```

성공하면 GitHub Issue가 생성됩니다. repository에서 Copilot coding agent가 활성화되어 있고 token 권한이 충분하면 `copilot-swe-agent`에 자동 배정됩니다. Copilot은 issue를 바탕으로 branch와 PR을 생성합니다.

Copilot 배정이 불가능하면 Worker는 Issue만 생성합니다. 이 경우 GitHub issue 화면에서 Assignees에 Copilot을 수동으로 지정해 작업을 시작할 수 있습니다.

## 배포 요청 테스트

Slack 채널에서 아래 명령을 입력합니다.

```text
/review-release 배포해
```

릴리즈 노트를 함께 보내고 싶다면 아래처럼 입력합니다.

```text
/review-release 배포해 이미지 업로드 안정화 및 자동 업데이트 추가
```

성공하면 GitHub Actions의 `Release Review Program` workflow가 실행되고, 완료 후 draft release가 생성됩니다. 최종 공개는 GitHub Release 화면에서 `Publish release`를 눌러 승인합니다.
