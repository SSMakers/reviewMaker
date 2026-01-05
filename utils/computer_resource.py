import subprocess
import platform


def get_system_uuid():
    """시스템의 고유 UUID를 가져옵니다."""
    try:
        os_type = platform.system()
        if os_type == "Windows":
            # 윈도우: wmic 명령 사용
            cmd = 'wmic csproduct get uuid'
            uuid = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
        elif os_type == "Darwin":  # Mac
            # 맥: ioreg 명령 사용
            cmd = "ioreg -rd1 -c IOPlatformExpertDevice | grep -E 'IOPlatformUUID'"
            output = subprocess.check_output(cmd, shell=True).decode()
            uuid = output.split('"')[-2]
        else:
            uuid = None
        return uuid
    except Exception as e:
        print(f"UUID 추출 실패: {e}")
        return None
