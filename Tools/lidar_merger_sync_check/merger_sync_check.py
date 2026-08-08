#!/usr/bin/env python3
"""dual_laser_merger 의 쌍 동기화·발행률 점검기.

두 가지 모드를 가진다.

  observe  이미 돌고 있는 시스템을 수동 관측한다. 토픽마다
             ① 도착률(수신 시각 기준)  ② 스탬프률(header.stamp 차분 기준)
             ③ 센서 자기신고 주기(LaserScan.scan_time)
             ④ 발행자 수와 QoS
           를 따로 낸다. "입력 34 Hz 인데 출력 40 Hz" 같은 관측이
           실제 발행률 차이인지 구독자 쪽 유실인지를 이 셋의 불일치로 가른다.
           도착률 < 스탬프률 이면 측정하는 쪽이 흘린 것이다.

  inject   하드웨어 없이 검증한다. 정확히 지정한 주기로 /scan_front·/scan_rear 를
           합성 발행하고 실제 merger 노드를 자식 프로세스로 띄운 뒤,
           merger 가 스스로 세는 생산자측 카운트(로그의 `sync:` 줄)와
           이쪽에서 세는 소비자측 카운트를 같이 보고한다.

사용 예:
  source /opt/ros/humble/setup.bash && source install/setup.bash
  python3 Tools/lidar_merger_sync_check/merger_sync_check.py observe --duration 20
  python3 Tools/lidar_merger_sync_check/merger_sync_check.py inject --rate 34 --duration 15
  python3 Tools/lidar_merger_sync_check/merger_sync_check.py inject --rate 34 --phase 0.5 --max-pair-skew 0.005
"""

import argparse
import bisect
import math
import os
import random
import re
import signal
import statistics
import subprocess
import sys
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float64

SENSOR_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=50,
    durability=QoSDurabilityPolicy.VOLATILE,
)

# 주입기는 실드라이버(기본 RELIABLE, depth 1)와 달리 깊은 RELIABLE 로 낸다.
# 주입 자체가 병목이 되어 입력 수를 흐리면 실험이 무의미하기 때문이다.
INJECT_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.RELIABLE,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=200,
    durability=QoSDurabilityPolicy.VOLATILE,
)


def stamp_to_sec(stamp):
    return stamp.sec + stamp.nanosec * 1e-9


def positive_float(v):
    f = float(v)
    if f <= 0.0:
        raise argparse.ArgumentTypeError(f"{v} — 0보다 커야 한다")
    return f


def nonneg_float(v):
    f = float(v)
    if f < 0.0:
        raise argparse.ArgumentTypeError(f"{v} — 음수는 안 된다")
    return f


def positive_int(v):
    i = int(v)
    if i <= 0:
        raise argparse.ArgumentTypeError(f"{v} — 0보다 커야 한다")
    return i


class TopicStats:
    """한 토픽의 도착 시각과 헤더 스탬프를 따로 모은다."""

    def __init__(self, name, warmup=1.0):
        self.name = name
        self.warmup = warmup
        self.t0 = None
        self.recv = []       # 수신 시각(단조 시계)
        self.stamps = []     # header.stamp [s]
        self.scan_times = [] # LaserScan.scan_time [s] (센서 자기신고 주기)

    def add(self, msg, now):
        if self.t0 is None:
            self.t0 = now
        if now - self.t0 < self.warmup:
            return  # 구독이 붙는 동안의 첫 구간은 유실처럼 보이므로 버린다
        self.recv.append(now)
        self.stamps.append(stamp_to_sec(msg.header.stamp))
        if isinstance(msg, LaserScan) and msg.scan_time > 0.0:
            self.scan_times.append(msg.scan_time)

    def window(self):
        """warmup 을 버린 뒤 실제로 관측한 [시작, 끝] 단조시각. 표본 부족이면 None."""
        return (self.recv[0], self.recv[-1]) if len(self.recv) >= 2 else None

    @staticmethod
    def _rate_from(series):
        if len(series) < 2:
            return None, None, None
        deltas = [b - a for a, b in zip(series, series[1:])]
        deltas = [d for d in deltas if d > 0.0]
        if not deltas:
            return None, None, None
        median = statistics.median(deltas)
        return (1.0 / median if median > 0 else None), min(deltas), max(deltas)

    def report(self):
        n = len(self.recv)
        lines = [f"  {self.name}: {n} msg"]
        if n < 2:
            lines.append("    (표본 부족)")
            return lines

        span = self.recv[-1] - self.recv[0]
        arrival_avg = (n - 1) / span if span > 0 else float("nan")
        arr_rate, arr_min, arr_max = self._rate_from(self.recv)
        stamp_rate, st_min, st_max = self._rate_from(self.stamps)

        lines.append(
            f"    도착률   평균 {arrival_avg:7.2f} Hz | 중앙 {arr_rate:7.2f} Hz"
            f" | 간격 {arr_min * 1e3:6.1f}~{arr_max * 1e3:7.1f} ms"
        )
        if stamp_rate:
            lines.append(
                f"    스탬프률 중앙 {stamp_rate:7.2f} Hz"
                f" | 간격 {st_min * 1e3:6.1f}~{st_max * 1e3:7.1f} ms"
            )
            # 도착률이 스탬프률보다 뚜렷이 낮으면 흘린 쪽은 발행자가 아니라 구독자다.
            if arrival_avg < stamp_rate * 0.97:
                lost = (1.0 - arrival_avg / stamp_rate) * 100.0
                lines.append(
                    f"    ⚠ 도착률이 스탬프률보다 {lost:.1f}% 낮다 —"
                    f" 이 측정 프로세스가 유실 중(BEST_EFFORT). 발행률 근거로 쓰지 말 것."
                )
        if self.scan_times:
            st = statistics.median(self.scan_times)
            lines.append(f"    센서신고 scan_time 중앙 {st * 1e3:.2f} ms → {1.0 / st:.2f} Hz")
        return lines


class Observer(Node):
    def __init__(self, topics, skew_topic, warmup=1.0):
        super().__init__("merger_sync_observer")
        self.stats = {t: TopicStats(t, warmup=warmup) for t in topics}
        self.subs = []
        for t in topics:
            self.subs.append(
                self.create_subscription(
                    LaserScan, t, lambda msg, name=t: self._cb(name, msg), SENSOR_QOS
                )
            )
        self.skews = []
        self.skew_topic = skew_topic
        if skew_topic:
            self.subs.append(
                self.create_subscription(Float64, skew_topic, self._skew_cb, SENSOR_QOS)
            )

    def _cb(self, name, msg):
        self.stats[name].add(msg, time.monotonic())

    def _skew_cb(self, msg):
        self.skews.append(msg.data)

    def publisher_report(self):
        lines = []
        for t in self.stats:
            infos = self.get_publishers_info_by_topic(t)
            names = [f"{i.node_namespace.rstrip('/')}/{i.node_name}" for i in infos]
            rel = {i.qos_profile.reliability.name for i in infos}
            flag = "  ⚠ 발행자 2개 이상 — 합산 수신률이 단일 노드 발행률로 오인된다" if len(infos) > 1 else ""
            lines.append(f"  {t}: 발행자 {len(infos)}개 {names} QoS={sorted(rel)}{flag}")
        return lines


# float 초로 환산한 ROS 스탬프의 ULP 는 1.75e9 s 부근에서 약 238 ns 다. 1e-9 를 문턱으로 쓰면
# float64 해상도 아래라 의미가 없으므로, "같은 스탬프"의 문턱을 1 µs 로 명시한다.
STAMP_EQ_TOL = 1e-6


def nearest(sorted_series, t):
    """정렬된 계열에서 t 에 가장 가까운 값. 이분 탐색이라 O(log n)."""
    i = bisect.bisect_left(sorted_series, t)
    if i == 0:
        return sorted_series[0]
    if i == len(sorted_series):
        return sorted_series[-1]
    before, after = sorted_series[i - 1], sorted_series[i]
    return after if (after - t) < (t - before) else before


def pairing_analysis(front, rear, merged):
    """merged 스탬프를 front·rear 스탬프에 되맞춰 실제 쌍 어긋남을 복원한다.

    반환: (출력줄, 지표dict). 지표는 판정에 쓰인다 — 계산해 놓고 인쇄만 하면
    "출력 ≤ 입력" 하나로 쌍 동기 구조를 단정하게 되는데, 그 명제는 필요조건일 뿐이다.
    """
    if not merged.stamps or not front.stamps or not rear.stamps:
        return ["  (쌍 분석 표본 부족)"], {}

    fs, rs = sorted(front.stamps), sorted(rear.stamps)
    exact_front = exact_rear = 0
    skews = []
    for t in merged.stamps:
        nf, nr = nearest(fs, t), nearest(rs, t)
        if abs(t - nf) < STAMP_EQ_TOL:
            exact_front += 1
        if abs(t - nr) < STAMP_EQ_TOL:
            exact_rear += 1
        skews.append(abs(nf - nr))

    n = len(merged.stamps)
    metrics = {
        "n": n,
        "front_ratio": exact_front / n,
        "rear_ratio": exact_rear / n,
        "skew_median": statistics.median(skews),
        "skew_max": max(skews),
    }
    lines = [
        f"  merged 스탬프 {n}개 중"
        f" front 스탬프와 정확 일치 {exact_front}개 · rear 와 정확 일치 {exact_rear}개"
        f" (문턱 {STAMP_EQ_TOL * 1e6:.0f} µs)",
        f"  쌍 어긋남 |t_front - t_rear| : 중앙 {metrics['skew_median'] * 1e3:.2f} ms"
        f" · 최대 {metrics['skew_max'] * 1e3:.2f} ms",
    ]
    if exact_front and not exact_rear:
        lines.append("  → merged 는 front 의 스탬프를 그대로 물려받는다(rear 의 시각은 버려진다).")
    elif exact_rear and not exact_front:
        lines.append("  → merged 는 rear 의 스탬프를 그대로 물려받는다(front 의 시각은 버려진다).")
    return lines, metrics


def check_output_stamp(metrics, policy):
    """merged 스탬프의 출처가 --output-stamp 설정과 맞는지 판정한다.

    지금까지는 이 값을 merger 에 넘기기만 하고 결과를 확인하지 않았다 —
    설정이 먹었는지조차 검증하지 않은 셈이다.
    """
    if not metrics:
        return None, "쌍 분석 표본 부족으로 output_stamp 검증 생략"
    f, r = metrics["front_ratio"], metrics["rear_ratio"]
    expect = {
        "laser_1": ("front 정확 일치 ≈100%", f > 0.95),
        "laser_2": ("rear 정확 일치 ≈100%", r > 0.95),
        "midpoint": ("front·rear 모두 낮음", f < 0.10 and r < 0.10),
        "latest": ("front+rear 합 ≈100%", f + r > 0.95),
        "earliest": ("front+rear 합 ≈100%", f + r > 0.95),
    }
    desc, ok = expect[policy]
    msg = (f"output_stamp={policy} 기대({desc}) — 실측 front {f * 100:.1f}% · rear {r * 100:.1f}%")
    return ok, msg


class Injector(Node):
    """정해진 주기로 합성 스캔을 낸다. 스탬프는 발행 시각 그대로."""

    def __init__(self, rate, phase, jitter, beams, front_topic, rear_topic, seed=0):
        super().__init__("merger_sync_injector")
        self.period = 1.0 / rate
        self.jitter = jitter
        self.beams = beams
        self.seed = seed
        self.pub_front = self.create_publisher(LaserScan, front_topic, INJECT_QOS)
        self.pub_rear = self.create_publisher(LaserScan, rear_topic, INJECT_QOS)
        # 발행 시각(단조)을 남긴다. 개수만 세면 관측 창과 다른 구간을 세게 되어
        # "산출 ≤ 입력" 판정이 warmup 만큼 편향된다.
        self.times_front = []
        self.times_rear = []
        self._stop = threading.Event()
        # phase 는 주기의 몇 배만큼 rear 를 늦출지. 0.5 면 반주기 엇갈림.
        self.phase = phase * self.period
        self._thread = threading.Thread(target=self._run, daemon=True)

    @property
    def n_front(self):
        return len(self.times_front)

    @property
    def n_rear(self):
        return len(self.times_rear)

    def count_in(self, t_begin, t_end):
        """[t_begin, t_end] 안에서 발행한 front/rear 개수."""
        f = sum(1 for t in self.times_front if t_begin <= t <= t_end)
        r = sum(1 for t in self.times_rear if t_begin <= t <= t_end)
        return f, r

    def _scan(self, frame):
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = frame
        msg.angle_min = -math.pi
        msg.angle_max = math.pi
        msg.angle_increment = 2.0 * math.pi / self.beams
        msg.time_increment = 0.0
        msg.scan_time = self.period
        msg.range_min = 0.05
        msg.range_max = 40.0
        msg.ranges = [2.0] * self.beams
        return msg

    def _run(self):
        # 지터를 스케줄에 더하면 오차가 누적돼 상대 위상이 random walk 가 된다 —
        # ±4 ms · 510 스텝이면 표준편차가 주기(29 ms)를 넘어 --phase 가 통제변수 구실을 못 한다.
        # 그래서 명목 격자 t0 + k·period 를 유지하고 지터는 매 발행에 한 번만 얹는다(비누적).
        # 시드를 고정해 같은 명령이 같은 실험이 되게 한다.
        rng = random.Random(self.seed)
        t0 = time.monotonic()
        k_front = k_rear = 0
        t_front = t0 + rng.uniform(-self.jitter, self.jitter)
        t_rear = t0 + self.phase + rng.uniform(-self.jitter, self.jitter)

        while not self._stop.is_set():
            now = time.monotonic()
            nxt = min(t_front, t_rear)
            if nxt > now:
                time.sleep(min(nxt - now, 0.005))
                continue
            if t_front <= t_rear:
                self.pub_front.publish(self._scan("base_link"))
                self.times_front.append(time.monotonic())
                k_front += 1
                t_front = t0 + k_front * self.period + rng.uniform(-self.jitter, self.jitter)
            else:
                self.pub_rear.publish(self._scan("base_link"))
                self.times_rear.append(time.monotonic())
                k_rear += 1
                t_rear = t0 + self.phase + k_rear * self.period + rng.uniform(-self.jitter, self.jitter)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2.0)
        if self._thread.is_alive():
            # 살아 있는 채로 rclpy.shutdown() 이 돌면 데몬 스레드의 publish 가 무효 컨텍스트에서
            # 실행돼 traceback 으로 출력이 오염된다. 조용히 넘기지 않는다.
            print("  ⚠ 주입 스레드가 2초 안에 멈추지 않았다 — 이후 출력에 traceback 이 섞일 수 있다.")


# merger 의 `sync:` 통계 줄. 숫자 클래스를 넓게 잡아 nan/inf 가 와도 매치는 되게 한다 —
# 매치 실패를 "merger 가 통계를 안 낸다"로 오진하면 원인 진단이 통째로 엇나간다.
SYNC_LINE = re.compile(
    r"sync: in (?P<in1>\d+)/(?P<in2>\d+) -> (?P<pairs>\d+) pairs \((?P<rate>\S+)/s\) over (?P<span>\S+)s"
    r" \| skew\(accepted\) mean (?P<mean>\S+) ms \| skew\(observed\) max (?P<max>\S+) ms"
    r" \| dropped-by-skew (?P<drop_win>\d+) this window, (?P<drop_total>\d+) total"
)
# 쌍이 하나도 없던 창 — merger 가 침묵 대신 내는 경고.
NO_PAIR_LINE = re.compile(r"sync: no scan pairs in (\S+) s")


def run_merger(max_pair_skew, output_stamp, front_topic, rear_topic, merged_topic):
    args = [
        "ros2", "run", "dual_laser_merger", "dual_laser_merger_node", "--ros-args",
        "-p", f"laser_1_topic:={front_topic}",
        "-p", f"laser_2_topic:={rear_topic}",
        "-p", f"merged_scan_topic:={merged_topic}",
        "-p", "merged_cloud_topic:=/cloud_merged_synthetic",
        "-p", "target_frame:=base_link",   # 합성 스캔도 base_link → TF 경로를 타지 않는다
        # calibration_file 은 기본값이 빈 문자열이라 넘기지 않는다
        # (`-p calibration_file:=` 는 rcl 이 파싱하지 못하고 노드가 죽는다)
        "-p", "tolerance:=0.01",
        "-p", "queue_size:=5",
        "-p", "angle_increment:=0.00436332",
        "-p", "angle_min:=-3.141592654",
        "-p", "angle_max:=3.141592654",
        # 실기 런치와 같은 값을 명시한다 — 기본값으로 두면 merger 가 1/30 을 쓰고,
        # 실기(0.0293)와도 이전 런치값(0.067)과도 달라 재현도가 떨어진다.
        "-p", "scan_time:=0.0293",
        "-p", "range_min:=0.05",
        "-p", "range_max:=40.0",
        "-p", "min_height:=-1.0",          # 기본값 DBL_MIN 은 양수라 전 점이 걸러진다
        "-p", "max_height:=1.0",
        "-p", "use_inf:=true",
        "-p", "enable_dynamic_param_refresh:=false",
        "-p", f"max_pair_skew:={max_pair_skew}",
        "-p", f"output_stamp:={output_stamp}",
        "-p", "publish_sync_diagnostics:=true",
    ]
    # start_new_session=True 는 setsid 등가이면서 스레드 안전하다. preexec_fn 은 스레드가 있는
    # 프로세스에서 안전하지 않다고 문서화돼 있어(호출 순서를 바꾸면 조용히 깨진다) 쓰지 않는다.
    return subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, start_new_session=True,
    )


def drain(proc, sink):
    for line in proc.stdout:
        sink.append(line.rstrip())


def terminate_group(proc):
    """자식(별도 세션)을 확실히 정리한다. 어떤 예외도 밖으로 내보내지 않는다.

    `preexec_fn=os.setsid` 때문에 터미널의 Ctrl-C 가 자식에게 가지 않는다. 정리가
    try/finally 밖에 있으면 중간에 예외 하나로 merger 가 살아남아, 다음 실행에서
    합성 토픽의 두 번째 발행자가 되어 결과를 오염시킨다.
    """
    if proc is None or proc.poll() is not None:
        return
    for sig in (signal.SIGINT, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError, OSError):
            return
        try:
            proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue


def spin_for(node, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end and rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)


def cmd_observe(args):
    rclpy.init()
    topics = args.topics
    obs = Observer(topics, args.skew_topic, warmup=args.warmup)
    print(f"[observe] {args.duration:.0f}초 관측: {', '.join(topics)}")
    spin_for(obs, args.duration)

    print("\n=== 발행자 ===")
    for line in obs.publisher_report():
        print(line)

    print("\n=== 토픽별 ===")
    for t in topics:
        for line in obs.stats[t].report():
            print(line)

    print("\n=== 쌍 분석 (merged ↔ front/rear) ===")
    lines, _ = pairing_analysis(obs.stats[topics[0]], obs.stats[topics[1]], obs.stats[topics[2]])
    for line in lines:
        print(line)

    if obs.skews:
        mag = [abs(s) for s in obs.skews]
        print(f"\n=== merger 자기보고 skew ({args.skew_topic}) ===")
        print(f"  {len(obs.skews)}개 | 중앙 {statistics.median(mag) * 1e3:.2f} ms"
              f" | 최대 {max(mag) * 1e3:.2f} ms")
    elif args.skew_topic:
        print(f"\n  ({args.skew_topic} 수신 0 — merger 가 publish_sync_diagnostics 없이 도는 구판일 수 있다)")

    obs.destroy_node()
    rclpy.shutdown()
    return 0


def cmd_inject(args):
    # 인스턴스 격리 — 같은 도메인에서 두 번 돌리거나 유령 merger 가 남아 있으면
    # 토픽이 겹쳐 결과가 조용히 오염된다.
    tag = os.getpid()
    front = f"/scan_front_synthetic_{tag}"
    rear = f"/scan_rear_synthetic_{tag}"
    merged = f"/scan_merged_synthetic_{tag}"
    skew_topic = "/dual_laser_merger/sync_skew"
    return _run_inject(args, front, rear, merged, skew_topic)


def _wait_for_merger(node, topic, timeout=15.0):
    """merger 가 실제로 구독을 붙일 때까지 기다린다(3초 sleep 가정 대신)."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
        if node.count_subscribers(topic) >= 1:
            return True
    return False


def _run_inject(args, front, rear, merged, skew_topic):
    proc = run_merger(args.max_pair_skew, args.output_stamp, front, rear, merged)
    log = []
    drain_thread = threading.Thread(target=drain, args=(proc, log), daemon=True)
    drain_thread.start()

    rclpy.init()
    obs = None
    inj = None
    try:
        obs = Observer([front, rear, merged], skew_topic, warmup=args.warmup)
        inj = Injector(args.rate, args.phase, args.jitter, args.beams, front, rear, seed=args.seed)

        if not _wait_for_merger(inj, front):
            print(f"  ⚠ merger 가 {front} 을 구독하지 않는다 — 기동 실패로 본다.")
            for line in log[-15:]:
                print(f"    {line}")
            return 1

        inj.start()
        print(f"[inject] rate={args.rate} Hz phase={args.phase}×주기 jitter=±{args.jitter * 1e3:.1f} ms"
              f" seed={args.seed} max_pair_skew={args.max_pair_skew} s output_stamp={args.output_stamp}"
              f" — {args.duration:.0f}초")
        spin_for(obs, args.duration)
        inj.stop()
        time.sleep(1.0)
        spin_for(obs, 0.5)
        # merger 가 아직 살아 있을 때 찍어 둔다. 종료 후에 조회하면 발행자가 0으로 보인다.
        pub_snapshot = (obs.publisher_report(),
                        {t: len(obs.get_publishers_info_by_topic(t)) for t in (front, rear, merged)})
        return _report_inject(args, obs, inj, log, proc, drain_thread, front, rear, merged, skew_topic,
                              pub_snapshot)
    finally:
        # 판정이 어디서 끊기든 자식은 반드시 정리한다.
        terminate_group(proc)
        if inj is not None:
            inj.destroy_node()
        if obs is not None:
            obs.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def _report_inject(args, obs, inj, log, proc, drain_thread, front, rear, merged, skew_topic,
                   pub_snapshot):
    # 자식을 먼저 끝내고 drain 을 join 한 뒤에 로그를 스냅샷한다 —
    # 읽는 도중에도 새 sync: 줄이 들어오면 마지막 창이 들어가기도 빠지기도 해 판정이 비결정적이 된다.
    terminate_group(proc)
    drain_thread.join(timeout=3.0)
    log = list(log)

    n_out = len(obs.stats[merged].recv)
    n_skew = len(obs.skews)
    failures = []

    print("\n=== 주입 대비 산출 ===")
    # 같은 창에서 센다. 이전 판은 주입 개수(warmup 포함)와 수신 개수(warmup 1초 제외)를
    # 그대로 비교해, 34 Hz·15초에서 "출력이 입력보다 7% 이상 많아야만" 경보가 뜨는 상태였다.
    win = obs.stats[merged].window()
    if win is None:
        print("  ⚠ merged 수신 표본 부족 — 주입 대비 판정 생략")
        failures.append("merged 표본 부족")
        n_in = None
    else:
        w0, w1 = win
        f_in, r_in = inj.count_in(w0, w1)
        n_in = min(f_in, r_in)
        print(f"  관측 창 {w1 - w0:.2f}s (warmup 제외) — 그 창의 주입 front {f_in} · rear {r_in} (min = {n_in})")
        print(f"  같은 창의 수신 {merged} {n_out} 개 · {skew_topic} {n_skew} 개")
        # 창 경계에서 ±1 은 정상(마지막 쌍이 창 밖에서 발행될 수 있다).
        if n_out > n_in + 1:
            print(f"  ⚠ 산출이 입력보다 많다({n_out} > {n_in}) — 쌍 동기화 구조가 아니다.")
            failures.append("산출 > 입력")
        else:
            print(f"  ✔ 산출 ≤ 입력 ({n_out} ≤ {n_in}+1).")
            print("    ※ 이는 쌍 동기화의 **필요조건**일 뿐이다 — 'front 마다 발행하고 rear 는"
                  " 최신 것을 갖다 쓰는' 비동기 구현도 이 검사를 통과한다."
                  " 충분조건은 아래 스탬프 출처·위상 검증이 맡는다.")

    print("\n=== merger 자기보고 (생산자측 계수) ===")
    sync_lines = [m for m in (SYNC_LINE.search(l) for l in log) if m]
    if sync_lines:
        for m in sync_lines:
            print(f"  in {m.group('in1')}/{m.group('in2')} -> {m.group('pairs')} pairs"
                  f" ({m.group('rate')}/s over {m.group('span')}s) | skew(accepted) mean {m.group('mean')} ms"
                  f" | skew(observed) max {m.group('max')} ms"
                  f" | dropped {m.group('drop_win')} this window, {m.group('drop_total')} total")
            # 입력은 들어왔는데 쌍이 덜 맺혔고 게이트도 안 버렸다면 정책이 내부에서 버린 것이다.
            lost = min(int(m.group("in1")), int(m.group("in2"))) - int(m.group("pairs")) \
                - int(m.group("drop_win"))
            if lost > 1:
                print(f"    ※ 위 창에서 {lost}쌍이 콜백에 도달하지 못했다 —"
                      f" ApproximateTime 정책이 내부에서 폐기한 것(콜백 카운터로는 보이지 않는다).")
        # 첫 줄은 창(window)이 노드 기동 직후라 부분 구간이므로 뺀다
        steady = [float(m.group("rate")) for m in sync_lines[1:]] or [float(sync_lines[-1].group("rate"))]
        prod = max(steady)
        # 비교 우변은 명목 --rate 가 아니라 실측 주입률이어야 한다. 부하가 걸리면 실제 주입이
        # 명목보다 느려지고, 그러면 명목 기준 판정이 실제보다 느슨해져 PASS 로 기운다.
        inj_window = (inj.times_front[-1] - inj.times_front[0]) if len(inj.times_front) >= 2 else 0.0
        actual_rate = (len(inj.times_front) - 1) / inj_window if inj_window > 0 else args.rate
        if abs(actual_rate - args.rate) > args.rate * 0.01:
            print(f"  ※ 실측 주입률 {actual_rate:.2f} Hz 가 명목 {args.rate:.2f} Hz 와 1% 이상 다르다"
                  f" — 판정은 실측 기준으로 한다.")
        if prod > actual_rate * 1.01:
            print(f"  ⚠ 생산자 발행률 {prod:.2f} Hz > 실측 주입 {actual_rate:.2f} Hz — 쌍 동기화 구조가 아니다.")
            failures.append("생산자 발행률 > 입력률")
        else:
            print(f"  ✔ 생산자 발행률 최대 {prod:.2f} Hz ≤ 실측 주입 {actual_rate:.2f} Hz.")
        # 게이트를 걸었으면 실제로 버렸는지 확인한다(양성 대조). 버린 게 0이면 게이트 미동작이다.
        total_dropped = int(sync_lines[-1].group("drop_total"))
        if args.expect_drops > 0:
            if total_dropped < args.expect_drops:
                print(f"  ⚠ 게이트가 버린 쌍 {total_dropped} < 기대 {args.expect_drops} — 게이트 미동작.")
                failures.append("게이트가 기대만큼 버리지 않음")
            else:
                print(f"  ✔ 게이트가 {total_dropped} 쌍을 버렸다 (기대 ≥ {args.expect_drops}).")
        cons = n_out / max(args.duration - 1.0, 1e-6)
        if prod > 1.0 and cons < prod * 0.95:
            print(f"  ⚠ 생산자 {prod:.2f} Hz vs 소비자 측정 {cons:.2f} Hz —"
                  f" 측정하는 쪽이 흘린다. 실기에서 이 차이가 '입력·출력 Hz 불일치'로 보인다.")
    else:
        print("  (sync: 줄 없음 — merger 로그를 확인)")
        for line in log[-15:]:
            print(f"    {line}")
        failures.append("merger 가 sync 통계를 내지 않음")

    print("\n=== 발행자 (자식 종료 전 스냅샷) ===")
    pub_lines, pub_counts = pub_snapshot
    for line in pub_lines:
        print(line)
    for t, n in pub_counts.items():
        if n > 1:
            failures.append(f"{t} 발행자 {n}개")

    print("\n=== 토픽별 ===")
    for t in (front, rear, merged):
        for line in obs.stats[t].report():
            print(line)

    print("\n=== 쌍 분석 ===")
    lines, metrics = pairing_analysis(obs.stats[front], obs.stats[rear], obs.stats[merged])
    for line in lines:
        print(line)

    # 스탬프 출처 검증 — 지금까지 --output-stamp 는 merger 에 넘기기만 하고 결과를 안 봤다.
    ok, msg = check_output_stamp(metrics, args.output_stamp)
    if ok is None:
        print(f"  ※ {msg}")
    elif ok:
        print(f"  ✔ {msg}")
    else:
        print(f"  ⚠ {msg}")
        failures.append("output_stamp 미반영")

    # 위상 검증 — 쌍 동기라면 주입한 위상차가 관측 skew 로 그대로 나와야 한다.
    # 비동기 구현이면 skew 가 0~1주기로 흩어져 이 검사에 걸린다. jitter 를 준 실행은
    # 기대값 자체가 흐려지므로 건너뛴다.
    if metrics and args.phase > 0.0 and args.jitter == 0.0:
        expected = args.phase * (1.0 / args.rate)
        observed = metrics["skew_median"]
        tol = max(0.2 * expected, 2e-3)
        if abs(observed - expected) > tol:
            print(f"  ⚠ 위상: 주입 {expected * 1e3:.2f} ms 인데 관측 중앙 {observed * 1e3:.2f} ms"
                  f" (허용 ±{tol * 1e3:.2f} ms) — 쌍이 주입한 짝과 다르게 맺힌다.")
            failures.append("주입 위상 ≠ 관측 skew")
        else:
            print(f"  ✔ 위상: 주입 {expected * 1e3:.2f} ms ≈ 관측 중앙 {observed * 1e3:.2f} ms.")
    if obs.skews:
        mag = [abs(s) for s in obs.skews]
        print(f"  merger 자기보고 skew: 중앙 {statistics.median(mag) * 1e3:.2f} ms"
              f" · 최대 {max(mag) * 1e3:.2f} ms")
        # 판정 기준은 merger 에 넘긴 값이 아니라 --assert-skew-under 로 따로 줄 수 있다.
        # (게이트를 뺀 merger 를 이 검사가 실제로 잡는지 확인하는 음성 대조용)
        bound = args.assert_skew_under if args.assert_skew_under > 0.0 else args.max_pair_skew
        if bound > 0.0 and max(mag) > bound + 1e-4:
            print(f"  ⚠ 경계 {bound * 1e3:.1f} ms 를 넘긴 쌍이 발행됐다"
                  f" (최대 {max(mag) * 1e3:.2f} ms) — 경계가 강제되지 않는다.")
            failures.append("쌍 어긋남 경계 미강제")
        elif bound > 0.0:
            print(f"  ✔ 발행된 모든 쌍이 경계 {bound * 1e3:.1f} ms 이내.")

    # 노드·프로세스 정리는 _run_inject 의 finally 가 맡는다(예외 경로 포함).
    if failures:
        print(f"\nFAIL: {', '.join(failures)}")
        return 1
    print("\nPASS")
    return 0


def cmd_bag(args):
    """녹화된 rosbag2(.db3)에서 header.stamp 만 읽어 발행률과 쌍 어긋남을 복원한다.

    실시간 구독이 아니므로 BEST_EFFORT 유실이 끼어들지 않는다. 다만 녹화 자체가
    구독이므로, 토픽별 건수 차이는 '발행률 차이'가 아니라 '녹화기 유실'일 수 있다 —
    그래서 건수와 스탬프 간격을 같이 낸다.
    """
    import sqlite3

    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message

    db = args.bag
    if os.path.isdir(db):
        cands = [os.path.join(db, f) for f in sorted(os.listdir(db)) if f.endswith(".db3")]
        if not cands:
            print(f"{db} 안에 .db3 가 없다")
            return 1
        # rosbag2 는 크기·시간 상한을 걸면 _0.db3, _1.db3 … 로 쪼갠다. 첫 조각만 읽고
        # 조용히 부분 결과를 내면 사용자는 전체를 분석했다고 믿는다.
        dbs = cands
    else:
        dbs = [db]

    print(f"[bag] {len(dbs)}개 파일: {', '.join(os.path.basename(d) for d in dbs)}")

    # 여러 조각을 이어 붙여 하나의 계열로 만든다.
    series, recvs, scan_times_all = {t: [] for t in args.topics}, {t: [] for t in args.topics}, {t: [] for t in args.topics}
    for path in dbs:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            topics = {name: (tid, typ) for tid, name, typ in con.execute("SELECT id, name, type FROM topics")}
            for t in args.topics:
                if t not in topics:
                    continue
                tid, typ = topics[t]
                msg_cls = get_message(typ)
                for rt, data in con.execute(
                    "SELECT timestamp, data FROM messages WHERE topic_id=? ORDER BY timestamp", (tid,)
                ):
                    m = deserialize_message(bytes(data), msg_cls)
                    series[t].append(stamp_to_sec(m.header.stamp))
                    recvs[t].append(rt * 1e-9)
                    if getattr(m, "scan_time", 0.0) > 0.0:
                        scan_times_all[t].append(m.scan_time)
        finally:
            con.close()

    for t in args.topics:
        stamps, recv, scan_times = series[t], recvs[t], scan_times_all[t]
        if not stamps:
            print(f"  {t}: 없음")
            continue
        if len(stamps) < 2:
            print(f"  {t}: {len(stamps)} msg (표본 부족)")
            continue
        span = recv[-1] - recv[0]
        # 양수만 취한다 — 스탬프 중복·역행이 있는 녹화에서 중앙값이 0이면 0으로 나눈다.
        deltas = sorted(d for d in (b - a for a, b in zip(stamps, stamps[1:])) if d > 0.0)
        if not deltas or span <= 0:
            print(f"  {t}: {len(stamps)} msg — 스탬프가 단조 증가하지 않아 발행률 산출 불가")
            continue
        med = statistics.median(deltas)
        # 발행률 정의를 TopicStats.report 와 맞춘다((n-1)/span).
        print(f"  {t}: {len(stamps)} msg / {span:.2f}s"
              f" → 녹화률 {(len(stamps) - 1) / span:6.2f} Hz"
              f" | 스탬프 간격 중앙 {med * 1e3:6.2f} ms → {1.0 / med:6.2f} Hz"
              f" | 간격 최대 {deltas[-1] * 1e3:7.1f} ms"
              + (f" | 센서신고 scan_time {statistics.median(scan_times) * 1e3:.2f} ms"
                 f" → {1.0 / statistics.median(scan_times):.2f} Hz" if scan_times else ""))

    f, r, mg = args.topics
    if all(len(series[k]) > 1 for k in (f, r, mg)):
        print("\n=== 쌍 분석 ===")
        fs, rs, ms = sorted(series[f]), sorted(series[r]), series[mg]
        exact_f = exact_r = 0
        skews = []
        for t in ms:  # 이분 탐색 — 이전 선형 스캔은 10,000건에서 49초가 걸렸다
            nf, nr = nearest(fs, t), nearest(rs, t)
            if abs(t - nf) < STAMP_EQ_TOL:
                exact_f += 1
            if abs(t - nr) < STAMP_EQ_TOL:
                exact_r += 1
            skews.append(abs(nf - nr))
        print(f"  merged {len(ms)}개 중 front 스탬프 정확 일치 {exact_f} · rear 정확 일치 {exact_r}"
              f" (문턱 {STAMP_EQ_TOL * 1e6:.0f} µs)")
        skews_sorted = sorted(skews)
        print(f"  쌍 어긋남 |t_front - t_rear|: 중앙 {statistics.median(skews) * 1e3:.2f} ms"
              f" · p95 {skews_sorted[int(len(skews_sorted) * 0.95)] * 1e3:.2f} ms"
              f" · 최대 {max(skews) * 1e3:.2f} ms")
        print(f"  건수: front {len(fs)} · rear {len(rs)} · merged {len(ms)}")
        if len(ms) > min(len(fs), len(rs)):
            print("  ⚠ merged 건수 > 입력 최소 건수. merger 는 쌍당 1회만 내므로 이는 발행률이 아니라")
            print("    녹화기가 입력(대형 메시지)을 더 많이 흘린 결과다 — 입력 건수를 발행률로 읽지 말 것.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("bag", help="녹화된 rosbag2 를 오프라인 분석")
    b.add_argument("bag", help=".db3 파일 또는 그 디렉터리")
    b.add_argument("--topics", nargs=3, metavar=("FRONT", "REAR", "MERGED"),
                   default=["/scan_front", "/scan_rear", "/scan_merged"])

    o = sub.add_parser("observe", help="돌고 있는 시스템을 수동 관측")
    o.add_argument("--duration", type=float, default=20.0)
    o.add_argument("--topics", nargs=3, metavar=("FRONT", "REAR", "MERGED"),
                   default=["/scan_front", "/scan_rear", "/scan_merged"])
    o.add_argument("--skew-topic", default="/dual_laser_merger/sync_skew")
    o.add_argument("--warmup", type=nonneg_float, default=1.0,
                   help="첫 수신 후 버릴 구간 [s]")

    i = sub.add_parser("inject", help="합성 입력으로 하드웨어 없이 검증")
    i.add_argument("--rate", type=positive_float, default=34.0, help="입력 1개당 발행률 [Hz]")
    i.add_argument("--duration", type=positive_float, default=15.0)
    i.add_argument("--phase", type=float, default=0.0, help="rear 지연 = phase × 주기")
    i.add_argument("--jitter", type=nonneg_float, default=0.0, help="발행마다 얹는 지터 진폭 [s] (비누적)")
    i.add_argument("--beams", type=positive_int, default=360)
    i.add_argument("--warmup", type=nonneg_float, default=1.0,
                   help="첫 수신 후 버릴 구간 [s]. 판정 창을 직접 결정한다")
    i.add_argument("--seed", type=int, default=0, help="지터 난수 시드 — 같은 명령을 같은 실험으로 만든다")
    i.add_argument("--expect-drops", type=int, default=0,
                   help="게이트가 최소 이만큼 버려야 한다(양성 대조). 0 = 검사 안 함")
    i.add_argument("--max-pair-skew", type=float, default=0.0, help="merger 에 넘길 경계 [s]")
    i.add_argument("--assert-skew-under", type=float, default=0.0,
                   help="판정에만 쓸 경계 [s]. merger 에 넘긴 값과 달리 두면 "
                        "게이트가 없는 merger 를 이 검사가 잡는지 확인할 수 있다(음성 대조).")
    i.add_argument("--output-stamp", default="laser_1",
                   choices=["laser_1", "laser_2", "latest", "earliest", "midpoint"])

    args = ap.parse_args()
    return {"observe": cmd_observe, "inject": cmd_inject, "bag": cmd_bag}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
