from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

import build_integrated_user_guide as ui


DOCS = ui.DOCS
ASSETS = ui.ASSETS
PAGE_DIR = ASSETS / "split-guide-pages"

PRODUCT_PDF = DOCS / "Review Writer 상품 설명서.pdf"
USER_PDF = DOCS / "Review Writer 사용자 가이드.pdf"
ADMIN_PDF = DOCS / "Review Writer 관리자 가이드.pdf"


def save_pdf(name: str, output: Path, pages: list[Image.Image]) -> None:
    folder = PAGE_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for idx, page in enumerate(pages, start=1):
        path = folder / f"page-{idx:02d}.png"
        page.save(path, quality=95)
        paths.append(path)
    rgb_pages = [Image.open(path).convert("RGB") for path in paths]
    rgb_pages[0].save(output, save_all=True, append_images=rgb_pages[1:], resolution=200.0)


def product_cover() -> Image.Image:
    img, draw = ui.new_page()
    ui.rounded(draw, (ui.M, 105, ui.PAGE_W - ui.M, 610), ui.COLORS["dark"], None, radius=46)
    ui.text(draw, (ui.M + 70, 170), "Review Writer", size=82, fill="#FFFFFF", weight="bold", width=20)
    ui.text(draw, (ui.M + 70, 285), "카페24 리뷰 등록 자동화 도구", size=56, fill="#DDE8FF", weight="bold", width=34)
    ui.text(
        draw,
        (ui.M + 70, 400),
        "엑셀 한 장으로 리뷰를 일괄 등록하고, 로컬 이미지는 자동으로 URL화해 Cafe24 리뷰 본문에 넣습니다.",
        size=32,
        fill="#CBD5E1",
        width=78,
    )
    values = [
        ("반복 작업 감소", "리뷰를 한 건씩 복사해 등록하는 시간을 줄입니다."),
        ("이미지 URL 자동화", "블로그에 이미지를 먼저 올리는 과정을 없앱니다."),
        ("실무형 운영", "사전 검사, 작업 로그, 자동 업데이트로 운영 부담을 낮춥니다."),
    ]
    for i, (title, body) in enumerate(values):
        x = ui.M + i * 730
        ui.card(draw, (x, 790, x + 640, 1120), title, body, n=str(i + 1), accent=ui.COLORS["blue"])
    ui.rounded(draw, (ui.M, 1300, ui.PAGE_W - ui.M, 1510), ui.COLORS["green2"], ui.COLORS["green"], width=3, radius=30)
    ui.text(draw, (ui.M + 46, 1350), "적합한 사용자", size=38, weight="bold", fill="#047857")
    ui.text(draw, (ui.M + 300, 1352), "카페24 쇼핑몰에서 리뷰 게시판을 운영하고, 엑셀 기반으로 리뷰 데이터를 관리하는 운영자", size=31, fill="#065F46", width=74)
    return img


def product_benefits() -> Image.Image:
    img, draw = ui.new_page()
    ui.header(draw, "01 / Benefits", "도입하면 얻는 이점", "사용자는 리뷰 등록 시간을 줄이고, 운영자는 이미지 포함 리뷰를 더 안정적으로 등록할 수 있습니다.")
    rows = [
        ("수작업 감소", "엑셀 데이터를 읽어 Cafe24 게시판 API로 한 번에 전송합니다."),
        ("이미지 처리 단순화", "PC에 있는 이미지는 파일명만 맞추면 서버가 URL을 생성합니다."),
        ("오류 확인 용이", "사전 검사와 작업 로그로 누락된 파일, 인증 문제, 전송 실패를 확인합니다."),
        ("업데이트 대응", "앱 실행 시 새 버전을 확인하고 업데이트 알림을 표시할 수 있습니다."),
    ]
    y = 390
    for i, (title, body) in enumerate(rows, start=1):
        ui.card(draw, (ui.M, y, ui.PAGE_W - ui.M, y + 210), title, body, n=str(i), accent=ui.COLORS["green"])
        y += 260
    return img


def product_features() -> Image.Image:
    img, draw = ui.new_page()
    ui.header(draw, "02 / Features", "제공 기능", "리뷰 데이터 준비부터 등록, 이미지 업로드, 업데이트까지 필요한 기능을 묶었습니다.")
    features = [
        ("엑셀 리뷰 등록", "제목, 작성자, 리뷰내용, 별점, 날짜를 읽어 게시글을 생성합니다."),
        ("제목 자동 생성", "제목이 비어 있으면 리뷰내용 앞부분으로 제목을 만듭니다."),
        ("URL 이미지 지원", "이미 공개된 이미지 URL을 리뷰 본문에 삽입합니다."),
        ("로컬 이미지 업로드", "이미지 파일명을 기준으로 서버에 업로드하고 URL을 자동 생성합니다."),
        ("Cafe24 OAuth 인증", "Cafe24 관리자 인증 후 API 권한으로 리뷰를 등록합니다."),
        ("작업 로그", "사용자에게는 쉬운 메시지, 개발자에게는 상세 로그를 제공합니다."),
    ]
    for idx, (title, body) in enumerate(features):
        col = idx % 2
        row = idx // 2
        x = ui.M + col * 1125
        y = 380 + row * 340
        ui.card(draw, (x, y, x + 1010, y + 270), title, body, n=str(idx + 1), accent=ui.COLORS["blue"])
    return img


def product_image_flow() -> Image.Image:
    return ui.page_local_images()


def user_cover() -> Image.Image:
    img, draw = ui.new_page()
    ui.rounded(draw, (ui.M, 105, ui.PAGE_W - ui.M, 560), ui.COLORS["dark"], None, radius=46)
    ui.text(draw, (ui.M + 70, 178), "Review Writer", size=76, fill="#FFFFFF", weight="bold", width=20)
    ui.text(draw, (ui.M + 70, 290), "사용자 가이드", size=62, fill="#DDE8FF", weight="bold", width=24)
    ui.text(draw, (ui.M + 70, 405), "구매 후 사용자가 실제 리뷰 등록을 완료하기 위해 따라야 하는 순서만 담았습니다.", size=32, fill="#CBD5E1", width=78)
    steps = [
        ("1", "PC UUID 전달", "기기 등록이 필요한 경우 UUID를 관리자에게 전달"),
        ("2", "엑셀 작성", "샘플 양식에 리뷰와 이미지 정보 입력"),
        ("3", "앱 설정", "게시판/상품/파일/이미지 폴더 선택"),
        ("4", "등록 시작", "Cafe24 인증 후 리뷰 등록"),
    ]
    for i, (n, title, body) in enumerate(steps):
        x = ui.M + i * 545
        ui.card(draw, (x, 790, x + 465, 1120), title, body, n=n, accent=ui.COLORS["purple"])
    return img


def user_finish() -> Image.Image:
    img, draw = ui.new_page()
    ui.header(draw, "05 / Finish", "등록 후 확인할 내용", "작업이 끝난 뒤 Cafe24 게시판에서 리뷰와 이미지가 정상 등록됐는지 확인합니다.")
    checks = [
        ("게시글 수", "엑셀에서 등록 가능한 행 수와 Cafe24 게시글 수가 맞는지 확인합니다."),
        ("이미지 표시", "URL 이미지와 로컬 업로드 이미지가 리뷰 본문에 보이는지 확인합니다."),
        ("작업 로그", "일부 실패가 표시되면 해당 행을 수정해 다시 등록합니다."),
        ("로그 파일", "고객센터나 관리자에게 문의할 때는 발생 시간과 작업 로그를 함께 전달합니다."),
    ]
    y = 390
    for i, (title, body) in enumerate(checks, start=1):
        ui.card(draw, (ui.M, y, ui.PAGE_W - ui.M, y + 215), title, body, n=str(i), accent=ui.COLORS["green"])
        y += 260
    return img


def admin_cover() -> Image.Image:
    img, draw = ui.new_page()
    ui.rounded(draw, (ui.M, 105, ui.PAGE_W - ui.M, 560), ui.COLORS["dark"], None, radius=46)
    ui.text(draw, (ui.M + 70, 178), "Review Writer", size=76, fill="#FFFFFF", weight="bold", width=20)
    ui.text(draw, (ui.M + 70, 290), "관리자 가이드", size=62, fill="#DDE8FF", weight="bold", width=24)
    ui.text(draw, (ui.M + 70, 405), "버전업, 배포 승인, GitHub Pages, 자동 업데이트 검증 등 내부 운영자만 알아야 하는 내용을 담았습니다.", size=31, fill="#CBD5E1", width=78)
    internal = [
        ("버전 관리", "PATCH/MINOR/MAJOR 기준"),
        ("배포 승인", "Draft Release 확인 후 Publish"),
        ("Pages 검증", "index.html/latest.json 확인"),
        ("장애 대응", "업데이트 실패 원인 확인"),
    ]
    for i, (title, body) in enumerate(internal):
        x = ui.M + i * 545
        ui.card(draw, (x, 790, x + 465, 1120), title, body, n=str(i + 1), accent=ui.COLORS["red"])
    ui.rounded(draw, (ui.M, 1320, ui.PAGE_W - ui.M, 1490), ui.COLORS["red2"], ui.COLORS["red"], width=3, radius=30)
    ui.text(draw, (ui.M + 46, 1365), "주의", size=36, weight="bold", fill="#B91C1C")
    ui.text(draw, (ui.M + 200, 1368), "이 문서의 Slack, GitHub, Release, Pages 운영 내용은 고객용 문서에 포함하지 않습니다.", size=30, fill="#7F1D1D", width=82)
    return img


def admin_versioning() -> Image.Image:
    img, draw = ui.new_page()
    ui.header(draw, "01 / Versioning", "버전업 기준", "Windows와 macOS는 항상 같은 앱 버전을 사용합니다. 배포 기준은 version.py입니다.")
    rows = [
        ("PATCH", "버그 수정, 문서 수정, 작은 안정화"),
        ("MINOR", "사용자가 체감하는 기능 추가"),
        ("MAJOR", "호환성이 깨지거나 운영 방식이 크게 바뀌는 변경"),
    ]
    for i, (name, body) in enumerate(rows, start=1):
        ui.card(draw, (ui.M, 390 + (i - 1) * 300, ui.PAGE_W - ui.M, 620 + (i - 1) * 300), name, body, n=str(i), accent=ui.COLORS["blue"])
    ui.code_box(draw, (ui.M, 1340, ui.PAGE_W - ui.M, 1460), "version.py")
    return img


def admin_slack_runner() -> Image.Image:
    img, draw = ui.new_page()
    ui.header(draw, "04 / Automation", "Slack 작업 요청과 Local Codex Runner", "Slack 명령으로 GitHub Issue를 만들고, 로컬 PC의 runner가 Codex 작업과 PR 생성을 수행합니다.")
    steps = [
        ("Slack /review-task", "작업 요청을 보냅니다."),
        ("GitHub Issue", "codex-task label이 붙은 Issue가 생성됩니다."),
        ("Local Runner", "PC가 켜져 있으면 Issue를 감지합니다."),
        ("Codex CLI", "코드 수정과 검증을 수행합니다."),
        ("Pull Request", "branch, commit, push, PR 생성을 완료합니다."),
    ]
    for i, (title, body) in enumerate(steps):
        x = ui.M + (i % 3) * 730
        y = 390 + (i // 3) * 390
        ui.card(draw, (x, y, x + 640, y + 310), title, body, n=str(i + 1), accent=ui.COLORS["purple"])
    ui.code_box(draw, (ui.M, 1240, ui.PAGE_W - ui.M, 1360), "python scripts/local_codex_runner.py --dashboard")
    return img


def admin_troubleshooting() -> Image.Image:
    img, draw = ui.new_page()
    ui.header(draw, "05 / Troubleshooting", "배포/업데이트 문제 대응", "latest.json, Release asset, GitHub Pages workflow를 순서대로 확인합니다.")
    rows = [
        ("latest.json 404", "Release가 publish됐는지, pages-on-release workflow가 성공했는지 확인합니다."),
        ("업데이트 알림 없음", "latest.json.version이 앱 version.py보다 높은지 확인합니다."),
        ("다운로드 실패", "Release asset URL과 sha256 값을 확인합니다."),
        ("Slack 명령 실패", "Cloudflare Worker secret과 GitHub token 권한을 확인합니다."),
    ]
    y = 390
    for i, (title, body) in enumerate(rows, start=1):
        ui.card(draw, (ui.M, y, ui.PAGE_W - ui.M, y + 215), title, body, n=str(i), accent=ui.COLORS["red"])
        y += 260
    return img


def build() -> None:
    save_pdf(
        "product",
        PRODUCT_PDF,
        [product_cover(), product_benefits(), product_features(), product_image_flow()],
    )
    save_pdf(
        "user",
        USER_PDF,
        [user_cover(), ui.page_uuid(), ui.page_excel(), ui.page_local_images(), ui.page_app(), user_finish()],
    )
    save_pdf(
        "admin",
        ADMIN_PDF,
        [admin_cover(), admin_versioning(), ui.page_release_ops(), ui.page_update_user(), admin_slack_runner(), admin_troubleshooting()],
    )
    print(PRODUCT_PDF)
    print(USER_PDF)
    print(ADMIN_PDF)


if __name__ == "__main__":
    build()
