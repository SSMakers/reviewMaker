import logging
import os
import platform
from pathlib import Path
from logging.handlers import RotatingFileHandler


def default_log_file() -> str:
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        log_dir = home / "Library" / "Logs" / "Review Writer"
    elif system == "Windows":
        log_dir = Path(os.getenv("LOCALAPPDATA", str(home))) / "Review Writer" / "Logs"
    else:
        log_dir = home / ".review-writer" / "logs"
    return str(log_dir / "app.log")

def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

@singleton
class FileLogger:
    def __init__(self, name="GlobalLogger", log_file=None, level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        log_file = log_file or default_log_file()

        if not self.logger.handlers:
            # 포맷 변경: [%(module)s.%(funcName)s:%(lineno)d] 추가
            # 결과 예시: [app.connect:42] - 자동 인증 성공...
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            # 콘솔 핸들러
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # 10MB 로테이팅 파일 핸들러
            log_dir = os.path.dirname(log_file)
            if log_dir:
                try:
                    os.makedirs(log_dir, exist_ok=True)
                except FileExistsError:
                    if not os.path.isdir(log_dir):
                        raise

            file_handler = RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=3, encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger

# 전역 인스턴스
logger = FileLogger().get_logger()
