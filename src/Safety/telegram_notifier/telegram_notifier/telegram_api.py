"""텔레그램 Bot API 전송 — 표준 라이브러리만, rclpy 무의존.

Bot API 는 토큰을 URL 경로에 싣는다(``/bot<token>/...``). urllib 예외 문자열에는
URL 이 들어가므로, 밖으로 나가는 모든 문자열은 :func:`redact_token` 을 거친다.
"""
from __future__ import annotations

import json
import urllib.request

_API_BASE = "https://api.telegram.org"
DEFAULT_TIMEOUT_S = 10.0
# 텔레그램 sendMessage 본문 상한은 4096자 — 초과분은 자른다(전송 거부보다 낫다)
MAX_TEXT_LEN = 4000


class TelegramSendError(RuntimeError):
    """전송 실패. 예외 메시지에서 봇 토큰은 이미 가려져 있다."""


def redact_token(text: str, token: str) -> str:
    """문자열 속 토큰을 ``<token>`` 으로 치환한다(로그·예외 누설 방지)."""
    if not token:
        return text
    return text.replace(token, "<token>")


def _call(token: str, method: str, payload: dict, timeout_s: float) -> dict:
    """Bot API 1회 호출. 네트워크·HTTP·형식 오류 전부 TelegramSendError 로 승격."""
    url = f"{_API_BASE}/bot{token}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise TelegramSendError(
            f"{method} 실패: {redact_token(str(exc), token)}") from None
    if not body.get("ok"):
        raise TelegramSendError(
            f"{method} 거부: {redact_token(str(body), token)}")
    return body


def send_message(token: str, chat_id: str, text: str,
                 timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
    """``chat_id`` 로 텍스트 1건을 보낸다. 실패는 :class:`TelegramSendError`."""
    _call(token, "sendMessage",
          {"chat_id": chat_id, "text": text[:MAX_TEXT_LEN]}, timeout_s)


def get_updates(token: str, timeout_s: float = DEFAULT_TIMEOUT_S) -> list[dict]:
    """봇이 받은 최근 업데이트 목록 — chat_id 를 모를 때 찾아보는 용도."""
    return _call(token, "getUpdates", {}, timeout_s).get("result", [])
