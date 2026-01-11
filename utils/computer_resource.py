import subprocess
import platform

from logger.file_logger import logger


def get_system_uuid():
    """시스템의 고유 UUID를 가져옵니다."""
    try:
        os_type = platform.system()
        if os_type == "Windows":
            # 윈도우: wmic는 deprecated 되었으므로 PowerShell 명령 사용 (Get-CimInstance)
            cmd = 'powershell -Command "Get-CimInstance -Class Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID"'
            uuid = subprocess.check_output(cmd, shell=True).decode().strip()
        elif os_type == "Darwin":  # Mac
            # 맥: ioreg 명령 사용
            cmd = "ioreg -rd1 -c IOPlatformExpertDevice | grep -E 'IOPlatformUUID'"
            output = subprocess.check_output(cmd, shell=True).decode()
            uuid = output.split('"')[-2]
        else:
            uuid = None
        return uuid
    except Exception as e:
        logger.error(f"UUID 추출 실패: {e}")
        return None
