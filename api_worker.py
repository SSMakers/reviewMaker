import time
import uuid

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from external_api.server.server_api import ServerApi
from image_mapping import ImageMappingMode, resolve_review_image
from logger.file_logger import logger
from review_article_builder import EXCEL_COLUMN_IMAGE_URL, build_article_from_excel_row
from review_preflight import analyze_reviews


BATCH_SIZE = 10
BATCH_DELAY_SEC = 0.5


class ApiWorker(QThread):
    # UI에 진행 상황을 알리기 위한 시그널
    log_signal = pyqtSignal(str)  # 로그 메시지 전송
    progress_signal = pyqtSignal(int)  # 진행률(%) 전송
    finished_signal = pyqtSignal(bool)  # 종료 알림

    def __init__(
            self,
            api_interface,
            file_path,
            board_no,
            product_no,
            *,
            image_folder_path=None,
            image_mapping_mode=ImageMappingMode.URL_THEN_FILENAME,
            device_id=None,
            mall_id=None,
    ):
        super().__init__()
        self.api = api_interface  # Cafe24Api 인스턴스 저장
        self.file_path = file_path
        self.board_no = board_no
        self.product_no = product_no
        self.image_folder_path = image_folder_path
        self.image_mapping_mode = ImageMappingMode(image_mapping_mode)
        self.device_id = device_id
        self.mall_id = mall_id
        self.server_api = None
        self.job_id = f"job_{uuid.uuid4().hex}"
        self.uploaded_image_ids = []

    def _send_batch(self, batch_data, processed_count, total_rows):
        if not batch_data:
            return

        try:
            current_batch_size = len(batch_data)
            response = self.api.create_articles(self.board_no, batch_data)

            if response.status_code in [200, 201]:
                self.log_signal.emit(f"✅ [{processed_count}/{total_rows}] {current_batch_size}건 일괄 전송 성공")
            else:
                error_detail = response.json() if response.content else response.text
                self.log_signal.emit(
                    f"❌ [{processed_count}/{total_rows}] 전송 실패 ({response.status_code}): {error_detail}")

        except Exception as e:
            self.log_signal.emit(f"⚠️ [{processed_count}/{total_rows}] 네트워크 오류: {str(e)}")

        finally:
            time.sleep(BATCH_DELAY_SEC)

    def _upload_image(self, upload_path, row_number):
        if not self.device_id:
            raise RuntimeError("이미지 업로드를 위한 device_id가 없습니다.")
        if not self.mall_id:
            raise RuntimeError("이미지 업로드를 위한 mall_id가 없습니다.")
        if self.server_api is None:
            self.server_api = ServerApi()

        result = self.server_api.upload_review_image(
            file_path=upload_path,
            device_id=self.device_id,
            mall_id=self.mall_id,
            source_row_id=str(row_number),
            job_id=self.job_id,
        )
        self.log_signal.emit(f"🖼️ [{row_number}] 이미지 업로드 완료: {upload_path.name}")
        self.uploaded_image_ids.append(result.image_id)
        return result.url

    def _cleanup_uploaded_images(self):
        if not self.uploaded_image_ids:
            return
        if self.server_api is None:
            self.server_api = ServerApi()

        try:
            result = self.server_api.cleanup_review_images(
                device_id=self.device_id,
                mall_id=self.mall_id,
                image_ids=self.uploaded_image_ids,
                job_id=self.job_id,
            )
            self.log_signal.emit(
                f"Temporary image cleanup complete: deleted={len(result.deleted)}, "
                f"not_found={len(result.not_found)}, failed={len(result.failed)}"
            )
        except Exception as e:
            self.log_signal.emit(f"Temporary image cleanup failed: {str(e)}")

    def run(self):
        success = False
        try:
            self.log_signal.emit(f"🚀 작업을 시작합니다. 파일: {self.file_path}")

            df = pd.read_excel(self.file_path)
            total_rows = len(df)
            self.log_signal.emit(f"📊 총 {total_rows}개의 데이터를 발견했습니다.")
            if total_rows == 0:
                self.log_signal.emit("❌ 등록할 데이터가 없습니다.")
                return

            preflight = analyze_reviews(
                df,
                product_no=self.product_no,
                image_folder_path=self.image_folder_path,
                mapping_mode=self.image_mapping_mode,
            )
            for line in preflight.to_log_lines():
                self.log_signal.emit(line)

            batch_data = []
            for index, row in df.iterrows():
                row_number = index + 1
                base_result = build_article_from_excel_row(row, product_no=self.product_no)
                if base_result.article is None:
                    logger.warning(f"{index}열 건너뜀: {base_result.skipped_reason}")
                    progress = int((row_number / total_rows) * 100)
                    self.progress_signal.emit(progress)
                    continue

                image = resolve_review_image(
                    row,
                    image_folder_path=self.image_folder_path,
                    mapping_mode=self.image_mapping_mode,
                    image_url_column=EXCEL_COLUMN_IMAGE_URL,
                )
                if image.warning:
                    self.log_signal.emit(f"⚠️ [{row_number}] {image.warning}")

                image_url = image.image_url
                if image.upload_path:
                    image_url = self._upload_image(image.upload_path, row_number)

                result = build_article_from_excel_row(
                    row,
                    product_no=self.product_no,
                    image_url_override=image_url,
                )

                batch_data.append(result.article)

                if len(batch_data) >= BATCH_SIZE:
                    self._send_batch(batch_data, row_number, total_rows)
                    batch_data = []

                # UI 업데이트를 위한 진행률 계산
                progress = int((row_number / total_rows) * 100)
                self.progress_signal.emit(progress)

            self._send_batch(batch_data, total_rows, total_rows)
            success = True

        except Exception as e:
            self.log_signal.emit(f"🔥 치명적 오류 발생: {str(e)}")
        finally:
            self._cleanup_uploaded_images()
            self.finished_signal.emit(success)
