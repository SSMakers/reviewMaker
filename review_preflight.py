from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from image_mapping import ImageMappingMode, SUPPORTED_IMAGE_EXTENSIONS, resolve_review_image
from review_article_builder import EXCEL_COLUMN_IMAGE_URL, build_article_from_excel_row


@dataclass(frozen=True)
class ReviewPreflightSummary:
    total_rows: int
    valid_rows: int
    skipped_rows: int
    url_image_rows: int
    upload_image_rows: int
    missing_image_rows: int
    warning_count: int

    def to_log_lines(self) -> list[str]:
        return [
            "🔎 사전 검사 완료",
            f"- 전체 행: {self.total_rows}건",
            f"- 등록 가능: {self.valid_rows}건",
            f"- 건너뜀: {self.skipped_rows}건",
            f"- URL 이미지: {self.url_image_rows}건",
            f"- 업로드 필요 이미지: {self.upload_image_rows}건",
            f"- 이미지 없음: {self.missing_image_rows}건",
            f"- 이미지 경고: {self.warning_count}건",
        ]


def analyze_reviews(
        df: pd.DataFrame,
        *,
        product_no: int,
        image_folder_path: str | None,
        mapping_mode: ImageMappingMode,
) -> ReviewPreflightSummary:
    valid_rows = 0
    skipped_rows = 0
    url_image_rows = 0
    upload_image_rows = 0
    missing_image_rows = 0
    warning_count = 0

    for _, row in df.iterrows():
        article_result = build_article_from_excel_row(row, product_no=product_no)
        if article_result.article is None:
            skipped_rows += 1
            continue

        valid_rows += 1
        image = resolve_review_image(
            row,
            image_folder_path=image_folder_path,
            mapping_mode=mapping_mode,
            image_url_column=EXCEL_COLUMN_IMAGE_URL,
        )
        if image.image_url:
            url_image_rows += 1
        elif image.upload_path:
            upload_image_rows += 1
        else:
            missing_image_rows += 1

        if image.warning:
            warning_count += 1

    return ReviewPreflightSummary(
        total_rows=len(df),
        valid_rows=valid_rows,
        skipped_rows=skipped_rows,
        url_image_rows=url_image_rows,
        upload_image_rows=upload_image_rows,
        missing_image_rows=missing_image_rows,
        warning_count=warning_count,
    )


def count_image_files(image_folder_path: str | None) -> int:
    if not image_folder_path:
        return 0
    folder = Path(image_folder_path)
    if not folder.is_dir():
        return 0
    return sum(1 for item in folder.iterdir() if item.is_file() and item.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS)
