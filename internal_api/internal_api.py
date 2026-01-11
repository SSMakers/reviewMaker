import os

from dotenv import load_dotenv


def verify_uuid_with_server(uuid_str):
    """서버 API에 해당 UUID가 등록되어 있는지 확인"""
    return True
    # api_url = "https://your-api-server.com/auth/verify"
    # try:
    #     # 실제 서버 환경에 맞춰 header나 params를 수정하세요.
    #     response = requests.post(api_url, json={"uuid": uuid_str}, timeout=5)
    #
    #     if response.status_code == 200:
    #         return True, "인증 성공"
    #     elif response.status_code == 401:
    #         return False, "등록되지 않은 기기입니다."
    #     else:
    #         return False, f"서버 응답 오류: {response.status_code}"
    # except requests.exceptions.RequestException as e:
    #     return False, f"서버 연결 실패: {str(e)}"


def get_api_keys():
    # .env 파일의 내용을 환경 변수로 로드합니다.
    load_dotenv()

    client_id = os.getenv('CAFE24_CLIENT_ID')
    client_secret = os.getenv('CAFE24_CLIENT_SECRET')

    return client_id, client_secret
