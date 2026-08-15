#!/usr/bin/env python3
"""can_relay 노드 health 감시·복귀 SIL(Software In the Loop) 하니스.

## 무엇을 하나

`link:=mock` 으로 드라이버와 감시자를 **실제 프로세스로** 띄우고, 프로세스를 죽이거나
상태를 조작해 감시·복귀 경로를 끝까지 돌린다. 판다도 로봇도 필요 없다 — `MockLink` 가
제어권·심박·호밍 시퀀서를 흉내내고, 감시자는 CAN 을 보지 않고 `/diagnostics` 만 본다.

단위 회귀(`test/test_supervisor.py`)와 목적이 다르다. 그쪽은 `decide()` 를 함수로 부르고,
여기는 **프로세스 경계·파일 기록·서비스 호출·재기동**까지 실물로 통과시킨다. 단위 시험이
통과해도 여기서 깨질 수 있는 것: 서비스 이름 오타, QoS 불일치, 기록 경로 권한,
재기동 후 파라미터 소실, 진단 KeyValue 누락.

## 무엇을 하지 않나

- **CAN 버스에 아무것도 보내지 않는다.** `link:=mock` 이므로 판다를 열지 않는다.
- **펌웨어 fail-safe 를 검증하지 않는다.** 심박 억제까지만 관측하고, 그 뒤 「릴레이가
  실제로 열리는가」는 실기 몫이다(debt-075).
- **조향 거동을 검증하지 않는다**(debt-076).

## 쓰는 법

    source /opt/ros/humble/setup.bash && source install/setup.bash
    python3 Tools/can_relay_sil/sil_health.py            # 전체
    python3 Tools/can_relay_sil/sil_health.py --only 3 5 # 골라서
    python3 Tools/can_relay_sil/sil_health.py --keep     # 실패 시 로그 보존
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MACHINE = os.path.join(REPO, "src/Comm/CAN/can_relay/config/machine/foil_a082.yaml")

# 감시자 임계를 실험용으로 좁힌다 — 기본값(두절 3 s·창 120 s)이면 한 항목에 분 단위가 걸린다.
# 판정 로직은 그대로이고 시간 축만 줄인다.
DIAG_TIMEOUT_S = 1.5
RESTART_WINDOW_S = 20.0
RESTART_LIMIT = 3


class Ctx:
    """한 실험이 쓰는 프로세스·경로 묶음.

    `cleanup()` 은 실험 함수가 예외로 끝나도 불린다(호출부 `main`). 다만 **하니스 자신이
    죽으면 불리지 않으므로** 자식은 `start_new_session` 으로 띄워 프로세스 그룹째 정리한다.
    """

    def __init__(self, tag: str, keep: bool):
        self.tag = tag
        self.keep = keep
        self.dir = tempfile.mkdtemp(prefix=f"sil-{tag}-")
        self.state_dir = os.path.join(self.dir, "state")
        os.makedirs(self.state_dir, exist_ok=True)
        self.procs: list = []
        self.logs: dict = {}
        # 도메인을 실험마다 바꿔 동시 실행·잔류 노드와 섞이지 않게 한다.
        self.domain = str(70 + (abs(hash(tag)) % 20))

    def env(self) -> dict:
        e = dict(os.environ)
        e["ROS_DOMAIN_ID"] = self.domain
        e["PYTHONUNBUFFERED"] = "1"
        return e

    def spawn(self, name: str, args: list) -> subprocess.Popen:
        log = open(os.path.join(self.dir, f"{name}.log"), "w+")
        self.logs[name] = log.name
        p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT,
                             env=self.env(), start_new_session=True)
        p._sil_name = name          # 진단 출력용
        self.procs.append(p)
        return p

    def driver(self, extra: list = None) -> subprocess.Popen:
        args = ["ros2", "run", "can_relay", "can_relay_node", "--ros-args",
                "--params-file", MACHINE,
                "-p", "link:=mock", "-p", "allow_bringup:=false"]
        args += extra or []
        return self.spawn(f"driver{len(self.procs)}", args)

    def supervisor(self, extra: list = None) -> subprocess.Popen:
        args = ["ros2", "run", "can_relay", "relay_supervisor", "--ros-args",
                "-p", f"state_dir:={self.state_dir}",
                "-p", f"diag_timeout_s:={DIAG_TIMEOUT_S}",
                "-p", f"restart_window_s:={RESTART_WINDOW_S}",
                "-p", f"restart_limit:={RESTART_LIMIT}",
                "-p", "tick_hz:=5.0"]
        args += extra or []
        return self.spawn("supervisor", args)

    def state(self) -> dict:
        try:
            with open(os.path.join(self.state_dir, "state.json")) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def log_text(self, name: str) -> str:
        try:
            with open(self.logs[name]) as f:
                return f.read()
        except (OSError, KeyError):
            return ""

    def cleanup(self):
        for p in self.procs:
            if p.poll() is None:
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGINT)
                except OSError:
                    pass
        t0 = time.monotonic()
        for p in self.procs:
            p.wait(timeout=max(0.5, 6.0 - (time.monotonic() - t0)))
        for p in self.procs:
            if p.poll() is None:
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                except OSError:
                    pass
        if not self.keep:
            shutil.rmtree(self.dir, ignore_errors=True)


def wait_for(cond, timeout: float, poll: float = 0.15) -> bool:
    """조건이 참이 될 때까지 기다린다. 반환 = 참이 됐는가."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if cond():
            return True
        time.sleep(poll)
    return False


def call(ctx: Ctx, service: str, srv_type: str, payload: str,
         timeout: float = 20.0) -> str:
    """`ros2 service call` 1회. 반환 = 표준출력(실패도 문자열로 돌려준다)."""
    r = subprocess.run(
        ["ros2", "service", "call", service, srv_type, payload],
        capture_output=True, text=True, env=ctx.env(), timeout=timeout)
    return r.stdout + r.stderr


def engage(ctx: Ctx, on: bool = True) -> str:
    return call(ctx, "/can_relay_node/engage", "std_srvs/srv/SetBool",
                "{data: %s}" % ("true" if on else "false"))


def wait_engaged(ctx: Ctx, want: bool, timeout: float = 15.0) -> bool:
    return wait_for(lambda: ctx.state().get("engaged") is want, timeout)


def hard_kill(p: subprocess.Popen):
    """`kill -9` — 종료 훅이 돌 틈을 주지 않는다(형태 ① 재현)."""
    try:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except OSError:
        pass
    p.wait(timeout=5)


# ─────────────────────────────────────────────────────────────────────────
# 실험 — 각 함수는 (성공?, 관측 요약) 을 돌려준다. 예외는 상위가 실패로 잡는다.
# ─────────────────────────────────────────────────────────────────────────
def exp1_kill_and_restore(ctx: Ctx):
    """① 프로세스 소멸 → DEAD 판정 → 재기동 → 제어권 자동 복귀."""
    d = ctx.driver()
    ctx.supervisor()
    if not wait_for(lambda: ctx.state().get("engaged") is not None, 25.0):
        return False, "감시자가 진단을 받지 못했다(기록 미생성)"
    engage(ctx, True)
    if not wait_engaged(ctx, True):
        return False, f"engage 후 기록이 engaged=True 가 되지 않았다: {ctx.state()}"

    hard_kill(d)
    if not wait_for(lambda: "DEAD" in ctx.log_text("supervisor"), 12.0):
        return False, "DEAD 판정이 나오지 않았다"

    ctx.driver()                       # systemd 재기동 대역
    if not wait_for(lambda: "복귀 지시" in ctx.log_text("supervisor"), 30.0):
        return False, "복귀 지시가 나가지 않았다"
    if not wait_for(lambda: "복귀 완료" in ctx.log_text("supervisor"), 20.0):
        return False, "복귀가 완료되지 않았다"
    if not wait_engaged(ctx, True):
        return False, "복귀 후 제어권이 잡히지 않았다"
    return True, "DEAD → 재기동 → engage 자동 복원"


def exp2_zombie_suppresses_heartbeat(ctx: Ctx):
    """③ ROS 실행기 정체 → 심박 억제 → 감시자 ZOMBIE.

    정체는 `SIGSTOP` 으로 만든다 — 프로세스는 살아 있고(=systemd 미개입) 콜백만 멈춘다.
    실행기가 멈추면 제어 스레드도 함께 멈추므로 심박은 어차피 끊기지만, **감시자가
    「프로세스는 살아 있다」를 근거로 DEAD 가 아니라 ZOMBIE 로 가르는지**가 이 실험의 대상이다.
    """
    d = ctx.driver()
    ctx.supervisor()
    if not wait_for(lambda: ctx.state().get("engaged") is not None, 25.0):
        return False, "감시자가 진단을 받지 못했다"
    engage(ctx, True)
    if not wait_engaged(ctx, True):
        return False, "engage 실패"

    os.killpg(os.getpgid(d.pid), signal.SIGSTOP)
    try:
        if not wait_for(lambda: "ZOMBIE" in ctx.log_text("supervisor"), 15.0):
            return False, "ZOMBIE 판정이 나오지 않았다(DEAD 로 갈렸을 수 있다)"
    finally:
        os.killpg(os.getpgid(d.pid), signal.SIGCONT)
    return True, "정지된 프로세스를 DEAD 가 아니라 ZOMBIE 로 갈랐다"


def exp3_home_failed_blocks_restore(ctx: Ctx):
    """`home_failed` 가 서 있으면 재기동 후 복귀하지 않는다.

    `_home_failed` 는 인스턴스 변수라 재기동으로 사라지고, 드라이브 `0x6041` bit15 는 실패한
    호밍 뒤에도 1 로 남는다. 그 조합에서 자동 복귀까지 얹히면 0° 지령 시 ≈136.7° 스윙이 난다.

    **호밍 실패는 시한 초과로 만든다.** `~/home_cancel` 은 쓰지 않는다 — 취소는
    「만들었지만 사용은 안 한다」로 결정돼 있다
    (`docs/adr/2026-08-04-amr-test-gui-swappable-backend.md` §②). 실기에서 관측된 실패는
    `ERR_TIMEOUT`(2026-08-03 09:58)·`ERR_GOZERO`(2026-08-14) 이며 둘 다 취소가 아니다.

    래치는 **호밍 개시 순간**에 선다(`backend.home()` — 「여기부터 축이 움직인다」).
    성공한 완주만 그것을 풀므로, 호밍 중에 노드가 죽으면 래치가 선 채로 남는다 —
    이 실험이 재현하는 것이 그 상태다. 시한 초과를 기다릴 필요가 없다.
    """
    d = ctx.driver()
    ctx.supervisor()
    if not wait_for(lambda: ctx.state().get("engaged") is not None, 25.0):
        return False, "감시자가 진단을 받지 못했다"
    engage(ctx, True)
    if not wait_engaged(ctx, True):
        return False, "engage 실패"

    # `~/home` 은 terminal 까지 반환하지 않으므로 별도 프로세스로 건다. mock 은 대본이
    # 없으면 ENABLE 에 머물러 백엔드 시한(180 s)에 걸린다 = ERR_TIMEOUT 재현.
    ctx.spawn("home", ["ros2", "service", "call", "/can_relay_node/home",
                       "std_srvs/srv/Trigger", "{}"])
    if not wait_for(lambda: ctx.state().get("home_failed") is True, 240.0):
        return False, f"home_failed 가 서지 않았다(기록: {ctx.state()})"

    hard_kill(d)
    if not wait_for(lambda: "DEAD" in ctx.log_text("supervisor"), 12.0):
        return False, "DEAD 판정이 나오지 않았다"
    ctx.driver()
    if not wait_for(lambda: "호밍" in ctx.log_text("supervisor")
                    and "HOLD" in ctx.log_text("supervisor"), 30.0):
        return False, "HOLD(호밍 미완료) 판정이 나오지 않았다"
    time.sleep(3.0)
    if "복귀 지시" in ctx.log_text("supervisor"):
        return False, "❌ 차단돼야 하는데 복귀를 시도했다"
    return True, "home_failed 관측으로 자동 복귀를 막았다"


def exp4_crash_loop_stops_restore(ctx: Ctx):
    """④ 반복 재기동 → 창 안에서 `restart_limit` 초과 시 복귀 중단."""
    ctx.supervisor()
    d = ctx.driver()
    if not wait_for(lambda: ctx.state().get("engaged") is not None, 25.0):
        return False, "감시자가 진단을 받지 못했다"
    engage(ctx, True)
    if not wait_engaged(ctx, True):
        return False, "engage 실패"

    for i in range(RESTART_LIMIT + 1):
        hard_kill(d)
        if not wait_for(lambda: "DEAD" in ctx.log_text("supervisor"), 12.0):
            return False, f"{i+1}회차 DEAD 판정 실패"
        d = ctx.driver()
        time.sleep(4.0)
    if not wait_for(lambda: "crash-loop" in ctx.log_text("supervisor"), 20.0):
        return False, "crash-loop 판정이 나오지 않았다"
    return True, f"{RESTART_LIMIT}회 초과 후 복귀를 멈췄다"


def exp5_estop_holds_restore(ctx: Ctx):
    """⑤ E-stop 인가 중에는 복귀하지 않는다."""
    d = ctx.driver()
    ctx.supervisor()
    if not wait_for(lambda: ctx.state().get("engaged") is not None, 25.0):
        return False, "감시자가 진단을 받지 못했다"
    engage(ctx, True)
    if not wait_engaged(ctx, True):
        return False, "engage 실패"

    # latched(TRANSIENT_LOCAL) 발행자를 상주시킨다 — 재기동한 노드가 구독 즉시 받아야 한다.
    ctx.spawn("estop", ["ros2", "topic", "pub", "/estop", "std_msgs/Bool",
                        "{data: true}", "--qos-durability", "transient_local",
                        "--qos-reliability", "reliable", "-r", "1"])
    if not wait_for(lambda: ctx.state().get("estop") is True, 20.0):
        return False, f"E-stop 이 기록에 반영되지 않았다: {ctx.state()}"

    hard_kill(d)
    if not wait_for(lambda: "DEAD" in ctx.log_text("supervisor"), 12.0):
        return False, "DEAD 판정 실패"
    ctx.driver()
    if not wait_for(lambda: "E-stop" in ctx.log_text("supervisor")
                    and "HOLD" in ctx.log_text("supervisor"), 30.0):
        return False, "HOLD(E-stop) 판정이 나오지 않았다"
    return True, "E-stop 래치가 자동 복귀를 막았다"


def exp6_manual_disengage_is_not_restored(ctx: Ctx):
    """⑥ 사람이 내린 제어권은 되돌리지 않는다(진단 두절이 없으므로)."""
    ctx.driver()
    ctx.supervisor()
    if not wait_for(lambda: ctx.state().get("engaged") is not None, 25.0):
        return False, "감시자가 진단을 받지 못했다"
    engage(ctx, True)
    if not wait_engaged(ctx, True):
        return False, "engage 실패"

    engage(ctx, False)
    if not wait_engaged(ctx, False):
        return False, "engage false 가 반영되지 않았다"
    time.sleep(4.0)
    if "복귀 지시" in ctx.log_text("supervisor"):
        return False, "❌ 수동 해제를 되돌렸다 — 감시자가 운용자와 싸운다"
    return True, "수동 해제를 IDLE 로 두고 개입하지 않았다"


def exp7_boot_id_mismatch_discards(ctx: Ctx):
    """⑦ 다른 부팅의 기록으로는 복귀하지 않는다(전원 사이클 방지)."""
    d = ctx.driver()
    sup = ctx.supervisor()
    if not wait_for(lambda: ctx.state().get("engaged") is not None, 25.0):
        return False, "감시자가 진단을 받지 못했다"
    engage(ctx, True)
    if not wait_engaged(ctx, True):
        return False, "engage 실패"

    hard_kill(d)
    if not wait_for(lambda: "DEAD" in ctx.log_text("supervisor"), 12.0):
        return False, "DEAD 판정 실패"
    hard_kill(sup)

    path = os.path.join(ctx.state_dir, "state.json")
    rec = ctx.state()
    if not rec.get("engaged"):
        return False, f"기록이 engaged 가 아니다: {rec}"
    rec["boot_id"] = "00000000-0000-0000-0000-000000000000"   # 다른 부팅으로 위조
    with open(path, "w") as f:
        json.dump(rec, f)

    ctx.supervisor()
    if not wait_for(lambda: "폐기" in ctx.log_text("supervisor"), 20.0):
        return False, "기록 폐기 로그가 없다"
    ctx.driver()
    time.sleep(5.0)
    if "복귀 지시" in ctx.log_text("supervisor"):
        return False, "❌ 다른 부팅의 기록으로 복귀했다"
    return True, "boot_id 불일치로 기록을 폐기하고 복귀하지 않았다"


def exp8_state_file_is_never_half_written(ctx: Ctx):
    """⑧ 저장 도중 죽여도 반쪽 JSON 이 남지 않는다(원자 교체).

    감시자를 기록이 도는 중에 여러 번 `kill -9` 하고, 매번 남은 파일이 파싱되는지 본다.
    반쪽 파일이 남으면 다음 기동이 「기록 없음」으로 읽어 복귀가 조용히 사라진다.
    """
    ctx.driver()
    for i in range(6):
        sup = ctx.supervisor()
        time.sleep(1.2 + 0.13 * i)      # 저장 시점에 걸치도록 조금씩 어긋나게
        hard_kill(sup)
        path = os.path.join(ctx.state_dir, "state.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    json.load(f)
            except ValueError as exc:
                return False, f"{i+1}회차에서 반쪽 JSON 이 남았다: {exc}"
        # 임시파일이 쌓이면 tmpfs 를 먹는다 — 정리되는지도 본다.
        leftovers = [n for n in os.listdir(ctx.state_dir) if n.startswith(".state-")]
        if len(leftovers) > 2:
            return False, f"임시파일이 {len(leftovers)}개 남았다: {leftovers[:3]}"
    return True, "강제 종료 6회에서 기록이 온전했다"


EXPERIMENTS = [
    (1, "프로세스 소멸 → 재기동 → 제어권 복귀", exp1_kill_and_restore),
    (2, "실행기 정체 → ZOMBIE 판정", exp2_zombie_suppresses_heartbeat),
    (3, "호밍 중 사망 → 복귀 차단", exp3_home_failed_blocks_restore),
    (4, "반복 재기동 → crash-loop 차단", exp4_crash_loop_stops_restore),
    (5, "E-stop 인가 중 복귀 차단", exp5_estop_holds_restore),
    (6, "수동 해제는 되돌리지 않음", exp6_manual_disengage_is_not_restored),
    (7, "boot_id 불일치 → 기록 폐기", exp7_boot_id_mismatch_discards),
    (8, "기록 원자성(반쪽 JSON 없음)", exp8_state_file_is_never_half_written),
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="*", type=int, help="실험 번호만 골라 실행")
    ap.add_argument("--keep", action="store_true", help="실패해도 로그·기록 보존")
    a = ap.parse_args(argv)

    picked = [e for e in EXPERIMENTS if not a.only or e[0] in a.only]
    print(f"can_relay health SIL — {len(picked)}개 실험 "
          f"(두절 임계 {DIAG_TIMEOUT_S}s · 복귀창 {RESTART_WINDOW_S}s/{RESTART_LIMIT}회)\n")

    results = []
    for num, title, fn in picked:
        ctx = Ctx(f"e{num}", a.keep)
        t0 = time.monotonic()
        try:
            ok, note = fn(ctx)
        except Exception as exc:                       # 하니스 자신의 실패도 실패로 센다
            ok, note = False, f"{type(exc).__name__}: {exc}"
        dt = time.monotonic() - t0
        results.append((num, title, ok, note, dt, ctx.dir if a.keep else ""))
        print(f"  [{'PASS' if ok else 'FAIL'}] {num}. {title}  ({dt:.1f}s)")
        print(f"         {note}")
        if not ok and a.keep:
            print(f"         로그: {ctx.dir}")
        ctx.cleanup()

    npass = sum(1 for r in results if r[2])
    print(f"\n결과: {npass}/{len(results)} PASS")
    print("\n⚠ 여기서 통과해도 실기 검증이 아니다 — 심박 상실 뒤 펌웨어가 실제로 릴레이를"
          "\n  여는가(debt-075)와 그때 조향이 어디로 가는가(debt-076)는 잭업 실기 몫이다.")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
