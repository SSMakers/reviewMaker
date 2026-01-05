import re
import uuid


def validate_uuid_format(uuid_string):
    """UUID 문자열의 형식이 올바른지 확인"""
    # 1. 정규표현식 검사 (8-4-4-4-12 구성 및 16진수 여부)
    pattern = re.compile(r'^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$', re.I)
    if not bool(pattern.match(uuid_string)):
        return False

    # 2. uuid 객체 변환 시도 (논리적 유효성)
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False