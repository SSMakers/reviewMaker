from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any


GITHUB_API_URL = "https://api.github.com"
DEFAULT_WORKFLOW_FILE = "release.yml"


def _response(status_code: int, body: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(body, dict):
        body_text = json.dumps(body, ensure_ascii=False)
        content_type = "application/json"
    else:
        body_text = body
        content_type = "text/plain; charset=utf-8"

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": content_type},
        "body": body_text,
    }


def _header(event: dict[str, Any], name: str) -> str:
    headers = event.get("headers") or {}
    lower_name = name.lower()
    for key, value in headers.items():
        if key.lower() == lower_name:
            return value or ""
    return ""


def _raw_body(event: dict[str, Any]) -> str:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        import base64

        return base64.b64decode(body).decode("utf-8")
    return body


def _verify_slack_signature(event: dict[str, Any], body: str):
    signing_secret = os.environ["SLACK_SIGNING_SECRET"]
    timestamp = _header(event, "X-Slack-Request-Timestamp")
    signature = _header(event, "X-Slack-Signature")

    if not timestamp or not signature:
        raise ValueError("Missing Slack signature headers")

    if abs(time.time() - int(timestamp)) > 60 * 5:
        raise ValueError("Slack request timestamp is too old")

    base = f"v0:{timestamp}:{body}".encode("utf-8")
    digest = hmac.new(signing_secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid Slack signature")


def _parse_slack_payload(body: str) -> dict[str, str]:
    parsed = urllib.parse.parse_qs(body)
    return {key: values[0] for key, values in parsed.items() if values}


def _assert_user_allowed(user_id: str):
    allowed = os.getenv("SLACK_ALLOWED_USER_IDS", "").strip()
    if not allowed:
        return
    allowed_ids = {item.strip() for item in allowed.split(",") if item.strip()}
    if user_id not in allowed_ids:
        raise PermissionError("이 Slack 사용자는 배포 권한이 없습니다.")


def _build_release_notes(text: str, user_name: str) -> str:
    clean_text = text.strip()
    if clean_text in {"배포해", "deploy", "release"}:
        return f"Slack 배포 요청 by {user_name}"
    return f"Slack 배포 요청 by {user_name}\n\n{clean_text}"


def _trigger_release_workflow(release_notes: str):
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    workflow_file = os.getenv("GITHUB_RELEASE_WORKFLOW", DEFAULT_WORKFLOW_FILE)
    ref = os.getenv("GITHUB_RELEASE_REF", "main")

    url = f"{GITHUB_API_URL}/repos/{repository}/actions/workflows/{workflow_file}/dispatches"
    payload = json.dumps({
        "ref": ref,
        "inputs": {"release_notes": release_notes},
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "review-writer-slack-release-bot",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status not in {200, 201, 202, 204}:
            raise RuntimeError(f"GitHub workflow dispatch failed: {response.status}")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        body = _raw_body(event)
        _verify_slack_signature(event, body)
        payload = _parse_slack_payload(body)
        text = payload.get("text", "").strip()
        user_id = payload.get("user_id", "")
        user_name = payload.get("user_name", user_id or "unknown")

        _assert_user_allowed(user_id)

        if text not in {"배포해", "deploy", "release"} and not text.startswith("배포해 "):
            return _response(
                200,
                "사용법: /review-writer-release 배포해 또는 /review-writer-release 배포해 이번 수정 내용",
            )

        _trigger_release_workflow(_build_release_notes(text, user_name))
        return _response(200, "Release workflow를 실행했습니다. GitHub Actions와 draft release를 확인해주세요.")
    except PermissionError as exc:
        return _response(200, str(exc))
    except Exception as exc:
        return _response(500, f"배포 요청 처리 실패: {exc}")
