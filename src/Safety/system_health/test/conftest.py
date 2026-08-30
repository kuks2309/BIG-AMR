"""테스트 공용 fixture.

`sampler.collect()` 는 인자가 많아 호출부마다 기본값을 다시 쓰게 된다. 그 헬퍼를 파일마다
따로 두면 실제 중복이 되고(`dup-signature` 가 잡는다), 기본값이 어긋나면 테스트끼리 다른
조건을 보게 된다. 그래서 한 곳에서만 정의한다.
"""
from __future__ import annotations

import pytest

from system_health import sampler

#: `collect_sample()` 의 테스트 기본값. 개별 테스트는 필요한 것만 덮어쓴다.
COLLECT_DEFAULTS = {
    "disk_paths": ["/"],
    "proc_scan": False,
    "top_rss": 3,
    "fan_daemon_name": "nvfancontrol",
}


@pytest.fixture
def collect_sample():
    """`sampler.collect(prev, **기본값+덮어쓰기)` 를 부르는 호출자.

    Returns:
        `(prev=None, **overrides) -> (record, SampleState)` 호출 가능 객체.
    """

    def _call(prev=None, **overrides):
        options = dict(COLLECT_DEFAULTS)
        options.update(overrides)
        return sampler.collect(prev, **options)

    return _call
