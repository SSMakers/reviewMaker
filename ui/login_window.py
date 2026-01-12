from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame

import version
from external_api.server.models import VerifyDenied
from external_api.server.server_api import ServerApi
from global_constants import IS_DEBUG
from logger.file_logger import logger
from utils.computer_resource import get_system_uuid


class LoginPage(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        logger.info(f"Version : {version.Version.MAJOR}.{version.Version.MINOR}.{version.Version.PATCH}")
        self.auth_result = None
        # self.btn_manual = None
        self.btn_login = None
        self.lbl_info = None
        self.uuid = None

        self.on_login_success = on_login_success  # 성공 시 다음 페이지 이동 콜백
        self.init_ui()

        if not IS_DEBUG:
            self.check_initial_uuid()

    def init_ui(self):
        # 전체 배경을 잡아주는 메인 수직 레이아웃
        outer_layout = QVBoxLayout()
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 실제 콘텐츠가 들어갈 내부 카드 스타일의 컨테이너 (여백 확보용)
        content_widget = QWidget()
        content_widget.setFixedWidth(400)  # 가로 폭을 고정하여 버튼 시인성 확보
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(30, 40, 30, 40)

        # (1) 타이틀 - 시인성을 높인 다크 네이비 컬러
        self.lbl_title = QLabel("🔒 시스템 인증")
        self.lbl_title.setStyleSheet("""
            font-size: 28px; 
            font-weight: 800; 
            color: #1a2a6c; 
            margin-bottom: 5px;
        """)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.lbl_title)

        # (2) 구분선 (디자인 요소)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #ecf0f1;")
        content_layout.addWidget(line)

        # (3) 상태 안내 라벨
        self.lbl_info = QLabel("시스템 고유 식별번호를 확인하고 있습니다...")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet("font-size: 13px; color: #57606f; padding: 10px;")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.lbl_info)

        # (4) 버튼 영역 (좌우 여백이 포함된 스타일)
        self.btn_login = QPushButton("🚀 프로그램 시작하기")
        self.btn_login.setMinimumHeight(55)
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #0984e3;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
                margin: 5px 10px; /* 상하 5px, 좌우 10px 여백 추가 */
            }
            QPushButton:hover { background-color: #74b9ff; }
            QPushButton:pressed { background-color: #0652dd; }
            QPushButton:disabled { background-color: #dfe6e9; color: #b2bec3; }
        """)

        if IS_DEBUG:
            self.btn_login.setVisible(True)
            self.btn_login.setEnabled(True)
        else:
            self.btn_login.setEnabled(False)  # 초기 비활성화

        self.btn_login.clicked.connect(self.__handle_login)
        content_layout.addWidget(self.btn_login)

        # (5) 수동 입력 버튼
        # self.btn_manual = QPushButton("🔑 수동 인증키 입력")
        # self.btn_manual.setMinimumHeight(45)
        # self.btn_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        # self.btn_manual.setStyleSheet("""
        #     QPushButton {
        #         background-color: #0984e3;
        #         color: white;
        #         font-size: 16px;
        #         font-weight: bold;
        #         border-radius: 12px;
        #         margin: 5px 10px; /* 상하 5px, 좌우 10px 여백 추가 */
        #     }
        #     QPushButton:hover { background-color: #74b9ff; }
        #     QPushButton:pressed { background-color: #0652dd; }
        #     QPushButton:disabled { background-color: #dfe6e9; color: #b2bec3; }
        # """)
        # self.btn_manual.setVisible(False)  # 기본 숨김
        # self.btn_manual.clicked.connect(self.open_manual_input)
        # content_layout.addWidget(self.btn_manual)

        outer_layout.addWidget(content_widget)
        self.setLayout(outer_layout)

    def set_auth_status(self, success, message):
        """인증 상태에 따른 UI 업데이트 공통 로직"""
        if success:
            self.lbl_info.setText(f"✅ {message}")
            self.lbl_info.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 13px;")
            self.btn_login.setEnabled(True)
            self.btn_login.setVisible(True)
            # self.btn_manual.setVisible(False)
        else:
            self.lbl_info.setText(f"❌ {message}")
            self.lbl_info.setStyleSheet("color: #d63031; font-weight: bold; font-size: 13px;")
            self.btn_login.setVisible(False)
            # self.btn_manual.setVisible(False)

    def check_initial_uuid(self):
        self.uuid = get_system_uuid()

        if self.uuid:
            try:
                self.auth_result = ServerApi().auth_verify(device_id=self.uuid)
                if isinstance(self.auth_result, VerifyDenied):
                    self.set_auth_status(False, f"{self.uuid} 등록되지 않은 기기입니다. 관리자에게 문의하세요. 🛑")
                    return
                else:
                    self.set_auth_status(True, f"자동 인증 성공 (ID: {self.uuid[:8]}...)")
                    logger.info(f"자동 인증 성공 (ID: {self.uuid})")
            except Exception as e:
                # 서버가 502 등을 뱉거나 연결이 안 될 때 앱이 꺼지지 않도록 방어
                err_msg = str(e)
                if "502" in err_msg:
                    err_msg = "서버 점검 중입니다 (502 Bad Gateway)"

                logger.error(f"서버 인증 실패: {e}")
                self.set_auth_status(False, f"서버 연결 실패: {err_msg}")
        else:
            self.set_auth_status(False, "UUID를 찾을 수 없습니다. 수동 인증이 필요합니다.")
            logger.warning(f"UUID를 찾을 수 없습니다. 수동 인증이 필요합니다.")

    # def open_manual_input(self):
    #     dialog = UUIDInputDialog(self)
    #     if dialog.exec() == UUIDInputDialog.DialogCode.Accepted:
    #         manual_uuid = dialog.get_uuid().strip()
    #         if manual_uuid:
    #             self.uuid = manual_uuid
    #
    #             if not validate_uuid_format(self.uuid):
    #                 QMessageBox.warning(self, "형식 오류", "UUID 형식이 올바르지 않습니다. 다시 확인해주세요. 🔍")
    #                 return
    #
    #             result = ServerApi().auth_verify(device_id=self.uuid)
    #             if isinstance(result, VerifyDenied):
    #                 QMessageBox.warning(self, "인증 실패", "등록되지 않은 기기입니다. 관리자에게 문의하세요. 🛑")
    #                 return
    #
    #             self.set_auth_status(True, "수동 인증이 완료되었습니다!")
    #         else:
    #             QMessageBox.warning(self, "경고", "UUID를 입력해야 합니다.")

    def __handle_login(self):
        logger.info(f"{self.uuid} 인증 완료. 메인 화면으로 진입합니다.")
        self.on_login_success(self.auth_result)
