from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox

from logger.file_logger import logger
from version import Version


DEFAULT_LATEST_JSON_URL = "https://ssmakers.github.io/reviewMaker/latest.json"
UPDATE_TIMEOUT_SEC = 10
DOWNLOAD_CHUNK_SIZE = 1024 * 256


def get_current_version() -> str:
    return f"{Version.MAJOR}.{Version.MINOR}.{Version.PATCH}"


def _version_tuple(version_text: str) -> tuple[int, int, int]:
    parts = version_text.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version: {version_text}")
    return tuple(int(part) for part in parts)


def is_newer_version(remote_version: str, current_version: str) -> bool:
    return _version_tuple(remote_version) > _version_tuple(current_version)


@dataclass(frozen=True)
class UpdateAsset:
    url: str
    sha256: str | None = None


@dataclass(frozen=True)
class UpdateMetadata:
    version: str
    published_at: str | None
    release_notes_url: str | None
    asset: UpdateAsset

    @classmethod
    def from_latest_json(cls, data: dict[str, Any], os_name: str) -> "UpdateMetadata":
        asset_data = data.get(os_name)
        if not isinstance(asset_data, dict):
            raise ValueError(f"latest.json does not contain asset info for {os_name}")

        url = asset_data.get("url")
        if not url:
            raise ValueError(f"latest.json {os_name}.url is empty")

        return cls(
            version=str(data["version"]),
            published_at=data.get("published_at"),
            release_notes_url=data.get("release_notes_url"),
            asset=UpdateAsset(
                url=str(url),
                sha256=asset_data.get("sha256"),
            ),
        )


def _env_path() -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, ".env")
    return os.path.join(os.getcwd(), ".env")


def _latest_json_url() -> str:
    load_dotenv(_env_path())
    return os.getenv("UPDATE_LATEST_URL", DEFAULT_LATEST_JSON_URL).strip()


def _current_os_key() -> str | None:
    system = platform.system()
    if system == "Windows":
        return "windows"
    if system == "Darwin":
        return "macos"
    return None


class UpdateCheckWorker(QThread):
    update_available = pyqtSignal(object)
    no_update = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, latest_json_url: str, current_version: str):
        super().__init__()
        self.latest_json_url = latest_json_url
        self.current_version = current_version

    def run(self):
        os_key = _current_os_key()
        if os_key is None:
            self.no_update.emit()
            return

        try:
            response = requests.get(self.latest_json_url, timeout=UPDATE_TIMEOUT_SEC)
            response.raise_for_status()
            data = response.json()
            metadata = UpdateMetadata.from_latest_json(data, os_key)
            if is_newer_version(metadata.version, self.current_version):
                self.update_available.emit(metadata)
            else:
                self.no_update.emit()
        except Exception as exc:
            self.error.emit(str(exc))


class UpdateDownloadWorker(QThread):
    downloaded = pyqtSignal(object, str)
    error = pyqtSignal(str)

    def __init__(self, metadata: UpdateMetadata):
        super().__init__()
        self.metadata = metadata

    def run(self):
        try:
            suffix = ".exe" if platform.system() == "Windows" else ".zip"
            download_path = Path(tempfile.gettempdir()) / f"Review_Program_{self.metadata.version}{suffix}"
            with requests.get(self.metadata.asset.url, stream=True, timeout=UPDATE_TIMEOUT_SEC) as response:
                response.raise_for_status()
                with download_path.open("wb") as target:
                    for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        if chunk:
                            target.write(chunk)

            if self.metadata.asset.sha256:
                digest = hashlib.sha256(download_path.read_bytes()).hexdigest()
                if digest.lower() != self.metadata.asset.sha256.lower():
                    raise ValueError("다운로드한 파일의 SHA256 값이 latest.json과 다릅니다.")

            self.downloaded.emit(self.metadata, str(download_path))
        except Exception as exc:
            self.error.emit(str(exc))


class AutoUpdater(QObject):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.check_worker: UpdateCheckWorker | None = None
        self.download_worker: UpdateDownloadWorker | None = None

    def check_in_background(self):
        latest_url = _latest_json_url()
        current_version = get_current_version()
        logger.info(f"업데이트 확인 시작: current={current_version}, url={latest_url}")

        self.check_worker = UpdateCheckWorker(latest_url, current_version)
        self.check_worker.update_available.connect(self._on_update_available)
        self.check_worker.no_update.connect(lambda: logger.info("사용 가능한 업데이트가 없습니다."))
        self.check_worker.error.connect(lambda message: logger.warning(f"업데이트 확인 실패: {message}"))
        self.check_worker.start()

    def _on_update_available(self, metadata: UpdateMetadata):
        current_version = get_current_version()
        answer = QMessageBox.question(
            self.parent_window,
            "새 버전 사용 가능",
            (
                f"Review Writer {metadata.version} 버전이 준비되어 있습니다.\n"
                f"현재 버전: {current_version}\n\n"
                "지금 다운로드하고 업데이트할까요?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.download_worker = UpdateDownloadWorker(metadata)
        self.download_worker.downloaded.connect(self._on_update_downloaded)
        self.download_worker.error.connect(self._on_download_error)
        self.download_worker.start()

    def _on_download_error(self, message: str):
        QMessageBox.warning(
            self.parent_window,
            "업데이트 다운로드 실패",
            f"업데이트 파일을 다운로드하지 못했습니다.\n\n{message}",
        )

    def _on_update_downloaded(self, metadata: UpdateMetadata, download_path: str):
        if not getattr(sys, "frozen", False):
            QMessageBox.information(
                self.parent_window,
                "업데이트 다운로드 완료",
                (
                    "개발 실행 환경이라 자동 교체는 건너뜁니다.\n"
                    f"다운로드 파일: {download_path}"
                ),
            )
            return

        try:
            self._apply_update(Path(download_path))
        except Exception as exc:
            QMessageBox.critical(
                self.parent_window,
                "업데이트 적용 실패",
                f"업데이트를 적용하지 못했습니다.\n\n{exc}",
            )

    def _apply_update(self, download_path: Path):
        system = platform.system()
        current_executable = Path(sys.executable).resolve()
        if system == "Windows":
            self._apply_windows_update(download_path, current_executable)
        elif system == "Darwin":
            self._apply_macos_update(download_path, current_executable)
        else:
            raise RuntimeError(f"지원하지 않는 OS입니다: {system}")

        QApplication.quit()

    def _apply_windows_update(self, download_path: Path, current_executable: Path):
        script_path = Path(tempfile.gettempdir()) / "review_writer_update.bat"
        script_path.write_text(
            "\n".join([
                "@echo off",
                "timeout /t 2 /nobreak >nul",
                f'copy /Y "{download_path}" "{current_executable}"',
                f'start "" "{current_executable}"',
                'del "%~f0"',
            ]),
            encoding="utf-8",
        )
        subprocess.Popen(
            ["cmd", "/c", "start", "", str(script_path)],
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )

    def _apply_macos_update(self, download_path: Path, current_executable: Path):
        extracted_executable = self._extract_macos_asset(download_path)
        target_path = self._macos_app_bundle(current_executable) or current_executable
        script_path = Path(tempfile.gettempdir()) / "review_writer_update.sh"
        if target_path.suffix == ".app":
            launch_command = f'open "{target_path}"'
            replace_command = f'rm -rf "{target_path}"\ncp -R "{extracted_executable}" "{target_path}"'
        else:
            launch_command = f'nohup "{target_path}" >/dev/null 2>&1 &'
            replace_command = f'cp "{extracted_executable}" "{target_path}"\nchmod +x "{target_path}"'

        script_path.write_text(
            "\n".join([
                "#!/bin/bash",
                "sleep 2",
                replace_command,
                launch_command,
                f'rm -f "{script_path}"',
            ]),
            encoding="utf-8",
        )
        script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
        subprocess.Popen(["/bin/bash", str(script_path)])

    def _extract_macos_asset(self, download_path: Path) -> Path:
        extract_dir = Path(tempfile.gettempdir()) / f"review_writer_update_{os.getpid()}"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(download_path) as archive:
            archive.extractall(extract_dir)

        app_candidates = list(extract_dir.glob("*.app"))
        if app_candidates:
            return app_candidates[0]

        file_candidates = [path for path in extract_dir.iterdir() if path.is_file()]
        if not file_candidates:
            raise RuntimeError("macOS 업데이트 압축 파일 안에서 실행 파일을 찾지 못했습니다.")
        file_candidates[0].chmod(file_candidates[0].stat().st_mode | stat.S_IXUSR)
        return file_candidates[0]

    def _macos_app_bundle(self, executable_path: Path) -> Path | None:
        for parent in [executable_path, *executable_path.parents]:
            if parent.suffix == ".app":
                return parent
        return None
