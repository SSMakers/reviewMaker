from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import pandas as pd


DEFAULT_WRITER_NAME = "이재용"
DEFAULT_CLIENT_IP = "127.0.0.1"
EXCEL_COLUMN_TITLE = "제목"
EXCEL_COLUMN_WRITER = "작성자"
EXCEL_COLUMN_CONTENT = "리뷰내용"
EXCEL_COLUMN_RATING = "별점"
EXCEL_COLUMN_CREATED_DATE = "날짜"
EXCEL_COLUMN_IMAGE_URL = "하이퍼링크"


@dataclass(frozen=True)
class ArticleBuildResult:
    article: dict[str, Any] | None
    skipped_reason: str | None = None


def _cell_to_string(value: Any, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value).strip()


def _cell_to_optional_value(value: Any) -> Any | None:
    if pd.isna(value):
        return None
    return value


def _cell_to_optional_string(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _cell_to_optional_int(value: Any) -> int | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _cell_to_optional_date_string(value: Any) -> str | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


def build_article_from_excel_row(
        row: pd.Series,
        *,
        product_no: int,
        image_url_override: str | None = None,
) -> ArticleBuildResult:
    title = _cell_to_string(row.get(EXCEL_COLUMN_TITLE, ""))
    writer_name = _cell_to_string(row.get(EXCEL_COLUMN_WRITER, DEFAULT_WRITER_NAME), DEFAULT_WRITER_NAME)
    content = _cell_to_string(row.get(EXCEL_COLUMN_CONTENT, ""))
    rating = _cell_to_optional_int(row.get(EXCEL_COLUMN_RATING))
    created_date = _cell_to_optional_date_string(row.get(EXCEL_COLUMN_CREATED_DATE))
    image_url = image_url_override if image_url_override is not None else _cell_to_optional_string(row.get(EXCEL_COLUMN_IMAGE_URL))

    if not title:
        title = content[:20] if len(content) > 20 else content
        if not title:
            return ArticleBuildResult(article=None, skipped_reason="제목과 본문이 모두 비어있습니다.")

    article_data: dict[str, Any] = {
        "product_no": product_no,
        "writer": writer_name,
        "title": title,
        "content": content,
        "client_ip": DEFAULT_CLIENT_IP,
    }

    if rating is not None:
        article_data["rating"] = rating
    if created_date:
        article_data["created_date"] = created_date
    if image_url:
        article_data["image_url"] = image_url

    return ArticleBuildResult(article=article_data)
