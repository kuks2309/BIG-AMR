"""카카오톡 "나에게 보내기" 전송 — 표준 라이브러리만, rclpy 무의존.

REST 키·access/refresh 토큰은 비밀정보다 — 밖으로 나가는 문자열은
:func:`redact_secrets` 를 거친다. access token 은 수 시간이면 만료되므로
:class:`KakaoSession` 이 401 에서 refresh 후 1회 재시도하고, 갱신 결과를
토큰 파일에 **즉시** 저장한다(refresh token 도 회전될 수 있다).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

AUTH_HOST = "https://kauth.kakao.com"
API_HOST = "https://kapi.kakao.com"
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_REDIRECT_URI = "http://localhost:8899/oauth"
# 카카오 텍스트 템플릿 text 상한(200자) — 초과분은 자른다(전송 거부보다 낫다)
MAX_TEXT_LEN = 200


class KakaoSendError(RuntimeError):
    """전송/인가 실패. 메시지에서 비밀은 이미 가려져 있다."""

    def __init__(self, message: str, http_code: int | None = None) -> None:
        super().__init__(message)
        self.http_code = http_code


def redact_secrets(text: str, secrets: tuple[str, ...]) -> str:
    """문자열 속 REST 키·토큰을 ``<secret>`` 으로 치환한다."""
    for s in secrets:
        if s:
            text = text.replace(s, "<secret>")
    return text


def _post(url: str, data: dict, headers: dict, timeout_s: float,
          secrets: tuple[str, ...]) -> dict:
    """form-encoded POST 1회. HTTP 오류는 응답 본문(오류 코드 포함)까지 실어 승격."""
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise KakaoSendError(
            redact_secrets(f"HTTP {exc.code}: {detail}", secrets),
            http_code=exc.code) from None
    except Exception as exc:
        raise KakaoSendError(redact_secrets(str(exc), secrets)) from None


def build_auth_url(rest_key: str,
                   redirect_uri: str = DEFAULT_REDIRECT_URI) -> str:
    """talk_message 권한 인가 URL — 사용자가 브라우저에서 연다."""
    q = urllib.parse.urlencode({
        "client_id": rest_key, "redirect_uri": redirect_uri,
        "response_type": "code", "scope": "talk_message"})
    return f"{AUTH_HOST}/oauth/authorize?{q}"


def exchange_code(rest_key: str, code: str,
                  redirect_uri: str = DEFAULT_REDIRECT_URI,
                  timeout_s: float = DEFAULT_TIMEOUT_S,
                  client_secret: str = "") -> dict:
    """인가 code 를 access/refresh 토큰으로 교환한다.

    앱에 클라이언트 시크릿이 활성화돼 있으면(카카오 키 발급 시 기본 ON)
    client_secret 없이는 KOE010 으로 거부된다.
    """
    payload = {"grant_type": "authorization_code", "client_id": rest_key,
               "redirect_uri": redirect_uri, "code": code}
    if client_secret:
        payload["client_secret"] = client_secret
    return _post(f"{AUTH_HOST}/oauth/token", payload,
                 {}, timeout_s, (rest_key, code, client_secret))


def refresh_tokens(rest_key: str, refresh_token: str,
                   timeout_s: float = DEFAULT_TIMEOUT_S,
                   client_secret: str = "") -> dict:
    """access token 갱신. 응답에 refresh_token 이 있으면 그것도 회전된 것이다."""
    payload = {"grant_type": "refresh_token", "client_id": rest_key,
               "refresh_token": refresh_token}
    if client_secret:
        payload["client_secret"] = client_secret
    return _post(f"{AUTH_HOST}/oauth/token", payload,
                 {}, timeout_s, (rest_key, refresh_token, client_secret))


def send_to_me(access_token: str, text: str,
               timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
    """내 카카오톡("나와의 채팅")으로 텍스트 1건. 실패는 KakaoSendError."""
    template = {"object_type": "text", "text": text[:MAX_TEXT_LEN],
                "link": {"web_url": "https://developers.kakao.com"}}
    body = _post(f"{API_HOST}/v2/api/talk/memo/default/send",
                 {"template_object": json.dumps(template, ensure_ascii=False)},
                 {"Authorization": f"Bearer {access_token}"},
                 timeout_s, (access_token,))
    if body.get("result_code", 0) != 0:
        raise KakaoSendError(f"전송 거부: result_code={body.get('result_code')}")


def load_tokens(path: str) -> dict:
    """토큰 파일 읽기. 없거나 깨졌으면 KakaoSendError(재인가 안내)."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise KakaoSendError(
            f"토큰 파일 읽기 실패({path}): {exc} — `--kakao-auth` 로 인가하라") from None


def save_tokens(path: str, tokens: dict) -> None:
    """토큰 저장(0600). 갱신 직후 반드시 호출 — 미루면 재인가가 필요해진다."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)
    os.chmod(path, 0o600)


class KakaoSession:
    """토큰 보유 전송기. 401 이면 refresh 1회 후 재시도한다.

    스레드 안전하지 않다 — SendWorker 스레드 하나에서만 쓴다.
    """

    def __init__(self, rest_key: str, token_file: str,
                 timeout_s: float = DEFAULT_TIMEOUT_S,
                 client_secret: str = "") -> None:
        self._rest_key = rest_key
        self._token_file = token_file
        self._timeout_s = timeout_s
        self._client_secret = client_secret
        self._tokens: dict | None = None  # 지연 로드 — 기동 시 파일 부재를 넘기고 전송 시점에 알림

    def send(self, text: str) -> None:
        if self._tokens is None:
            self._tokens = load_tokens(self._token_file)
        try:
            send_to_me(self._tokens["access_token"], text, self._timeout_s)
            return
        except KakaoSendError as exc:
            if exc.http_code != 401:
                raise
        fresh = refresh_tokens(self._rest_key, self._tokens["refresh_token"],
                               self._timeout_s, self._client_secret)
        self._tokens = {**self._tokens, **fresh}
        save_tokens(self._token_file, self._tokens)
        send_to_me(self._tokens["access_token"], text, self._timeout_s)
