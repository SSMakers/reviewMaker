import base64
import json
import webbrowser

import requests

from external_api.utils.url_utils import get_access_refresh_token
from internal_api.internal_api import get_api_keys
from logger.file_logger import logger


class Cafe24Api:
    def __init__(self, mall_id):
        self.mall_id = mall_id
        self.client_id, self.client_secret = get_api_keys()
        self.access_token = None
        self.refresh_token = None
        self.redirect_uri = f"https://{mall_id}.cafe24.com/order/basket.html"
        self.base_url = f"https://{mall_id}.cafe24api.com/api/v2"
        self.api_base_url = f"https://{mall_id}.cafe24api.com/api/v2/admin"

    def get_authorization_url(self, state="manageMall",
                              scope="mall.write_community,mall.read_community,mall.read_product"):
        """
        1단계: 사용자 인증을 위한 브라우저 접속용 URL 생성
        """
        auth_url = (
            f"https://{self.mall_id}.cafe24api.com/api/v2/oauth/authorize?"
            f"response_type=code&"
            f"client_id={self.client_id}&"
            f"state={state}&"
            f"redirect_uri={self.redirect_uri}&"
            f"scope={scope}"
        )

        logger.info(f"브라우저를 엽니다: {auth_url}")
        webbrowser.open(auth_url)

        return auth_url

    def fetch_access_token(self, auth_code):
        """
        2단계: 브라우저에서 받아온 code를 이용해 액세스 토큰 발급
        """
        token_url = f"{self.base_url}/oauth/token"

        # Basic Auth Header 설정 (client_id:client_secret을 base64 인코딩)
        auth_str = f"{self.client_id}:{self.client_secret}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri
        }

        response = requests.post(token_url, headers=headers, data=data)
        response_json = response.json()

        self.access_token, self.refresh_token = get_access_refresh_token(response_json)
        if self.access_token is None or self.refresh_token is None:
            logger.error(f"❌ access, refresh token 업데이트 실패")
            return False

        return True

    def get_review_board_articles(self, board_no, limit=10):
        """
        특정 게시판(board_no)의 게시글 목록을 가져옵니다.
        """
        review_board_url = f"{self.api_base_url}/boards/4/articles"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Cafe24-Api-Version": "2025-12-01"  # 카페24 권장 버전 헤더
        }

        try:
            response = requests.get(review_board_url, headers=headers)
            response.raise_for_status()  # 200 OK가 아니면 에러 발생
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "detail": response.text if response else "No response"}