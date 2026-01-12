import time

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from logger.file_logger import logger


class ApiWorker(QThread):
    # UI에 진행 상황을 알리기 위한 시그널
    log_signal = pyqtSignal(str)  # 로그 메시지 전송
    progress_signal = pyqtSignal(int)  # 진행률(%) 전송
    finished_signal = pyqtSignal(bool)  # 종료 알림

    def __init__(self, api_interface, file_path, board_no, product_no):
        super().__init__()
        self.api = api_interface  # Cafe24Api 인스턴스 저장
        self.file_path = file_path
        self.board_no = board_no
        self.product_no = product_no

    def run(self):
        try:
            self.log_signal.emit(f"🚀 작업을 시작합니다. 파일: {self.file_path}")

            # 1. 엑셀 파일 읽기
            df = pd.read_excel(self.file_path)
            total_rows = len(df)
            self.log_signal.emit(f"📊 총 {total_rows}개의 데이터를 발견했습니다.")

            batch_data = []  # 데이터를 모을 리스트
            for index, row in df.iterrows():
                # 2. 데이터 추출 및 전처리
                # Pandas의 NaN(Not a Number) 값은 JSON 표준이 아니므로 None이나 빈 문자열로 변환해야 합니다.
                title_val = row.get("제목", "")
                title = str(title_val).strip() if not pd.isna(title_val) else ""

                writer_val = row.get("작성자", "이재용")
                writer_name = str(writer_val) if not pd.isna(writer_val) else "이재용"

                content_val = row.get("리뷰내용", "")
                content = str(content_val) if not pd.isna(content_val) else ""

                rating = row.get("별점")
                if pd.isna(rating): rating = None

                created_date = row.get("날짜")
                if pd.isna(created_date): created_date = None

                image_url = row.get("하이퍼링크")
                if pd.isna(image_url): image_url = None

                # 제목 처리 로직: 제목이 비어있으면 본문 앞 20자 사용
                if not title:
                    title = content[:20] if len(content) > 20 else content
                    if not title:  # 본문도 비어있을 경우 방어 코드
                        logger.warning(f"{index}열 제목, 본문 모두 빈칸입니다.")
                        continue

                # 개별 게시글 데이터 구성 (API 스펙에 맞춤)
                article_data = {
                    "product_no": self.product_no,
                    "writer": writer_name,
                    "title": title,
                    "content": content,
                    "client_ip": "127.0.0.1"
                }
                if rating:
                    article_data["rating"] = int(rating)
                if created_date:
                    article_data["created_date"] = created_date
                if image_url:
                    article_data["image_url"] = image_url

                batch_data.append(article_data)

                # 3. 배치 전송 (10개가 모이거나, 마지막 데이터일 때)
                if len(batch_data) >= 10 or (index + 1) == total_rows:
                    try:
                        current_batch_size = len(batch_data)
                        response = self.api.create_articles(self.board_no, batch_data)

                        if response.status_code in [200, 201]:
                            self.log_signal.emit(f"✅ [{index + 1}/{total_rows}] {current_batch_size}건 일괄 전송 성공")
                        else:
                            error_detail = response.json() if response.content else response.text
                            self.log_signal.emit(
                                f"❌ [{index + 1}/{total_rows}] 전송 실패 ({response.status_code}): {error_detail}")

                    except Exception as e:
                        self.log_signal.emit(f"⚠️ [{index + 1}/{total_rows}] 네트워크 오류: {str(e)}")
                    
                    finally:
                        batch_data = []  # 배치 초기화
                        # 서버 과부하 방지를 위한 대기 (배치 단위이므로 조금 더 여유를 둠)
                        time.sleep(0.5)

                # UI 업데이트를 위한 진행률 계산
                progress = int(((index + 1) / total_rows) * 100)
                self.progress_signal.emit(progress)

            self.finished_signal.emit(True)

        except Exception as e:
            self.log_signal.emit(f"🔥 치명적 오류 발생: {str(e)}")
            self.finished_signal.emit(False)
