"""설정 로드 단위시험 — ROS 무의존."""
import json

import pytest

from telegram_notifier.config import NotifierConfig, load_config


def write(tmp_path, data, mode=0o600):
    p = tmp_path / "telegram.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    p.chmod(mode)
    return str(p)


def test_defaults_and_override():
    cfg = NotifierConfig.from_mapping({"token": "t", "chat_id": "c",
                                       "renotify_s": 60})
    assert cfg.renotify_s == 60
    assert cfg.notify_warn is False
    assert cfg.stale_after_s == 15.0


def test_unknown_key_rejected():
    with pytest.raises(KeyError):
        NotifierConfig.from_mapping({"token": "t", "renotify_sec": 60})


def test_comment_keys_ignored():
    cfg = NotifierConfig.from_mapping({"_comment": "x", "token": "t",
                                       "chat_id": "c"})
    assert cfg.token == "t"


def test_warn_ignore_becomes_tuple():
    cfg = NotifierConfig.from_mapping({"warn_ignore": ["a", "b"]})
    assert cfg.warn_ignore == ("a", "b")


def test_load_missing_required_exits(tmp_path):
    path = write(tmp_path, {"token": "t"})  # chat_id 없음
    with pytest.raises(SystemExit):
        load_config(path)


def test_load_unknown_key_exits(tmp_path):
    path = write(tmp_path, {"token": "t", "chat_id": "c", "oops": 1})
    with pytest.raises(SystemExit):
        load_config(path)


def test_load_ok_and_perm_warning(tmp_path, capsys):
    path = write(tmp_path, {"token": "t", "chat_id": "c"}, mode=0o644)
    cfg = load_config(path)
    assert cfg.chat_id == "c"
    assert "chmod 600" in capsys.readouterr().err


def test_load_tight_perm_no_warning(tmp_path, capsys):
    path = write(tmp_path, {"token": "t", "chat_id": "c"}, mode=0o600)
    load_config(path)
    assert capsys.readouterr().err == ""


def test_load_broken_json_exits(tmp_path):
    p = tmp_path / "telegram.json"
    p.write_text("{", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_config(str(p))


def test_unknown_channel_rejected():
    with pytest.raises(KeyError):
        NotifierConfig.from_mapping({"channels": ["telegram", "sms"]})


def test_kakao_channel_requires_rest_key(tmp_path):
    path = write(tmp_path, {"channels": ["kakao"]})
    with pytest.raises(SystemExit):
        load_config(path)


def test_kakao_only_needs_no_telegram_token(tmp_path):
    path = write(tmp_path, {"channels": ["kakao"], "kakao_rest_api_key": "rk"})
    cfg = load_config(path)
    assert cfg.token == ""
    # 토큰 파일 기본값은 설정 파일 옆이다
    assert cfg.kakao_token_file == str(tmp_path / "kakao_tokens.json")


def test_both_channels_require_both_credentials(tmp_path):
    path = write(tmp_path, {"channels": ["telegram", "kakao"],
                            "token": "t", "chat_id": "c",
                            "kakao_rest_api_key": "rk"})
    cfg = load_config(path)
    assert set(cfg.channels) == {"telegram", "kakao"}
