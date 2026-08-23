"""설정 파일(telegram.json) 로드·검증 — rclpy 무의존."""
from __future__ import annotations

import dataclasses
import json
import os
import stat
import sys
from collections.abc import Mapping

# `_` 접두 키는 주석으로 무시한다 — system_health thresholds.json 과 같은 관례
COMMENT_KEY_PREFIX = "_"
ALLOWED_CHANNELS = frozenset({"telegram", "kakao"})


@dataclasses.dataclass(frozen=True)
class NotifierConfig:
    """토큰·수신자·전송 정책. 기본값은 여기 한 곳에만 있다."""

    # 켤 채널 목록. 채널별 필수값 검증은 그 채널이 켜졌을 때만 한다
    channels: tuple[str, ...] = ("telegram",)
    token: str = ""
    chat_id: str = ""
    # 카카오 "나에게 보내기" — developers.kakao.com 앱의 REST API 키
    kakao_rest_api_key: str = ""
    # 클라이언트 시크릿 — 카카오 키 발급 시 기본 활성화라 사실상 필수
    kakao_client_secret: str = ""
    # 토큰 파일 경로. 비우면 설정 파일 옆 kakao_tokens.json
    kakao_token_file: str = ""
    # 메시지 머리표. 비우면 노드가 호스트명을 쓴다(다중 로봇 구분)
    message_prefix: str = ""
    notify_start: bool = True
    notify_warn: bool = False
    warn_ignore: tuple[str, ...] = ("제어권 미획득 (대기)",)
    renotify_s: float = 1800.0
    stale_after_s: float = 15.0
    send_timeout_s: float = 10.0

    @classmethod
    def from_mapping(cls, raw: Mapping) -> "NotifierConfig":
        """기본값 위에 덮어쓴다.

        미지의 키는 KeyError — 오타가 조용히 무시되면 값을 바꿨다고 믿는데
        실제로는 안 바뀐 상태가 된다(system_health 와 같은 규칙).
        """
        known = {f.name for f in dataclasses.fields(cls)}
        overrides = {}
        for key, value in raw.items():
            if key.startswith(COMMENT_KEY_PREFIX):
                continue
            if key not in known:
                raise KeyError(f"미지의 설정 키 {key!r} (허용: {sorted(known)})")
            if key in ("warn_ignore", "channels"):
                value = tuple(str(v) for v in value)
            overrides[key] = value
        cfg = cls(**overrides)
        bad = set(cfg.channels) - ALLOWED_CHANNELS
        if bad:
            raise KeyError(f"미지의 채널 {sorted(bad)} (허용: {sorted(ALLOWED_CHANNELS)})")
        return cfg


def load_config(path: str) -> NotifierConfig:
    """JSON 설정을 읽고 필수값(token·chat_id)을 검증한다. 실패는 SystemExit.

    파일이 소유자 외에도 읽히면 stderr 경고만 낸다 — 차단하면 현장 복구를 막는다.
    """
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"설정 읽기 실패 ({path}): {exc}")
    try:
        cfg = NotifierConfig.from_mapping(raw)
    except (KeyError, TypeError) as exc:
        raise SystemExit(f"설정 형식 오류 ({path}): {exc}")
    if "telegram" in cfg.channels and (not cfg.token or not cfg.chat_id):
        raise SystemExit(
            f"telegram 채널에는 token·chat_id 가 필수다 ({path}). "
            "봇 생성: 텔레그램 @BotFather → /newbot, "
            "chat_id: 봇에게 메시지를 한 번 보낸 뒤 `--get-updates` 로 확인")
    if "kakao" in cfg.channels:
        if not cfg.kakao_rest_api_key:
            raise SystemExit(
                f"kakao 채널에는 kakao_rest_api_key 가 필수다 ({path}) — "
                "developers.kakao.com 앱의 REST API 키")
        if not cfg.kakao_token_file:
            default_tokens = os.path.join(os.path.dirname(os.path.abspath(path)),
                                          "kakao_tokens.json")
            cfg = dataclasses.replace(cfg, kakao_token_file=default_tokens)
    mode = os.stat(path).st_mode
    if mode & (stat.S_IRGRP | stat.S_IROTH):
        print(f"경고: {path} 가 소유자 외에도 읽힌다 — chmod 600 권장",
              file=sys.stderr)
    return cfg
