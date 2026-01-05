from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox


class UUIDInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UUID 수동 입력")
        self.setFixedWidth(300)

        layout = QVBoxLayout()

        self.label = QLabel("시스템 UUID를 입력해주세요:")
        layout.addWidget(self.label)

        self.input_field = QLineEdit()
        layout.addWidget(self.input_field)

        # OK, Cancel 버튼 설정
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)  # OK 누르면 완료
        self.buttons.rejected.connect(self.reject)  # Cancel 누르면 닫기
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def get_uuid(self):
        return self.input_field.text()