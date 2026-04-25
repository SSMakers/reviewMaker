# Slack Release Webhook

이 문서는 Slack에서 작업 요청과 배포 요청을 처리하는 Cloudflare Worker 연동 구조를 설명합니다.

## 현재 Slack 연동 단계

1. GitHub Slack 앱 설치 및 계정 연결
2. Slack 채널에서 `/github subscribe SSMakers/reviewMaker pulls releases deployments workflows` 실행
3. PR, release, deployment 알림을 Slack에서 확인
4. 커스텀 Slash Command `/review-task`로 Codex 작업 대기 Issue 생성
5. 커스텀 Slash Command `/review-writer-release`로 release workflow 실행

GitHub Slack 앱은 알림과 GitHub 협업 액션에 적합합니다. 다만 한국어 자연어 명령으로 작업 Issue 생성과 workflow 실행을 하려면 Slack Slash Command를 받는 별도 endpoint가 필요합니다.

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

GitHub token은 fine-grained personal access token을 사용합니다. repository는 `SSMakers/reviewMaker`만 선택하고, repository permission은 아래처럼 부여합니다.

- `Actions`: Read and write
- `Issues`: Read and write

GitHub REST API의 workflow dispatch endpoint는 fine-grained token에 `Actions` write 권한이 필요합니다. `/review-task`는 GitHub Issue를 생성하므로 `Issues` write 권한이 필요합니다.

## Slack App 설정

1. Slack API 페이지에서 앱 생성
2. `Slash Commands`에서 `/review-task` 생성
3. `/review-task` Request URL에 Cloudflare Worker URL 입력
4. `Slash Commands`에서 `/review-writer-release` 생성
5. `/review-writer-release` Request URL에 같은 Cloudflare Worker URL 입력
6. 앱을 workspace에 설치

두 명령은 같은 Worker URL을 사용합니다. Worker가 Slack payload의 `command` 값을 보고 작업 요청과 배포 요청을 구분합니다.

## 작업 요청 테스트

Slack 채널에서 아래 명령을 입력합니다.

```text
/review-task README에 테스트용 주석 한 줄 추가
```

성공하면 GitHub Issue가 생성되고 Slack에 Issue URL이 반환됩니다. 이 Issue는 Codex가 작업을 이어받기 위한 접수 기록입니다.

이후 Codex에게 아래처럼 요청합니다.

```text
방금 생성된 Issue #123 처리해줘. 브랜치 만들고 수정, 테스트, PR까지 진행해줘.
```

Codex가 PR을 만들면 GitHub Slack 앱 구독 설정에 따라 PR 알림이 Slack 채널로 전달됩니다.

## 전체 플로우 테스트 순서

처음에는 배포까지 바로 가지 말고, 문서 한 줄 변경으로 PR 알림까지 확인합니다.

1. Slack에서 작업 요청

```text
/review-task README에 테스트용 문장 한 줄 추가
```

2. Slack 응답에서 GitHub Issue URL 확인
3. Codex에게 Issue 처리 요청

```text
Issue #123 처리해줘. 브랜치 만들고 수정, 테스트, PR까지 진행해줘.
```

4. GitHub PR 생성 확인
5. Slack 채널에 PR 알림이 오는지 확인
6. PR 내용을 확인하고 merge
7. 배포 테스트가 필요할 때만 `/review-writer-release 배포해 ...` 실행

주의: release workflow는 `version.py` 기준 tag를 만들기 때문에 같은 버전으로 두 번 실행하면 tag 중복으로 실패합니다. 문서-only PR 테스트에서는 배포 명령을 실행하지 않는 편이 안전합니다.

## 배포 요청 테스트

Slack 채널에서 아래 명령을 입력합니다.

```text
/review-writer-release 배포해
```

릴리즈 노트를 함께 보내고 싶다면 아래처럼 입력합니다.

```text
/review-writer-release 배포해 이미지 업로드 안정화 및 자동 업데이트 추가
```

아래 입력도 같은 배포 요청으로 처리됩니다.

```text
/review-writer-release
/review-writer-release 배포
/review-writer-release deploy
/review-writer-release release
```

성공하면 GitHub Actions의 `Release Review Program` workflow가 실행되고, 완료 후 draft release가 생성됩니다. 최종 공개는 GitHub Release 화면에서 `Publish release`를 눌러 승인합니다.

Slack 응답에 `나에게만 표시`가 붙는 경우는 ephemeral 메시지입니다. 특히 사용법 안내나 오류 메시지는 채널 전체가 아니라 명령 실행자에게만 보입니다. 배포 요청이 정상 처리되면 채널에 `Release workflow를 실행했습니다.` 메시지가 표시됩니다.
