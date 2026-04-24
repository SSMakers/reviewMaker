# Slack Operations

Review Writer 운영 채널에서 coding bot에게 작업을 요청할 때 사용하는 템플릿입니다.

## 추천 채널 운영

초기에는 하나의 채널로 시작합니다.

```text
#review-writer-dev
```

트래픽이 늘어나면 아래처럼 분리합니다.

```text
#review-writer-bugs
#review-writer-release
```

## 버그 수정 요청 템플릿

```text
[버그 수정 요청]
증상:
재현 절차:
기대 결과:
실제 결과:
첨부 파일/로그:
긴급도:
버전:
```

## 기능 구현 요청 템플릿

```text
[기능 구현 요청]
목표:
사용자 시나리오:
필수 동작:
제외 범위:
버전 bump 예상: minor / major / none
```

## Bot 작업 규칙

coding agent는 작업 전에 아래 문서를 읽습니다.

```text
1. Index.md
2. docs/release-process.md
```

작업 완료 후 bot은 PR을 만들고 Slack에 아래 형식으로 알립니다.

```text
[PR 생성 완료]
PR:
변경 유형:
버전 증가:
현재 버전:
다음 버전:
테스트:
릴리즈 노트:
리스크:
확인 요청:
```

## 작업 요청

Slack에서 coding agent에게 작업을 요청할 때는 아래 명령을 사용합니다.

```text
/review-task README에 테스트용 주석 한 줄 추가
```

이 명령은 Cloudflare Worker를 통해 GitHub Issue를 만들고, 가능하면 Copilot coding agent에 자동 배정합니다. Copilot 배정이 불가능하면 Issue만 생성되므로 GitHub에서 수동으로 Copilot을 Assignee에 추가합니다.

## 배포 요청

PR이 merge된 뒤 개발자가 Slack에서 아래처럼 요청합니다.

```text
/review-release 배포해
```

릴리즈 노트를 함께 전달하려면 아래처럼 입력합니다.

```text
/review-release 배포해 이미지 업로드 안정화 및 자동 업데이트 추가
```

이 명령은 GitHub Actions release workflow 실행 요청입니다. workflow는 draft GitHub Release를 생성합니다. 실제 사용자 공개 전 GitHub Release 화면에서 산출물과 릴리즈 노트를 확인한 뒤 `Publish release`를 눌러 최종 승인합니다.

Slack Slash Command endpoint 설정은 `docs/slack-release-webhook.md`를 참고합니다.
