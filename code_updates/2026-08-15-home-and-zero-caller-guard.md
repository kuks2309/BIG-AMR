# 2026-08-15 — 호밍 후 조향 0° 복귀: 드라이버 결합 대신 **호출자 가드** 채택

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md`, `hooks/coding-comment-gate.py`).
> 약어: DI(Digital Input) · PP(Profile Position) · SOP(Standard Operating Procedure)

- 사용자 지시: 2026-08-15 「드라이버에서 호밍 + 0도 조향 기능이 있으면 조합해서 사용하면
  되지 않을까?」 → 「조합 + 호출자 가드만 추가」
- 선행 결정: `docs/adr/2026-08-08-steer-zero-return-after-homing.md`

## 무엇이 문제인가 (현재 사실)

호밍만으로는 조향축이 0° 에 서지 않는다. 펌웨어 시퀀서의 `GOZERO` 목표
`SEER_HOME_ZERO_N3/N4`(= 7,882,020 / 7,859,062)는 **호밍 후 정착값**이고, 실측 0°
(`steer_home_counts` = [7,871,815, 7,840,086])에서 **+0.178° / +0.331°** 떨어져 있다.
펌웨어 도달 허용오차가 1.0° 라 펌웨어는 그 편차를 검출하지 못한다.

드라이버는 이미 두 기능을 **따로** 노출한다 — `~/home`(블로킹 서비스)과 `~/steer_deg`.
따라서 **조합으로 충분하다**: `~/home` 이 반환된 뒤 `~/steer_deg` 에 `0.0` 을 발행하면 된다.
`~/home` 이 블로킹이라 순서가 보장되고, 성공하면 `_homed=True` 라 조향 게이트도 통과한다.

**그런데 조합만으로는 위험한 구멍이 하나 남는다.**
`RelayBackend.homed_effective()` 는 드라이브가 보고한 `0x6041` bit15 만으로도 True 를
돌려준다(Seer 가 호밍한 경우를 인정하기 위한 설계). 그래서 **호밍이 실패해도 조향 지령이
수리된다.** 복귀하지 못한 축은 `0x6064` 가 0 을 읽어 실제 각도를 알 수 없는데도 그렇다.
그 상태에서 절대위치 지령을 내면 축이 어디로 갈지 알 수 없다.

실기 관측(Foil_A082)이 정확히 그 조합이었다:

| 항목 | 값 |
| --- | --- |
| 호밍 결과 | `ERR_GOZERO (30s, reached_mask=0x01)` — 실패 |
| node3 | `pos=7,882,021`(= +0.178°) · `sw=0x9450`(bit15=1) · `DI=1` |
| node4 | `pos=0` · `sw=0x9450`(bit15=1) · `DI=9`(bit3 = −Limit) |

두 축 모두 bit15=1 이므로 `homed_effective()` 는 True 다. 호밍은 실패했는데 조향은 열려 있었다.

## 채택안

**드라이버는 그대로 두고**(`backend.py`·`driver_node.py` 무변경, 펌웨어도 무변경)
호출자 쪽에 절차와 가드를 둔다.

`can_relay/home_and_zero.py` (`ros2 run can_relay home_and_zero`):

1. `~/home` 호출
2. **응답 `success` 가 False 면 0° 를 보내지 않고 종료**(코드 2) ← 이 파일의 요지
3. 성공이면 `~/steer_deg` 에 `0.0` 발행
4. `joint_states` 로 두 축이 `tol_deg`(기본 0.1°) 안에 들어올 때까지 대기
   — **실측 없는 축은 도달로 치지 않는다**
5. 종료코드 0 / 3(미도달) / 4(서비스 없음)

판정 로직 `ZeroReturnGuard` 는 전송을 `client` 로 주입받아 **ROS·하드웨어 없이 회귀로 고정**된다.
허용오차를 드라이버의 `settle_tol_deg`(3.0°)로 쓰지 않는 이유는 그 폭이 바로잡으려는
편차(0.178°/0.331°)보다 커서 **지령 전에도 「도달」로 읽히기** 때문이다.

## 기각한 안

**드라이버 결합**(`home()` 이 `steer_to_zero()` 를 이어 호출) — 구현·검증까지 마쳐
`session/6e5a2017`(커밋 `0522d2d`)에 있으나 채택하지 않았다. 사용자 결정이며, 같은 결과를
호출자 조합으로 얻을 수 있고 드라이버 표면을 늘리지 않는다.
**펌웨어 상수 교체**도 기각 상태 그대로다(재플래시 회피 — ADR §Alternatives).

## 검증

```
$ PYTHONPATH=. python3 -m pytest test/test_home_and_zero.py -q
10 passed

$ python3 src/Comm/CAN/can_relay/mutation_check.py
✅ 검출  Z1   호밍 실패에도 0° 를 보낸다 — 가드 제거(이 도구가 지키는 핵심)
✅ 검출  Z2   도달 허용오차를 느슨하게 — GOZERO 정착 편차가 0° 로 통과
✅ 검출  Z3   실측 없는 축을 도달로 인정 — 「모르면 됐다고 친다」
✅ 검출  Z4   0° 를 호밍보다 먼저 보낸다 — 호밍이 그 목표를 덮어쓴다
✅ 검출  Z5   실패 사유를 로그에서 지운다 — 조용한 실패
✅ 전 항목 검출
```

**실기 미검증** — 이 스크립트로 실제 호밍을 돌린 적은 없다. 첫 실기는 이동구역 확보 또는
잭업 상태에서 할 것. `tol_deg` 0.1° 와 `timeout_s` 10초는 **선택값이며 실측 근거가 없다**.

## 남는 것

- **debt-034 · debt-016 은 닫히지 않는다.** 상수명이 사실과 어긋나는 문제와 펌웨어가 편차를
  검출하지 못하는 문제는 그대로다. 이 변경은 「0° 로 보내는 것」과 「실패 시 안 보내는 것」만 다룬다.
- **node4 복구 미완** — `0x6064` 가 0 을 읽는 현상은 debt-036 소관이며 인과 미판정이다.
- `Tools/amr_test_gui/gui.py` 는 이미 자체 `_steer_zero_return()` 을 갖고 있다(별도 경로).
- ⚠ **시험 수집 함정(별건)**: `test/test_master_frame_match.py` 는 `Log/` 캡처가 없으면 모듈
  레벨 skip 을 내는데, pytest 6.2 에서 그 skip 이 **디렉터리 수집 전체를 0건으로 만든다.**
  캡처가 없는 워크트리에서 `pytest test` 는 `1 skipped` 만 찍혀 **통과처럼 보인다.**
  당분간 `--ignore=test/test_master_frame_match.py` 로 돌릴 것.
