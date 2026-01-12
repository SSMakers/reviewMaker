from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Dict, Any

import requests
from dotenv import load_dotenv

from external_api.server.models import parse_verify_response, VerifyConfirm, VerifyDenied
from logger.file_logger import logger


def _get_env_path() -> str:
    """
    PyInstaller로 빌드된 환경(sys._MEIPASS)인지, 일반 개발 환경인지 구분하여
    .env 파일의 절대 경로를 반환합니다.
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 임시 폴더 경로
        return os.path.join(sys._MEIPASS, '.env')
    # 일반 개발 환경 (현재 작업 디렉토리 기준)
    return os.path.join(os.getcwd(), '.env')

# .env 파일의 내용을 환경 변수로 로드합니다. (경로 명시)
load_dotenv(_get_env_path())


@dataclass
class ApiConfig:
    base_url: str
    timeout_sec: float


def _load_config() -> ApiConfig:
    base_url = os.getenv("API_BASE_URL")
    if not base_url:
        raise RuntimeError("API_BASE_URL is not set in .env")

    timeout = float(os.getenv("API_TIMEOUT_SEC", "10"))

    return ApiConfig(
        base_url=base_url,
        timeout_sec=timeout,
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

    def _url(self, path: str) -> str:
        return self.config.base_url.rstrip("/") + "/" + path.lstrip("/")

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            r = self.session.post(
                self._url(path),
                json=payload,
                timeout=self.config.timeout_sec,
                verify=False
            )
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
