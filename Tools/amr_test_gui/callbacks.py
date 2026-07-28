#!/usr/bin/env python3
"""콜백 경계 — Qt 무의존 계층이 화면으로 결과를 내보낼 때 쓰는 단일 규약.

`tongyi_can` 과 `seer_status` 는 화면을 알지 못하고 콜백만 부른다. 그런데 종료 순간에는
콜백 반대편(창)이 먼저 파괴돼 Qt 가 `RuntimeError` 를 던진다. 그때 하위 계층이 할 일은
역추적을 남기는 것이 아니라 **조용히 루프를 끝내는 것**이라, 그 판정을 여기 한 곳에 둔다.
"""
from __future__ import annotations


def emit(cb, *args) -> bool:
    """콜백 1회. 수신부가 이미 죽었으면(`RuntimeError`) False 를 돌려준다.

    `cb` 가 None 이면 아무것도 하지 않고 True — 콜백을 안 꽂은 구성도 정상이다.
    반환값을 무시해도 되지만, 폴링 루프는 False 를 보면 그 자리에서 끝내야 한다.
    """
    if cb is None:
        return True
    try:
        cb(*args)
    except RuntimeError:
        return False
    return True
