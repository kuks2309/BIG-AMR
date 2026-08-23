"""텔레그램 전송 단위시험 — urlopen 을 mock 해 네트워크 없이 검증한다."""
import io
import json
import urllib.request

import pytest

from telegram_notifier import telegram_api

TOKEN = "123456:SECRET-TOKEN"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_redact_token():
    assert telegram_api.redact_token(f"url /bot{TOKEN}/x", TOKEN) == \
        "url /bot<token>/x"
    assert telegram_api.redact_token("no token", "") == "no token"


def test_send_message_posts_payload(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        seen["body"] = json.loads(req.data.decode("utf-8"))
        seen["timeout"] = timeout
        return FakeResponse(b'{"ok": true, "result": {}}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    telegram_api.send_message(TOKEN, "42", "hello", timeout_s=3.0)
    assert seen["url"].endswith(f"/bot{TOKEN}/sendMessage")
    assert seen["body"] == {"chat_id": "42", "text": "hello"}
    assert seen["timeout"] == 3.0


def test_send_message_truncates_long_text(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout):
        seen["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    telegram_api.send_message(TOKEN, "42", "x" * 5000)
    assert len(seen["body"]["text"]) == telegram_api.MAX_TEXT_LEN


def test_network_error_redacts_token(monkeypatch):
    def fake_urlopen(req, timeout):
        raise urllib.error.URLError(f"cannot reach /bot{TOKEN}/sendMessage")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(telegram_api.TelegramSendError) as ei:
        telegram_api.send_message(TOKEN, "42", "hi")
    assert TOKEN not in str(ei.value)
    assert "<token>" in str(ei.value)


def test_api_rejection_raises(monkeypatch):
    def fake_urlopen(req, timeout):
        return FakeResponse(b'{"ok": false, "description": "Unauthorized"}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(telegram_api.TelegramSendError) as ei:
        telegram_api.send_message(TOKEN, "42", "hi")
    assert "Unauthorized" in str(ei.value)


def test_get_updates_returns_result_list(monkeypatch):
    def fake_urlopen(req, timeout):
        return FakeResponse(
            b'{"ok": true, "result": [{"message": {"chat": {"id": 7}}}]}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    updates = telegram_api.get_updates(TOKEN)
    assert updates[0]["message"]["chat"]["id"] == 7
