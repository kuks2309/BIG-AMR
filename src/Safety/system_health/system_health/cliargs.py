"""CLI 인자 범위 검증 — 세 진입점(`sampler`·`report`·`webview`)이 공유한다. 표준 라이브러리만.

**왜 별도 모듈인가**: 같은 검증을 모듈마다 복사하면 이름이 겹쳐 `checks/dup-signature.sh` 에
걸리고, 무엇보다 한쪽만 고치는 순간 규칙이 갈린다. 진입점을 합치지 않는다는 설계
(`.dup-allow` 참조)와 검증 규칙을 한 곳에 두는 것은 충돌하지 않는다 — 진입점은 셋이되
"주기는 0 보다 커야 한다"는 규칙은 하나다.

`sampler` 가 import 하므로 이 모듈도 `rclpy` 를 끌어오지 않는다
(ADR 2026-07-28 §Decision 2, `test/test_no_rclpy_import.py` 가 검사).
"""
from __future__ import annotations

import argparse


def positive_float(text: str) -> float:
    """0 보다 큰 실수만 받는다.

    0·음수 주기를 막는 것이 주 목적이다. `sampler._sleep_until` 은 이미 지난 마감시각에서 즉시
    반환하므로, 그런 값이 들어오면 루프가 `/proc`·`/sys` 를 최대 속도로 읽어 초당 수백 표본을
    쏟는다. 감시기가 감시 대상의 부하가 되면 측정값 자체가 오염된다.

    Args:
        text: 명령행에서 온 문자열.
    Returns:
        실수 값.
    Raises:
        argparse.ArgumentTypeError: 0 이하일 때. 숫자가 아니면 `float()` 가 `ValueError` 를
            내고 argparse 가 같은 경로로 처리한다.
    """
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError(f"0 보다 커야 한다 (받은 값 {text})")
    return value


def non_negative_int(text: str) -> int:
    """0 이상 정수만 받는다. 0 은 "하지 않음"을 뜻하는 자리다(`--proc-scan-every 0`).

    Args:
        text: 명령행에서 온 문자열.
    Returns:
        정수 값.
    Raises:
        argparse.ArgumentTypeError: 음수일 때.
    """
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError(f"0 이상이어야 한다 (받은 값 {text})")
    return value
