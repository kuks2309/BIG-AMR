"""GUI 감시 표시의 순수 부분 — `parse_supervisor_status` 회귀.

고정하는 계약: 감시자 항목(`can_relay_supervisor` 접두)만 읽고, verdict 는
KeyValue 가 정본이며, 항목이 없으면 `None`(미수신과 구분).
"""
from types import SimpleNamespace as NS

from can_relay.ui.backend_ros2 import parse_supervisor_status


def _st(name, message="", values=()):
    return NS(name=name, message=message,
              values=[NS(key=k, value=v) for k, v in values])


def test_supervisor_entry_is_extracted():
    out = parse_supervisor_status([
        _st("can_relay: 릴레이 구동", "정상"),
        _st("can_relay_supervisor: 노드 감시", "RUNNING — 제어권 보유",
            [("verdict", "RUNNING"), ("was_down", "False")]),
    ])
    assert out == ("RUNNING", "RUNNING — 제어권 보유")


def test_absent_entry_returns_none():
    assert parse_supervisor_status([_st("icp_odometry: x", "y")]) is None
    assert parse_supervisor_status([]) is None


def test_missing_verdict_key_degrades_to_empty():
    out = parse_supervisor_status([_st("can_relay_supervisor: 노드 감시", "m")])
    assert out == ("", "m")
