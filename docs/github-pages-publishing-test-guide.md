# GitHub Pages 배포 및 업데이트 테스트 가이드

이 문서는 Review Writer 배포 후 GitHub Pages와 앱 자동 업데이트가 정상 동작하는지 확인하는 절차입니다.

## 배포 구조

- 실행 파일은 GitHub Releases에 업로드합니다.
- GitHub Pages는 다운로드 페이지와 `latest.json`만 제공합니다.
- 앱은 실행 시 `latest.json`을 확인하고 현재 `version.py`보다 높은 버전이면 업데이트 알림을 표시합니다.

## 배포 전 확인

1. `version.py` 버전이 변경 유형에 맞게 올라갔는지 확인합니다.
2. PR 본문에 테스트 결과와 릴리즈 노트가 적혀 있는지 확인합니다.
3. PR을 `main`에 merge합니다.
4. GitHub Actions 기본 빌드가 통과했는지 확인합니다.

## Release workflow 실행

Slack에서 아래 명령을 실행합니다.

```text
/review-writer-release 배포해 변경 요약 입력
```

이 명령은 GitHub Actions의 `release.yml` workflow를 실행합니다.

## Draft Release 확인

GitHub의 Releases 화면에서 draft release를 열고 아래 항목을 확인합니다.

- tag가 `version.py`와 같은지
- Windows 실행 파일이 첨부되어 있는지
- macOS zip 파일이 첨부되어 있는지
- `latest.json`이 첨부되어 있는지
- 릴리즈 노트가 사용자에게 보여도 되는 내용인지

문제가 없다면 `Publish release`를 누릅니다.

## GitHub Pages 확인

Release를 publish하면 `pages-on-release.yml` workflow가 실행됩니다.

확인 URL:

```text
https://ssmakers.github.io/reviewMaker/
https://ssmakers.github.io/reviewMaker/latest.json
```

확인 항목:

- 다운로드 페이지가 열리는지
- Windows 다운로드 버튼이 release asset을 가리키는지
- macOS 다운로드 버튼이 release asset을 가리키는지
- `latest.json`의 `version`이 배포 버전과 같은지
- `latest.json`의 `windows.url`, `macos.url`이 실제 다운로드 가능한 URL인지
- `sha256` 값이 비어 있지 않은지

## 앱 자동 업데이트 테스트

1. 이전 버전 앱을 실행합니다.
2. 앱 로그에서 `업데이트 확인 시작` 메시지를 확인합니다.
3. 새 버전 알림창이 표시되는지 확인합니다.
4. 업데이트를 승인합니다.
5. 다운로드가 완료되고 앱이 재시작되는지 확인합니다.
6. 재실행 후 로그인 화면의 버전이 최신 버전인지 확인합니다.

## 실패 시 확인

### `latest.json`이 404인 경우

- Release가 아직 publish되지 않았을 수 있습니다.
- `pages-on-release.yml` workflow가 실패했을 수 있습니다.
- GitHub Pages 설정이 `GitHub Actions` 배포 방식인지 확인합니다.

### 업데이트 알림이 뜨지 않는 경우

- `version.py`보다 `latest.json.version`이 높은지 확인합니다.
- 앱의 `UPDATE_LATEST_URL` 값이 올바른지 확인합니다.
- `latest.json`이 브라우저에서 열리는지 확인합니다.

### 다운로드가 실패하는 경우

- release asset URL이 브라우저에서 다운로드되는지 확인합니다.
- `sha256` 값이 release asset과 일치하는지 확인합니다.
- 회사/고객 PC의 보안 정책이 GitHub 다운로드를 막는지 확인합니다.

## 배포 성공 기준

- GitHub Release가 publish 상태입니다.
- GitHub Pages 다운로드 페이지가 최신 release asset을 가리킵니다.
- `latest.json`의 버전과 URL이 최신 release와 일치합니다.
- 이전 버전 앱에서 업데이트 알림이 표시됩니다.
- 사용자가 업데이트 승인 후 새 버전 앱을 실행할 수 있습니다.
