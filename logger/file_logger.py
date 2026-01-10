import logging
import os
from logging.handlers import RotatingFileHandler

def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

@singleton
class FileLogger:
    def __init__(self, name="GlobalLogger", log_file="logs/app.log", level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

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
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            file_handler = RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=3, encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger

# 전역 인스턴스
logger = FileLogger().get_logger()