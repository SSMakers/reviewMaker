from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd


EXCEL_COLUMN_IMAGE_FILENAME = "이미지파일명"
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


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


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _resolve_image_file(image_folder_path: str | None, filename: str) -> Path | None:
    if not image_folder_path or not filename:
        return None

    candidate = Path(image_folder_path).expanduser() / filename
    if candidate.is_file():
        return candidate

    folder = Path(image_folder_path).expanduser()
    if not folder.is_dir():
        return None

    filename_lower = filename.lower()
    for item in folder.iterdir():
        if item.is_file() and item.name.lower() == filename_lower:
            return item

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
    filename_candidate = filename

    if excel_url and not _is_http_url(excel_url) and not filename_candidate:
        filename_candidate = excel_url

    if mapping_mode == ImageMappingMode.EXCEL_URL_ONLY:
        if not excel_url:
            return ImageResolution()
        if _is_http_url(excel_url):
            return ImageResolution(image_url=excel_url)
        return ImageResolution(warning=f"'{excel_url}' 값은 사용할 수 있는 이미지 URL이 아닙니다.")

    if mapping_mode == ImageMappingMode.URL_THEN_FILENAME and excel_url and _is_http_url(excel_url):
        return ImageResolution(image_url=excel_url)

    if filename_candidate and Path(filename_candidate).suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        return ImageResolution(warning=f"'{filename_candidate}' 파일은 지원하지 않는 이미지 형식입니다.")

    upload_path = _resolve_image_file(image_folder_path, filename_candidate)
    if upload_path:
        return ImageResolution(upload_path=upload_path)

    if filename_candidate and not image_folder_path:
        return ImageResolution(warning=f"이미지 폴더가 선택되지 않아 '{filename_candidate}' 파일을 찾을 수 없습니다.")

    if filename_candidate:
        return ImageResolution(warning=f"선택한 이미지 폴더에서 '{filename_candidate}' 파일을 찾을 수 없습니다.")

    if mapping_mode == ImageMappingMode.FILENAME_ONLY and excel_url:
        return ImageResolution(warning="파일명 매칭 모드에서는 하이퍼링크 URL을 사용하지 않습니다.")

    return ImageResolution()
