import sys

from PyQt6.QtWidgets import QApplication, QStackedWidget, QMainWindow

from logger.file_logger import logger
from ui.login_window import LoginPage
from ui.main_window import MainPage  # 아직 만들지 않았다면 아래 3번 참고


class AppController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Review Writer")
        self.setMinimumSize(500, 400)

        # 1. QStackedWidget 생성 (페이지 관리자)
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # 2. 페이지 인스턴스 생성
        # 로그인 성공 시 실행할 콜백 함수(go_to_main)를 전달합니다.
        self.login_page = LoginPage(on_login_success=self.go_to_main)
        self.main_page = MainPage()

        # 3. 스택에 페이지 추가
        self.stacked_widget.addWidget(self.login_page)  # index 0
        self.stacked_widget.addWidget(self.main_page)  # index 1

        # 4. 첫 화면 설정
        self.stacked_widget.setCurrentIndex(0)

    def go_to_main(self):
        """로그인 성공 시 호출되어 메인 화면으로 전환함"""
        logger.info("[LOG] 메인 화면으로 전환합니다.")
        self.stacked_widget.setCurrentIndex(1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = AppController()
    controller.show()
    sys.exit(app.exec())
