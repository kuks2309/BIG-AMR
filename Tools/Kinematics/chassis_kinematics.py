#!/usr/bin/env python3
"""AMR(Autonomous Mobile Robot) 4륜 독립조향(multi-steer) 기구학 — 순수 수학 모듈.

can_relay/drive_gui.py 에서 **기구학 부분만** 추출(CAN·PyQt 의존성 제거).
원본 수식·상수는 비트 동일하게 보존 — 하드웨어 송신 로직은 제외한 순수 변환만 담는다.

원본 출처:
  can_relay/drive_gui.py (can_relay_2026-07-10.zip)
    └ chassis_kin::inverse_multisteer 이식 (kin_viz, seer_robotics_analysis@b0bce72, models.hpp:127-142)
  ADR: docs/adr/2026-07-09-kinviz-multisteer-to-drive-gui.md

역기구학(inverse kinematics): 차체명령 (vx, vy, ω) → 바퀴별 (조향각 θ, 바퀴속도 v)
  θᵢ = atan2(vy + ω·xᵢ, vx − ω·yᵢ),  vᵢ = hypot(vy + ω·xᵢ, vx − ω·yᵢ)

⚠ 미검증 가정(ADR §가정): 노드 매핑(node1=Rear, node2=Front)·KIN_STEER_SIGN(조향 부호)은
  실차 미검증. 첫 실차 구동은 저속에서 크랩/스핀 방향 확인 후 사용.

함수표:
  kin_inverse(vx, vy, w, vmax)   → {구동노드: [θ(rad), v(m/s)]}   역기구학 core
  twist_to_targets(vx, vy, w, …) → (vel_units, steer_counts)      θ·v → 액추에이터 목표(순수)
  kin_selftest()                 → bool                            5케이스 수학 검증

사용:
    python3 chassis_kinematics.py --selftest    # 무-하드웨어 수학 자가시험
"""
import math

# ── 바퀴 기하 / 노드 매핑 (kin_viz 이식 상수 @b0bce72) ─────────────────────
# 기하: Roll_A084 실측 config (live_models.hpp:67) — Front x=+0.6039, Rear x=-0.5961,
#       y=-0.0014 (휠베이스 1.200 m). 노드 매핑은 SPIN 부호 정합에서 도출한 가정.
KIN_NODE_XY = {1: (-0.5961, -0.0014), 2: (+0.6039, -0.0014)}  # 구동노드 → (x, y) m
KIN_STEER_OF = {1: 3, 2: 4}     # 구동노드 → 짝 조향노드
KIN_DRIVE_SIGN = -1             # FORWARD 모드 vel=-s 실측: 양수 모터값 = 차체 -x
KIN_STEER_SIGN = +1             # +counts = +θ(CCW) 가정 — 실차 검증 필요

# ── 물리 한계 / 스케일 상수 ────────────────────────────────────────────────
STEER_LIMIT_RAD = 2.443         # 조향 한계 ±140° (live_models.hpp:86)
M_S_PER_UNIT = 4.0906e-5        # 1 unit(0.1rpm) → m/s (r=0.125 m, reduction=32)
COUNTS_PER_RAD = 57344.0 * 180.0 / math.pi  # 조향 57,344 counts/° (90°=5,160,960)
VEL_MAX = 4889                  # 구동 속도 unit 상한 (0.1rpm)
KIN_VMAX = VEL_MAX * M_S_PER_UNIT  # ≈0.2 m/s (안전 상한)
KIN_WMAX = 0.3                  # 기구학 모드 ω 상한 (rad/s)

# 조향 홈/90° counts (액추에이터 절대위치 — twist_to_targets 기본값)
STEER_HOME = {3: 7871815, 4: 7840086}
STEER_90 = 5160960


def kin_inverse(vx, vy, w, vmax=KIN_VMAX):
    """chassis_kin::inverse_multisteer 이식 (models.hpp:127-142@b0bce72).

    차체명령 (vx,vy[m/s], ω[rad/s]) → {구동노드: [조향각θ(rad), 바퀴속도v(m/s)]}.
    θᵢ=atan2(vy+ω·xᵢ, vx−ω·yᵢ), vᵢ=hypot(같은 성분). 원본과 다른 점 2가지(ADR):
      1) ±140° 초과 시 등가해 접기 (θ∓π, −v) — 원본은 §6 find_right_steer_angle 상위 정책 소관
      2) 속도 포화를 vmax 단일 상한으로 (원본은 바퀴별 max_speed 배열, 여기선 전 바퀴 동일 한계)
    """
    out = {}
    vpeak = 0.0
    for n, (xi, yi) in KIN_NODE_XY.items():
        ax = vx - w * yi
        ay = vy + w * xi
        th = math.atan2(ay, ax)
        v = math.hypot(ax, ay)
        if abs(th) > STEER_LIMIT_RAD:  # 접기 후 |θ'|=π-|θ|<40° — 항상 한계 내
            th -= math.copysign(math.pi, th)
            v = -v
        out[n] = [th, v]
        vpeak = max(vpeak, abs(v))
    if vpeak > vmax > 0:  # 비율 유지 포화 (models.hpp:139-140)
        f = vmax / vpeak
        for n in out:
            out[n][1] *= f
    return out


def twist_to_targets(vx, vy, w, vmax=KIN_VMAX, steer_home=None):
    """차체명령 (vx,vy,ω) → (vel_units, steer_counts) 순수 변환.

    drive_gui.py DirectDriver.set_twist 의 계산부만 추출(하드웨어 송신 제외):
      vel_units[구동노드]  = clamp(round(KIN_DRIVE_SIGN·v / M_S_PER_UNIT), ±VEL_MAX)  [0.1rpm]
      steer_counts[조향노드] = round(steer_home[sn] + KIN_STEER_SIGN·θ·COUNTS_PER_RAD)  [counts]
    """
    home = dict(steer_home if steer_home is not None else STEER_HOME)
    tgt = kin_inverse(vx, vy, w, vmax)
    vel_units, steer_counts = {}, {}
    for n, (th, v) in tgt.items():
        u = int(round(KIN_DRIVE_SIGN * v / M_S_PER_UNIT))
        vel_units[n] = max(-VEL_MAX, min(VEL_MAX, u))
        sn = KIN_STEER_OF[n]
        steer_counts[sn] = int(round(home[sn] + KIN_STEER_SIGN * th * COUNTS_PER_RAD))
    return vel_units, steer_counts


def kin_selftest() -> bool:
    """kin_inverse 수학 검증 (하드웨어 불요) — 직진/후진(접기)/크랩/스핀/포화 5케이스."""
    E = 1e-9
    ok = True

    def chk(name, cond):
        nonlocal ok
        print(f"  kin {name}: {'PASS' if cond else 'FAIL'}")
        ok = ok and cond

    t = kin_inverse(0.1, 0, 0)  # 직진: θ≈0(|y|=0.0014 오프셋), v=0.1
    chk("직진", all(abs(v - 0.1) < 1e-6 and abs(th) < 0.02 for th, v in t.values()))
    t = kin_inverse(-0.1, 0, 0)  # 후진: |θ|=π→접기→θ≈0, v≈-0.1
    chk("후진(±140°접기)", all(abs(v + 0.1) < 1e-6 and abs(th) < 0.02 for th, v in t.values()))
    t = kin_inverse(0, 0.1, 0)  # 좌크랩: θ≈+90°, v=0.1
    chk("크랩", all(abs(math.degrees(th) - 90) < 1.0 and abs(v - 0.1) < 1e-6 for th, v in t.values()))
    t = kin_inverse(0, 0, 0.2)  # 제자리 CCW: 전륜(N2,x>0) θ≈+90°, 후륜(N1,x<0) θ≈-90°, v>0
    chk("스핀", abs(math.degrees(t[2][0]) - 90) < 1.0 and abs(math.degrees(t[1][0]) + 90) < 1.0
        and t[1][1] > E and t[2][1] > E and abs(t[1][1] - 0.2 * 0.5961) < 1e-3)
    t = kin_inverse(1.0, 0, 0)  # 포화: 1.0 → KIN_VMAX 로 비율 축소
    chk("포화", all(abs(v - KIN_VMAX) < 1e-6 for _, v in t.values()))
    return ok


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        print("chassis_kinematics 자가시험 (kin_inverse):")
        sys.exit(0 if kin_selftest() else 1)
    # 데모: 몇 가지 차체명령의 역기구학 출력
    print("역기구학 데모 — (vx, vy, ω) → {노드: [θ°, v m/s]}")
    for cmd in [(0.1, 0, 0), (0, 0.1, 0), (0, 0, 0.2)]:
        out = kin_inverse(*cmd)
        pretty = {n: [round(math.degrees(th), 2), round(v, 4)] for n, (th, v) in out.items()}
        print(f"  vx={cmd[0]} vy={cmd[1]} ω={cmd[2]}  →  {pretty}")
