#!/usr/bin/env python3
"""카메라 자동 등록 2단계 — 보드 인식 → 시리얼↔위치 매핑 → 로스터·udev 규칙 생성.

절차: 보드 1~6(generate_boards.py 산출물)을 번호 규약대로 각 카메라 앞(≤1m)에
배치한 뒤 실행한다. 각 카메라가 보는 보드 번호로 그 카메라의 장착 위치를 판정한다.

  python3 register_cameras.py                # 판정 + out/ 에 제안 파일 생성(dry-run)
  python3 register_cameras.py --apply        # 로스터(camera_common.yaml) 백업 후 갱신
  python3 register_cameras.py --source device  # 퍼블리셔 정지 상태에서 장치 직접 개방

프레임 소스 기본값은 ROS 토픽이다 — usb-cam@ 유닛이 이미 장치를 잡고 스트리밍
중이므로(EBUSY) 그 산출물을 구독한다. 로스터가 틀려도 무방하다: 로스터는
이름↔시리얼 대응만 제공하고, 위치는 보드가 정한다.

udev 규칙은 out/99-amr-cameras.rules 로 생성만 한다 — 설치는 sudo 가 필요해
사용자 몫(파일 머리에 설치 명령 동봉).
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import sys
import time
from collections import Counter

import cv2
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "camera_service"))
from camera_params import device_path, load_roster  # noqa: E402
from generate_boards import (  # noqa: E402
    ARUCO_DICT_NAME,
    BOARD_MAP,
    board_number_from_marker_id,
)

_DEFAULT_CONFIG = os.path.join(_HERE, "..", "..", "config", "camera", "camera_common.yaml")


def detect_board_votes(gray: "np.ndarray") -> Counter:
    """한 프레임의 마커 검출 → 보드 번호 득표. 무소속 ID(캘리브레이션 보드 등)는 버린다."""
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, ARUCO_DICT_NAME))
    detector = cv2.aruco.ArucoDetector(dictionary)
    _corners, ids, _rejected = detector.detectMarkers(gray)
    votes: Counter = Counter()
    if ids is not None:
        for marker_id in ids.flatten():
            board_no = board_number_from_marker_id(int(marker_id))
            if board_no:
                votes[board_no] += 1
    return votes


def decide_board(votes: Counter, min_votes: int = 3) -> int | None:
    """카메라 1대의 누적 득표 → 보드 판정. 임계 미만·최다 동률이면 None(불확정)."""
    if not votes:
        return None
    ranked = votes.most_common(2)
    top_board, top_count = ranked[0]
    if top_count < min_votes:
        return None
    if len(ranked) > 1 and ranked[1][1] == top_count:
        return None
    return top_board


def build_mapping(observed: dict[str, int | None]) -> tuple[dict[str, str], list[str]]:
    """시리얼→관측 보드 → (위치명→시리얼, 오류 목록).

    오류: 미검출 시리얼 / 같은 보드를 본 시리얼 중복 / 배정 안 된 위치.
    오류가 하나라도 있으면 매핑은 참고용이며 --apply 를 거부해야 한다.
    """
    errors = []
    by_board: dict[int, list[str]] = {}
    for serial, board_no in observed.items():
        if board_no is None:
            errors.append(f"시리얼 {serial}: 보드 미검출/불확정")
        else:
            by_board.setdefault(board_no, []).append(serial)

    mapping: dict[str, str] = {}
    for board_no, serials in sorted(by_board.items()):
        name = BOARD_MAP[board_no][0]
        if len(serials) > 1:
            errors.append(f"보드 {board_no}({name}): 카메라 {len(serials)}대가 동시 검출 {serials}")
        else:
            mapping[name] = serials[0]
    for board_no, (name, _pos) in BOARD_MAP.items():
        if name not in mapping:
            errors.append(f"위치 {name}(보드 {board_no}): 배정된 카메라 없음")
    return mapping, errors


def render_udev_rules(mapping: dict[str, str]) -> str:
    """위치명→시리얼 매핑 → udev 규칙 텍스트(/dev/camera/<위치명> 심링크)."""
    lines = [
        "# AMR 카메라 위치 심링크 — Tools/camera_autoreg/register_cameras.py 생성",
        "# 설치: sudo cp 99-amr-cameras.rules /etc/udev/rules.d/ \\",
        "#       && sudo udevadm control --reload-rules && sudo udevadm trigger",
        "# 확인: ls -l /dev/camera/",
    ]
    for name in (BOARD_MAP[n][0] for n in sorted(BOARD_MAP)):
        serial = mapping.get(name)
        if serial:
            lines.append(
                f'SUBSYSTEM=="video4linux", ATTRS{{serial}}=="{serial}", '
                f'ATTR{{index}}=="0", SYMLINK+="camera/{name}"')
    return "\n".join(lines) + "\n"


def rewrite_roster_serials(yaml_text: str, mapping: dict[str, str]) -> str:
    """로스터 yaml 에서 각 `- name: "cam_x"` 블록의 serial 값만 표적 치환한다.

    yaml.dump 재직렬화는 파일의 주석·순서를 파괴하므로 줄 단위로만 손댄다.
    치환은 name 줄 다음에 처음 나오는 serial 줄 1개에만 적용된다.
    """
    lines = yaml_text.split("\n")
    current_name = None
    for i, line in enumerate(lines):
        name_match = re.match(r'\s*-\s*name:\s*"?(\w+)"?', line)
        if name_match:
            current_name = name_match.group(1)
            continue
        serial_match = re.match(r'(\s*serial:\s*)"?[\w-]+"?(.*)$', line)
        if serial_match and current_name in mapping:
            lines[i] = f'{serial_match.group(1)}"{mapping[current_name]}"{serial_match.group(2)}'
            current_name = None
    return "\n".join(lines)


def _decode_votes(jpeg_bytes: bytes) -> Counter:
    buf = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    gray = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    return detect_board_votes(gray) if gray is not None else Counter()


def grab_frames_topics(cameras, frames_per_cam: int, timeout_sec: float) -> dict[str, Counter]:
    """구동 중인 퍼블리셔의 압축 토픽에서 카메라별 N프레임을 모아 득표 집계.

    반환 키는 시리얼. 로스터의 이름↔시리얼 대응으로 토픽을 찾는다.
    """
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import CompressedImage

    rclpy.init()
    node = rclpy.create_node("camera_autoreg")
    votes: dict[str, Counter] = {cam["serial"]: Counter() for cam in cameras}
    counts: dict[str, int] = {cam["serial"]: 0 for cam in cameras}

    def _make_cb(serial):
        def _cb(msg):
            if counts[serial] < frames_per_cam:
                counts[serial] += 1
                votes[serial].update(_decode_votes(bytes(msg.data)))
        return _cb

    subs = [
        node.create_subscription(
            CompressedImage, f"{cam['name']}/image_raw/compressed",
            _make_cb(cam["serial"]), qos_profile_sensor_data)
        for cam in cameras
    ]
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline and any(
            n < frames_per_cam for n in counts.values()):
        rclpy.spin_once(node, timeout_sec=0.1)
    lacking = [s for s, n in counts.items() if n == 0]
    if lacking:
        print(f"⚠ 프레임 0장(토픽 무발행 — 유닛 상태 확인): {', '.join(lacking)}", file=sys.stderr)
    del subs
    node.destroy_node()
    rclpy.shutdown()
    return votes


def discover_devices(by_id_prefix: str) -> list[str]:
    """연결된 카메라의 시리얼을 /dev/v4l/by-id/ 실스캔으로 직접 읽는다.

    로스터 무의존 — 신품·교체 카메라도 시리얼이 그대로 나온다. 시리얼은 카메라
    개체의 영속 식별자로, 향후 시리얼별 내부 파라미터 캘리브레이션 파일 매칭의
    키가 된다(위치명은 장착이 바뀌면 따라 바뀌지만 시리얼은 카메라를 따라간다).
    """
    import glob

    pattern = f"/dev/v4l/by-id/usb-{by_id_prefix}_*-video-index0"
    serials = []
    for path in sorted(glob.glob(pattern)):
        match = re.match(
            rf"usb-{re.escape(by_id_prefix)}_(.+)-video-index0", os.path.basename(path))
        if match:
            serials.append(match.group(1))
    return serials


def grab_frames_devices(serials, by_id_prefix: str, frames_per_cam: int) -> dict[str, Counter]:
    """발견된 by-id 장치를 직접 열어 득표 집계 — usb-cam@ 가 잡고 있으면 EBUSY 이므로 선정지 요구."""
    import subprocess

    result = subprocess.run(
        ["/usr/bin/systemctl", "list-units", "--state=active", "--plain",
         "--no-legend", "usb-cam@*"],
        capture_output=True, text=True, timeout=5)
    active = [line.split()[0] for line in (result.stdout or "").splitlines() if line.strip()]
    if active:
        raise SystemExit(
            f"퍼블리셔가 장치를 잡고 있다({', '.join(active)}) — "
            "camctl stop all 후 --source device 를 다시 실행하거나, 기본(토픽) 모드를 쓰라")

    votes: dict[str, Counter] = {}
    for serial in serials:
        path = device_path(by_id_prefix, serial)
        tally: Counter = Counter()
        capture = cv2.VideoCapture(path, cv2.CAP_V4L2)
        if capture.isOpened():
            for _ in range(frames_per_cam):
                ok, frame = capture.read()
                if ok and frame is not None:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
                    tally.update(detect_board_votes(gray))
            capture.release()
        else:
            print(f"⚠ 장치 개방 실패: {path}", file=sys.stderr)
        votes[serial] = tally
    return votes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="ChArUco 보드 인식으로 카메라 위치를 판정해 로스터·udev 규칙을 만든다")
    parser.add_argument("--config", default=os.path.normpath(_DEFAULT_CONFIG))
    parser.add_argument("--source", choices=("topics", "device"), default="topics")
    parser.add_argument("--frames", type=int, default=10, help="카메라당 판정 프레임 수")
    parser.add_argument("--timeout", type=float, default=15.0, help="토픽 수집 제한(초)")
    parser.add_argument("--min-votes", type=int, default=3, dest="min_votes",
                        help="보드 확정에 필요한 최소 마커 득표")
    parser.add_argument("--out", default=os.path.join(_HERE, "out"))
    parser.add_argument("--apply", action="store_true",
                        help="오류 0건일 때 로스터를 백업 후 실제 갱신")
    args = parser.parse_args(argv)

    config = load_roster(args.config)
    cameras = config["cameras"]
    prefix = config["by_id_prefix"]

    if args.source == "topics":
        votes = grab_frames_topics(cameras, args.frames, args.timeout)
    else:
        serials = discover_devices(prefix)
        if not serials:
            raise SystemExit("연결된 카메라가 없다 — /dev/v4l/by-id/ 스캔 0건")
        print(f"장치 스캔: 시리얼 {len(serials)}개 발견 — {', '.join(serials)}")
        votes = grab_frames_devices(serials, prefix, args.frames)

    observed = {serial: decide_board(tally, args.min_votes) for serial, tally in votes.items()}
    mapping, errors = build_mapping(observed)

    name_by_serial = {cam["serial"]: cam["name"] for cam in cameras}
    print(f"{'시리얼':<14} {'현재 이름':<8} {'검출 보드':<9} {'판정 위치':<8} 득표")
    for serial, board_no in observed.items():
        new_name = BOARD_MAP[board_no][0] if board_no else "-"
        tally = dict(votes[serial]) or "-"
        print(f"{serial:<14} {name_by_serial.get(serial, '?'):<8} "
              f"{board_no if board_no else '-':<9} {new_name:<8} {tally}")

    os.makedirs(args.out, exist_ok=True)
    if errors:
        print("\n오류 — 매핑 미완성(--apply 불가):")
        for error in errors:
            print(f"  · {error}")
        return 1

    with open(args.config, encoding="utf-8") as handle:
        roster_text = handle.read()
    proposed = rewrite_roster_serials(roster_text, mapping)
    proposed_path = os.path.join(args.out, "camera_common.proposed.yaml")
    with open(proposed_path, "w", encoding="utf-8") as handle:
        handle.write(proposed)
    rules_path = os.path.join(args.out, "99-amr-cameras.rules")
    with open(rules_path, "w", encoding="utf-8") as handle:
        handle.write(render_udev_rules(mapping))

    changed = proposed != roster_text
    print(f"\n제안 로스터: {proposed_path} ({'변경 있음' if changed else '현행과 동일'})")
    print(f"udev 규칙:   {rules_path} (설치 명령은 파일 머리 주석)")

    if args.apply:
        if changed:
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = f"{args.config}.bak-{stamp}"
            with open(backup, "w", encoding="utf-8") as handle:
                handle.write(roster_text)
            with open(args.config, "w", encoding="utf-8") as handle:
                handle.write(proposed)
            print(f"로스터 갱신 완료(백업: {backup}) — 반영: camctl restart all")
        else:
            print("로스터가 이미 정확하다 — 갱신 생략")
    elif changed:
        print("적용하려면 --apply (로스터 백업 후 갱신)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
