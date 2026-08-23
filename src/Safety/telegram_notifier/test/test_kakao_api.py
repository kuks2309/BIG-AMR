"""카카오 "나에게 보내기" 단위시험 — urlopen 을 mock 해 네트워크 없이 검증한다."""
import io
import json
import urllib.error
import urllib.parse
import urllib.request

import pytest

from telegram_notifier import kakao_api

REST = "restkey123"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_build_auth_url_contains_key_and_scope():
    url = kakao_api.build_auth_url(REST)
    assert url.startswith(kakao_api.AUTH_HOST)
    assert "client_id=restkey123" in url
    assert "scope=talk_message" in url


def test_redact_secrets():
    out = kakao_api.redact_secrets(f"key={REST} tok=abc", (REST, "abc"))
    assert REST not in out and "abc" not in out


def test_send_to_me_posts_text_template(monkeypatch):
    seen = {}

    def fake(req, timeout):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        form = urllib.parse.parse_qs(req.data.decode("utf-8"))
        seen["template"] = json.loads(form["template_object"][0])
        return FakeResponse(b'{"result_code": 0}')

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    kakao_api.send_to_me("at", "hello")
    assert seen["url"].endswith("/v2/api/talk/memo/default/send")
    assert seen["auth"] == "Bearer at"
    assert seen["template"]["object_type"] == "text"
    assert seen["template"]["text"] == "hello"


def test_send_to_me_truncates_to_200(monkeypatch):
    seen = {}

    def fake(req, timeout):
        form = urllib.parse.parse_qs(req.data.decode("utf-8"))
        seen["text"] = json.loads(form["template_object"][0])["text"]
        return FakeResponse(b'{"result_code": 0}')

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    kakao_api.send_to_me("at", "x" * 500)
    assert len(seen["text"]) == kakao_api.MAX_TEXT_LEN


def test_http_error_carries_code_and_detail(monkeypatch):
    def fake(req, timeout):
        raise urllib.error.HTTPError(
            req.full_url, 401, "Unauthorized", None,
            io.BytesIO(b'{"msg":"this access token does not exist","code":-401}'))

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    with pytest.raises(kakao_api.KakaoSendError) as ei:
        kakao_api.send_to_me("at", "hi")
    assert ei.value.http_code == 401
    assert "-401" in str(ei.value)


def test_session_refreshes_once_on_401(monkeypatch, tmp_path):
    token_file = tmp_path / "kakao_tokens.json"
    token_file.write_text(json.dumps(
        {"access_token": "old", "refresh_token": "rt"}), encoding="utf-8")
    calls = []

    def fake(req, timeout):
        calls.append(req.full_url)
        if req.full_url.endswith("/oauth/token"):
            return FakeResponse(b'{"access_token": "new"}')
        auth = req.get_header("Authorization")
        if auth == "Bearer old":
            raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized",
                                         None, io.BytesIO(b"{}"))
        return FakeResponse(b'{"result_code": 0}')

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    session = kakao_api.KakaoSession(REST, str(token_file))
    session.send("hi")
    # 전송(401) → 갱신 → 재전송 순서였는지
    assert [u.split("/")[-1] for u in calls] == ["send", "token", "send"]
    saved = json.loads(token_file.read_text(encoding="utf-8"))
    assert saved["access_token"] == "new"
    assert saved["refresh_token"] == "rt"


def test_session_non_401_propagates(monkeypatch, tmp_path):
    token_file = tmp_path / "kakao_tokens.json"
    token_file.write_text(json.dumps(
        {"access_token": "at", "refresh_token": "rt"}), encoding="utf-8")

    def fake(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden",
                                     None, io.BytesIO(b"{}"))

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    session = kakao_api.KakaoSession(REST, str(token_file))
    with pytest.raises(kakao_api.KakaoSendError) as ei:
        session.send("hi")
    assert ei.value.http_code == 403


def test_exchange_and_refresh_carry_client_secret(monkeypatch):
    seen = []

    def fake(req, timeout):
        seen.append(urllib.parse.parse_qs(req.data.decode("utf-8")))
        return FakeResponse(b'{"access_token": "at"}')

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    kakao_api.exchange_code(REST, "code1", client_secret="sec")
    kakao_api.refresh_tokens(REST, "rt", client_secret="sec")
    assert seen[0]["client_secret"] == ["sec"]
    assert seen[1]["client_secret"] == ["sec"]
    # 시크릿 미지정이면 파라미터 자체를 보내지 않는다
    kakao_api.refresh_tokens(REST, "rt")
    assert "client_secret" not in seen[2]


def test_load_tokens_missing_file_guides_auth(tmp_path):
    with pytest.raises(kakao_api.KakaoSendError) as ei:
        kakao_api.load_tokens(str(tmp_path / "none.json"))
    assert "--kakao-auth" in str(ei.value)
