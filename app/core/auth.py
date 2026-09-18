import base64
import binascii
import hmac
from typing import Mapping

from app.core import fault


def check_auth(headers: Mapping[str, str]) -> bool:
    config = fault.state.config
    if not config.auth_enabled:
        return True
    if config.auth_type != "basic":
        return True
    raw = headers.get("authorization") or headers.get("Authorization")
    if not raw:
        return False
    scheme, _, token = raw.partition(" ")
    if scheme.lower() != "basic" or not token:
        return False
    try:
        decoded = base64.b64decode(token).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    username, sep, password = decoded.partition(":")
    if not sep:
        return False
    return hmac.compare_digest(username, config.username) and hmac.compare_digest(
        password, config.password
    )
