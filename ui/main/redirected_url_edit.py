from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtCore import Qt


class RedirectedUrlEdit(QPlainTextEdit):
    def __init__(self, parent=None, on_enter_func=None):
        super().__init__(parent)
        self.on_enter_func = on_enter_func  # 엔터 칠 때 실행할 함수

    def keyPressEvent(self, event):
        # 엔터키(Enter) 또는 숫자패드 엔터키가 눌렸는지 확인
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.on_enter_func:
                self.on_enter_func()  # 연결된 함수 실행
            return  # 부모의 이벤트를 호출하지 않음으로써 줄바꿈 방지

        # 엔터 외의 다른 키는 정상적으로 입력되게 함
        super().keyPressEvent(event)
