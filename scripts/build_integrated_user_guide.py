from __future__ import annotations

from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont, JpegImagePlugin  # noqa: F401


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"
OUTPUT = DOCS / "Review Writer 통합 사용자 가이드.pdf"
PAGE_DIR = ASSETS / "integrated-guide-pages"

PAGE_W = 2400
PAGE_H = 1700
M = 110

FONT_PATH = Path("/System/Library/Fonts/AppleSDGothicNeo.ttc")
FALLBACK_FONT_PATH = Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf")

COLORS = {
    "ink": "#111827",
    "muted": "#64748B",
    "soft": "#F8FAFC",
    "line": "#D8E1EE",
    "blue": "#2563EB",
    "blue2": "#EFF6FF",
    "green": "#10B981",
    "green2": "#ECFDF5",
    "red": "#EF4444",
    "red2": "#FEF2F2",
    "purple": "#4F46E5",
    "amber": "#F59E0B",
    "dark": "#0F172A",
}


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    if FONT_PATH.exists():
        # AppleSDGothicNeo.ttc indices vary by macOS version, but these map well
        # on current machines: 0 regular, 6 semibold/bold.
        index = 6 if weight in {"bold", "semibold"} else 0
        return ImageFont.truetype(str(FONT_PATH), size=size, index=index)
    return ImageFont.truetype(str(FALLBACK_FONT_PATH), size=size)


def new_page() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (PAGE_W, PAGE_H), "#FFFFFF")
    return img, ImageDraw.Draw(img)


def text(draw: ImageDraw.ImageDraw, xy, value: str, size=34, fill=None, weight="regular", width=42, leading=1.35):
    fill = fill or COLORS["ink"]
    f = font(size, weight)
    x, y = xy
    for paragraph in value.split("\n"):
        lines = textwrap.wrap(paragraph, width=width, replace_whitespace=False) or [""]
        for line in lines:
            draw.text((x, y), line, font=f, fill=fill)
            y += int(size * leading)
    return y


def rounded(draw: ImageDraw.ImageDraw, box, fill, outline=None, width=2, radius=28):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def header(draw: ImageDraw.ImageDraw, section: str, title: str, subtitle: str | None = None):
    text(draw, (M, 70), section, size=24, fill=COLORS["blue"], weight="semibold", width=80)
    text(draw, (M, 112), title, size=62, weight="bold", width=36, leading=1.14)
    if subtitle:
        text(draw, (M, 205), subtitle, size=29, fill=COLORS["muted"], width=92)
    draw.line((M, 285, PAGE_W - M, 285), fill=COLORS["line"], width=3)


def step_badge(draw: ImageDraw.ImageDraw, x: int, y: int, n: str, fill=COLORS["purple"]):
    draw.ellipse((x, y, x + 58, y + 58), fill=fill)
    text(draw, (x + 19, y + 10), n, size=31, fill="#FFFFFF", weight="bold", width=2)


def card(draw: ImageDraw.ImageDraw, box, title: str, body: str, n: str | None = None, accent=COLORS["blue"]):
    rounded(draw, box, "#FFFFFF", COLORS["line"], width=3, radius=30)
    x1, y1, x2, _ = box
    if n:
        step_badge(draw, x1 + 32, y1 + 34, n, accent)
        tx = x1 + 108
    else:
        tx = x1 + 38
    text(draw, (tx, y1 + 38), title, size=34, weight="bold", width=18)
    text(draw, (x1 + 38, y1 + 108), body, size=26, fill=COLORS["muted"], width=max(20, int((x2 - x1) / 28)))


def code_box(draw: ImageDraw.ImageDraw, box, command: str):
    rounded(draw, box, COLORS["dark"], "#334155", width=2, radius=22)
    text(draw, (box[0] + 28, box[1] + 28), command, size=27, fill="#E5E7EB", width=74, leading=1.45)


def draw_table(draw: ImageDraw.ImageDraw, x: int, y: int):
    col_w = [200, 160, 500, 110, 270, 460, 250]
    row_h = [70, 106, 106, 106, 106]
    headers = ["제목", "작성자", "리뷰내용", "별점", "날짜", "하이퍼링크", "이미지파일명"]
    rows = [
        ["", "이길남", "이미지 없이 등록할 리뷰", "4", "2026-04-10", "", ""],
        ["", "박성수", "URL 이미지를 사용하는 리뷰", "5", "2026-04-10", "https://example.com/review_001.jpg", ""],
        ["", "이재성", "로컬 이미지를 업로드할 리뷰", "5", "2026-04-10", "test_review.jpg", ""],
        ["리뷰", "박상길", "파일명을 별도 칸에 적는 방식", "5", "2026-04-10", "", "test_review.jpg"],
    ]
    for r in range(5):
        cx = x
        for c, w in enumerate(col_w):
            fill = COLORS["dark"] if r == 0 else ("#FFFFFF" if r % 2 else COLORS["soft"])
            draw.rectangle((cx, y, cx + w, y + row_h[r]), fill=fill, outline="#CBD5E1", width=2)
            value = headers[c] if r == 0 else rows[r - 1][c]
            text(draw, (cx + 16, y + 18), value, size=25 if r == 0 else 22, fill="#FFFFFF" if r == 0 else COLORS["ink"], weight="semibold" if r == 0 else "regular", width=max(8, int(w / 15)))
            cx += w
        y += row_h[r]


def page_cover() -> Image.Image:
    img, draw = new_page()
    rounded(draw, (M, 105, PAGE_W - M, 520), COLORS["dark"], None, radius=42)
    text(draw, (M + 70, 170), "Review Writer", size=76, fill="#FFFFFF", weight="bold", width=20)
    text(draw, (M + 70, 270), "통합 사용자 가이드", size=58, fill="#DDE8FF", weight="bold", width=24)
    text(draw, (M + 70, 370), "엑셀 작성, 로컬 이미지 업로드, 앱 사용, PC UUID 확인, 업데이트 배포 테스트까지 한 문서로 정리했습니다.", size=29, fill="#CBD5E1", width=82)

    labels = [
        ("1", "엑셀 준비", "샘플 양식에 리뷰 입력"),
        ("2", "이미지 등록", "URL 또는 파일명 사용"),
        ("3", "앱 실행", "Cafe24 인증 후 등록"),
        ("4", "업데이트", "GitHub Pages 배포 확인"),
    ]
    x = M
    for i, (n, title, body) in enumerate(labels):
        bx = x + i * 540
        card(draw, (bx, 680, bx + 480, 930), title, body, n=n)

    rounded(draw, (M, 1100, PAGE_W - M, 1400), COLORS["blue2"], "#BFDBFE", width=3, radius=34)
    text(draw, (M + 46, 1150), "이 문서의 사용법", size=38, weight="bold")
    text(draw, (M + 46, 1210), "사용자는 1~4장만 보면 리뷰 등록을 시작할 수 있습니다. 운영자 또는 관리자만 6~8장의 UUID, 업데이트, 배포 테스트 내용을 확인하면 됩니다.", size=30, fill=COLORS["muted"], width=96)
    return img


def page_excel() -> Image.Image:
    img, draw = new_page()
    header(draw, "01 / Excel", "엑셀은 이렇게 채우면 됩니다", "제목 또는 리뷰내용은 반드시 하나 이상 입력하고, 이미지는 URL 또는 파일명 중 하나만 적으면 됩니다.")
    draw_table(draw, M, 345)
    rounded(draw, (M, 1035, 720, 1310), COLORS["red2"], COLORS["red"], width=4, radius=30)
    text(draw, (M + 38, 1080), "리뷰 기본 정보", size=34, weight="bold", fill="#B91C1C")
    text(draw, (M + 38, 1140), "제목은 비워도 됩니다. 리뷰내용이 있으면 앱이 제목을 자동 생성합니다.", size=27, fill=COLORS["ink"], width=34)
    rounded(draw, (790, 1035, 1470, 1310), COLORS["blue2"], COLORS["blue"], width=4, radius=30)
    text(draw, (828, 1080), "URL 이미지", size=34, weight="bold", fill="#1D4ED8")
    text(draw, (828, 1140), "이미 인터넷에 올라간 이미지는 하이퍼링크 칸에 URL을 붙여넣습니다.", size=27, fill=COLORS["ink"], width=34)
    rounded(draw, (1540, 1035, PAGE_W - M, 1310), COLORS["green2"], COLORS["green"], width=4, radius=30)
    text(draw, (1578, 1080), "로컬 이미지", size=34, weight="bold", fill="#047857")
    text(draw, (1578, 1140), "PC 폴더에 있는 이미지는 파일명만 적고, 앱에서 이미지 폴더를 선택합니다.", size=27, fill=COLORS["ink"], width=34)
    return img


def page_local_images() -> Image.Image:
    img, draw = new_page()
    header(draw, "02 / Local Images", "이미지 URL을 직접 만들 필요가 없습니다", "파일명과 실제 이미지 파일명이 일치하면 서버가 자동으로 URL을 만들고 Cafe24 리뷰 본문에 이미지를 넣습니다.")
    items = [
        ("이미지 폴더 준비", "Test_Image 폴더 안에 실제 이미지 파일을 넣습니다.", "test_review.jpg"),
        ("엑셀에 파일명 입력", "하이퍼링크 또는 이미지파일명 칸에 파일명을 그대로 적습니다.", "test_review.jpg"),
        ("앱에서 폴더 선택", "이미지 폴더 선택 버튼으로 같은 폴더를 선택합니다.", "Test_Image"),
        ("자동 업로드", "서버가 URL을 만들고 리뷰 본문에 이미지를 넣습니다.", "https://.../img.jpg"),
    ]
    for i, (title, body, sample) in enumerate(items):
        x = M + i * 545
        card(draw, (x, 380, x + 465, 900), title, body, n=str(i + 1), accent=COLORS["green"])
        rounded(draw, (x + 40, 760, x + 425, 845), "#FFFFFF", "#94A3B8", width=2, radius=16)
        text(draw, (x + 65, 783), sample, size=28, weight="semibold", width=20)
        if i < 3:
            draw.line((x + 485, 635, x + 525, 635), fill="#94A3B8", width=7)
            draw.polygon([(x + 525, 635), (x + 500, 618), (x + 500, 652)], fill="#94A3B8")
    rounded(draw, (M, 1080, PAGE_W - M, 1260), COLORS["green2"], COLORS["green"], width=3, radius=28)
    text(draw, (M + 44, 1124), "핵심", size=34, weight="bold", fill="#047857")
    text(draw, (M + 150, 1126), "파일명과 실제 이미지 파일명이 다르면 업로드할 이미지를 찾지 못합니다. 대소문자와 확장자까지 확인하세요.", size=30, fill="#065F46", width=82)
    return img


def page_app() -> Image.Image:
    img, draw = new_page()
    header(draw, "03 / App", "앱에서는 네 가지만 확인하면 됩니다", "게시판 번호, 상품 번호, 엑셀 파일, 이미지 폴더를 선택한 뒤 Cafe24 인증을 완료합니다.")
    rows = [
        ("게시판 번호", "리뷰가 등록될 Cafe24 게시판 번호입니다."),
        ("상품 번호", "리뷰를 연결할 상품 번호입니다."),
        ("엑셀 파일", "작성한 리뷰 엑셀 파일을 선택합니다."),
        ("이미지 폴더", "로컬 이미지 파일을 사용할 때 선택합니다."),
        ("이미지 매칭 방식", "기본값은 URL 우선, 없으면 파일명입니다."),
        ("인증", "Cafe24 관리자 계정으로 로그인하고 권한을 허용합니다."),
    ]
    x1, y1, x2, y2 = M, 360, PAGE_W - M, 1280
    rounded(draw, (x1, y1, x2, y2), COLORS["soft"], COLORS["line"], width=3, radius=34)
    text(draw, (x1 + 50, y1 + 46), "메인 화면 입력 순서", size=42, weight="bold")
    for i, (name, desc) in enumerate(rows):
        y = y1 + 145 + i * 115
        step_badge(draw, x1 + 54, y - 8, str(i + 1), COLORS["blue"])
        text(draw, (x1 + 130, y), name, size=31, weight="bold", width=18)
        text(draw, (x1 + 430, y + 4), desc, size=28, fill=COLORS["muted"], width=60)
    rounded(draw, (1420, 500, 2140, 1020), "#FFFFFF", "#CBD5E1", width=3, radius=26)
    text(draw, (1470, 550), "작업 로그", size=34, weight="bold")
    log_lines = [
        "이미지 매칭 방식: URL 우선, 없으면 파일명",
        "사전 검사 완료",
        "URL 이미지: 1건",
        "업로드 필요 이미지: 2건",
        "리뷰 등록 시작",
    ]
    for i, line in enumerate(log_lines):
        text(draw, (1470, 630 + i * 64), line, size=26, fill=COLORS["muted"], width=36)
    return img


def page_logs() -> Image.Image:
    img, draw = new_page()
    header(draw, "04 / Logs", "작업 로그는 짧게, 상세 내용은 파일로 남깁니다", "사용자에게는 이해하기 쉬운 요약만 보여주고, 원인 분석이 필요한 정보는 logs/app.log에서 확인합니다.")
    card(draw, (M, 380, 760, 760), "성공", "일괄 전송 성공 또는 이미지 업로드 완료 메시지가 표시됩니다.", n="1", accent=COLORS["green"])
    card(draw, (830, 380, 1490, 760), "일부 실패", "성공/실패 건수만 표시하고 상세 응답은 로그 파일에 저장합니다.", n="2", accent=COLORS["amber"])
    card(draw, (1560, 380, PAGE_W - M, 760), "중단", "이미지 업로드 실패나 네트워크 오류가 있으면 작업이 중단됩니다.", n="3", accent=COLORS["red"])
    code_box(draw, (M, 900, PAGE_W - M, 1180), "logs/app.log\n\nCafe24 partial batch failure...\nReview image upload failed...\nAPI response payload...")
    text(draw, (M, 1250), "고객 응대 팁", size=38, weight="bold")
    text(draw, (M, 1310), "사용자에게는 로그 파일 전체를 요구하기보다, 발생 시간과 작업 로그 화면을 먼저 확인하세요. 개발자 분석이 필요할 때 logs/app.log를 추가로 요청합니다.", size=30, fill=COLORS["muted"], width=92)
    return img


def page_uuid() -> Image.Image:
    img, draw = new_page()
    header(draw, "05 / Device UUID", "PC UUID 확인 방법", "기기 등록 또는 인증 확인이 필요할 때 아래 UUID 값을 관리자에게 전달합니다.")
    card(draw, (M, 380, PAGE_W - M, 680), "macOS", "터미널 앱을 열고 아래 명령어를 실행합니다.", n="1", accent=COLORS["dark"])
    code_box(draw, (M + 44, 570, PAGE_W - M - 44, 670), "ioreg -rd1 -c IOPlatformExpertDevice | awk -F\\\" '/IOPlatformUUID/{print $(NF-1)}'")
    card(draw, (M, 760, PAGE_W - M, 1110), "Windows PowerShell", "PowerShell을 열고 아래 명령어를 실행합니다.", n="2", accent=COLORS["blue"])
    code_box(draw, (M + 44, 950, PAGE_W - M - 44, 1050), "Get-CimInstance Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID")
    text(draw, (M, 1190), "Windows CMD를 쓰는 경우", size=34, weight="bold")
    code_box(draw, (M, 1260, PAGE_W - M, 1360), "wmic csproduct get uuid")
    rounded(draw, (M, 1460, PAGE_W - M, 1590), COLORS["blue2"], "#BFDBFE", width=3, radius=24)
    text(draw, (M + 38, 1496), "하이픈이 포함된 UUID 전체를 복사하세요. 앞뒤 공백이나 설명 문구는 제외하고 UUID 값만 전달하면 됩니다.", size=29, fill="#1E3A8A", width=92)
    return img


def page_update_user() -> Image.Image:
    img, draw = new_page()
    header(draw, "06 / Update", "사용자는 어떻게 업데이트하나요?", "앱이 켜질 때 GitHub Pages의 latest.json을 확인하고, 새 버전이 있으면 업데이트 알림을 보여줍니다.")
    items = [
        ("앱 실행", "현재 앱 버전을 확인합니다."),
        ("latest.json 확인", "GitHub Pages에서 최신 버전 정보를 가져옵니다."),
        ("새 버전 비교", "현재 버전보다 높으면 알림창을 표시합니다."),
        ("다운로드/재시작", "사용자가 승인하면 파일을 받고 앱을 재시작합니다."),
    ]
    for i, (title, body) in enumerate(items):
        x = M + i * 545
        card(draw, (x, 390, x + 465, 850), title, body, n=str(i + 1), accent=COLORS["blue"])
        if i < 3:
            draw.line((x + 485, 615, x + 525, 615), fill="#94A3B8", width=7)
            draw.polygon([(x + 525, 615), (x + 500, 598), (x + 500, 632)], fill="#94A3B8")
    rounded(draw, (M, 1040, PAGE_W - M, 1290), COLORS["soft"], COLORS["line"], width=3, radius=28)
    text(draw, (M + 44, 1080), "확인할 URL", size=34, weight="bold")
    code_box(draw, (M + 44, 1150, PAGE_W - M - 44, 1250), "https://ssmakers.github.io/reviewMaker/latest.json")
    text(draw, (M, 1370), "업데이트가 보이지 않을 때는 GitHub Release가 Publish 되었는지, Pages가 최신 latest.json을 배포했는지 확인합니다.", size=30, fill=COLORS["muted"], width=92)
    return img


def page_release_ops() -> Image.Image:
    img, draw = new_page()
    header(draw, "07 / Release", "GitHub Pages 퍼블리싱과 배포 테스트", "실행 파일은 GitHub Releases에 두고, GitHub Pages는 다운로드 페이지와 latest.json만 제공합니다.")
    rows = [
        ("1", "PR merge", "수정 PR을 main에 merge합니다."),
        ("2", "Slack 배포 명령", "`/review-writer-release 배포해 ...`로 release workflow를 실행합니다."),
        ("3", "Draft Release 확인", "버전, 릴리즈 노트, Windows/macOS asset, latest.json을 확인합니다."),
        ("4", "Publish release", "GitHub Release 화면에서 Publish release를 눌러 최종 공개합니다."),
        ("5", "Pages 확인", "GitHub Pages의 index.html과 latest.json이 갱신됐는지 확인합니다."),
        ("6", "앱 업데이트 테스트", "이전 버전 앱을 실행해 업데이트 알림과 다운로드를 확인합니다."),
    ]
    y = 360
    for n, title, body in rows:
        rounded(draw, (M, y, PAGE_W - M, y + 135), "#FFFFFF", COLORS["line"], width=2, radius=22)
        step_badge(draw, M + 32, y + 38, n, COLORS["purple"])
        text(draw, (M + 115, y + 32), title, size=31, weight="bold", width=20)
        text(draw, (M + 520, y + 36), body, size=27, fill=COLORS["muted"], width=66)
        y += 165
    rounded(draw, (M, 1390, PAGE_W - M, 1550), COLORS["green2"], COLORS["green"], width=3, radius=24)
    text(draw, (M + 44, 1430), "배포 성공 기준", size=34, weight="bold", fill="#047857")
    text(draw, (M + 300, 1434), "Release asset 다운로드 가능, Pages latest.json 버전 일치, 앱 자동 업데이트 알림 정상 표시", size=29, fill="#065F46", width=72)
    return img


def save_pdf(pages: list[Image.Image]) -> None:
    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for idx, page in enumerate(pages, start=1):
        path = PAGE_DIR / f"page-{idx:02d}.png"
        page.save(path, quality=95)
        paths.append(path)
    rgb_pages = [Image.open(path).convert("RGB") for path in paths]
    rgb_pages[0].save(OUTPUT, save_all=True, append_images=rgb_pages[1:], resolution=200.0)


def build() -> None:
    pages = [
        page_cover(),
        page_excel(),
        page_local_images(),
        page_app(),
        page_logs(),
        page_uuid(),
        page_update_user(),
        page_release_ops(),
    ]
    save_pdf(pages)
    print(OUTPUT)


if __name__ == "__main__":
    build()
