from __future__ import annotations

import mimetypes
import os
from pathlib import Path
import sys
from dataclasses import dataclass
from typing import Dict, Any

import requests
from dotenv import load_dotenv

from external_api.server.models import (
    ReviewImageCleanupResult,
    ReviewImageUploadResult,
    parse_verify_response,
    VerifyConfirm,
    VerifyDenied,
)
from logger.file_logger import logger

def _get_env_path() -> str:
    """
    PyInstaller로 빌드된 환경(sys._MEIPASS)인지, 일반 개발 환경인지 구분하여
    .env 파일의 절대 경로를 반환합니다.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, '.env')
    return os.path.join(os.getcwd(), '.env')

load_dotenv(_get_env_path())

def _get_cert_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.getcwd(), relative_path)

@dataclass
class ApiConfig:
    base_url: str
    timeout_sec: float
    upload_timeout_sec: float
    api_ca_cert_path: str | None


def _load_config() -> ApiConfig:
    base_url = os.getenv("API_BASE_URL")
    if not base_url:
        raise RuntimeError("API_BASE_URL is not set in .env")

    timeout = float(os.getenv("API_TIMEOUT_SEC", "10"))
    upload_timeout = float(os.getenv("API_UPLOAD_TIMEOUT_SEC", "60"))
    cert_env = os.getenv("API_CA_CERT_PATH")

    use_default_trust = cert_env is None or cert_env.strip().lower() in {"", "default", "system", "none"}
    api_ca_cert_path = None if use_default_trust else _get_cert_path(cert_env)
    if api_ca_cert_path and not os.path.exists(api_ca_cert_path):
        raise RuntimeError(f"CA cert not found: {api_ca_cert_path}")

    return ApiConfig(
        base_url=base_url,
        timeout_sec=timeout,
        upload_timeout_sec=upload_timeout,
        api_ca_cert_path=api_ca_cert_path,
    )


# ---- Error Types ----
class ApiError(Exception):
    """Base API error."""


class NetworkError(ApiError):
    """Cannot reach server (connection error, DNS, etc.)."""


class TimeoutError(ApiError):
    """Request timed out."""


class HttpError(ApiError):
    """Non-2xx HTTP response."""

    def __init__(self, status_code: int, message: str, payload: Any = None):
        super().__init__(f"{status_code}: {message}")
        self.status_code = status_code
        self.payload = payload


class BadResponseError(ApiError):
    """Response is not valid JSON (or unexpected format)."""

    def __init__(self, message: str, raw_text: str = ""):
        super().__init__(message)
        self.raw_text = raw_text


class ServerApi:
    def __init__(self):
        self.config = _load_config()
        self.session = requests.Session()
        if getattr(self.config, "api_ca_cert_path", None):
            self.session.verify = str(self.config.api_ca_cert_path)

    def _url(self, path: str) -> str:
        return self.config.base_url.rstrip("/") + "/" + path.lstrip("/")

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            r = self.session.post(
                self._url(path),
                json=payload,
                timeout=self.config.timeout_sec,
            )
        except requests.exceptions.SSLError as e:
            raise NetworkError(
                "TLS certificate verification failed. "
                "Check API_BASE_URL host and API_CA_CERT_PATH in .env."
            ) from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Timeout after {self.config.timeout_sec}s") from e
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Cannot connect to server: {e}") from e

        try:
            data = r.json() if r.content else {}
        except Exception:
            ct = r.headers.get("Content-Type", "")
            # ✅ 상태코드/콘텐츠타입/앞부분 포함
            raise BadResponseError(
                f"Response is not JSON (status={r.status_code}, content-type={ct})",
                raw_text=(r.text or "")[:1000],
            )

        if not r.ok:
            msg = data.get("detail") or data.get("message") or r.reason
            raise HttpError(r.status_code, msg, payload=data)

        return data

    def _post_multipart(self, path: str, *, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

        try:
            with file_path.open("rb") as file_obj:
                files = {
                    "file": (file_path.name, file_obj, content_type),
                }
                r = self.session.post(
                    self._url(path),
                    data=data,
                    files=files,
                    timeout=self.config.upload_timeout_sec,
                )
        except requests.exceptions.SSLError as e:
            raise NetworkError(
                "TLS certificate verification failed. "
                "Check API_BASE_URL host and API_CA_CERT_PATH in .env."
            ) from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Timeout after {self.config.upload_timeout_sec}s") from e
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Cannot connect to server: {e}") from e
        except OSError as e:
            raise ApiError(f"Cannot read upload file: {file_path}") from e

        try:
            response_data = r.json() if r.content else {}
        except Exception:
            ct = r.headers.get("Content-Type", "")
            raw_text = (r.text or "")[:1000]
            if not r.ok:
                raise HttpError(r.status_code, r.reason, payload={"content_type": ct, "raw_text": raw_text})
            raise BadResponseError(
                f"Response is not JSON (status={r.status_code}, content-type={ct})",
                raw_text=raw_text,
            )

        if not r.ok:
            msg = response_data.get("detail") or response_data.get("message") or r.reason
            raise HttpError(r.status_code, msg, payload=response_data)

        return response_data

    # -------------------------
    # POST /member/request
    # -------------------------
    def member_request(
            self,
            *,
            device_id: str,
            plan: str,
            client_id: str,
            secret_key: str,
            mall_id: str,
            redirect_url: str,
    ) -> Dict[str, Any]:
        return self._post("/member/request", {
            "device_id": device_id,
            "plan": plan,
            "client_id": client_id,
            "secret_key": secret_key,
            "mall_id": mall_id,
            "redirect_url": redirect_url,
        })

    # -------------------------
    # POST /auth/verify
    # -------------------------
    def auth_verify(self, *, device_id: str) -> VerifyConfirm | VerifyDenied:
        payload = {"device_id": device_id}
        data = self._post("/auth/verify", payload)  # 여기서 네트워크/HTTP 예외는 raise
        result = parse_verify_response(data)

        if isinstance(result, VerifyConfirm):
            logger.info(f"인증 확인: 남은일수={result.remaining_days}")
        elif isinstance(result, VerifyDenied):
            logger.info(f"{device_id} 인증 실패 : {result.reason}")

        return result

    # -------------------------
    # POST /review/image/upload
    # -------------------------
    def upload_review_image(
            self,
            *,
            file_path: str | Path,
            device_id: str,
            mall_id: str,
            source_row_id: str | None = None,
            job_id: str | None = None,
    ) -> ReviewImageUploadResult:
        payload = {
            "device_id": device_id,
            "mall_id": mall_id,
        }
        if source_row_id:
            payload["source_row_id"] = source_row_id
        if job_id:
            payload["job_id"] = job_id

        data = self._post_multipart(
            "/review/image/upload",
            data=payload,
            file_path=Path(file_path),
        )
        return ReviewImageUploadResult.from_dict(data)

    # -------------------------
    # POST /review/image/cleanup
    # -------------------------
    def cleanup_review_images(
            self,
            *,
            device_id: str,
            mall_id: str,
            image_ids: list[str],
            job_id: str | None = None,
    ) -> ReviewImageCleanupResult:
        payload: Dict[str, Any] = {
            "device_id": device_id,
            "mall_id": mall_id,
            "image_ids": image_ids,
        }
        if job_id:
            payload["job_id"] = job_id

        data = self._post("/review/image/cleanup", payload)
        return ReviewImageCleanupResult.from_dict(data)
