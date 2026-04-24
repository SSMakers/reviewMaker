# Local Codex Runner

이 문서는 Slack 작업 요청을 로컬 PC의 Codex CLI로 이어받아 PR까지 만드는 운영 구조를 설명합니다.

## 결론

추천 구조는 아래와 같습니다.

```text
Slack /review-task ...
-> Cloudflare Worker
-> GitHub Issue 생성
-> 내 PC의 local Codex runner가 Issue 감지
-> codex exec 실행
-> branch, code change, test, commit, push, PR
-> GitHub Slack 앱이 PR 알림 전송
```

Slack이 직접 로컬 Codex를 호출하는 것이 아니라, GitHub Issue를 작업 큐로 사용합니다. 이 방식은 PC가 꺼져 있어도 요청이 유실되지 않고, PC가 켜진 뒤 runner가 이어서 처리할 수 있습니다.

## Rich 대시보드 운영 판단

Rich 대시보드는 추가하는 편을 권장합니다. 다만 기본 상시 운영 화면으로 강제하지 않고, 선택 모드로 둡니다.

권장 모드:

```text
python scripts/local_codex_runner.py --once
python scripts/local_codex_runner.py --once --dry-run
python scripts/local_codex_runner.py --watch
python scripts/local_codex_runner.py --dashboard
```

각 모드의 역할:

| Mode | Purpose |
| --- | --- |
| `--once` | Issue 하나만 처리하고 종료합니다. 테스트와 디버깅에 가장 안전합니다. |
| `--watch` | 일정 주기로 Issue를 확인합니다. 상시 운영 기본 모드입니다. |
| `--dashboard` | Rich UI로 상태, 최근 로그, 현재 작업, 실패 원인을 보여줍니다. 처음 운영할 때 추천합니다. |

상시 운영 추천:

- 초기 1-2주는 `--dashboard`로 직접 눈으로 확인합니다.
- 안정화 후에는 `--watch`를 launchd 또는 터미널 세션으로 조용히 돌립니다.
- 로그는 `logs/local_codex_runner.log`에 항상 남깁니다.
- 상태 파일은 `.codex-runner/state.json`에 남깁니다.

## Runner 책임

local Codex runner는 아래 책임만 가집니다.

1. GitHub Issue 조회
2. 처리 대상 Issue 선별
3. 로컬 git 상태 확인
4. 작업 브랜치 생성
5. Codex CLI 실행
6. 테스트 실행
7. commit, push
8. PR 생성
9. Issue에 결과 댓글 작성

## 처리 대상 Issue 조건

처음에는 너무 똑똑하게 만들지 않고, 안전한 조건만 처리합니다.

필수 조건:

- Issue title이 `[Slack Task]`로 시작
- Issue가 open 상태
- Issue에 `codex-task` label이 있음
- Issue에 `codex-running`, `codex-done`, `codex-failed` label이 없음

Cloudflare Worker의 `/review-task`는 Issue를 만들 때 `codex-task` label을 붙이도록 확장하는 것이 좋습니다.

현재 Worker는 Issue 생성 시 `codex-task` label을 자동으로 붙입니다. label이 없으면 Worker가 먼저 생성합니다.

## 안전장치

local runner는 로컬 PC에서 코드와 git 권한을 사용하므로 안전장치가 중요합니다.

필수 안전장치:

- 한 번에 하나의 Issue만 처리
- 작업 전 `git status --short` 확인
- 허용된 untracked 파일만 무시
- `main` 직접 push 금지
- PR 생성까지만 수행
- 실패 시 Issue에 로그 요약 댓글 작성
- 실패 시 `codex-failed` label 부여
- 성공 시 `codex-done` label 부여

현재 repo에는 `selfsigned.crt`가 untracked로 남아 있을 수 있습니다. runner는 이런 파일을 사용자 소유 변경으로 보고 삭제하거나 commit하지 않습니다.

## Codex CLI 실행 예시

Codex CLI는 로컬에 설치되어 있어야 합니다. 현재 runner 기본값은 급한 수정 자동화를 우선하여 Codex를 아래 모드로 실행합니다.

```text
codex exec -C <repo-root> --dangerously-bypass-approvals-and-sandbox ...
```

즉 Codex가 로컬에서 필요한 명령을 승인 없이 실행할 수 있습니다. 그래도 runner는 최종적으로 PR을 만들 뿐이며, 사용자는 merge 단계에서 diff를 검토합니다.

권한을 낮춰 테스트하고 싶을 때는 아래 옵션을 사용합니다.

```text
python scripts/local_codex_runner.py --once --issue 123 --codex-mode workspace-write
python scripts/local_codex_runner.py --once --issue 123 --codex-mode full-auto
```

어느 폴더에서 runner를 실행해도 `git rev-parse --show-toplevel`로 repository root를 찾아 작업합니다.

runner가 Codex에 넘길 prompt는 아래처럼 구성합니다.

```text
GitHub Issue #123을 처리하세요.

작업 전 반드시 Index.md와 docs/release-process.md를 읽으세요.
main 브랜치에 직접 push하지 마세요.
작업 브랜치를 만들고, 필요한 코드/문서 수정 후 테스트를 실행하세요.
완료되면 commit, push, PR 생성까지 진행하세요.
PR 본문에는 변경 유형, version bump, 테스트 결과, 리스크를 포함하세요.

Issue 내용:
...
```

## 필요한 로컬 도구

아래 명령이 통과해야 합니다.

```text
gh auth status
codex --help
git status
```

주의: Codex 앱, 일반 터미널, IDE 터미널이 서로 다른 PATH나 GitHub 인증 상태를 가질 수 있습니다. runner를 실행할 바로 그 터미널에서 `gh auth status`가 통과해야 합니다.

## 추천 테스트 순서

처음에는 완전 자동 watch 모드로 바로 가지 않고, `--once`로 한 건씩 검증합니다.

1. Cloudflare Worker 최신 코드 배포
2. Slack에서 작업 요청

```text
/review-task README에 테스트용 문장 한 줄 추가
```

3. GitHub Issue가 생성되고 `codex-task` label이 붙었는지 확인
4. 로컬에서 runner dry run 실행

```text
python scripts/local_codex_runner.py --once --dry-run
```

5. dry run 결과에서 처리 대상 Issue가 맞는지 확인
6. 실제 실행

```text
python scripts/local_codex_runner.py --once
```

7. PR 생성 확인
8. Slack PR 알림 확인
9. PR merge
10. 문서-only 테스트라면 배포 명령은 실행하지 않음

특정 Issue만 테스트하려면 아래처럼 실행합니다.

```text
python scripts/local_codex_runner.py --once --issue 5 --dry-run
python scripts/local_codex_runner.py --once --issue 5
```

Codex에게 git 명령까지 프롬프트상 허용하고 싶으면 아래처럼 실행합니다.

```text
python scripts/local_codex_runner.py --once --issue 5 --allow-codex-git
```

처음 테스트에서 실제 Codex 실행이 부담되면, 먼저 `--dry-run`으로 runner가 올바른 Issue를 잡는지만 확인하세요.

## 운영 단계

초기:

```text
python scripts/local_codex_runner.py --dashboard
```

안정화 후:

```text
python scripts/local_codex_runner.py --watch
```

문제가 생겼을 때:

```text
python scripts/local_codex_runner.py --once --issue 123 --dry-run
```

Rich가 설치되어 있지 않으면 dashboard 모드는 아래 메시지와 함께 종료됩니다.

```text
dashboard 모드는 rich가 필요합니다. `pip install rich` 후 다시 실행하세요.
```

## 구현 상태

현재 `scripts/local_codex_runner.py`가 구현된 범위:

- `gh`와 `codex` 실행 가능 여부 확인
- `codex-task`, `codex-running`, `codex-done`, `codex-failed` label 생성
- 처리 대상 Issue 조회
- dry run
- 작업 전 git 상태 검사
- 작업 브랜치 생성
- `codex exec` 실행
- 기본 py_compile 테스트 실행
- 변경 파일 commit/push
- PR 생성
- Issue 댓글 작성
- 성공/실패 label 업데이트

현재 제한:

- 한 번에 하나의 Issue만 처리합니다.
- 기본 테스트 명령은 Python 문법 검사 중심입니다. 기능별 테스트가 생기면 `--test-command`로 교체합니다.
- `gh auth status`가 runner 실행 터미널에서 통과해야 합니다.
- `codex exec`가 실제 수정 품질을 보장하지는 않으므로 PR review는 계속 필요합니다.

## 이미지 생성용 프롬프트

아래 프롬프트를 이미지 생성 도구에 그대로 넣어 운영 흐름 이미지를 만들 수 있습니다.

```text
Create a clean modern Korean process infographic for a desktop app development automation flow.

Canvas:
- Wide landscape ratio 16:9
- White or very light gray background
- Professional SaaS operations style
- Use clear numbered cards connected by arrows
- Use blue, green, teal, and orange accents
- Avoid dark background, avoid purple-dominant palette
- Use simple line icons similar to Slack, GitHub, terminal, laptop, PR, release, download
- Korean text must be legible and large enough

Title:
"Slack 요청부터 Codex PR, 배포, 자동 업데이트까지"

Top row: Development task flow, 8 numbered steps
1. "사용자/개발자 요청"
   small text: "버그 리포트, 기능 요청, 개선 사항"
   icon: person with checklist
2. "Slack /review-task"
   small text: "작업 내용을 채널에 입력"
   icon: Slack logo style
3. "Cloudflare Worker"
   small text: "Slack 서명 검증 후 GitHub Issue 생성"
   icon: cloud function
4. "GitHub Issue"
   small text: "codex-task 라벨로 작업 큐에 등록"
   icon: GitHub issue
5. "Local Codex Runner"
   small text: "내 PC가 켜져 있으면 Issue 감지"
   icon: laptop with terminal
6. "Codex CLI 작업"
   small text: "브랜치 생성, 코드 수정, 테스트"
   icon: terminal with code
7. "Pull Request 생성"
   small text: "commit, push, PR 생성"
   icon: GitHub PR
8. "Slack PR 알림"
   small text: "GitHub Slack 앱이 채널에 알림"
   icon: Slack notification

Middle separator:
"개발자가 PR 테스트 후 승인/merge"
Use a human reviewer icon with a green check mark.

Bottom row: Release flow, 6 numbered steps
9. "Slack /review-release 배포해"
   small text: "배포 요청 입력"
   icon: Slack command
10. "Release Workflow 실행"
   small text: "GitHub Actions가 Windows/macOS 빌드"
   icon: GitHub Actions workflow
11. "Draft Release 생성"
   small text: "실행 파일, checksums, latest.json 준비"
   icon: package box
12. "최종 승인"
   small text: "GitHub Release에서 Publish"
   icon: shield with check
13. "GitHub Pages 갱신"
   small text: "다운로드 페이지와 latest.json 업데이트"
   icon: web page
14. "사용자 업데이트"
   small text: "새 exe 다운로드 또는 앱 자동 업데이트"
   icon: download arrow and app window

Side panel on the right:
Title: "운영 안전장치"
Bullets:
- "main 직접 push 금지"
- "한 번에 하나의 Issue만 처리"
- "codex-task 라벨만 자동 처리"
- "실패 시 Issue에 로그 댓글"
- "배포는 Draft Release 후 최종 승인"

Footer:
"PC가 꺼져 있으면 Issue는 대기하고, PC가 켜지면 Local Codex Runner가 처리합니다."

Style details:
- Each card has 8px radius, thin border, subtle shadow
- Arrows are clean and directional
- Use consistent icon size
- Make Korean labels accurate and not cramped
- No decorative blobs or abstract gradients
```
