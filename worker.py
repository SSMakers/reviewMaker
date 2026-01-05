import pandas as pd
import requests
import time
from PyQt6.QtCore import QThread, pyqtSignal


class ApiWorker(QThread):
    # UI에 진행 상황을 알리기 위한 시그널
    log_signal = pyqtSignal(str)  # 로그 메시지 전송
    progress_signal = pyqtSignal(int)  # 진행률(%) 전송
    finished_signal = pyqtSignal(bool)  # 종료 알림

    def __init__(self, file_path, board_no, product_no):
        super().__init__()
        self.file_path = file_path
        self.board_no = board_no
        self.product_no = product_no
        self.api_url = "https://api.your-service.com/reviews"  # 실제 API 주소로 변경

    def run(self):
        try:
            self.log_signal.emit(f"🚀 작업을 시작합니다. 파일: {self.file_path}")

            # 1. 엑셀 파일 읽기
            df = pd.read_excel(self.file_path)
            total_rows = len(df)
            self.log_signal.emit(f"📊 총 {total_rows}개의 데이터를 발견했습니다.")

            for index, row in df.iterrows():
                # 2. 전송할 데이터 구성 (엑셀 컬럼명이 'content'라고 가정)
                payload = {
                    "board_id": self.board_no,
                    "product_id": self.product_no,
                    "author": row.get("작성자", ""),  # 엑셀의 'content' 컬럼 읽기
                    "content": row.get("리뷰내용", ""),
                    "num_star": row.get("별점", ""),
                    "date": row.get("날짜", ""),
                    "image_url": row.get("하이퍼링크", "")
                }
                print(payload)

                # 3. API 요청
                try:
                    # 실제 환경에선 auth token 등이 필요할 수 있습니다.
                    response = requests.post(self.api_url, json=payload, timeout=10)

                    if response.status_code == 200 or response.status_code == 201:
                        self.log_signal.emit(f"✅ [{index + 1}/{total_rows}] 전송 성공")
                    else:
                        self.log_signal.emit(f"❌ [{index + 1}/{total_rows}] 실패 (상태코드: {response.status_code})")

                except Exception as e:
                    self.log_signal.emit(f"⚠️ [{index + 1}/{total_rows}] 네트워크 오류: {str(e)}")

                # UI 업데이트를 위한 진행률 계산
                progress = int(((index + 1) / total_rows) * 100)
                self.progress_signal.emit(progress)

                # 서버 과부하 방지를 위한 미세한 대기 (선택 사항)
                time.sleep(0.1)

            self.finished_signal.emit(True)

        except Exception as e:
            self.log_signal.emit(f"🔥 치명적 오류 발생: {str(e)}")
            self.finished_signal.emit(False)