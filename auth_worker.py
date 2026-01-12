from PyQt6.QtCore import QThread, pyqtSignal


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