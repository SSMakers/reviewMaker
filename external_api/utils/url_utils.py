def get_access_refresh_token(json):
    if "access_token" not in json or "refresh_token" not in json:
        return None, None
    return json["access_token"], json["refresh_token"]
