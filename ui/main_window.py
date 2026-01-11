import sys
from datetime import datetime, timedelta

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QProgressBar, QMessageBox)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QSpinBox, QFileDialog, QPlainTextEdit)

from external_api.cafe24_api import Cafe24Api
from global_constants import IS_SAMPLE, BUILD_DATE
from logger.file_logger import logger
from ui.main.mall_id_edit import MallIdEdit
from worker import ApiWorker


class AuthWorker(QThread):
    """브라우저 인증 과정을 백그라운드에서 처리하는 워커"""
    finished_signal = pyqtSignal(str)  # 성공 시 auth_code 전달
    error_signal = pyqtSignal(str)  # 실패 시 에러 메시지 전달

    def __init__(self, api_interface):
        super().__init__()
        self.api = api_interface

    def run(self):
        try:
            code = self.api.get_authorization_url()
            if code:
                self.finished_signal.emit(code)
            else:
                self.error_signal.emit("인증 코드를 찾을 수 없습니다.")
        except Exception as e:
            self.error_signal.emit(str(e))


class MainPage(QWidget):
    def __init__(self):
        super().__init__()

        # API
        self.cafe24_interface = None
        self.access_token = None
        self.refresh_token = None

        # UI
        self.btn_submit = None
        self.btn_select_file = None
        self.lbl_file_status = None
        self.spin_product = None
        self.lbl_product = None
        self.spin_board = None
        self.lbl_board = None
        self.progress_bar = None
        self.init_ui()

        # 프로그램 실행 시 라이선스(샘플 기간) 체크 수행
        self.check_license()

    def check_license(self):
        """샘플 버전일 경우 빌드 날짜로부터 2일간만 사용 가능하도록 제한"""
        if IS_SAMPLE:
            try:
                build_date = datetime.strptime(BUILD_DATE, "%Y-%m-%d")
                expiration_date = build_date + timedelta(days=2)
                current_date = datetime.now()

                if current_date > expiration_date:
                    QMessageBox.critical(
                        self,
                        "기간 만료",
                        f"사용 기간이 만료되었습니다.\n(만료일: {expiration_date.strftime('%Y-%m-%d')})\n개발자에게 문의하세요."
                    )
                    sys.exit(0)  # 프로그램 강제 종료
                else:
                    logger.info(f"Trial Mode 실행 중. 만료일: {expiration_date.strftime('%Y-%m-%d')}")
            except ValueError:
                logger.error("Global Constants의 날짜 형식이 잘못되었습니다.")
                sys.exit(0)

    def init_ui(self):
        # 전체 메인 레이아웃 (수직)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- 상단 레이아웃 (1, 2, 3 컴포넌트 가로 배치) ---
        top_layout = QHBoxLayout()

        # (1) 게시판 번호
        board_layout = QVBoxLayout()
        self.lbl_board = QLabel("게시판 번호")
        self.spin_board = QSpinBox()
        self.spin_board.setRange(0, 999999)  # 입력 범위 설정
        self.spin_board.setFixedHeight(30)
        board_layout.addWidget(self.lbl_board)
        board_layout.addWidget(self.spin_board)

        # (2) 상품 번호
        product_layout = QVBoxLayout()
        self.lbl_product = QLabel("상품 번호")
        self.spin_product = QSpinBox()
        self.spin_product.setRange(0, 999999)
        self.spin_product.setFixedHeight(30)
        product_layout.addWidget(self.lbl_product)
        product_layout.addWidget(self.spin_product)

        # (3) 파일선택 버튼e
        file_layout = QVBoxLayout()
        self.lbl_file_status = QLabel("파일: 미선택")
        self.btn_select_file = QPushButton("엑셀 파일 선택")
        self.btn_select_file.setFixedHeight(30)
        self.btn_select_file.clicked.connect(self.open_file_dialog)
        file_layout.addWidget(self.lbl_file_status)
        file_layout.addWidget(self.btn_select_file)

        # 상단 레이아웃에 그룹들 추가
        top_layout.addLayout(board_layout)
        top_layout.addLayout(product_layout)
        top_layout.addLayout(file_layout)
        main_layout.addLayout(top_layout)

        # --- mall id 레이아웃 ---
        # mall id
        token_layout = QHBoxLayout()
        self.lbl_mall_id = QLabel("mall ID")
        self.mall_id_edit = MallIdEdit(self, on_enter_func=self.__get_redirect_url)
        self.mall_id_edit.setFixedHeight(30)
        self.btn_refresh = QPushButton("인증")
        self.btn_refresh.setFixedHeight(30)
        self.btn_refresh.clicked.connect(self.__get_redirect_url)

        token_layout.addWidget(self.lbl_mall_id)
        token_layout.addWidget(self.mall_id_edit)
        token_layout.addWidget(self.btn_refresh)
        main_layout.addLayout(token_layout)

        # --- 중간 레이아웃 (4. 리뷰 등록 버튼) ---
        self.btn_submit = QPushButton("리뷰 등록 시작")
        self.btn_submit.setFixedHeight(45)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.btn_submit.clicked.connect(self.start_review_process)
        main_layout.addWidget(self.btn_submit)

        # --- 프로그레스 바  ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #bdc3c7;
                        border-radius: 5px;
                        text-align: center;
                        height: 20px;
                    }
                    QProgressBar::chunk {
                        background-color: #3498db;
                        width: 10px;
                    }
                """)
        main_layout.addWidget(self.progress_bar)

        # --- 하단 레이아웃 (5. 로그 뷰어) ---
        main_layout.addWidget(QLabel("작업 로그"))
        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setReadOnly(True)  # 사용자 수정 불가
        self.log_viewer.setPlaceholderText("여기에 작업 진행 상황이 표시됩니다...")

        # 약 15~20줄 정도 보이도록 최소 높이 설정
        self.log_viewer.setMinimumHeight(250)

        # 폰트를 고정폭 폰트로 설정 (로그 보기 편함)
        self.log_viewer.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 12px;")

        main_layout.addWidget(self.log_viewer)

        self.setLayout(main_layout)

    def __get_redirect_url(self):
        mall_id = self.mall_id_edit.toPlainText().strip()  # 쇼핑몰 ID는 PC의 UUID를 가지고 가져오기
        if not mall_id:
            logger.error("❌ 오류: 쇼핑몰 ID를 입력하세요")
            self.append_log("❌ 오류: 쇼핑몰 ID를 입력하세요")
            return

        self.cafe24_interface = Cafe24Api(mall_id)

        # UI 비활성화 및 안내
        self.btn_refresh.setEnabled(False)
        self.append_log("⏳ 브라우저를 실행합니다. 로그인 후 권한 동의를 진행해주세요...")

        # 백그라운드 스레드에서 인증 시작
        self.auth_worker = AuthWorker(self.cafe24_interface)
        self.auth_worker.finished_signal.connect(self.on_auth_success)
        self.auth_worker.error_signal.connect(self.on_auth_error)
        self.auth_worker.start()

    def on_auth_success(self, auth_code):
        """인증 성공 시 호출: 자동으로 토큰 발급 진행"""
        self.btn_refresh.setEnabled(True)
        self.append_log("✅ 인증 코드 획득 성공! 토큰 발급을 진행합니다.")

        # 토큰 발급 요청
        if self.cafe24_interface.fetch_access_token(auth_code):
            self.append_log("✨ Access Token 발급 및 저장 완료!")
        else:
            self.append_log("❌ Access Token 발급 실패. 로그를 확인하세요.")

    def on_auth_error(self, error_msg):
        """인증 실패 시 호출"""
        self.btn_refresh.setEnabled(True)
        self.append_log(f"❌ 인증 과정 중 오류 발생: {error_msg}")

    def open_file_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, "엑셀 파일 선택", "", "Excel Files (*.xlsx *.xls)")
        if fname:
            self.lbl_file_status.setText(f"파일: {fname.split('/')[-1]}")
            self.file_path = fname
            logger.info(f"파일 : {fname}")

    def start_review_process(self):
        # 파일 선택 여부 확인
        if not hasattr(self, 'file_path') or not self.file_path:
            logger.error("❌ 오류: 엑셀 파일을 먼저 선택해주세요.")
            self.append_log("❌ 오류: 엑셀 파일을 먼저 선택해주세요.")
            return

        # UI 상태 변경
        self.btn_submit.setEnabled(False)
        self.btn_select_file.setEnabled(False)
        self.log_viewer.clear()

        # 스핀박스에서 값 가져오기
        board_no = self.spin_board.value()
        product_no = self.spin_product.value()

        # Worker 쓰레드 생성 및 시작
        if not self.cafe24_interface or not self.cafe24_interface.access_token:
            self.append_log("❌ 오류: 먼저 '인증' 버튼을 눌러 인증을 완료해주세요.")
            self.btn_submit.setEnabled(True)
            self.btn_select_file.setEnabled(True)
            return

        self.worker = ApiWorker(self.cafe24_interface, self.file_path, board_no, product_no)

        # 시그널 연결
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_progress_bar)  # QProgressBar가 있다면 연결
        self.worker.finished_signal.connect(self.on_process_finished)

        self.worker.start()

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)

    def on_process_finished(self, success):
        self.btn_submit.setEnabled(True)
        self.btn_select_file.setEnabled(True)
        if success:
            logger.info("✨ 모든 작업이 종료되었습니다.")
            self.append_log("✨ 모든 작업이 종료되었습니다.")
        else:
            logger.warning("🚫 작업이 중단되었습니다. 로그를 확인하세요.")
            self.append_log("🚫 작업이 중단되었습니다. 로그를 확인하세요.")

    def append_log(self, text):
        self.log_viewer.appendPlainText(text)
        self.log_viewer.verticalScrollBar().setValue(
            self.log_viewer.verticalScrollBar().maximum()
        )

    def start_process(self):
        self.btn_run.setEnabled(False)
        self.worker = ApiWorker(self.file_path, self.url_input.text())

        # 시그널 연결
        self.worker.progress_update.connect(self.progress_bar.setValue)
        self.worker.status_update.connect(self.statusBar().showMessage)
        self.worker.finished.connect(self.on_complete)

        self.worker.start()

    def on_complete(self, success, message):
        self.statusBar().showMessage(message)
        self.btn_run.setEnabled(True)
