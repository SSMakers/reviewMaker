from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd


EXCEL_COLUMN_IMAGE_FILENAME = "이미지파일명"


class ImageMappingMode(str, Enum):
    EXCEL_URL_ONLY = "excel_url_only"
    FILENAME_ONLY = "filename_only"
    URL_THEN_FILENAME = "url_then_filename"


@dataclass(frozen=True)
class ImageResolution:
    image_url: str | None = None
    upload_path: Path | None = None
    warning: str | None = None


def _string_cell(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _resolve_image_file(image_folder_path: str | None, filename: str) -> Path | None:
    if not image_folder_path or not filename:
        return None

    candidate = Path(image_folder_path).expanduser() / filename
    if candidate.is_file():
        return candidate

    return None


def resolve_review_image(
        row: pd.Series,
        *,
        image_folder_path: str | None,
        mapping_mode: ImageMappingMode,
        image_url_column: str,
) -> ImageResolution:
    excel_url = _string_cell(row.get(image_url_column))
    filename = _string_cell(row.get(EXCEL_COLUMN_IMAGE_FILENAME))

    if mapping_mode == ImageMappingMode.EXCEL_URL_ONLY:
        return ImageResolution(image_url=excel_url or None)

    if mapping_mode == ImageMappingMode.URL_THEN_FILENAME and excel_url:
        return ImageResolution(image_url=excel_url)

    upload_path = _resolve_image_file(image_folder_path, filename)
    if upload_path:
        return ImageResolution(upload_path=upload_path)

    if filename and not image_folder_path:
        return ImageResolution(warning=f"이미지 폴더가 선택되지 않아 '{filename}' 파일을 찾을 수 없습니다.")

    if filename:
        return ImageResolution(warning=f"선택한 이미지 폴더에서 '{filename}' 파일을 찾을 수 없습니다.")

    if mapping_mode == ImageMappingMode.FILENAME_ONLY and excel_url:
        return ImageResolution(warning="파일명 매칭 모드에서는 하이퍼링크 URL을 사용하지 않습니다.")

    return ImageResolution()
