# Release Process

이 문서는 Review Writer의 버그 수정, 기능 추가, 버전 증가, PR 승인, 배포 승인 흐름을 정의합니다. 모든 개발자와 coding bot은 이 규칙을 따릅니다.

## 핵심 원칙

- Windows와 macOS는 항상 같은 앱 버전을 사용합니다.
- 버전의 단일 기준은 `version.py`입니다.
- Git tag, GitHub Release, Pages `latest.json`, 실행 파일명은 모두 같은 버전을 사용합니다.
- PR 승인과 배포 승인은 다른 의미입니다.
  - PR 승인: 코드가 `main`에 들어가도 된다는 승인
  - 배포 승인: 사용자가 다운로드할 실행 파일로 공개해도 된다는 승인
- `main` 브랜치의 기본값은 배포 가능한 상태여야 합니다. `IS_DEBUG=True` 같은 개발 설정은 main에 남기지 않습니다.

## 버전 규칙

Semantic Versioning 스타일을 사용합니다.

| 변경 유형 | 버전 증가 | 예시 |
| --- | --- | --- |
| 버그 수정 | PATCH | `1.0.0 -> 1.0.1` |
| 기능 추가 | MINOR | `1.0.1 -> 1.1.0` |
| 호환성 깨지는 변경 | MAJOR | `1.1.0 -> 2.0.0` |

예외적으로 문서만 변경하거나 내부 운영 문서만 수정하는 PR은 버전을 올리지 않을 수 있습니다.

## 작업 요청별 기본 흐름

버그 수정과 기능 구현은 같은 운영 흐름을 따릅니다. 차이는 버전 증가 기준뿐입니다.

```text
1. 사용자 또는 개발자가 버그/기능 요청을 전달
2. 개발자가 Slack에서 coding bot에게 작업 요청
3. coding bot이 작업 브랜치 생성
4. coding bot이 코드 수정, 테스트, 버전 bump 수행
5. coding bot이 PR 생성
6. coding bot이 Slack으로 PR 링크와 요약 알림
7. 개발자가 PR artifact 또는 로컬 빌드로 테스트
8. 개발자가 PR 승인 및 merge
9. 개발자가 Slack에서 "배포해" 명령
10. bot이 GitHub Actions release workflow를 workflow_dispatch로 실행
11. GitHub Actions가 draft GitHub Release를 생성
12. 개발자가 GitHub Release 화면에서 산출물, 버전, 릴리즈 노트를 확인
13. 개발자가 Publish release를 눌러 최종 배포 승인
14. Release published 이벤트가 Pages latest metadata와 다운로드 페이지를 갱신
```

## PR에 반드시 포함할 내용

coding bot은 PR 본문에 아래 내용을 포함해야 합니다.

```text
Change type: bugfix | feature | breaking | docs | internal
Version bump: patch | minor | major | none
Current version: x.y.z
Next version: x.y.z
Tested:
- ...
Release notes:
- ...
Risk:
- ...
```

## 버전 bump 위치

배포되는 코드 변경 PR은 `version.py`를 함께 수정합니다.

예시:

```python
class Version:
    MAJOR = 1
    MINOR = 0
    PATCH = 1
```

배포 workflow는 `version.py`를 읽어 다음 산출물을 같은 버전으로 생성합니다.

```text
Git tag: v1.0.1
GitHub Release: v1.0.1
Windows artifact: Review_Program_v1.0.1.exe
macOS artifact: Review_Program_v1.0.1_macOS.zip
Pages metadata: latest.json version = 1.0.1
```

## GitHub Pages와 자동 업데이트

실행 파일 자체는 GitHub Pages에 두지 않는 것을 기본 정책으로 합니다.

- GitHub Releases: `.exe`, macOS zip/dmg, checksum, release notes 보관
- GitHub Pages: 다운로드 페이지와 최신 버전 metadata 제공

권장 `latest.json` 형태:

```json
{
  "version": "1.0.1",
  "published_at": "2026-04-24",
  "windows": {
    "url": "https://github.com/SSMakers/reviewMaker/releases/download/v1.0.1/Review_Program_v1.0.1.exe",
    "sha256": "..."
  },
  "macos": {
    "url": "https://github.com/SSMakers/reviewMaker/releases/download/v1.0.1/Review_Program_v1.0.1_macOS.zip",
    "sha256": "..."
  },
  "release_notes_url": "https://github.com/SSMakers/reviewMaker/releases/tag/v1.0.1"
}
```

앱 자동 업데이트는 아래 순서를 따릅니다.

```text
1. 앱 실행 시 Pages의 latest.json 확인
2. 현재 앱 버전과 latest.json 버전 비교
3. 새 버전이 있으면 사용자에게 업데이트 안내
4. 사용자가 동의하면 GitHub Release asset 다운로드
5. sha256 검증
6. 업데이트 파일 실행 또는 교체 후 재시작 안내
```

## 승인 정책

초기 운영은 안전 우선으로 진행합니다.

- Slack의 "배포해" 명령은 draft release 생성 workflow 시작 요청입니다.
- 실제 배포 공개 전 GitHub Release 화면에서 `Publish release`를 한 번 더 눌러야 합니다.
- 최종 배포자는 draft release에서 대상 버전, commit, release notes, asset을 확인하고 publish합니다.
- release가 publish되면 별도 Pages workflow가 `latest.json`과 다운로드 페이지를 갱신합니다.

이 방식은 GitHub environment required reviewers를 사용할 수 없을 때도 최종 승인 단계를 유지할 수 있습니다. 운영 안정화 후에는 Slack 승인만으로 release를 바로 publish하는 방식으로 완화할 수 있습니다.

## 금지 사항

- OS별로 다른 앱 버전을 배포하지 않습니다.
- `main`에 디버그 인증 우회 상태를 남기지 않습니다.
- PR 없이 coding bot이 바로 `main`에 push하지 않습니다. 긴급 장애는 예외로 하되, 사후 PR 또는 기록을 남깁니다.
- 릴리즈 asset URL을 직접 하드코딩하지 않습니다. Pages metadata 또는 GitHub Release API를 기준으로 합니다.
