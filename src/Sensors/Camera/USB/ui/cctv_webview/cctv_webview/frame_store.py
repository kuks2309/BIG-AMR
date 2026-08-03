# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""카메라별 최신 JPEG 바이트 보관 — 순수 자료구조(ROS·HTTP 무관, 단위 시험 가능).

바이트를 **디코드하지 않고** 그대로 들고 있다가 HTTP 스트림으로 흘린다. 이 파일에
디코드가 들어가는 순간 웹 뷰어의 존재 이유(로봇 PC 는 픽셀을 만지지 않는다)가 사라진다.
"""

import threading
import time


class FrameStore:
    """카메라별 최신 프레임 1장씩만 보관(덮어쓰기, 메모리 상한 = 카메라수 x 1프레임).

    큐가 아니라 덮어쓰기인 이유: 느린 시청자가 밀린 프레임을 쌓게 두면 메모리가 무한히
    자란다(2026-07-27 vision_guard OOM 선례). 늦은 시청자는 최신 프레임만 본다.
    """

    def __init__(self, clock=time.monotonic):
        self._lock = threading.Lock()
        self._frames = {}          # name -> (bytes, stamp, seq)
        self._seq = {}             # name -> 누적 수신 수
        self._clock = clock

    def put(self, name, data):
        """수신 콜백에서 호출. 같은 카메라의 이전 프레임을 덮어쓴다."""
        with self._lock:
            seq = self._seq.get(name, 0) + 1
            self._seq[name] = seq
            self._frames[name] = (data, self._clock(), seq)

    def get(self, name):
        """(bytes, stamp, seq) 또는 아직 한 장도 없으면 None."""
        with self._lock:
            return self._frames.get(name)

    def get_newer_than(self, name, last_seq):
        """``last_seq`` 보다 새 프레임이 있으면 반환, 없으면 None(중복 전송 방지)."""
        with self._lock:
            entry = self._frames.get(name)
            if entry is None or entry[2] <= last_seq:
                return None
            return entry

    def names(self):
        with self._lock:
            return sorted(self._frames)

    def stats(self):
        """{name: {"seq": 누적 수신, "age_s": 마지막 수신 경과}} — 상태 표시용."""
        now = self._clock()
        with self._lock:
            return {
                name: {"seq": seq, "age_s": now - stamp, "bytes": len(data)}
                for name, (data, stamp, seq) in self._frames.items()
            }


class DetectionStore:
    """카메라별 최신 검출 결과 — 좌표만 보관한다(픽셀은 만지지 않는다).

    화면에 그리는 일은 브라우저가 한다. 서버가 박스를 영상에 굽는 순간 JPEG 를 디코드·
    재인코딩해야 하므로 이 뷰어의 존재 이유가 사라진다.
    """

    def __init__(self, clock=time.monotonic):
        self._lock = threading.Lock()
        self._latest = {}
        self._clock = clock

    def put(self, name, boxes, image_width, image_height):
        with self._lock:
            self._latest[name] = {
                "boxes": boxes,
                "width": image_width,
                "height": image_height,
                "stamp": self._clock(),
            }

    def snapshot(self):
        """{name: {"boxes": [...], "width", "height", "age_ms"}} — HTTP 응답용."""
        now = self._clock()
        with self._lock:
            return {
                name: {
                    "boxes": entry["boxes"],
                    "width": entry["width"],
                    "height": entry["height"],
                    "age_ms": (now - entry["stamp"]) * 1000.0,
                }
                for name, entry in self._latest.items()
            }


def camera_label(topic):
    """`/cam_lf/image_raw/compressed` → `cam_lf`. 관례를 못 맞추면 원문을 그대로 쓴다."""
    parts = [p for p in topic.split("/") if p]
    return parts[0] if parts else topic


POSITION_NAMES = {
    "cam_f": "전면 F",
    "cam_r": "후면 R",
    "cam_lf": "좌전 LF",
    "cam_lr": "좌후 LR",
    "cam_rf": "우전 RF",
    "cam_rr": "우후 RR",
}


def display_name(name):
    """장착 위치 이름. 로스터에 없는 이름이면 그대로 보여준다."""
    return POSITION_NAMES.get(name, name)
