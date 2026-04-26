import os

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QMessageBox, QInputDialog

import version
from external_api.server.models import VerifyConfirm, VerifyDenied
from external_api.server.server_api import ServerApi, HttpError
from global_constants import IS_DEBUG
from logger.file_logger import logger
from utils.computer_resource import get_system_uuid


class LoginPage(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        logger.info(f"Version : {version.Version.MAJOR}.{version.Version.MINOR}.{version.Version.PATCH}")
        self.auth_result = None
        self.settings = QSettings("SSMakers", "ReviewWriter")
        self.btn_request_membership = None
        self.btn_login = None
        self.lbl_info = None
        self.uuid = None

        self.on_login_success = on_login_success  # 성공 시 다음 페이지 이동 콜백
        self.init_ui()

        if IS_DEBUG:
            self.configure_debug_auth()
        else:
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

        # (5) 등록 요청 버튼 (미등록 기기일 때만 표시)
        self.btn_request_membership = QPushButton("📝 등록 요청")
        self.btn_request_membership.setMinimumHeight(45)
        self.btn_request_membership.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_request_membership.setStyleSheet("""
            QPushButton {
                background-color: #6c5ce7;
                color: white;
                font-size: 14px;
                font-weight: 700;
                border-radius: 12px;
                margin: 5px 10px;
            }
            QPushButton:hover { background-color: #7f6df0; }
            QPushButton:pressed { background-color: #5b4dc9; }
            QPushButton:disabled { background-color: #dfe6e9; color: #b2bec3; }
        """)
        self.btn_request_membership.setVisible(False)
        self.btn_request_membership.clicked.connect(self.__request_membership)
        content_layout.addWidget(self.btn_request_membership)

        outer_layout.addWidget(content_widget)
        self.setLayout(outer_layout)

    def set_auth_status(self, success, message, *, allow_membership_request=False):
        """인증 상태에 따른 UI 업데이트 공통 로직"""
        if success:
            self.lbl_info.setText(f"✅ {message}")
            self.lbl_info.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 13px;")
            self.btn_login.setEnabled(True)
            self.btn_login.setVisible(True)
            self.btn_request_membership.setVisible(False)
        else:
            self.lbl_info.setText(f"❌ {message}")
            self.lbl_info.setStyleSheet("color: #d63031; font-weight: bold; font-size: 13px;")
            self.btn_login.setVisible(False)
            self.btn_request_membership.setVisible(allow_membership_request)
            self.btn_request_membership.setEnabled(allow_membership_request)

    def _membership_pending_key(self, device_id: str) -> str:
        return f"membership/request_pending/{device_id}"

    def _is_membership_pending(self, device_id: str) -> bool:
        if not device_id:
            return False
        return bool(self.settings.value(self._membership_pending_key(device_id), False, type=bool))

    def _mark_membership_pending(self, device_id: str, pending: bool) -> None:
        if not device_id:
            return
        self.settings.setValue(self._membership_pending_key(device_id), pending)

    def check_initial_uuid(self):
        self.uuid = get_system_uuid()

        if self.uuid:
            try:
                self.auth_result = ServerApi().auth_verify(device_id=self.uuid)
                if isinstance(self.auth_result, VerifyDenied):
                    if self._is_membership_pending(self.uuid):
                        self.set_auth_status(
                            False,
                            f"{self.uuid} 등록 요청이 접수되어 승인 대기 중입니다. 관리자 승인 후 다시 시도해주세요.",
                            allow_membership_request=False,
                        )
                        return
                    self.set_auth_status(
                        False,
                        f"{self.uuid} 등록되지 않은 기기입니다. 관리자에게 문의하세요. 🛑",
                        allow_membership_request=True,
                    )
                    return
                else:
                    self._mark_membership_pending(self.uuid, False)
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

    def configure_debug_auth(self):
        self.uuid = get_system_uuid() or "debug-device"
        client_id = os.getenv("CAFE24_CLIENT_ID", "").strip()
        client_secret = os.getenv("CAFE24_CLIENT_SECRET", "").strip()
        mall_id = (
            os.getenv("CAFE24_MALL_ID", "").strip()
            or os.getenv("DEBUG_MALL_ID", "").strip()
        )
        redirect_url = (
            os.getenv("CAFE24_REDIRECT_URL", "").strip()
            or (f"https://{mall_id}.cafe24.com/order/basket.html" if mall_id else "")
        )

        missing = []
        if not client_id:
            missing.append("CAFE24_CLIENT_ID")
        if not client_secret:
            missing.append("CAFE24_CLIENT_SECRET")
        if not mall_id:
            missing.append("CAFE24_MALL_ID 또는 DEBUG_MALL_ID")

        self.auth_result = VerifyConfirm(
            result="confirm",
            contract_id="debug-contract",
            remaining_days=9999,
            client_id=client_id,
            secret_key=client_secret,
            mall_id=mall_id,
            redirect_url=redirect_url,
        )

        if missing:
            message = f"디버그 인증 사용 중, 설정 누락: {', '.join(missing)}"
            logger.warning(message)
            self.set_auth_status(True, message)
        else:
            self.set_auth_status(True, f"디버그 인증 사용 중 (ID: {self.uuid[:8]}...)")

        logger.info(f"디버그 인증 구성 완료 (ID: {self.uuid}, mall_id={mall_id})")

    def _membership_request_payload(self):
        mall_id = (
            os.getenv("CAFE24_MALL_ID", "").strip()
            or os.getenv("DEBUG_MALL_ID", "").strip()
        )
        plan = os.getenv("MEMBERSHIP_PLAN", "12").strip() or "12"

        if not mall_id:
            mall_id, ok = QInputDialog.getText(
                self,
                "쇼핑몰 ID 입력",
                "Cafe24 mall ID를 입력해주세요 (예: venel):",
            )
            if not ok:
                return None
            mall_id = (mall_id or "").strip()

        if not mall_id:
            QMessageBox.warning(self, "요청 실패", "mall ID를 입력해야 등록 요청을 보낼 수 있습니다.")
            return None

        return {"mall_id": mall_id, "plan": plan}

    def __request_membership(self):
        if not self.uuid:
            QMessageBox.warning(self, "요청 실패", "UUID를 찾을 수 없어 등록 요청을 보낼 수 없습니다.")
            return

        payload = self._membership_request_payload()
        if payload is None:
            return

        self.btn_request_membership.setEnabled(False)
        self.lbl_info.setText("⏳ 등록 요청을 전송하고 있습니다...")
        self.lbl_info.setStyleSheet("color: #57606f; font-weight: bold; font-size: 13px;")

        try:
            data = ServerApi().member_request(
                device_id=self.uuid,
                plan=payload["plan"],
                mall_id=payload["mall_id"],
            )
            request_id = data.get("request_id", "-")
            status = data.get("status", "pending")
            logger.info("멤버십 등록 요청 성공: request_id=%s status=%s device_id=%s", request_id, status, self.uuid)
            QMessageBox.information(
                self,
                "등록 요청 완료",
                f"등록 요청이 접수되었습니다.\n요청 ID: {request_id}\n상태: {status}",
            )
            self._mark_membership_pending(self.uuid, True)
            self.set_auth_status(
                False,
                f"{self.uuid} 등록 요청이 접수되었습니다. 관리자 승인 후 다시 시도해주세요.",
                allow_membership_request=False,
            )
        except HttpError as e:
            # 서버에서 중복 pending 요청을 409로 돌려주는 경우를 idempotent 성공으로 처리합니다.
            if e.status_code == 409:
                self._mark_membership_pending(self.uuid, True)
                self.set_auth_status(
                    False,
                    f"{self.uuid} 등록 요청이 이미 접수되어 승인 대기 중입니다.",
                    allow_membership_request=False,
                )
                QMessageBox.information(self, "등록 요청 대기", "이미 등록 요청이 접수되어 승인 대기 중입니다.")
                return
            logger.exception("멤버십 등록 요청 실패: device_id=%s", self.uuid)
            QMessageBox.critical(self, "요청 실패", f"등록 요청 전송에 실패했습니다.\n{e}")
            self.set_auth_status(
                False,
                f"{self.uuid} 등록되지 않은 기기입니다. 관리자에게 문의하세요. 🛑",
                allow_membership_request=True,
            )
        except Exception as e:
            logger.exception("멤버십 등록 요청 실패: device_id=%s", self.uuid)
            QMessageBox.critical(self, "요청 실패", f"등록 요청 전송에 실패했습니다.\n{e}")
            self.set_auth_status(
                False,
                f"{self.uuid} 등록되지 않은 기기입니다. 관리자에게 문의하세요. 🛑",
                allow_membership_request=True,
            )
        finally:
            if self.btn_request_membership.isVisible():
                self.btn_request_membership.setEnabled(True)

    def __handle_login(self):
        if self.auth_result is None:
            self.set_auth_status(False, "인증 정보가 준비되지 않았습니다. 설정을 확인해주세요.")
            return

        logger.info(f"{self.uuid} 인증 완료. 메인 화면으로 진입합니다.")
        self.on_login_success(self.auth_result)
