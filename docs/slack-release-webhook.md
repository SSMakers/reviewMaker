# Slack Release Webhook

이 문서는 Slack에서 `/review-release 배포해` 명령으로 GitHub Actions release workflow를 실행하는 구조를 설명합니다.

## 현재 Slack 연동 단계

1. GitHub Slack 앱 설치 및 계정 연결
2. Slack 채널에서 `/github subscribe SSMakers/reviewMaker pulls releases deployments workflows` 실행
3. PR, release, deployment 알림을 Slack에서 확인
4. 커스텀 Slash Command `/review-release`로 release workflow 실행

GitHub Slack 앱은 알림과 GitHub 협업 액션에 적합합니다. 다만 한국어 자연어 명령인 "배포해"를 감지해서 workflow를 실행하려면 Slack Slash Command를 받는 별도 endpoint가 필요합니다.

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

## Lambda 환경 변수

`scripts/slack_release_lambda.py`를 AWS Lambda에 올릴 때 필요한 환경 변수입니다.

| Name | Required | Example |
| --- | --- | --- |
| `SLACK_SIGNING_SECRET` | Yes | Slack app의 Signing Secret |
| `GITHUB_TOKEN` | Yes | GitHub fine-grained token |
| `GITHUB_REPOSITORY` | Yes | `SSMakers/reviewMaker` |
| `GITHUB_RELEASE_WORKFLOW` | No | `release.yml` |
| `GITHUB_RELEASE_REF` | No | `main` |
| `SLACK_ALLOWED_USER_IDS` | No | `U123,U456` |

GitHub token 권한은 Actions workflow dispatch를 실행할 수 있어야 합니다.

## Slack App 설정

1. Slack API 페이지에서 앱 생성
2. `Slash Commands`에서 `/review-release` 생성
3. Request URL에 Lambda Function URL 입력
4. 명령 설명에 `Review Writer 배포 workflow 실행` 입력
5. 앱을 workspace에 설치

## 테스트 명령

Slack 채널에서 아래 명령을 입력합니다.

```text
/review-release 배포해
```

릴리즈 노트를 함께 보내고 싶다면 아래처럼 입력합니다.

```text
/review-release 배포해 이미지 업로드 안정화 및 자동 업데이트 추가
```

성공하면 GitHub Actions의 `Release Review Program` workflow가 실행되고, 완료 후 draft release가 생성됩니다. 최종 공개는 GitHub Release 화면에서 `Publish release`를 눌러 승인합니다.
