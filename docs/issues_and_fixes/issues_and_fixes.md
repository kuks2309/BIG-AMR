# 이슈 및 수정 기록 (Issues and Fixes)

> ⚠ **조향 홈 관련 서술 정정 — 정본은 아래 한 곳이다. 원문은 이력으로 보존한다.**
> **정본: `docs/homing/2026-08-03-can-relay-homing-assets.md` §0** (호밍 **10회 연속 실측**, 2026-08-03 15:33~15:40)
> (값 정본은 `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml` 의 `steer_home_counts`)
>
> - 조향 0° = **`[7871815, 7840086]`** — ⚠ **Seer 좌표계 기준**이며 **물리적 직진은 미확인**이다.
> - **`7882020 / 7859062` 는 0° 가 아니다** — 「**호밍 후 정착값**」이며 0° 에서
>   **+0.178° / +0.331°** 벗어나 있다. 호밍 10회 실측 정착값은 node3 **7,882,021**(σ≈2.8c) ·
>   node4 **7,859,065**(σ≈3.2c) 로 σ≈3 counts 에 재현된다 ⇒ **결함이 아니라 설계 동작**이다.
> - `counts/°` = **57,344**(지령각→CAN 기울기 실측 1.000000) · `0x6098` 호밍 방식 = **1**(−리밋) ·
>   리밋 스위치 **실재** · 호밍 성공률 **10/10**, 소요 **35.0 s**.
>
> **❌ 2026-08-02 판정(`docs/verified_facts/2026-08-02-steer-home-closed.md`)은 폐기됐다 — 인용 금지:**
> - ~~홈 = `[7871810, 7839894]`~~ → **틀렸다.** node4 가 193c 어긋난 raw 판독값이었다.
> - ~~구값 `7871815 / 7840086` 은 「출처 없는 값」~~ → **반증됐다.** 출처는 **Seer 가 실시간으로 내는
>   `0x607A` 조향 목표**이며, 그 값이 1 count 이내로 맞았다.
> - ~~「CAN ↔ Seer 독립 교차확인」~~ → **성립하지 않는다.** Seer 1040 은 판다가 엿듣는 **바로 그
>   `0x6064` 의 아핀 변환**이다(기울기 ×57,344 = **1.000001**). 같은 프레임을 두 번 읽은 것이라
>   역산 `0° = CAN + Seer°×57344` 는 **항등식**이고 자세와 무관하게 같은 값을 낸다.
>   그 측정이 확정한 것은 **Seer 내부 조향 영점**이지 물리적 0° 가 아니다.
> - `debt-007` 은 종결이나, **홈 상수 부채 id 는 계보마다 다르다** — `origin/main` 이 정본:
>   홈 상수 하드코딩 = **debt-026** · can_relay 이름 충돌 = **debt-025** · 구동축 브링업 = **debt-027**.

> ❌ **정정 2026-08-03: 위 배너의 값·판정 2건이 실측으로 뒤집혔다.** 원문은 이력으로 보존한다.
> 정본: `docs/homing/2026-08-03-can-relay-homing-assets.md` §10 (실측 2026-08-03 11:44)
>
> - **홈(0°) = `[7871815, 7840086]`** 이다. 위 배너의 `[7871810, 7839894]` 은 **0° 가 아니라 raw 판독값**이었다 —
>   0° 는 같은 배너 마지막 줄의 역산식 `0° = CAN_0x6064 + Seer_deg × 57344` 로 구해야 하는데 적용되지 않았다.
>   실측 0° 는 node3 **7,871,816** / node4 **7,840,087** 이고, 구값 `[7871815, 7840086]` 은 **양 노드 모두 1 count
>   (0.000017°) 이내**로 맞다. 위 배너 값은 node4 에서 **193 counts = 0.0034°** 어긋난다.
> - 「구값은 **틀린 값이 아니라 출처 없는 값**」도 반증됐다 — **출처가 있다.** Seer 가 실시간으로 내는
>   `0x607A` 조향 목표다(passthrough 캡처에서 연속 관측).
>   > ❌ **재정정 2026-08-03 17:00. [E8]** 「출처가 `0x607A`」는 유효하나 **0° 근거로는 선택 인용**이다.
>   > `Log/homing_capture_220350.jsonl` 의 `0x607A:00` 다운로드 전수(노드당 n=6,464):
>   > `7,871,815 / 7,840,086` = **145회 (2.2%)** vs `7,882,020 / 7,859,062`(GOZERO 상수) = **6,319회 (97.8%)**.
>   > Seer 가 압도적으로 많이 지령한 값은 **채택값 쪽이 아니다.**
>   > 다른 근거였던 「1040 역산 재현」도 같은 캠페인이 **항등식이라 무효화**했다.
>   > ⇒ `[7871815, 7840086]` 은 **값만 유지**(정본 `foil_a082.yaml:134`)하고
>   > 라벨은 **「공학적 채택값」**까지만 — **「실측 0°」·「실측 확정」 표현 금지**.
> - ⚠ **과장 금지**: 193 counts = **0.0034°** 로 **거동상 무의미**하다. 안전 문제가 아니라 정본 정확성 문제다.
> - ⚠ `7882020 / 7859062`(펌웨어 `SEER_HOME_ZERO_N3/N4`)가 **0° 가 아니라 호밍 후 정착값**이라는 위 배너 서술은
>   **그대로 유효**하다 — 별개 사안이다. 다만 0° 가 바뀌었으므로 편차는 재계산해 **+0.178° / +0.331°**
>   (node3 +10,204 c / node4 +18,975 c @ 57,344 c/°)이다. 「0° 에 정확히 놓지 않는다」는 결론은 불변.

---

## 2026-08-10

### [Fix] pytest 수집 중단 해소 — 모듈 레벨 skip → fixture (debt-057 상환)

`test_master_frame_match.py` 가 캡처 부재 시 **모듈 최상위**에서
`pytest.skip(..., allow_module_level=True)` 를 내어 **디렉터리 전체 수집이 중단**됐다.

```
수정 전  pytest test/   → collected 0 items / 1 skipped   ← 앞선 파일 6개도 수집 안 됨
수정 후  pytest test/   → 393 passed, 8 skipped (exit 0)
```

원인은 `MASTER = _master_frames()` 를 모듈 최상위에서 부른 것이다. 그 자리의 주석은
`allow_module_level=True` 가 「수집 오류로 다른 시험까지 죽는 것」을 막는다고 적고 있었으나,
**실제로는 그 방식 자체가 디렉터리 수집을 죽인다**(pytest 6.2.5 실측).
`master` **fixture** 로 옮겨 skip 을 함수 단위로 내리자 이 파일의 8개만 건너뛰고 나머지는
정상 수집·실행된다.

⚠ **이 함정이 다른 문제를 가리고 있었다** — 수집이 0이라 아무것도 돌지 않았으므로
전량 실행의 실패든 크래시든 보일 수가 없었다. 출력이 `1 skipped` 뿐이라
**「문제 없다」로 읽히는 것이 가장 위험한 부분**이었다.

### [Fix] `robot_geometry` · `RecursiveMovingAverage` · `ActionMutex` gtest 11건 (debt-049 계속)

2WS `trnav_2ws_core` 의 **순수 자산을 모두 덮었다**(`TransientGuard`·`TrapezoidalProfile`·
`math_utils` 에 이어 나머지 3종).

```
colcon test → trnav_2ws_core 36 tests, 0 failures
돌연변이 ① parsePlatform 대체를 DD 로            → 2 failures
돌연변이 ② RMA 재귀식 부호 오류(new−old → old−new) → 3 failures
돌연변이 ③ ActionMutexGuard 가 해제하지 않음      → 3 failures
원복                                              → 0 failures
```

특히 **`parsePlatform` 의 무성 대체를 못 박았다** — 모르는 이름·오타·빈 문자열이 예외도 경고도
없이 `QD_DIAGONAL` 로 해석된다. 이 기체는 QD 대각이 **아니므로** 그 해석은 틀린 기하로 이어지고,
같은 계열의 사고가 이미 있었다(QD 기본 기하가 흘러들어와 제자리 회전이 187 mm 병진이 됨).
⚠ **바람직해서가 아니라 사실이라서 고정한다** — 대체를 없애거나 바꾸려면 이 시험이 먼저 실패한다.
`"INLINE_DUAL_STEER"`(이 기체의 실제 배치 이름)조차 QD 로 떨어진다는 것도 함께 남겼다.

`ActionMutexGuard` 는 **예외 경로에서의 해제**를 고정했다 — 풀리지 않으면 한 번 죽은 뒤
이후 모든 기동이 거부된다.

### [Fix] 전량 실행 간헐 segfault 해소 — 스핀 스레드 join 누락 (debt-058 상환)

`test_gui_node.py` 의 `rig` 픽스처가 `MultiThreadedExecutor` 를 데몬 스레드에서 돌리는데
**그 스레드를 join 하지 않고** 노드를 파괴했다.

```python
executor.shutdown()
thread.join(timeout=5.0)   # ← 추가
client.destroy_node()
driver.destroy_node()
```

- **`Executor.shutdown()` 은 미결 콜백을 기다린다**(`_work_tracker.wait()`, 문서에도
  "wait for their completion"). ⚠ 처음에 「종료를 요청할 뿐」이라고 적었는데 **틀렸다** —
  rclpy 소스를 확인하고 정정했다.
- 그러나 **호출자의 스핀 스레드를 join 하지는 않는다.** 콜백이 끝난 뒤에도 그 스레드는
  `spin()` 내부(대기셋 처리·guard condition 정리)에 있을 수 있고, 그 상태에서
  `destroy_node()` 가 rcl 핸들을 해제하면 경합이 난다. 픽스처가 **시험마다 새로 돌므로**
  (15회) 경합 창이 그만큼 열린다.

**A/B 실측**

```
A  join 없음   실패 2 / 12   (segfault, exit 139)
B  join 있음   실패 0 / 12
누계          미수정 4/15 실패 · 수정 0/18 실패
전량 실행     4회 연속 exit 0 · 398 passed, 8 skipped
```

⇒ **한 프로세스로 전량 실행이 가능해졌다.** 종전에는 `test_gui_node.py` 를 분리해야 했다.

#### PyQt5 가설은 기각됐다

처음에는 「PyQt5 와 rclpy 가 한 프로세스에 함께 적재돼서」로 추정했으나 **틀렸다** —
`test_gui_node.py` **단독**으로도 3회 중 2회 죽었다(PyQt5 조합은 3회 중 1회).
크래시는 이 파일 고유의 경합이었고 PyQt5 는 무관하다.

### [Fix] `TrapezoidalProfile` · `math_utils` gtest 16건 (debt-049 계속)

`turn` 의 Stage 1(coarse)이 이 프로파일 위에 서 있고, 오늘 넣은 두 가드(`−7`·`−8`)가
`normalizeAngle*` 로 각도 오차를 잰다. 프로파일이 바뀌면 감속이 어긋나고, 각도 정규화가
어긋나면 ±180° 부근에서 가드가 반대로 판정한다.

```
colcon test → trnav_2ws_core 25 tests, 0 failures
돌연변이 ① normalizeAngle 을 fmod 로            → 5 failures
돌연변이 ② 삼각형에서도 피크를 max_speed 로      → 2 failures
돌연변이 ③ isComplete 를 >= 에서 > 로            → 2 failures
원복                                             → 0 failures
```

#### 시험 작성 중 **제 가정이 틀렸다** — 코드가 옳았다

```
normalizeAngle(3π)      →  −π   (내 기대 +π)
normalizeAngleDeg(540)  →  −180 (내 기대 +180)
```

`std::remainder` 의 **round-half-even 타이브레이크** 때문이다. 몫이 정확히 x.5 인 입력
(±180 의 홀수배)은 짝수 쪽으로 접힌다: `540/360 = 1.5 → 2` → `540 − 720 = −180`.
헤더 주석이 이미 「±π 를 한 부호로 뭉개지 않는다」고 명시하고 있었는데 읽지 않고 기대값을 적었다.

⇒ 시험을 코드에 맞추되, **그 규약 자체를 못 박는 시험**(`TieBreakAtBoundaryIsRoundHalfEven`)을
새로 넣었다. 「+180 이 나올 것」이라 가정하는 호출자가 생기면 그때 잡힌다.

#### 돌연변이 확인에서도 한 번 헛짚었다

「삼각형 판정 제거」 돌연변이가 미검출로 나와 시험이 눈먼 줄 알았으나, **치환 자체가 적용되지
않았다** — 정규식이 `std::min(...)` 을 찾았는데 실제 코드는 `std::sqrt(...)` 였다.
대상 코드를 확인하고 다시 걸자 2 failures 로 검출됐다.
**미검출을 보면 시험을 의심하기 전에 돌연변이가 실제로 적용됐는지부터 확인해야 한다.**

### [Fix] `TwoWsDualSteerIK` gtest 14건 — 제자리 회전 자세 강제 고정 (debt-049 계속)

이번 세션에서 `computeSpin` 을 「범용 IK 를 푸는 것」에서 **「±90° 를 강제하는 것」**으로 바꿨는데
그 변경에 시험이 없었다. 예전 방식은 결과가 `wheels_[i].y == 0` 에 전적으로 의존해 기하
파라미터가 어긋나면 **조용히 다른 자세**가 나왔다 — QD 기본값(±0.330, ±0.135)이 흘러들어와
−67.75°(양 축 같은 부호)가 나오고 제자리 회전이 **187 mm 병진**이 된 사례가 있다.

```
colcon test → 14 tests, 0 failures
돌연변이 ① computeSpin 을 범용 IK 로 되돌림  → 2 failures
돌연변이 ② isInline 을 항상 true 로           → 3 failures
원복                                          → 0 failures
```

고정한 성질:

- **자세 강제** — ω 크기와 무관하게 ±90°, 앞뒤 부호 반대, ω 부호 반전 시 조향 반전,
  속도는 `|ω·x_i|`. **기하가 어긋나도(y=±0.05) 자세가 ±90° 로 유지**되는 것까지 확인한다 —
  이것이 예전 방식과의 결정적 차이다.
- **인라인 전제** — `isInline()` 이 대각 배치를 거짓으로 판정하고 허용오차를 지킨다.
- **원호 조향 항등식** — `atan(x_i / R)`. R=1.0 m 에서 전륜 +31.13° / 후륜 −30.80° 로
  실기 실측과 일치하며, **전후 비대칭(0.33°)** 이 살아 있어야 한다(대칭 근사로 되돌아가면 실패).
- **±90° 정규화** — 어떤 (vx, vy) 조합에서도 조향이 ±90° 를 넘지 않고, 후진은 조향이 아니라
  `direction` 이 담으며, `wheel_speed` 는 항상 비음수다.

### [Fix] 2WS 스택 **최초의 자동 시험** — `TransientGuard` gtest 10건 (debt-049 부분 상환)

⚠ **`debt-049` 는 등록된 것보다 범위가 넓다.** 조사해 보니 `trnav_2ws_action_server` 뿐 아니라
**2WS 5개 패키지 전부**가 시험 인프라 0이다(`test/` 디렉터리 0 · CMake 등록 0).

```
trnav_2ws_action_server  dir:—  cmake:0        trnav_2ws_core        dir:—  cmake:0
trnav_2ws_interfaces     dir:—  cmake:0        trnav_2ws_kinematics  dir:—  cmake:0
trnav_2ws_motion         dir:—  cmake:0
```

**액션서버의 `execute()` 는 거대한 단일 함수라 리팩터 없이는 단위시험이 안 된다.**
거기에 gtest 를 억지로 붙이면 거짓 안심만 남는다. 그래서 **순수 클래스부터** 시작했다.

`TransientGuard` 를 고른 이유는 오늘 넣은 **조향 미도달 감시(`status −8`)가 이 클래스의
`gate_blocked` 위에 서 있기** 때문이다. 게이트 판정이 조용히 바뀌면 그 가드가 발화하지
않거나 반대로 정상 주행을 막는데, 어느 쪽도 현장에서야 드러난다.

```
ament_add_gtest 등록 → colcon test → 10 tests, 0 failures
돌연변이 ① 주행 중에도 Phase0 임계(3°) 사용   → 5 failures
돌연변이 ② drive_scale 클램프 제거            → 2 failures
원복                                          → 0 failures
```

특히 **게이트 임계가 국면마다 다르다**는 사실을 고정했다 — Phase 0 은 3°,
주행 중은 15°(`transient_guard.cpp:49,53`). 이것을 모르면 「주행 중 3° 넘으면 막힌다」로
오해하는데, 실제로는 정상 주행에서 `gate_blocked` 가 참이 되지 않는다.

**남는 것**: 액션서버 4개(`turn`·`turn_reverse`·`yaw_control`·`yaw_control_reverse`)의
제어 루프는 여전히 시험이 없다. `debt-049` 를 **닫지 않고** 범위를 정정해 남긴다.

### [Fix] `RelayBackend.start()` 브링업 회귀 5건 신설 (debt-047 상환)

2026-08-08 의 두 수정 중 **어느 쪽이 실제로 고정돼 있는지 돌연변이로 먼저 확인**했다.

```
A  조향 게이트를 self._homed 로 되돌림   → 1 failed   ← 이미 고정돼 있었다
   (test_backend.py::test_low_cmd_steer_allowed_when_drive_reports_homed, 타 세션 b0bbc62)
B  start() 의 브링업 호출 2줄 제거        → 393 passed · **미검출**
```

B 만 비어 있었으므로 그쪽에 회귀 5건을 붙였다(`test/test_relay_bringup.py`).
`_write_bringup()` 을 직접 부르지 않고 **`start()` 를 돌려** 배선을 지나가게 했다.

```
돌연변이 확인
  ① start() 브링업 호출 제거   → test_start_sends_drive_bringup_when_enabled 실패
  ② 조향축까지 브링업          → test_bringup_is_not_sent_to_steer_axes 실패
  ③ allow_bringup 플래그 무시  → test_no_bringup_when_disabled 실패
  원복                         → 5 passed
```

작성 중 **오탐 1건** — `0x60FF=0`(목표속도 0)은 정상 지령 루프도 보내므로 「브링업이 안 나갔다」를
검사할 수 없다. 브링업 **고유** 프레임 4개(`0x6040=0x86`·`0x100C`·`0x100D`·`0x6060=3`)만
보도록 좁혔다. `DirectBackend` 시험 때와 **같은 종류의 오탐**을 두 번 냈다.

**회귀 결과**: `test_gui_node.py` 단독 15 passed(exit 0) + 나머지 전량 383 passed·8 skipped(exit 0)
= **398개 통과, 실패 0**. 한 프로세스로 합치면 아래 `debt-058` 로 죽으므로 분리 실행했다.

### [Open→정정] 전량 실행 간헐 segfault (exit 139) — `debt-058`

⚠ **종전 서술 「모두 통과 뒤 종료 시점」은 틀렸다.** faulthandler 로 지점을 특정했다:

```
Current thread:
  rclpy/node.py:1468 create_service
  can_relay/driver_node.py:218 __init__
  test/test_gui_node.py:66 rig          ← 약 53% 지점, 실행 중
```

요약줄만 보고 「종료 시점」이라 추정한 것이었다. 실제로는 `test_gui_node.py` 의 rclpy 노드·
서비스 생성 중에 죽으며 **간헐적**이다. 분리하면 양쪽 다 정상(15 + 383).

수집이 정상화되자 드러났다.

```
전량        exit 0 · 393 passed, 8 skipped   × 4회
--ignore    exit 139 Segmentation fault      × 1회 (같은 조합 이후 2회는 exit 0)
```

- **제 수정과 무관하다** — 크래시는 `--ignore` 조합에서 났고, 수정 후 전량 실행은 4회 모두 exit 0.
- 한 프로세스에 **PyQt5 와 rclpy 확장 모듈이 함께 적재**되며(faulthandler 출력에 둘 다 등장),
  종료 순서 문제로 보인다. **기전 미확정.**
- ⚠ **종료코드를 봐야 안다.** 요약줄은 `393 passed` 로 정상이고 크래시는 그 **뒤**에 난다 —
  요약만 보고 성공으로 읽으면 CI 가 붉어지는 이유를 못 찾는다.
  (내가 앞선 보고에서 종료코드를 확인하지 않았다.)

### [Fix] `DirectBackend` 에 구동축 브링업 추가 + 회귀 4건 (debt-045 상환)

2026-08-08 의 구동축 브링업 수정이 `RelayBackend` **한쪽에만** 들어가 UI 직결 경로는 같은 고장
(프로세스 재시작 뒤 구동축이 `0x60FF` 를 받고도 안 돎)이 그대로 재현되는 상태였다.

`RelayBackend.start()` 와 **같은 위치**(제어권 확인 후 · 폴 스레드 시작 전)에 같은 프레임을 넣었다.
`P.drive_init_frames(n, MOTOR_BUS)` 를 쓰므로 두 경로의 바이트가 같다 —
이 백엔드의 존재 이유가 「UI 는 같은데 백엔드만 다르다」는 비교 기준이기 때문이다.
조건 없이 보낸다(ROS 경로의 `allow_bringup` 은 배포 yaml 이 true 라 실질 동작이 같고,
여기에 쓰이지 않는 손잡이를 새로 만들지 않는다).

**회귀 4건 신설** (`test/test_direct_bringup.py`) — 핸들러를 직접 부르지 않고 **가짜 판다로
`set_engaged(True)` 를 끝까지 돌려** 배선을 지나가게 했다(2026-08-04-001 의 실패 형태 회피).

```
돌연변이 확인 (통과 숫자가 아니라 이것이 커버리지 근거다)
  ① set_engaged 의 _write_bringup() 호출 제거   → 3 failed  (누락·바이트·순서)
  ② 조향축까지 브링업                            → 1 failed  (조향 제외 시험)
  원복                                           → 4 passed
```

시험 작성 중 **오탐을 한 번 냈다** — 「조향축으로 나간 모든 프레임」을 금지로 판정했더니
폴 루프의 정상 SDO 읽기(`0x40`, `0x6064`·`0x606C`·`0x6078`·`0x6041`)가 걸렸다.
판정 대상을 **조향축에 대한 브링업 프레임**으로 좁혀 고쳤다.

**전체 회귀**: `393 passed` (실패 0). 제외한 것은 `test_master_frame_match.py` 하나이며
캡처 파일 부재로 어차피 skip 되는 파일이다 — 아래 [Trap] 참조.

### [Trap] `pytest <디렉터리>` 가 **수집을 통째로 중단**한다 — "1 skipped" 로 끝난다

```
python3 -m pytest test/                    → collected 0 items / 1 skipped
python3 -m pytest test/test_protocol.py    → 29 passed
python3 -m pytest test/ --ignore=test/test_master_frame_match.py → 393 passed
```

`test_master_frame_match.py:31` 이 캡처 파일(`Log/homing_capture_220350.jsonl`) 부재로
**모듈 레벨 skip** 을 내는데, 그 순간 **전체 수집이 0으로 끝난다**(pytest 6.2.5).
알파벳 순서상 그 파일 앞에 6개가 있는데도 하나도 수집되지 않는다.

⚠ **위험한 형태다.** 출력이 `1 skipped` 뿐이라 **「돌릴 게 없다 / 문제 없다」로 읽힌다.**
실패가 있어도 보이지 않는다. 캡처 파일이 있는 환경에서는 정상 수집되므로 **환경에 따라
조용히 달라진다.** → `debt-057` 등록.

### [Fix] `yaw_control` 계열 SIL 런치 신설 — 로봇 없이 가드 회귀 가능 (debt-056 상환)

기존 8개 기동에는 `sil_*.launch.py` 가 있는데 `yaw_control`·`yaw_control_reverse` 만 없어
**SIL 검증 이력이 0** 이었다. 오늘 `−7`·`−8` 가드 검증도 전부 실기로만 했다.

**다른 SIL 런치와 다른 점 — `sil_pose_adapter_node` 를 포함한다.**

```
플랜트 translate_sim_odom_node → map→base TF + /rtabmap/localization_pose(PoseWithCovariance, BEST_EFFORT)
sil_pose_adapter_node          → /robot_pose (PoseStamped, RELIABLE)     ← 기본 토픽이 맞아 리맵 불요
```

`turn`·`spin` 등은 IMU yaw 만 쓰고 `LocalizationMonitor` 를 쓰지 않아 어댑터가 필요 없다
(기존 8개 런치 중 **어느 것도 어댑터를 포함하지 않는다**). `yaw_control` 은 시작 시 맵 자세로
`yaw_offset` 을 잡고, `−7` 가드가 맵 yaw 와 대조하며, `LocalizationMonitor` 가 `/robot_pose` 를
구독하므로 어댑터가 필수다.

**검증 (2026-08-10, 도메인 7 격리)**

```
정상 주행       /robot_pose 50.0 Hz · status 0 · 거리 0.500 m · 헤딩오차 0.000°
파라미터 콜백    임계 0.001 시도 → "out of range [0.01, 90.00]" 로 거부 (SIL 에서도 동작)
−7 가드 재현    imu_yaw_noise:=3.0 주입 + 임계 0.5° → status −7 · 0.5 s · 8 mm
                로그: |IMU기준 -4.52° − 맵 0.00°| = 4.52° > 0.50° 가 10 cycle 연속
```

⚠ **SIL 의 구조적 한계 2건 — 기록해 둔다.**
1. **플랜트는 IMU 와 맵 자세를 같은 지상진값에서 만든다** → 괴리가 **정확히 0.000°** 다.
   `−7` 을 보려면 `imu_yaw_noise` 로 IMU 만 오염시켜야 한다. 그냥 돌리면 영원히 발화하지 않는다.
2. **즉응 플랜트는 조향 지연이 없어 `gate_blocked` 가 발생하지 않는다** → `−8` 을 SIL 로 보려면
   `steer_rate` 를 낮게 줘야 한다. 이 두 조건을 런치 docstring 에 적어 두었다.

### [Fix] `yaw_control` 계열 파라미터 콜백 신설 — **거짓 성공 제거** (debt-055 상환)

콜백이 없어 모든 파라미터가 생성자 전용이었고, `ros2 param set` 이 **성공을 반환하면서 거동을
바꾸지 않았다**(2026-08-10 실측: 발산 임계를 set 으로 낮췄으나 가드가 발화하지 않음).
근거·설계: `docs/adr/2026-08-10-yaw-control-param-callback.md`.

**핵심은 화이트리스트가 아니라 「명시적 거부」다.** `spin` 의 기존 콜백은 화이트리스트 밖 키를
**조용히 통과**시켜 거짓 성공이 그대로 남는다. `yaw_control` 계열은 자기 네임스페이스
(`yaw_control*_` · `transient_`)의 비-화이트리스트 키를 만나면 **거부하고 이유를 돌려준다.**

**검증 (2026-08-10, 전진·후진 양판)**

```
(a) 화이트리스트   heading_divergence_deg 5.0 → 3.0        성공 · get 으로 값 반영 확인
(b) 생성자 전용    yaw_control_pose_topic                   실패 + "생성자에서만 읽힌다 — 재기동할 것"
(b2) transient_    transient_runtime_gate_threshold_deg     실패 + 같은 이유
(c) 범위 밖        heading_divergence_deg 200.0             실패 + "out of range [0.01, 90.00]"
회귀 주행          헤딩 유지 0.4 m                          status 0 · 거리 0.402 m · 오차 +0.009°
```

**죽은 키 5개 삭제** — 감사에서 읽는 코드가 0건인 키가 나왔다. 값은 goal 필드로 준다.

```
전진판  yaw_control_max_steer_deg · yaw_control_i_max_deg
후진판  yaw_control_reverse_max_steer_deg · _i_max_deg · _pose_qos
⇒ 이제 그 이름으로 get 하면 "Parameter not set" 으로 즉시 드러난다
```

⚠ **범위 한정**: 다른 네임스페이스(기하·플랫폼 등 베이스 소관)는 건드리지 않았다 — 이 노드가
판단할 근거가 없다. 그 범위의 거짓 성공은 남으며, `spin`·`mpc`·`translate_*` 의 화이트리스트 밖
거짓 성공도 그대로다(별건).

### [Retract→Fix] `debt-050` 오진 정정 — `yaw_control_reverse` 는 pose 를 정상 수신한다

**종전 기록이 틀렸다.** 「`yaw_control_reverse` 가 `/rtabmap/localization_pose` 를 구독하는데
발행자가 0개라 pose 를 못 받는다」고 적었으나, 소스·실행 양쪽으로 확인하니 사실이 아니다.

```
yaw_control_reverse_pose_topic 을 읽는 코드          0건 (죽은 yaml 키)
LocalizationMonitor::Params::pose_topic 기본값       "/robot_pose"  (localization_monitor.hpp:27)
⇒ reverse 는 pose_topic 을 설정하지 않으므로 기본값 /robot_pose 를 쓴다
```

**실행 확인**: 노드 기동 시 `/robot_pose` 구독자 1 → 2 증가, 노드 구독 목록에 `/robot_pose` 존재,
`/rtabmap/localization_pose` 는 **토픽 자체가 없음**(구독조차 안 함).

⇒ 나를 속인 것은 **읽히지도 않는 yaml 키가 실재하지 않는 토픽을 가리키고 있었던 것**이다.
yaml 만 보고 코드를 확인하지 않아 없는 결함을 등록했다.

**조치 (2026-08-10)**

1. **죽은 키를 살렸다** — `lm_params.pose_topic = safeParam("yaw_control_reverse_pose_topic", "/robot_pose")`
   를 코드에 추가하고 yaml 값을 `/robot_pose` 로 정정했다. 이제 전진판과 같은 규약이며
   fused pose 로 redirect 할 수 있다.
2. **`−7`·`−8` 가드를 이식했다** — 전진판에 넣은 헤딩 발산 탐지와 조향 미도달 감시를
   `yaw_control_reverse` 에도 같은 규약으로 넣었다(파라미터 접두만 `yaw_control_reverse_`).

**`yaw_control_reverse` 첫 실기 검증 (2026-08-10)**

```
헤딩 유지 · 0.4 m · vx_max 0.05(magnitude)
status 0 · 거리 0.401 m · 최종 헤딩오차 +0.020° · 가드 오탐 0
```

이 액션은 그동안 **실기 이력이 0** 이었다 — 이번이 첫 확인이다.
### [Fix] Giving way did not release the junction — a circular wait that failed 1 job in 5

**Symptom.** In a two-robot Gazebo run, jobs failed with
`gave way for 45s and nobody passed — giving up`. Four of eighteen jobs failed
in 27 minutes (22%). Every failure was this and nothing else: no docking
failure, no timeout, no rejection, and no `WARN`/`ERROR` of any other kind.

**Root cause.** The junction reservation and the give-way handshake were each
correct alone and wrong together, and nothing tested the seam.
`SimAcs.claim_junction` states the invariant the whole scheme rests on:

> "A robot always releases the junction it holds before claiming another, so no
> robot ever waits on a junction while holding one — which is what makes a
> circular wait impossible."

That holds only along the path through `_junction_control`, which is the only
place a junction is released while a job runs. A robot told to give way returns
from `SimRobot.drive()` **before** reaching it (`sim_acs.py`, the yield branch),
so it stood aside — off the road, stationary, announcing "clear — you may pass"
— while still holding its red light. The robot it was yielding TO then waited on
that light. Neither could move until `YIELD_LIMIT` (45 s) killed the job.

The clearest instance was a MUTUAL hold, each robot sitting on the junction the
other needed:

```
690.8  join_GRV1_ULD: held by amr2
696.5  join_GRV1_LD:  held by amr1
696.9  [amr2] holding at join_GRV1_LD — amr1 has it
699.7  amr2 gives way to amr1 -> stepping aside -> clear — you may pass
706.7  [amr1] holding at join_GRV1_ULD — amr2 has it
744.8  [amr2] gave way for 45s and nobody passed — giving up
744.8  join_GRV1_ULD: held by amr1      <- freed ONLY by giving up
745.0  [job_0025] FAILED
```

The last two lines are the proof: the passer took the junction within 50 ms of
the give-up. **Space was never the constraint** — both robots had already
stopped and the yielder was off the lane. The blocker was a dict entry. This is
why enlarging the world does not fix it: a bigger hall makes encounters rarer,
turning a reproducible deadlock into an intermittent one, and at the documented
fleet size (six 3.5T AGVs on segment C, [S16]) encounters are the normal case.

**Fix.** Release the yielder's junction at the single point where a robot
*becomes* a yielder — `SimAcs.who_yields`, since `_giving_way` is written
nowhere else. Two lines:

```python
self.release_junction(chosen)
chosen._junction = None
```

A yielder cannot re-claim while standing aside (it returns early), and it
re-acquires normally through `_junction_control` once it rejoins. `YIELD_LIMIT`
is kept as a safety net.

**Regression test.** `src/MES/csm/test/test_traffic.py` — 8 tests, new file.
The junction/give-way seam had **zero** coverage before. It drives the fleet
bookkeeping directly (no ROS, no poses), so a deadlock that took 20 minutes of
Gazebo to surface now reproduces in 0.12 s. Verified the tests actually catch
the bug: with the fix reverted, **4 of 8 fail**, including
`test_the_mutual_hold_that_failed_three_jobs`.

**Verification — two 2-robot Gazebo runs, identical settings**
(`FLEET_ROBOTS=2`, `--robots 2 --batch-seconds 15`):

| | before | after |
|---|---|---|
| runtime | 1638 s (27 min) | 3213 s (53 min) |
| delivered | 17 | 42 |
| **failed** | **4** | **0** |
| give-way encounters | 5 | 5 |
| **passes completed** | **1 of 5** | **5 of 5** |
| deadlock give-ups | 4 | 0 |
| `WARN`/`ERROR` lines | — | 0 |
| docking failures | 0 | 0 |
| closest approach (body gap) | 1.46 m | 1.90 m |

Delivery rate after the fix is flat across the run (7, 8, 8, 8, 8 per 10 min),
so nothing degrades over an hour. Unit suite 143 -> 151 passed.

**Not a safety defect.** Closest body gap never fell below 1.46 m against a
0.90 m contact threshold and a 1.20 m avoidance target, in either build. The
avoidance layer always held; the failure mode was liveness only.

**Liveness check.** 52 jobs created, 42 delivered, 0 failed. The only jobs never
retired are the four `CTR*_ULD -> SLT_LD*` (segment C) jobs plus the newest
in-flight batch. Segment C has no robot bound to it — amr3 is not yet written —
so those queue as BUSY for ever by design, which is the behaviour that confirms
adding amr3 will pick them up. No servable job starved.

**Relevance to amr3.** `who_yields` picks the yielder by name order
(`chosen = a if a.name > b.name else b`), so amr3 would have been the fleet's
permanent yielder and would have absorbed nearly every one of these deadlocks.
Fixing this before writing amr3 avoids a failure that would have looked like
"amr3 is broken" when it was not.

Files: `src/MES/csm/csm/adapters/sim_acs.py`, `src/MES/csm/test/test_traffic.py`.

### [Fix] `yaw_control` 조향 미도달 지속 감시 — `status −8` 신설 (debt-052)

조향축 비응답 시 `yaw_control` 이 **60초를 아무 진단 없이 대기**했다(실측: 지령 −20.2°,
실제 0.00°, 거리 0.001 m, `status −3`). `TransientGuard` 가 구동을 0 으로 묶는 것은
**정상 안전 동작**이지만, 그 상태가 무한 지속돼도 보고하는 경로가 없었다.
근거·설계: `docs/adr/2026-08-10-yaw-control-gate-blocked-guard.md`.

```cpp
gate_blocked 연속 지속 > yaw_control_gate_blocked_timeout_sec(5.0) → abort(−8)
```

임계 5.0 s 는 **정상 조향 이동 시간(실측 0→31° 에 약 3 s)보다 길게** 잡은 값이다.
`steer_timeout_sec`(조향이 목표에 닿는 데 허용하는 시간)와 의미가 같아 같은 값을 쓴다.

**실기 검증 2건 (2026-08-10)**

```
(a) 정상 주행 · 임계 5 s              status 0 · 거리 0.400 m          ⇒ 오탐 0
(b) 가드 임계 0.5° · 지속 임계 0.1 s   status −8 · 0.1 s · 이동 1 mm    ⇒ 발화·코드 정상
    로그: 조향 미도달 0.1 s 지속 — 지령 F=-7.59°/R=0.00° 대 실제 F=-0.02°/R=-0.02°
```

- **(b) 를 두 번 실패하고서야 조건을 알았다.** 주행 중 가드는 `steer_gate_threshold`(3°)가
  아니라 **`runtime_gate_threshold`(15°)** 를 쓴다(`transient_guard.cpp:53`, Phase 0 만 3°).
  게다가 `steer_rate_limit` 이 지령을 완만하게 올려 **정상 주행에서는 조향 오차가 15° 에
  도달하지 않는다.** 즉 `gate_blocked` 는 실제로 조향이 실패했을 때만 참이 된다 —
  어제 발화한 것은 지령 −20.2° 대 실제 0° 로 20° 오차가 났기 때문이다.
  → 재현하려면 가드 임계 자체를 낮춰야 했다.
- ⚠ **원인은 고치지 않았다.** 조향축이 왜 비응답이 되는지(`debt-051`)는 그대로다.
  본 수정은 **5초 안에 드러나게** 할 뿐이다.
- ⚠ `turn`·`turn_reverse`·`spin` 은 손대지 않았다 — 셋 다 Phase 0 에서 이미 abort 한다.

### [Fix] `yaw_control` 에 조대(粗大) 헤딩 발산 탐지기 — `status −7` 신설 (debt-053)

IMU 가 회전을 놓쳐도 알 방법이 없어 **25° 틀어진 채 `status 0`(성공)** 을 반환한 사례가 있었다.
제어 소스는 **IMU 그대로 두고**(측위 heading 은 정밀도가 낮아 미세 제어에 쓰면 오히려 나빠진다),
**고장 탐지만** 추가했다. 근거·설계: `docs/adr/2026-08-10-yaw-control-heading-divergence-guard.md`.

```cpp
diverge = |normalizeAngleDeg(보정 yaw − 맵 yaw)|
diverge > yaw_control_heading_divergence_deg(5.0) 가 count(10) cycle 연속 → abort(−7)
```

주행 루프가 이미 `lookupMapToBase` 로 맵 자세를 조회하면서 yaw 를 `dummy_yaw` 로 버리고 있었다 —
그 값을 살려 쓰므로 **추가 조회 비용이 없다.**

**실기 검증 2건 (2026-08-10)**

```
(a) 정상 주행 · 임계 5°     status 0 · 거리 0.400 m · 최종 헤딩오차 +0.016°   ⇒ 오탐 0
(b) 임계 0.01° 로 강제      status −7 · 0.4 s · 이동 4 mm                     ⇒ 발화·코드 정상
    로그: |IMU기준 −94.97° − 맵 −95.01°| = 0.05° > 0.01° 가 10 cycle 연속
```

- **(b) 로그가 임계 근거를 실측으로 확인해 준다** — 정상 주행 중 실제 괴리가 **0.05°** 다.
  임계 5° 는 그 100배이고 고장 사례 25° 의 1/5 이라, 오탐·미탐 모두 성립하지 않는다.
- ⚠ **적용 범위는 `yaw_control` 뿐이다.** `yaw_control_reverse` 는 pose 토픽이 죽어 있어
  (`debt-050`) 탐지기가 성립하지 않는다. `turn`·`spin` 적용 여부는 별건.
- ⚠ **원인은 고치지 않았다** — IMU 가 왜 저속에서 못 읽는지(`debt-054` 기전)는 여전히 미확정이다.
  본 수정은 증상을 조기에 드러낼 뿐이다.

### [Trap] `yaw_control` 의 파라미터는 **전부 생성자 전용** — `ros2 param set` 이 거짓 성공한다

위 (b) 시험을 처음에 `ros2 param set yaw_control_heading_divergence_deg 0.01` 로 하려 했으나
**`Set parameter successful` 이 뜨고 거동은 그대로**였다(status 0 으로 0.4 m 완주).
`yaw_control` 에는 `add_on_set_parameters_callback` 이 **없어서** 멤버가 생성자에서만 채워진다.

- **내가 새로 만든 3개뿐 아니라 기존 파라미터 전부**가 이 상태다(`pose_topic`·`max_steer_deg`·
  watchdog 토글 등). `spin` 은 콜백이 있어(`spin_action_server.cpp:38`) 일부 키가 hot-reload 된다.
- 2026-08-09 `spin_params.yaml` 에서 제거한 「값만 담고 안 읽히는 손잡이」와 **같은 함정**이다.
  다만 여기는 값이 읽히긴 하고 **갱신만 안 되는** 형태다.
- 조치: `yaw_control_params.yaml` 머리에 **전 파라미터가 생성자 전용**임을 명시했다.
  콜백 신설은 별건(`debt-055` 등록).

### [Closed] `debt-054` 규명 — IMU 회전 추종은 **약 2.8 °/s 이상에서만 유효**

Seer 개루프(`19205/2010`)로 제자리 회전시키며 IMU 와 맵 측위를 동시 적산해 회전율의 함수로 측정했다.
액션서버(`spin`)를 쓰지 않은 이유는 Stage 1 하한(`min_speed_dps` 2.0, `spin_action_server.cpp:319`)이
**저속 구간을 원천적으로 만들 수 없기** 때문이다. 도구는 `Tools/imu_rate_check/`.

| 실측 회전율 | IMU/맵 비 | 표본 |
| --- | --- | --- |
| 0.280 °/s | 0.013 | n=1 |
| 0.564 °/s | 0.049 · 0.065 | n=2 (독립 2회 sweep 일치) |
| 1.130 °/s | 0.363 · 0.539 | n=2 |
| 2.84 °/s | 0.988 · 0.991 · 0.992 · 0.995 | n=4 |
| 5.69 °/s | 0.988 · 0.994 | n=2 |

- **약 2.8 °/s 이상에서 정확(≈0.99), 그 아래로 급락, 0.3 °/s 에서 사실상 실명(0.013).**
- 어젯밤 `spin` 대조(2.8 dps → 1.015, 10 dps → 0.991)와 정합하고,
  `yaw_control` 실패 건(0.6 °/s, 실제 24.7° 를 1.7° 로 판독)이 이 곡선 위에 정확히 놓인다.
- **1차 sweep 의 `2.823 °/s → 1.350` 은 이상치였다** — 같은 조건 4회 반복에서 전부 0.99.
  단일 표본으로 결론 내지 않은 것이 옳았다.

**운용 규칙 (실측 도출)**

```
ω ≥ 2.8 °/s   IMU 폐루프 신뢰 가능
ω ≲ 1  °/s    IMU 폐루프 금지 — 맵 측위 교차검증 또는 다른 수단
```

`turn` 은 `ω = v / R` 이므로 **큰 반경이 위험 구간**이다. `v = 0.05 m/s` 기준 `R = 1.0 m` 는
2.86 °/s 로 경계에 걸치고(오늘까지의 실기가 이 조합), `R ≳ 3 m` 면 1 °/s 아래로 떨어진다.

⚠ **원인(기전)은 여전히 미확정.** 「AHRS 바이어스 추정이 느린 정상회전을 흡수한다」가 유력하나
드라이버 설정(시상수·zero-rate update)을 확인하지 않았다. 본 항목이 답한 것은 **「어디까지 믿을 수
있나」이지 「왜 그런가」가 아니다.**

#### [계측 실패] 1차 sweep 은 앨리어싱으로 무효였다

끝점 두 샘플 차이에 `wrap()` 을 걸어 |Δ| > 180° 회전이 접혔다. `w=+0.200` 지령이
`−0.512 °/s`(실제 약 +345°)로 나온 것이 그 증거다. **매 샘플 delta 를 unwrap 해 누적**하도록
고쳐 재측정했다. 5점 중 2점(17°·34° 회전)만 앨리어싱이 없어 유효했고, 그 2점은 재측정 결과와
일치했다 — 우연히 결론이 같았을 뿐 **1차 자료 자체는 인용하지 말 것.**

### [Verify→부분 철회] `yaw_control` 첫 실기 — **조향 실행 미확인**이었다 (2026-08-10 01:2x 정정)

> ⚠ **아래 ①② 는 조향 작동을 증명하지 못한다.** 두 시험 모두 조향 지령이 각각 ~0° 와 1.6° 라
> 게이트(`steer_gate_threshold` 3°)를 실제 조향 이동 없이 통과했고, 그 시각 **조향축은 비응답
> 상태였다**(아래 [Fix] 참조). 즉 ②의 「오차 1.90→1.62°」는 조향이 만든 결과가 아니라
> 잡음·드리프트일 수 있다. **헤딩 제어 권한은 이 두 시험으로 검증되지 않았다.**
> 유효하게 남는 것은 ①의 「거리 정확도 0.501 m / 직진 유지」뿐이다.

`yaw_control` 은 이 기체에서 **한 번도 실기 검증된 적이 없었다**. 2건 수행(후방 여유 5.53 m 확보,
mcl2d 수렴을 `rviz2` 스캔-맵 대조로 선확인 — 오늘 22° 사고의 재발 방지 절차).

```
① 후진 0.5 m · 목표 yaw = 현재 헤딩(오차 0)      kp 1.0 · kd 0.1 · ki 0
   status 0 · 거리 0.501 m(1 mm) · 최종 헤딩오차 −0.006°
   주행 중 헤딩 최대 이탈 0.039° · 조향 지령 ±0.05° 이내
   헤딩 변화  측위 −0.021°  IMU +0.005°   (두 계통 0.03° 이내 일치)

② 전진 0.5 m · 목표 yaw −2.0°(초기 오차 +1.9°)   같은 게인
   status 0 · 거리 0.501 m · 오차 1.90° → 1.62° (수렴 미완)
   조향 = kp·오차 를 정확히 추종 (오차 1.704° 일 때 조향 1.694°)
```

- **②의 「수렴 미완」은 결함이 아니다.** `yaw_control` 의 종료 조건은 **거리**이지 헤딩 수렴이 아니다.
  코드에서 재확인했다 — 루프 탈출은 거리 한 곳뿐이고 헤딩 오차로 나가는 분기가 없다:

```cpp
if (prof_out.phase == ProfilePhase::DONE || current_distance >= goal->target_distance)
{ reached = true; break; }          // yaw_control_action_server.cpp:351
```

  `.action` 도 `target_distance # exit distance (m, > 0)` 로 명시한다. 즉 헤딩은 **추종 목표**일 뿐
  종료 판정에 들어가지 않는다. `turn`·`spin` 과 성격이 다르다 —
  그쪽은 각도가 목표이자 종료 조건이라 도달할 때까지 돌지만, `yaw_control` 은 못 맞춰도 거리를
  채우면 끝난다. 헤딩 권한은 주행거리에 비례한다:

```
dψ/ds = tan(δ)/L      δ 1.65° · L 1.2 m  ⇒  1.4°/m
1.9° 를 지우려면 이 게인에서 약 1.4 m 필요 — 0.5 m 로는 원리적으로 불가
```

  실측 헤딩 변화도 이와 부합한다. 즉 **거리와 게인을 함께 잡아야 목표 헤딩에 도달**한다.
- **다음 시험(사용자 지시 2026-08-10)**: 「후진 −10° → 원복 → 다시 −10° → 원복」 폐합 시험.
  ⚠ 착수 전 **필요 거리를 먼저 계산**할 것 — 현 게인 `kp 1.0` 의 초기 권한 1.4°/m 로는 10° 에
  약 7 m 가 필요하고 후방 여유는 5.53 m 다. `kp` 를 올리면 조향 상한(`max_steer_deg` 25°)까지
  δ 가 커져 거리가 줄지만, 그 조합은 미검증이므로 SIL 로 먼저 잡는다.
- **게인은 저장소 어디에도 기록이 없었다** — `.action` 의 `kp`/`kd`/`ki` 는 전부 호출자가 넘기는
  값이고 yaml·런치·문서에 예시가 0건이다. **`kp 1.0 · kd 0.1 · ki 0` 을 이 기체의 첫 동작 확인값으로
  남긴다**(최적값이 아니라 동작 확인값이다 — 튜닝하지 않았다). `ki` 는 사용자 상시 지시로 0.

### [Fix 필요] 조향축이 **비응답 상태**로 빠진다 — 지령은 CAN 직전까지 정상, 모터만 안 움직임

`yaw_control` 이 −20.2° 를 60초간 지령했는데 실제 조향은 0.00° 였다. 체인을 전 구간 추적했다:

```
액션 발행 /motion/wheel_cmd/yaw_control   −20.21° / 속도 0     정상
mux 출력  /motor/wheel_cmd                −20.21° / 속도 0     정상(통과)
translator /motor/low_cmd                 node3 target_pos 1,048,066 = 18.28°
                                          (지령 19.95° − 오프셋 1.676° 와 일치)  정상
실제      /wheel_motor_state              −0.00°               ← 여기서 끊긴다
```

- **조향축 자체의 문제다(액션 고유 아님).** 같은 시각 `turn` 으로 대조하니 +31.13/−30.80° 지령에
  실제 0.00° 로 똑같이 움직이지 않았다. 다만 **`turn` 은 Phase 0 타임아웃(5 s)에서 `status −3` 로
  정상 abort** 했다 — 즉 `turn` 의 보고는 제대로 동작했다.
  ⚠ 2026-08-10 정정: 이 대비를 근거로 「`turn` 도 보고가 없다」고 적었던 서술(`debt-052`)은 틀렸다.
  `turn`·`turn_reverse`·`spin` 셋 다 Phase 0 에서 abort 한다. 진단이 없는 것은 **`yaw_control`
  뿐**이며, 그쪽은 Phase 0 목표가 δ=0 이라 통과해 버리고 주 루프 가드가 조용히 구동을 막는다.
- **제어권 반납 → 재획득으로 즉시 회복**됐다(재획득 후 2초 만에 +31.13/−30.80° 도달).
- 오늘 초저녁 같은 `turn` 으로 ±31° 가 정상 동작했으므로, 그 사이 어느 시점에 비응답으로 빠졌다.
  engage/disengage 를 여러 번 반복한 구간이다. **`debt-046`(재시작이 축 상태를 지운다) ·
  타 세션 `4aea32d`(구동축 CiA402 운전 상태 복구 — 「지령·재송신만으로는 안 돈다」)와 같은 계열**로 보인다.
- ⚠ **가장 나쁜 점은 조용하다는 것이다.** 조향이 안 움직이는데 `/motor/low_cmd` 까지 정상값이
  흐르므로 상위에서 알 방법이 없다. `yaw_control` 은 60초를 기다려 `status −3`(타임아웃)만 냈고,
  `turn` 은 Phase 0 타임아웃 경고만 남기고 진행했다. **조향 도달 실패를 오류로 보고하는 경로가 없다.**

### [Fix 필요] `yaw_control` 이 시작 시 잡은 맵 기준을 **주행 중 재확인하지 않는다** — 25° 틀어진 채 `status 0`

조향축 회복 후 10° 시험(후진 2.0 m · `kp 2.0`)에서:

```
조향 −14° · 2.0 m 주행   기구학 예측 회전 ≈ 20°
맵 측위(mcl2d)  +24.7°     ← 예측과 부합. 로봇은 실제로 그만큼 돌았다
IMU             +1.7°      ← 회전을 거의 못 읽었다
액션 자기보고    +2.9°      (IMU 기반이라 같이 틀림)
결과            status 0 · 거리 2.001 m — **성공으로 보고**
```

- **기준 설정 자체는 정상이었다.** 코드는 `yaw_offset = start_yaw_map − start_yaw_imu` 를
  시작 시 1회 계산한다(`yaw_control_action_server.cpp:184`). 역산하면 시작 시 보정 yaw 는
  +2.00°, 같은 시각 맵 측위는 +2.094° — **0.09° 이내로 맞았다.**
  ⇒ 이것은 **기준(reference) 실패가 아니라 추종(tracking) 실패**다.
- ⚠ **정정(사용자, 2026-08-10): 「오프셋 1회 + IMU 추종」은 결함이 아니라 의도된 선택이다.**
  현재 측위는 **heading 정밀도를 보정해 줄 만큼 정확하지 않다.** 미세 제어를 측위 heading 으로
  닫으면 오히려 정밀도가 떨어진다. 그래서 **측위는 절대 기준을 1회 주고, 추종은 정밀한 IMU 가**
  하는 지금 구조가 맞다. 본 절이 종전에 이를 「설계 결함」으로 적은 것은 **틀렸다.**
- **실제로 빠진 것은 조대(粗大) 고장 탐지기다.** 제어 소스를 바꾸자는 것이 아니라,
  `|보정 yaw − 맵 yaw|` 가 **맵 잡음보다 훨씬 큰 임계**를 넘으면 전용 오류코드로 abort 하자는 것이다.
  25° 급 고장만 잡으면 되고 정밀도에는 관여하지 않는다. 이 탐지기가 있었다면
  2026-08-10 건은 **2초 안에 멈췄을 것**이고, `status 0` 로 성공을 반환하지 않았을 것이다.
- **`status 0` 으로 성공을 반환한 것이 가장 위험하다** — 상위 로직이 이 결과를 신뢰한다.
- ⚠ **IMU 가 왜 못 읽었는지는 미확정.** 회전율이 약 0.5 °/s 로 오늘 spin 대조(10 dps · 2.8 dps,
  둘 다 일치)보다 훨씬 느렸다. 「느린 정상회전을 AHRS 바이어스 추정이 흡수한다」가 유력하나
  spin 2.8 dps 가 멀쩡했던 것과 완전히 정합하지 않는다. **정지 상태 gyro_z 는 −0.004 °/s 로 정상**이고
  10초에 0.023° 밖에 안 움직이므로 **센서 고장은 아니다.** 결론 내지 않는다.
- **파급 범위 — 오늘 검증한 `turn`·`spin` 은 해당 없다.** 세 기동이 모두 IMU 로 루프를 닫는 것은
  맞지만, **관측된 실패는 저속 회전 구간에서만** 나왔다:

```
spin 10 dps    비 0.991     ✔        spin 2.8 dps   비 1.015   ✔
turn R=1.0 · v=0.05 → ω 2.86 °/s     ✔ n=8 · 왕복 폐합 확인
yaw_control 실패 건   ω ≈ 0.6 °/s    ✘   ← 조향 14° = 유효반경 4.8 m 이라 ω 가 낮았다
```

  ⇒ **위험 구간은 ω ≲ 1 °/s** 이며, `turn` 에서는 **큰 반경**(v=0.05 기준 R ≳ 3 m)이 여기에 든다.
  오늘 쓴 R=1.0 m 조합은 안전 구간이다. 큰 반경 `turn` 은 미검증이므로 그때 확인한다.

### [Trap] `yaw_control_reverse` 는 **존재하지 않는 토픽**을 구독한다 — 실행하면 pose 를 못 받는다

```
yaw_control          yaw_control_pose_topic:         "/robot_pose"                  발행자 1 (정상)
yaw_control_reverse  yaw_control_reverse_pose_topic: "/rtabmap/localization_pose"   발행자 0
```

`rtabmap` 은 이 스택에서 가동하지 않는다(측위는 `mcl2d` → `sil_pose_adapter` → `/robot_pose`).
따라서 `yaw_control_reverse` 를 그대로 띄우면 **측위 입력이 영영 오지 않아** localization watchdog
에 걸리거나 헤딩 제어가 성립하지 않는다.

**오늘 후진 시험은 `yaw_control` 에 `vx_max` 를 음수로 주어 수행했다** — `.action` 이
`vx_max # (!=0, +forward/-reverse)` 로 양방향을 명시하므로 별도 액션 없이 후진이 된다.
⇒ `yaw_control_reverse` 의 존재 의의와 pose 토픽 설정은 **재검토 대상**이다(부채 등록: `debt-050`).

### [Verify] `turn` 계열 오차 피드백 도입 후 실기 n=8 — 허용 규격 **|오차| ≤ 0.5°** 확정

계측은 **액션 자기보고**(달성각)다. `hold_steer=true` 시험에서 자기보고가 정지 순간 기준
IMU 와 +0.056° 로 일치함을 확인했으므로 유효하다.

| # | 액션 | 지령 | 자기보고 | 추종오차 |
| --- | --- | --- | --- | --- |
| 1 | `turn_reverse` | +10.000° | +9.572° | −0.428° |
| 2 | `turn` | −11.480° | −11.069° | −0.411° |
| 3 | `turn_reverse` | −90.000° | −89.615° | −0.385° |
| 4 | `turn` | +112.410° | +112.029° | −0.381° |
| 5 | `turn_reverse` | −111.554° | −111.116° | −0.438° |
| 6 | `turn` | +89.100° | +88.667° | −0.433° |
| 7 | `turn` | +10.000° | +9.576° | −0.424° |
| 8 | `turn_reverse` | −10.000° | −9.581° | −0.419° |

```
평균 −0.415°   범위 −0.381 ~ −0.438°   폭 0.057°   전부 부족 방향
10° 와 112° 가 같은 값 — **오차가 기동 크기와 무관하다**(종단 제어의 서명)
```

- **허용 규격 `|오차| ≤ 0.5°` (사용자 승인 2026-08-10)** — 실기 8/8 · SIL 4/4 통과.
- ⚠ **성능 근거는 SIL 이 정본이다.** 위 실기 표는 제어기가 **자기 센서로 잰 값**이라 그 자체로는
  성능 증명이 아니다(오차 피드백 제어기는 자기가 잰 오차가 작아지면 멈추므로 작게 나오는 것이
  당연하다 — 순환 논증). **플랜트 참값과 대조되는 SIL** 에서 −0.262~−0.264° · 자기보고와
  참값 괴리 −0.001° 가 나온 것이 성능 근거이고, 위 표는 **그 거동이 실기에서 같은 크기·같은
  부호로 재현된다는 확인**이다.
- ⚠ **변경 전후 수치를 직접 비교하지 말 것.** 변경 전 n=6 은 mcl2d(독립 센서), 변경 후 n=8 은
  자기보고로 **계측 방식이 다르다.** 같은 잣대의 A/B 는 SIL 에서만 가능하며 수행하지 않았다.
- ⚠ 오차는 일관된 **부족 방향 상수 편향**이다. `ki` 를 두지 않으므로 남는다. 줄이는 손잡이는
  `fine_correction_threshold_deg` 이며 SIL 에서 0.3 → 0.05 로 조이면 −0.264 → −0.041°(소요 +8%).
  단 SIL 은 IMU 잡음 0 이라 실기 적용 전 재측정이 필요하다.

### [Diag] 정지 후 「되돌아감」은 기구 되풀림이 아니라 **IMU(AHRS) 기동 후 완화** — 이중센서로 확정

- **배경**: `turn` 계열 실기에서 액션 자기보고와 외부 IMU 측정이 매번 0.5° 어긋났다. 원인 후보로
  ① 누적기 편향(→ 구조 변경으로 제거) ② Phase 4 조향 복귀 스크럽 ③ 기구 되풀림 을 놓고 갈랐다.
- **①·② 배제**: `hold_steer = true` 로 **Phase 4 를 건너뛰고** 재측정했다.

```
지령 +10°  hold_steer=true       자기보고 +9.576°
  결과 직후  IMU +9.520°   괴리 +0.056°   ← 액션 보고는 정지 순간 기준으로 **정확하다**
  +1 s       IMU +9.321°   (0.20° 되돌아감)
  +3 s       IMU +9.006°   (0.51° 되돌아감)   ← 조향은 31° 유지 중, Phase 4 없음
```

  ⇒ 조향 스크럽이 아니다. 그리고 **자기보고 결함도 아니다** — 정지 순간에는 0.056° 로 맞는다.
- **③ 판별 — 맵 기준 mcl2d 를 동시에 읽었다**(지령 −10°, `hold_steer = true`):

```
 t[s]    IMU Δ      mcl2d Δ     차이
  0.0   −9.580     −11.338     +1.758
  4.0   −8.980     −11.430     +2.450
  8.0   −8.772     −11.392     +2.620
```

  **mcl2d 는 정지 후 8초간 ±0.05° 안에서 평평**하고 IMU 만 0.82° 기어간다.
  ⇒ **차체는 움직이지 않는다. 움직이는 것은 IMU 의 자세추정값이다.**
  기구 되풀림 가설도 기각. `AHRS(Attitude and Heading Reference System)` 의 기동 후 완화다.
- **정지 상태 대조**(움직이지 않고 30초): IMU −0.036° · mcl2d −0.036° — **정상 드리프트는 ~4°/hr 로 작다.**
  즉 위 0.8° 는 정상 드리프트가 아니라 **기동 직후 과도현상**이며, 수 초 안에 잦아든다.
- **실무 함의**: 기동 직후 수 초 안에 IMU 로 최종 자세를 재면 **최대 0.8° 틀린다.**
  액션 자체는 정지 순간에 판정하므로 영향이 없지만, **외부 계측 스크립트가 「정착 대기」로 3초를
  기다리면 오히려 틀린 값을 잡는다** — 오늘 제 계측이 그랬다.

### [Retract] 「Phase 4 조향 복귀가 원인」·「기구 되풀림」 — 둘 다 철회

같은 세션에서 제가 순서대로 주장했고 둘 다 위 실측으로 기각됐다. 또한 **Phase 4 를 수행한 것은
설계 요구가 아니라 제 시험 스크립트의 선택**이었다(`hold_steer=False`, `exit_steer_angle=0.0` 을
앞선 스크립트에서 그대로 복사). 연속 계측에서 매 다리마다 조향을 0 으로 되돌릴 이유는 없다 —
의미 있는 시점은 **Seer 에 제어권을 넘기기 직전**뿐이다.

### [Closed] **IMU 회전량이 맵 기준의 0.80 배** 가설 — 실험으로 기각. 원인은 **미수렴 mcl2d 를 지령으로 쓴 것**

`turn` 실기에서 IMU 와 mcl2d 가 계통적으로 어긋나 「IMU 가 참값의 0.80 만 읽는다」를 의심했다.
**제자리 `spin` 대조로 기각됐다** — 병진을 없애고 회전만 남기면 둘이 맞는다.

```
                      회전율      병진      IMU/mcl2d 비
turn (당시)           ~2.8 dps   1.7 m     0.79 ~ 0.85
spin  90° 빠름          10 dps    20 mm     0.991
spin −90° 느림         2.8 dps    33 mm     1.015      ← 회전율 가설도 함께 기각
```

- 회전율을 `turn` 과 같은 2.8 dps 로 낮춘 대조군에서도 **1.015** 다. 따라서
  **IMU 스케일 오차도, 느린 회전율의 바이어스 흡수도 아니다.** 둘 다 기각.
- **참 원인**: `turn` 시험 당시 **mcl2d 가 수렴 상태가 아니었다.** 세션 중 노드를 죽였다 살린 뒤
  `/initialpose` 재시딩을 하지 않았고, 그 상태의 값을 그대로 읽었다. spin 시험은 mcl2d 가
  재수렴한 뒤였기에 일치한다.
- **피해**: 그 미수렴 값(+112.41°)을 **되짚기 지령으로 그대로 보내** 로봇이 필요량보다 22° 더 돌았다.
  `turn` 자체는 정상이었다 — 자기보고와 IMU 가 0.5° 안에서 맞았고, 그 0.5° 도 외부 계측이 3초를
  기다려 잡은 **AHRS 완화분**이다(위 [Diag] 참조).
- ⚠ **Seer 는 이 판정에 쓰지 않았다.** `spin` 90° 전후로 `(−12.6823, +9.6128, −6.073°, conf 0.631)`
  **동일 값**을 반환했다 — 90° 돌았는데 변화 0, 즉 **동결**이다. 같은 세션에서 내가
  「Seer 와 mcl2d 가 0.13° 이내 일치」라고 적은 것도 이 정지된 값이었으므로 **근거로 쓰면 안 된다.**
  제어권 반납 후에도 Seer 가 자동 재측위하지 않는다는 것 자체가 별건의 관찰 대상이다.
- **재발 방지**: 측위값을 **지령으로 바꾸기 전에** 그 측위의 수렴을 확인한다. 노드 재기동 후에는
  `/initialpose` 재시딩과 맵 정합 확인이 선행 조건이다(`rviz2` 스캔-맵 대조 1회면 충분하다).

---

## 2026-08-09

### [Fix] 구동 지령을 넣어도 바퀴가 안 돎 — 구동축이 운전 가능 상태가 아니었다

- **문제**: 조그를 눌러도 구동륜이 돌지 않았다. 로그는 정상으로 보였고
  (`조향 정착 — 구동 raw=-1222`) **구동 재송신도 돌고 있었다.** 그런데 `0x60FF=-1222` 를
  3 초 넣는 동안 두 구동축 엔코더가 **1 count 도 안 움직였다** — node1 `-516,397` 고정 /
  node2 `222,376` 고정.
- **원인**: 지령이 아니라 **드라이브 상태**.
  - 양 구동축 **`operation enabled`(상태워드 bit2) = 0**, node1 은
    **`0x603F = 0x0080` Motor overload alarm**(Handbook §6.6.4 p.7614)
  - Seer 알람 `Motor Error:FrontWalk-0x80` 이 독립 경로로 동일 확인
  - GUI 를 거치지 않은 맨 스크립트도 동일 → UI 배제. 드라이브가 **자기 상태워드로**
    보고 → 판다 펌웨어 배제.
  - **재송신은 이 상황을 못 고친다** — 지령을 반복할 뿐 꺼진 축을 켜지 못한다.
    `Tools/amr_test_gui/gui.py` `MainWindow._drive` 는 `0x60FF` 만 보내고 조향
    (`_steer_axis`)처럼 `0x6040` 을 동반하지 않아, Seer 가 켜 둔 상태를 물려받아
    동작해 왔을 뿐이다.
  - **제어권을 Seer 에 반환했다 되찾으면 node1 이 `Switch On Disabled` 로 떨어진다**
    (node2 는 유지, fault 없음). 잡는 쪽이 상태를 갖추지 않으면 조향만 되고 구동이 취소된다.
- **해결**: CiA402 상태 복구 경로 신설(Handbook §6.6.1 Controlword 명령표 근거).
  - `_drives_ready()` · `_drive_faults()` — 상태워드 bit2/bit3 판정
  - `_enable_drives()` — Fault Reset(bit7 **상승엣지**) → **fault 가 걷힐 때까지 대기**
    → Shutdown `0x06` → Switch On `0x07` → Enable Operation `0x0F`
  - `_ensure_drives_enabled()` — **제어권 획득 직후** 점검·복구. 단 **fault 가 있으면
    자동으로 켜지 않고** 사유를 남긴다(원인 모른 채 재기동 금지)
  - `_jog_run` 이 구동 직전 운전가능을 확인하고, 아니면 **사유를 남기고 취소**한다
    (전에는 지령만 나가고 조용히 실패해 원인을 가렸다)
  - `⚡ 구동축 활성화 (FAULT 해제)` 버튼 + 과부하 재발 경고 확인 대화상자
  - ⚠ **대기 단계는 실기가 가르쳐 준 것** — 리셋 직후 50 ms 간격으로 전이를 몰아 보냈더니
    node1 이 fault 만 걷히고 `Switch On Disabled`(`0x8050`)에 멈췄다.
- **파일**: `Tools/amr_test_gui/gui.py` ·
  `Tools/amr_test_gui/test/test_drive_enable.py`(신규 11건)
- **상태**: 완료 — 실기 복구·주행 확인
  - 상태 복구: n1 `0x8018`→`0x8037` · n2 `0x8050`→`0x8037` (양축 enabled=1 · fault=0)
  - 제어권 획득 시 자동 복구: `n1 0x8050`→`0x8037`
  - 주행: 전진 `raw=-1222` 19 초 · 후진 `raw=+1222` · 크랩 정상(사용자 확인)
  - 시험: 기준선 `6 failed / 125 passed` → `6 failed / 136 passed`(**기존 실패 6건 불변**,
    신규 11건 추가). 기존 6건은 본 변경과 무관한 선재 실패다.
  - ⚠ `mutation_check.py` 는 12개 전부 「검출」로 나오지만 **그 판정은 근거가 되지 못한다** —
    검출 근거로 지목된 시험이 선재 실패 3건뿐이라 어떤 변조에도 같은 결과가 나온다(**debt-046**).
- **출처**: 별도 세션 브랜치 `origin/session/56a709a5-tools`(@`9100ebe`)에서 검증한 뒤
  본 구조(단일 `gui.py`)에 맞춰 이식. 그 브랜치의 3계층 분할은 채택하지 않았다.
- **미해결**: 과부하(`0x0080`)의 물리적 원인 미규명 — **debt-045**.

### [Verify] `turn`·`turn_reverse` 90° 실기 검증 — 왕복 폐합 14 mm / +0.64°

- **배경**: `turn_reverse` 는 ADR `docs/adr/2026-08-09-turn-reverse.md` 로 신설했고 SIL 과
  ±10° 실기까지만 확인돼 있었다. 검증 계획 §3(「후방 2 m 여유 안에서 작은 호」)을 넘어
  **90° 큰 호**를 후진→전진 복귀 왕복으로 수행했다(사용자 지시: 「후진만 가능함」·「후진후 전진복귀로」).
- **조건**: `R = 1.0 m` · `max_linear_speed = 0.05 m/s` · `accel_angle = 5.0°` ·
  `hold_steer = false`. 현(chord) 1.41 m 로 후방 여유 2 m 안에 든다.
  측위는 mcl2d(`/mcl_pose`, 맵 정합 0.0103 m 수렴)와 Seer(19204 / 1004) 두 계통을 함께 읽었다.

```
① 후진 90°   목표 −90.00°   mcl2d −90.53°   IMU(외부) −89.63°   액션 자기보고 −90.22°
             변위 1445 mm   차체기준 +135.9° (이론 +135°, 후방-좌측)   반경추정 1.017 m   35.9 s
② 전진 복귀  목표 +90.53°   mcl2d +91.19°                          액션 자기보고 +90.69°
             변위 1432 mm   차체기준  +45.6° (전방-좌측)            반경추정 1.003 m   35.9 s

왕복 폐합    기준 (−12.5592, +9.6217) yaw −2.54°
             mcl2d (−12.5725, +9.6175) yaw −1.90°  ⇒ 14 mm · +0.64°
             Seer  (−12.5735, +9.6210) yaw −2.08°  ⇒ 14 mm · +0.46°
             두 독립 측위계가 1.0 / 3.5 mm · 0.18° 로 일치 — 폐합값은 한 계통의 착시가 아니다.
```

- **기구학 대조(합격)**: 조향은 전 구간 `F = +31.13° / R = −30.80°` 로 고정됐다.
  이는 `atan(w1_x/R) = atan(0.6039/1.0) = 31.13°` · `atan(0.5961/1.0) = 30.80°` 과 **정확히 일치** —
  IK 가 대칭 근사가 아니라 실측 비대칭 기하를 쓰고 있음이 확인된다.
  구동 엔코더도 맞는다. 바퀴는 중심에서 x 로 ±0.60 m 떨어져 있어 **중심보다 큰 반경**을 쓴다:

```
휠→ICR 거리  전 √(0.6039²+1.0²) = 1.1682 m → 호 1.835 m   실측 1.8458 m  (+0.6 %)
             후 √(0.5961²+1.0²) = 1.1642 m → 호 1.829 m   실측 1.8345 m  (+0.3 %)
```

  ⚠ 계측 스크립트가 「이론 호 1.571 m」로 출력했으나 그것은 **차체 중심**의 호다(휠 호 아님).
  표기만 틀렸고 거동은 위와 같이 0.6 % 이내로 정확했다.

- **조향각은 목표각이 아니라 반경이 정한다**: 90° 든 10° 든 `R = 1.0 m` 면 같은 ±31° 다.
  본 세션에서 「90° 는 조향이 클램프(±115°)에 근접한다」고 말한 적이 있으나 **틀린 서술**이며
  여기서 철회한다. 클램프가 문제되는 것은 큰 각이 아니라 **작은 반경**이다.
- **미결로 남기는 것**: `turn` 계열의 **허용 규격이 없다**(`spin` 은 사용자 승인 ≤ 0.40°).
  규격은 사용자가 정한다 — 여기서는 자료만 남긴다. 전수는 아래 표.

#### `turn` 계열 각도 오차 전수 (2026-08-09 실기, n = 6 다리)

부호 규약을 하나로 고정한다 — **과회전량 = |실측| − |지령|** (+ 는 더 돎, − 는 덜 돎).
왕복의 두 번째 다리는 첫 다리의 **실측값**을 지령으로 되짚었으므로 지령이 정수가 아니다.

| # | 액션 | 지령 | 실측 | 과회전량 | 상대 | 왕복 폐합 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `turn_reverse` | +10.00° | +10.38° | **+0.38°** | +3.8 % | ① 5 mm · +0.15° |
| 2 | `turn` | −10.38° | −10.19° | **−0.19°** | −1.8 % | ↑ |
| 3 | `turn_reverse` | −10.00° | −10.01° | **+0.01°** | +0.1 % | ② 6 mm · −0.38° |
| 4 | `turn` | +10.01° | +9.66° | **−0.35°** | −3.5 % | ↑ |
| 5 | `turn_reverse` | −90.00° | −90.53° | **+0.53°** | +0.59 % | ③ 14 mm · +0.64° |
| 6 | `turn` | +90.53° | +91.19° | **+0.66°** | +0.73 % | ↑ |

```
|과회전량|  최소 0.01°  최대 0.66°  ·  부호 3 과 / 2 부족 / 1 무시가능
10° 다리(n=4)  |오차| 0.01 ~ 0.38°   상대 0.1 ~ 3.8 %
90° 다리(n=2)  |오차| 0.53 ~ 0.66°   상대 0.59 ~ 0.73 %
⇒ 절대오차는 각이 클수록 크고, 상대오차는 각이 작을수록 크다.
```

- **규격 결정에 직접 걸리는 사실**: `spin` 의 ≤ 0.40° 를 그대로 가져오면 **6개 중 2개(90° 다리
  둘 다)가 탈락**한다. 반대로 n = 6 을 전부 통과시키려면 ≤ 0.70° 가 필요한데, 그것은
  표본에 맞춰 사후에 그은 선이라 근거가 약하다.
- ⚠ **먼저 정할 것이 규격이 아닐 수 있다.** `turn` 은 오차 피드백이 없는 구조라(아래 [Diag])
  지금 규격을 박으면 **누적기의 편향을 규격으로 승인**하는 셈이 된다. `debt-048` 상환 후
  재측정하고 규격을 정하는 순서를 권한다 — 판단은 사용자 몫이다.
- ⚠ **표본의 한계**: 반경은 전부 `R = 1.0 m` 한 점, 속도는 0.05 m/s(90°·①)와 0.10 m/s(②) 두 점뿐이다.
  측정계도 다리마다 다르다 — 1·2·5·6 은 측위 기준(5·6 은 mcl2d + Seer 이중), 3·4 는 별도 계측
  스크립트 출력이다. **분포를 주장할 수 있는 자료가 아니다.**
- ⚠ 2026-08-09 정정: 본 항목을 처음 적을 때 **「n = 4, ±10° 에서 −0.19 ~ +0.38°」로 보고했으나
  틀렸다.** ① 표본은 6개이고 ②·③번 왕복의 두 다리(#3 +0.01° · #4 −0.35°)가 누락됐으며,
  ② 「±10° −0.19 ~ +0.38」과 「90° −0.53」이 **서로 다른 부호 규약**으로 섞여 있었다
  (앞은 |실측|−|지령|, 뒤는 실측−지령). 위 표는 규약을 하나로 통일해 다시 세운 것이다.
- ⚠ 최종 verdict 는 저자가 찍지 않는다(`coding.md:88` never-self-approve).

### [Diag→기각] `turn` 자기보고가 지도 기준보다 작다 — 0 클램프 래칫 의심 **(2026-08-10 기각)**

> ⚠ **본 절의 「의심 기전」은 틀렸다.** 원인은 누적기가 아니라 ① AHRS 기동 후 완화(외부 계측이
> 3초 기다려 잡음) ② 당시 mcl2d 미수렴이었다. 정지 순간 기준으로는 자기보고와 IMU 가 +0.056° 로
> 맞는다. 아래 서술은 **판단 이력으로 보존**하며 현재 사실로 인용하지 말 것.
> 정정 전말: 2026-08-10 `[Closed]` 절.

- **관측**: 위 90° 왕복에서 같은 회전을 세 계통이 다르게 읽었고, **두 다리 모두 같은 순서**였다.

```
             액션 자기보고   외부 IMU 델타   mcl2d(맵 절대)
후진 90°       −90.22°        −89.63°         −90.53°
전진 복귀      +90.69°        (+90.1 부근)     +91.19°
        ⇒ |mcl2d| > |자기보고| > |외부 IMU|   (방향 무관하게 동일 순서)
```

  즉 **실제로는 지령보다 약 0.6 % 더 돌았는데 액션은 덜 돈 것으로 보고**한다.
  절대 기준(mcl2d·Seer)이 서로 일치하므로 초과 회전 쪽이 참이다.
- ⚠ **이것은 overshoot(오버슈트)가 아니다 — 용어를 구분한다.** 오버슈트는 과도응답이 목표를
  넘었다가 **되돌아오는** 것인데, 여기엔 되돌아온 구간이 없다(후진 다리 `t = 33.3 s` −88.15° →
  종료 −89.63° 로 단조, 이어진 미세보정도 같은 방향으로만 더했다). 정확히는 **과회전
  (over-rotation) = 종료 시점의 최종 오차**다. 구분이 중요한 이유는 처방이 갈리기 때문이다:

```
진짜 overshoot 이라면   원인 감속 프로파일·게인   처방 accel_angle · 감속률
지금의 과회전이라면     원인 종료 판정(누적기)    처방 절대 목표 yaw 로 교체 (debt-048)
```

  액션은 **자기 카운터가 목표를 찍는 순간** 멈췄다. 그 카운터가 실제보다 덜 세고 있었으니
  감속이 과했던 것이 아니라 **정지 신호가 늦은 것**이다. `debt-048` 의 처방은 후자에만 듣는다.
- **의심 기전(미확정)**: `turn` 은 IMU 델타를 누적하는데, 그 누적기에 **0 클램프**가 있다 —
  `turn_action_server.cpp:259-260 · 314-315 · 387-388`(`turn_reverse` 는 `:262 · :317 · :393`).
  음의 델타가 누적을 0 아래로 끌면 **0 으로 잘라 버리므로** 그 음수는 영구히 사라진다.
  이는 **한 방향으로만**(과대계상) 편향될 수 있어 관측 방향과 부합한다. 다만 관측은 n = 2 이고
  래칫이 실제로 발화했는지 로그로 확인하지 않았다 — **기전 확정 아님**.
- **구조적 원인 — `turn` 에는 오차 피드백이 없다** (사용자 지적, 2026-08-09):

```cpp
auto prof_out = profile.getSpeed(accumulated_angle);   // turn_action_server.cpp:204
double omega_dps = prof_out.speed;                     // ← 지령 생성 끝. 오차항 없음.
```

  각속도 지령은 **누적각의 함수(사다리꼴 표 조회)** 일 뿐이며 「목표 대비 얼마나 벗어났나」를
  보고 고치는 항이 **어디에도 없다**. IMU 는 지령 생성에 관여하지 않고 오직 `accumulated_angle`
  (진행량)에만 들어간다. 즉 **피드포워드 프로파일을 측정 진행량으로 인덱싱**하는 구조이고,
  닫혀 있는 것은 **「언제 멈출까」 하나뿐**이다.

```
spin   e = target_yaw − cur_yaw  →  PID  →  ω      진짜 오차 피드백
turn   s = 누적각                →  표 조회 →  ω      오차항 없음 (진행량 스케줄링)
```

  ⇒ **누적기가 틀리면 틀린 만큼 그대로 더 간다 — 잡아 줄 두 번째 기구가 없다.**
  Phase 3.5 미세보정도 `angle_error = target_abs − accumulated_angle` 로 **같은 누적기**를
  보므로 누적기 자신의 편향은 **원리적으로** 못 잡는다. 2026-08-09 의 `spin` 정착 게이트
  문제와 성질이 다르다 — 그쪽은 게이트가 느슨했던 것이고, 이쪽은 **고칠 경로가 없는 것**이다.
  반경(경로)은 더해서, cross-track 피드백이 아예 없어 **완전 개루프**다. 왕복이 14 mm 로
  닫힌 것은 기구학·엔코더가 정확해서지 제어가 잡아 준 것이 아니다.
- **이미 알려진 더 나은 방식**: `spin` 은 델타 누적을 쓰지 않는다. 시작 시 **절대 목표 yaw**
  (`spin_action_server.cpp:263 target_imu_yaw`)를 잡고 `normalizeAngle(target − cur)` 로 재
  드리프트·편향이 원천 소거된다. `turn` 소스의 주석(`:253-256`)이 이미 이 방식을 권하면서
  「별건(구조 변경)」으로 미뤄 두었다.
- **영향 판정**: 왕복 폐합 14 mm / 0.64° 는 양호하고 오차는 어떤 합리적 규격 안에도 든다.
  **기동 자체의 결함이 아니라 자기보고 정확도 문제**이므로 본 검증의 차단 사유로 보지 않는다.
  → `debt-048` 로 등록.

### [Fix] 채널 0 탈취 **3번째** 재발 — 가드가 「우리가 뺏는 것」만 막고 「이미 뺏긴 상태」는 못 봤다

- **문제**: 병합 직후 상태 점검에서 활성 구성의 채널 0 이 또 `192.168.192.10`(젯슨)을 가리켰다.
  Seer 빔 프레임 갱신 **0/3**(정지), 알람 `52102 localization module cannot get laser data` ·
  `52103 timeout receive laser data …` — **발생 시각 2026-08-08 20:37**, 즉 전날 저녁부터
  오전까지 Seer 가 계속 굶고 있었다.
- **원인**: 두 겹이다. ① 그 시각에 **아직 병합 전이던 옛 코드**(channel 0)로 누군가 스택을 띄웠다.
  ② 그리고 **가드가 그 상태를 통과시켰다** — `assert_channel_free` 는 *우리가 쓸 채널(1)* 만
  검사하므로, 남의 채널 0 이 이미 이탈해 있어도 아무 말 없이 지나간다. 가드는 **사고를 일으키는
  것은 막지만 이미 난 사고는 보이지 않게** 설계돼 있었다.
- **해결**:
  1. 즉시 복구 — `set_output_channel.py` 로 채널 0 을 `192.168.192.5:6060/6061` 로 원복.
     실측: 복구 후 Seer 빔 갱신 **4/4**. 실행 중이던 타 세션 스택(채널 1 수신)은 무중단.
  2. 가드에 **`warn_foreign_drift()` 추가** — 저장(177)과 활성(178)을 모두 읽어, **우리 것이 아닌**
     채널의 목적지가 저장값에서 이탈했으면 경고하고 **복구 명령을 그대로 출력**한다.
     막지는 않는다: 우리 잘못이 아니고 기동을 막아도 복구되지 않는다.
- **파일**: `src/Sensors/Lidar/2D/sick_safetyscanners2/launch/channel_guard.py` ·
  `.../sick_safetyscanners2_launch.py`
- **상태**: 완료 — 논리 검증 4/4 PASS(이탈 검출 · 정상 시 무경고 · **우리 채널은 이탈로 세지 않음** ·
  조회 실패 시 통과), 실기 확인 이탈 0건. Seer 빔 갱신 4/4 회복.
- **교훈**: 방지책의 **검사 대상 범위**를 사고 시나리오와 대조하지 않았다. "우리가 남의 것을 뺏는다"
  하나만 상정했고, "남이 뺏어 둔 채로 우리가 올라온다"는 시나리오가 빠졌다. 실제 3번째 사고는
  후자였다. 이 저장소 `docs/claude-mistake/INDEX.md` §메타 패턴의 "**검증했는데 대상이 틀린 것**"과
  같은 계열이다.


### [Fix] 죽은 파라미터 4개를 **주석이 아니라 코드에서** 제거 — set 이 성공을 반환하던 함정

- **문제**: `fine_correction_timeout_sec` 는 값을 읽어 담기만 하고 **읽는 코드가 없는데**
  hot-reload 화이트리스트에는 들어 있었다. 결과적으로 세 겹의 거짓 긍정 신호를 줬다 —
  `ros2 param set` 이 **성공 반환**, `param get` 이 **바뀐 값 반환**, 범위 검사(0.5~30) 통과.
  튜닝하는 사람은 적용됐다고 믿는데 **거동은 하나도 바뀌지 않는다.** 실제 fine timeout 은
  기동 규모에 비례해 코드가 계산한다(`max(2.0, 3.0 × target_abs / max_ω)`).
  같은 성격의 죽은 손잡이가 `fine_correction_speed_dps` · `settling_delay_ms` ·
  `yaw_control_pose_qos` 에도 있었다(모두 코드 참조 0건).
- **원인**: 고정 타이머를 적응 계산으로 바꾸면서(`:351-352` 주석에 경위 기록)
  **파라미터·헤더 멤버·화이트리스트 항목을 함께 정리하지 않았다.** 기능은 사라지고 껍데기만 남았다.
- **해결**: 처음에는 주석으로 함정을 **설명만** 했으나, 그것은 「읽는 사람이 주석을 본다」는
  전제에 기대는 것이라 **손잡이 자체를 제거**했다 —
  헤더 멤버 3개 · `safeParam` 선언 3개 · 화이트리스트 분기 1개 · yaml 키 4개.
- **파일**: `src/Control/Motion_Control/2WS/trnav_2ws_action_server/`
  `include/trnav_2ws_action_server/spin/spin_action_server.hpp` ·
  `src/spin/spin_action_server.cpp` · `config/spin_params.yaml` · `config/yaw_control_params.yaml`
- **상태**: 완료 — 재기동 후 실증:

  ```
  제거 전  set fine_correction_timeout_sec 10.0 → "Set parameter successful"   (거동 변화 0)
  제거 후  같은 명령                            → "cannot be set because it was not declared"
  살아있는 것  settle_rate_dps 판독 0.5 정상 · kp_spin set 정상 · 액션 정상 기동
  ```

### [Fix] spin 정착 판정이 느슨해 액션 자기보고와 실제 자세가 어긋났다 — `settle_rate_dps` 2.0 → 0.5

- **문제**: 실기 spin 이 끝난 뒤 **밖에서 잰 값이 액션 자기보고보다 나빴다.**
  자기보고 +0.22° 인데 정지 2초 후 IMU 실측은 +0.43°(괴리 0.21°). 즉 액션이 「도달했다」고
  판단한 시점 이후에도 차체가 계속 움직였다.
- **원인**: 조기종료 게이트(`spin_action_server.cpp:405-407`)의 회전율 조건
  `settle_rate_dps = 2.0` 이 느슨했다. 실제 종료 로그가 `|rate|=0.35~0.50 dps` 에서
  **「settled」로 판정**했다 — 아직 돌고 있는데 정착으로 본 것이다. 그 잔여 회전과 3톤 차체의
  되말림이 정지 후 0.2° 를 더 만들었다.
  ⚠ `ki_spin = 0.0` 이라 이 정상오차를 흡수할 적분항이 없다. 코드 주석(`:424-427`)이
  「fine 은 floor 없이 0 으로 자연 정착, 정지마찰 잔류는 ki 가 흡수」라고 설계를 밝히는데,
  **사용자 지시로 `ki` 는 사용 금지**(진동 위험)이므로 그 경로는 쓸 수 없다.
- **해결**: 게인은 **손대지 않고**(진동 위험 회피) 종료 조건만 조였다 —
  `config/spin_params.yaml` 의 `settle_rate_dps: 2.0 → 0.5`.
  같은 파일의 잘못된 주석도 정정했다(아래 별항).
- **파일**: `src/Control/Motion_Control/2WS/trnav_2ws_action_server/config/spin_params.yaml`
- **상태**: 완료 — ±20°, 정지 2초 후 IMU 외부 측정, n=6:

  ```
  0.26 · 0.25 · 0.24 · 0.22 · 0.26 · 0.40      |평균| 0.27°   최대 0.40°
  자기보고 ↔ 실측 괴리  0.21° → 0.01~0.04° (소멸)
  ```

  **허용 규격 ≤ 0.40°(사용자 승인 2026-08-09) 기준 6/6 통과.**
  ⚠ 앞 5회가 0.22~0.26° 로 촘촘한데 6번째만 0.40° 로 튀었고 **원인 미규명**이다.
  표본 6개뿐이므로 분포를 주장하지 않는다. 오차는 **일관되게 부족 방향**이다.

### [Fix] `spin_params.yaml` 이 실제로 쓰이는 파라미터를 「미사용」이라 적어 두었다

- **문제**: `settle_rate_dps`·`settle_count` 가 「하이브리드 전환으로 미사용; yaml 호환 위해 유지」
  주석 블록에 묶여 있었다. 이 주석을 믿으면 **위 튜닝 지렛대를 아예 찾지 못한다.**
- **원인**: 과거 리팩터 시점의 주석이 갱신되지 않고 남았다. 실제 참조를 세면 —

  ```
  settle_rate_dps            3회 참조   spin_action_server.cpp:405   ← 사용
  settle_count               3회 참조   :407                          ← 사용
  fine_correction_speed_dps  1회(선언만)                              ← 진짜 미사용
  settling_delay_ms          1회(선언만)                              ← 진짜 미사용
  ```

  값을 2.0 → 0.5 로 바꾸자 거동이 실제로 달라진 것이 사용 증거다.
- **해결**: 주석을 실제 사용 여부대로 두 블록으로 분리하고, 종료 조건식과 실측 근거를 함께 적었다.
- **파일**: `src/Control/Motion_Control/2WS/trnav_2ws_action_server/config/spin_params.yaml`
- **상태**: 완료 — 인자 없이 재기동해 yaml 값(0.5)이 노드에 반영되는 것을 확인.

### [Verify] spin 실기 검증 완료 — 어제 「재검증 필요」 항목 종결

- **문제**: 2026-08-08 의 유일한 실기 spin 은 전륜 구동이 죽은 상태에서 수행돼(중심 이탈 550 mm)
  정상 상태의 기록이 없었다.
- **확인**: 구동축 브링업 수정(`a7420a6`) 적용 상태에서 재실행 —

  ```
  IMU 실측 회전  −19.76°  (목표 −20.00°, 오차 +0.24°)
  구동 2축       node1 −0.2115 m · node2 −0.2084 m   차이 3.1 mm
  이론 호 길이   0.2083 / 0.2056 m (회전 19.76° × 반경 0.6039 / 0.5961)
  조향 자세      Phase 0 이 F=−90.00° / R=+90.00° 로 정렬(182° 스윙, 4.1 s)
  ```

  구동 2축이 대칭이고 실측 호 길이가 이론값과 3 mm 이내로 맞으므로 **차체 중심 회전**이 확인된다.
- **상태**: 완료 — 어제 기록의 「spin 재검증 필요」를 닫는다.

## 2026-08-08

### [Fix] 2WS 액션의 기하 기본값이 QD 대각 잔재 — params 파일이 빠지면 spin 이 조용히 −67.75° 로 돈다

- **문제**: `sil_spin.launch.py` 없이 `ros2 run amr_spin_node` 로 띄우고 spin 을 걸었더니 조향이
  ±90° 가 아니라 **F=−67.75° / R=−67.75°(양 축 같은 부호)** 로 섰고, 제자리 회전이어야 할 기동이
  **187 mm 병진**했다(SIL). 회전각 자체는 −44.72°(목표 −45°)로 맞아 **각도만 보면 정상으로 보인다.**
- **원인**: `trnav_2ws_motion` 이 QD 에서 갈라져 나올 때 **기하 기본값만 안 고쳐졌다.**
  `qd_action_server_base.hpp` 의 `get_d("w1_y", 0.135)` 등이 QD 대각 배치(±0.330, ±0.135 ·
  `wheel_radius` 0.080 · `gear_walk` 20.0)를 그대로 들고 있었다. params 파일이 있으면 덮어써서
  드러나지 않지만, 빠지면 조용히 QD 기하로 풀린다. 산술이 일치한다 —
  `atan2(0.330, −0.135) = 112.2°` 를 ±90° 반평면으로 접으면 **−67.8°**.
  같은 잔재가 `mpc`·`mpc_reverse`·`translate_forward`·`translate_reverse`·`yaw_control`·
  `yaw_control_reverse` 6개 액션 서버에도 개별 복제돼 있었다.
- **해결**: 세 겹으로 막았다.
  1. **기하 기본값 정정** — 7곳 전부 이 기체(Foil_A082 인라인 듀얼스티어) 값으로:
     `w1(0.6039, 0.0)` · `w2(−0.5961, 0.0)` · `wheel_radius 0.125` · `gear_walk 32.0`
  2. **`computeSpin` 을 IK 풀이에서 강제로 전환** — 인라인 배치는 `v_i = ω × r_i = (0, ω·x_i)`
     이라 조향각이 ±90° 하나뿐이다. `atan2` 를 거치지 않고 `copysign(π/2, ω·x_i)` 로 박았다.
     속도 `|ω·x_i|` 만 기하에서 계산한다. **QD 대각 배치는 자세가 기하에 따라 달라져 IK 가
     필요하지만 이 기체는 다른 조향이다** — 풀 대상이 아니었다.
  3. **`isInline()` 전제 가드** — `qd_action_server_base` 생성자가 `|w_i.y| > 1 mm` 를 검사해
     `RCLCPP_FATAL` 후 기동 실패시킨다. 2WS 액션 **9개 전부**에 걸린다.
- **파일**: `src/Control/Motion_Control/2WS/trnav_2ws_kinematics/{include/.../qd_inverse_kinematics.hpp,
  src/qd_inverse_kinematics.cpp}` · `trnav_2ws_motion/include/.../qd_action_server_base.hpp` ·
  `trnav_2ws_action_server/src/{mpc,mpc_reverse,translate_forward,translate_reverse,yaw_control,
  yaw_control_reverse}/*.cpp`
- **상태**: 완료 — SIL 3조건 검증:

  | 조건 | 조향 (F, R) | 회전 | 중심 이탈 |
  | --- | --- | --- | --- |
  | 수정 전(기본값 QD) | (−67.8, −67.8) | −44.72° | **187 mm** |
  | 수정 후 · params 있음 | (−90.0, +90.0) | −44.74° (오차 +0.26°) | **0 mm** |
  | 수정 후 · params 없음 | (−90.0, +90.0) | −44.72° (오차 +0.28°) | **0 mm** |
  | 수정 후 · QD 기하 주입 | — | — | **기동 실패(FATAL)** |

- ⚠ **미해결·범위 밖**:
  - **실기 spin 재검증 미실시** — 본 수정은 SIL 로만 확인했다. 오늘 유일한 실기 spin 은 별건의
    구동 고장 중이었으므로 정상 상태의 실기 spin 기록이 아직 없다.
  - `compute()`(일반 주행 IK)는 **미변경** — crab·translate 는 자세가 실제로 기하에 의존하므로
    푸는 것이 맞다. 강제로 바꾼 것은 spin 하나다.
  - **QD 스택(`trnav_motion_qd`)은 미점검** — 별개 파일이라 이번 변경의 영향은 없으나, 같은
    기하 기본값 잔재가 있는지는 확인하지 않았다.
  - **회귀 시험 0건** — 이 변경을 덮는 시험이 없다(debt-047 와 같은 성격).

### [Fix] 재시작 후 전륜 구동축(node1)이 지령을 받고도 안 돈다 — PC 경로 어디도 구동축 브링업을 보내지 않았다

- **문제**: can_relay 프로세스를 재시작하면 `node1 walk_front` 가 `0x60FF` 를 정상 수신하고도
  회전하지 않는다. 같은 지령을 받는 `node2` 는 정상. 드라이브는 `error_code 0` ·
  `motor_enabled true` 로 이상 없다고 보고한다.
- **원인**: 제어권 획득 시 아무도 구동축 브링업(`0x6040=0x86` · `0x60FF=0` · `0x100C`/`0x100D` ·
  `0x6060=3` PV)을 보내지 않았다. `Tools/amr_test_gui/gui.py` 는 Seer 가 세워 둔 축에 올라타
  `0x60FF` 만 덮어쓰고(`protocol.py:160-162`), can_relay 도 `allow_bringup: false` 라 같은
  처지였다. 축이 그 상태를 잃으면 PC 쪽 어느 경로도 되살리지 못한다.
  원인 격리: 조향각 0°/45°/70° 전부 실패(각도 무관) · 제어권 반환↔재획득 사이클로는 재현
  안 됨 · **프로세스 재시작에서 재현**(시행 1회, 반복 횟수 미기록) · Seer 가 한 번 주행하면 복구.
- **해결**: `_write_bringup()` 을 **구동축 전용**으로 좁히고(조향축 제외 — fault reset 이
  위치 카운터를 지워 조향 0° 기준을 무효화한다), 배포 설정 `config/can_relay.yaml` 을
  `allow_bringup: true` 로 전환. **코드 기본값 `RelayConfig.allow_bringup` 은 여전히 False** 이며
  활성화는 배포 yaml 에서만 일어난다.
- **파일**: `src/Comm/CAN/can_relay/can_relay/backend.py` ·
  `src/Comm/CAN/can_relay/config/can_relay.yaml`
- **상태**: 완료(실기 관측 근거) — 브링업 적용 후 지면 주행 2회: node1 +0.0830 m / node2 +0.0794 m
  (차 3.6 mm), node1 −0.0888 m / node2 −0.0893 m(차 0.5 mm). 조향 판독은 브링업 전후 불변
  (5,168,577 / 5,153,238). 통합 확인으로 crab +y 0.5 m(횡오차 −0.0001 m · 헤딩 −0.197°)과
  crab 차체 45° 0.4 m(횡오차 −0.0021 m · 헤딩 −0.014°)이 통과했다.
- ⚠ **미해결로 남은 것**(완료로 읽지 말 것):
  - `ui/backend_direct.py` 의 **DirectBackend 는 미수정** — 그 경로는 같은 고장이 재현된다
  - **`node2` 가 왜 멀쩡했는지 미규명** — 「재시작이 축 상태를 지운다」는 관측이며 기전은 미확정
  - **회귀 시험 0건** — 이 변경을 덮는 시험이 없다
  - **debt-017 부분 상환** — 잭업·E-STOP 상비·`0x6041`/`0x603F`/SDO abort 전수 기록 미이행

### [Fix] can_relay raw 경로만 조향을 전량 거부 — 호밍 판정이 경로마다 달랐다

- **증상**: Seer 로 호밍을 끝낸 상태(드라이브 `0x6041` bit15=1, `/motor/low_state` 4축 전부
  `home_comp: true`)에서 ROS2 모션 체인의 crab Phase 0 이 조향 87.65° 를 5초간 지령했으나
  **조향 엔코더가 0 counts** — 한 카운트도 움직이지 않고 `Phase 0 steer timeout` 으로 abort.
  구동은 정상이라 translate 는 통과했다.
- **계측**: 체인 각 단의 조향 최대치를 동시에 재서 끊긴 지점을 특정했다.

  | 단 | 건수 | 조향 최대 |
  | --- | --- | --- |
  | 액션 `/motion/wheel_cmd/crab_linear` | 252 | 87.65° |
  | mux `/motor/wheel_cmd` | 252 | 87.65° |
  | translator `/motor/low_cmd` | 252 | 89.32° |
  | 실제 `/motor/low_state` | 678 | **0.00°** |

  → 지령은 can_relay 입력까지 정상 도달. 로그에 `지령 거부 — node3 호밍 미완료 — 조향 거부`.
- **원인**: 호밍 판정이 **경로마다 달랐다.** `set_steer_deg`(`:271`)·`set_steer_axis_deg`(`:308`)
  는 `homed_effective()`(우리 호밍 **또는** 드라이브 bit15)를 쓰는데, ROS2 체인이 타는 저수준
  `set_motor_cmds`(`:372`)만 프로세스 변수 `self._homed` 를 직접 봤다. Seer 가 호밍하면
  `self._homed` 는 False 이므로 이 경로만 전량 거부된다.
  같은 결함이 **2026-08-04 에 이미 한 번 잡혀** `homed_effective()` 도입과 발행 필드
  `home_comp` 정정(`:457-459`)이 이뤄졌는데, **raw 경로가 그때 누락**됐다.
- **해결**: `set_motor_cmds` 의 판정을 `homed_effective()` 로 통일 (`backend.py:372`).
- **파일**: `src/Comm/CAN/can_relay/can_relay/backend.py`
- **상태**: 완료 — 실기에서 조향이 동작하기 시작해 crab 이 Phase 0 을 통과했다(3.88 s).
  spin 은 조향을 F=−90.0°/R=+90.0° 로 **세우는 데까지** 정상이었다(회전 −53.00°, 목표 대비
  오차 −0.21°). ⚠ 다만 같은 spin 이 중심 이탈 550 mm 를 냈다 — **조향은 정상, 구동이 비정상**
  이었고 그 원인은 별건(위 [Fix] 브링업)이다. 「spin 정상 기동」으로만 읽지 말 것.

  ❌ **정정 — 시험 숫자**: 원문의 ~~「311 passed / 0 failed」~~ 는 `test_backend_swap.py` 를
  `--ignore` 로 제외하고 돌린 값인데 **제외 사실을 적지 않았다.** 전체 실행 실측은
  **364 passed / 4 failed / 5 skipped** 이다(실패 4건은 `rclpy` 미소싱 환경 문제로 본 변경과
  무관하나, 여과한 숫자를 전체인 것처럼 보고한 것은 잘못이다).
  ⚠ **이 변경을 덮는 회귀 시험은 0건**이다 — 통과 숫자는 커버리지의 근거가 아니다.

### [Diag] 전륜 구동축(node1 walk_front)이 지령을 받고도 회전하지 않음 — 세션 중 발생

- **증상**: crab·spin 이 목표 거리·각도는 맞추는데 자세가 크게 틀어졌다(crab 0.5 m 에 헤딩
  −52.4°, spin 은 중심 이탈 550 mm).
- **판정**: 엔코더가 두 구동축의 비대칭을 그대로 보여준다.

  | 기동 | node1 walk_front | node2 walk_rear |
  | --- | --- | --- |
  | translate (같은 날 앞선 시험) | +0.5014 m | +0.5016 m |
  | crab | +0.0004 m | +1.2250 m |
  | spin | −0.0002 m | −1.1143 m |

  회전 53.0°(0.925 rad)에 한쪽 축 주행 1.1143 m 이면 회전 반경은 **1.204 m** 로,
  휠베이스 1.2 m 와 일치한다 ⇒ 차체 중심이 아니라 **한쪽 구동륜을 축으로 회전**했다.

  ⚠ **정정** — 원문은 여기에 「중심 이동 0.6039 × 0.925 = 0.559 m ≈ 실측 550 mm」를 덧붙여
  세 곳이 맞는다고 적었으나, **호(arc)와 직선 이탈(chord)을 섞었다.** 0.559 m 는 중심이
  그리는 **호의 길이**이고 실측 550 mm 는 시작–끝 **직선 거리**다. 같은 조건의 chord 는
  `2 × 0.6039 × sin(26.5°) = 0.539 m` 로 0.559 m 와 다르다. 두 값이 가까운 것은 각이 작아서지
  같은 양이기 때문이 아니다 — **독립된 세 번째 확인으로 세지 말 것.**
  또한 「전륜을 축으로」는 `motor_id_walk_front: 1`(translator config) 를 전제한 표현이며,
  **엔코더만으로는 두 구동륜 중 어느 쪽인지 구분되지 않는다.**
- **지령 도달 여부**: 축별로 지령과 실제를 함께 기록해 갈랐다 — 두 축이 **완전히 같은 지령**을
  받는다. `node1 지령 −4816..0 / 실제 −93..+17`, `node2 지령 −4816..0 / 실제 −4538..+1`
  (0.1 rpm). **지령은 정상 도달하고 회전만 하지 않는다.**
- **각도 의존성 배제**: `~/steer_axis_deg` + `~/drive_mmps` 경로로 같은 시험을 0°·45°·70°
  에서 반복했고 **전부 동일하게 실패**했다(node1 +0.0011 / +0.0010 / +0.0006 m,
  node2 +0.0615 / +0.0808 / +0.0842 m). ⇒ **조향 각도 문제는 아니다.**

  ❌ **정정** — 원문은 여기에 「ROS2 경로 문제도 아니다 ⇒ **소프트웨어 원인 배제**」를 덧붙였으나
  **오추론이다.** `/motor/low_cmd`(`driver_node.py` → `set_motor_cmds`)와 `~/steer_axis_deg`·
  `~/drive_mmps`(→ `set_steer_axis_deg`·`set_drive_mmps`)는 **같은 `RelayBackend` 인스턴스**를
  탄다. 이 시험은 **상류 경로 의존성만** 배제하며, 두 진입점이 공유하는 백엔드 공통 구간
  (기동 시퀀스·브링업)은 배제되지 않는다 — **실제 원인이 바로 거기였다.**
- **드라이브 자기보고**: `error_code 0` · `motor_enabled true` · 정지 중 `amps 452`.

  ❌ **철회** — 원문은 이것을 「**구속(stall)** 의 전형」이라 읽었다. **틀렸다.** 이 전류는
  드라이브가 PV 모드 브링업을 받지 못해 지령을 소비하지 못하는 상태의 전류이며,
  **기계적 구속의 증거가 아니다.** SDO 프레임 송신만으로 0.5 mm 까지 복구된 것이 반증이다.
- **상태**: **해결(같은 날, 커밋 `a7420a6`).** 원인은 물리 구속이 아니라 **can_relay 가 제어권
  획득 시 구동축 브링업을 보내지 않은 것**이었다 — 위 [Fix] 항목 참조.

  ❌ **철회된 원문**: ~~「미해결 — 소프트웨어 원인 배제됨, 물리 점검 필요」~~ ·
  ~~「손상 위험이 있어 구동 시험을 중단했다」~~ ·
  ~~「확인 항목: 전륜 구동륜 수동 회전 시 구속 유무, 접지 상태, 배선·커플링, 드라이브 전원 재인가」~~
  → **물리 점검은 불필요했다.** 「이 세션 진행 중 발생」은 「**can_relay 프로세스 재시작 시
  재현되는 축 브링업 상태 소실**」로 읽는다.
- **부수**: 같은 날 제기했던 「crab yaw 보정 부호가 반대」 주장의 철회는 유효하나, 그 철회 사유로
  적은 「실제 원인은 이 구동 고장」은 **인과 귀속이 아직 확정되지 않았다**(아래 항목 참조).

### [Retract] 「crab yaw 보정 부호가 뒤집혔다」 — SIL 재현 실패로 철회

- **주장**: 실차 crab 에서 yaw 오차가 −6.3° → −52.3° 로 단조 증가하고 조향 차이(F−R)가 함께
  커진 것을 보고 「보정 부호가 반대이며 양의 되먹임」이라고 적었다.
- **반증**: SIL 에서 목표 yaw 를 10° 틀어 보정을 강제하고 `dir=−1` 까지 재현했으나 **발산하지
  않았다.** 2 m 주행에서 `dir=+1` 10.00°→9.23°(lat 3.0e-5 m), `dir=−1` 10.00°→10.13°
  (lat 6.3e-2 m) — 후자는 발산이 아니라 **정상상태**(횡오차 −0.065 m 수렴, F−R 7.2° 일정).
  0.13° 표류를 발산으로 읽은 것이 과대 해석이었다.

  ⚠ **이 시험의 검출력은 낮다.** 같은 항목이 아래에 적듯 crab 은 base steer 가 90° 부근이라
  heading 보정의 권한이 `cos(89.3°)=0.012` 로 거의 0 이다. 즉 **부호가 틀렸더라도 이 시험에는
  거의 안 나타난다.** 따라서 이 결과가 뒷받침하는 것은 「**실차의 52° 는 이 부호로 설명되지
  않는다**」까지이고, 「부호가 옳다」는 **증명되지 않았다** — 정확한 상태는 철회가 아니라
  **미판정**이다.
- **실차 재확인(같은 날, 브링업 수정 후)**: crab +y 0.5 m 가 횡오차 −0.0001 m · 헤딩 −0.197°,
  crab 차체 45° 0.4 m 가 횡오차 −0.0021 m · 헤딩 −0.014° 로 통과했다. 구동 비대칭이 사라지자
  52° 가 재현되지 않았다 ⇒ 원인이 구동 쪽이라는 것과 정합하나, **yaw 보정 부호의 옳고 그름은
  여전히 이 시험으로 판정되지 않는다**(권한이 ≈0 이므로).
- **부수 확인(유효)**: `qd_crab_inverse_kinematics.hpp:25` 는 `rear_steer_offset = −dir ×
  delta_heading` 이라 규정하는데 구현(`:55`)에 `dir` 이 없다 — **문서/구현 불일치는 실재**한다.
  다만 `dir` 을 넣어도 거동이 유의미하게 바뀌지 않았다(10.13° → 10.47°). crab 은 base steer 가
  90° 부근이라 `omega ∝ Δ·cos(base)`, `cos(89.3°)=0.012` 로 **heading 보정의 권한 자체가
  거의 0** 이기 때문이다. 어느 쪽이 옳은지 미결이라 **검증 없는 변경을 남기지 않고** 원형을
  유지하고 주석으로만 남겼다. 같은 줄이 QD `trnav_qd_kinematics/src/qd_crab_inverse_kinematics.cpp:55`
  에도 있다(미변경).
- **파일**: `src/Control/Motion_Control/2WS/trnav_2ws_kinematics/src/qd_crab_inverse_kinematics.cpp`
  (주석만)

### [Diag] mcl2d 측위가 90° 어긋난 채 수렴 — 원인은 **스캔 입력 경로 오배선**(내 설정)

- **증상**: PC 측위가 Seer 대비 위치 0.40 m · 헤딩 **+94.6°** 로 정착. `/initialpose` 를 줘도
  같은 자리로 되돌아왔다(30초간 σ 0.2° — 수렴 중이 아니라 **확신하며 그 해를 찾아감**).
- **판정**: 로봇을 움직이지 않고, Seer 자세를 참으로 놓고 스캔을 map 프레임에 얹어 맵
  장애물과의 최근접 거리 중앙값을 잰다(`Tools/seer_viz/mount_check.py`, KD-tree).

  | 구성 | 중앙값 |
  | --- | --- |
  | `/scan_merged` + `laser_mounts [0,0,0]` | **0.017 m** ← 정답(맵 해상도 0.02 m 수준) |
  | `/scan_front` + 마운트(front −45°) | 1.862 m |
  | `/scan_rear` + 마운트(rear 135.29°) | 1.441 m |
  | `/scan_front` + 항등(대조) | 1.991 m |

- **원인**: `dual_laser_merger` 가 두 라이다를 **차체 기준으로 합쳐** `/scan_merged` 를 낸다
  (`base_link→scan_merged` TF 가 **완전 항등**으로 실측 확인). 그 입력에는 마운트가 항등이어야
  하는데, 원본 `/scan_front`·`/scan_rear` 를 쓰면서 마운트를 **또** 적용해 이중 변환이 됐다.
  대조 행이 보여주듯 원본 스캔은 마운트를 빼도 맞지 않는다 — **이 파이프라인의 입력이 아니다.**
- **부차 요인**(원인 아님, 증폭): `init_angle_scatter` π(전방향) vs 0.10 rad ·
  `init_dist_scatter` 0.7 vs 0.30 m. 입력이 1.9 m 어긋나면 산포를 좁혀도 맞는 해가 없다.
- **정본 배선**(타 세션 `50990c6a-v2` 구성, 실측 Seer 대비 **8 mm / 0.44°**, 24초 안정):

  ```
  -r scan:=/scan_merged   +   laser_mounts: [0.0, 0.0, 0.0]
  init_dist_scatter: 0.30   init_angle_scatter: 0.10
  ```

- **철회**: 조사 중 「라이다 마운트 규약이 ~96° 어긋났다」고 적었으나 **틀렸다.** 마운트 값은
  정상이고, 그 값을 **적용하면 안 되는 입력에 적용**한 것이 문제였다. 마운트를 ±90°·180°·스왑으로
  돌려도 맞는 조합이 없던 이유가 이것이다.
- **부수**: 진단 프로브가 `/scan_merged` 를 기본 RELIABLE 로 구독해 한 건도 못 받았다 —
  rviz 에서 고친 것과 **같은 QoS 함정**이다. 라이다 토픽 구독은 BEST_EFFORT 여야 한다.
### [Fix] 같은 사고 재발 — 채널 1 수정이 **세션 워크트리에만 있어** 다른 세션이 채널 0 을 다시 점유

- **문제**: 사용자 보고 "현재 seer 와 pc와 라이다 공유가 안되는데". Seer 알람
  `52102 localization module cannot get laser data` · `52103 timeout receive laser data from
  Nanosick, IP: 192.168.192.101` (08:13:29). 활성 구성 판독 결과 **채널 0 이 다시
  `192.168.192.10`(젯슨)** 을 가리키고 채널 1 은 비활성이었다.
- **원인**: **전날 수정이 병합되지 않았다.** 실행 중이던 스택은 **다른 세션의 워크트리**에서 떴고
  그 install 의 런치는 아직 `channel: 0` 이었다 —
  `Big-AMR-ses-c9ea2414/install/…/sick_safetyscanners2_launch.py` → `"channel": 0`
  (본 트리 `Big-AMR/install/…` 도 동일. `channel: 1` 은 `Big-AMR-ses-50990c6a-v2` 에만 존재).
  즉 2026-08-07 항목의 수정 자체는 옳았으나 **미커밋·미병합이라 다른 워크트리에 보이지 않았다.**
- **해결**: 실행 중인 다른 세션 스택을 **죽이지 않고** 양쪽을 복구했다. 실행 중 노드가
  `0.0.0.0:6060/6061` 로 듣고 있어 **채널 번호가 바뀌어도 같은 포트로 계속 수신**한다는 점을 이용했다.
  1. **채널 1 → `192.168.192.10:6060/6061` 먼저 켜고**(PC 스트림 끊김 방지)
  2. **채널 0 → `192.168.192.5:6060/6061` 로 원복**
  CoLa 2 메서드 `176`(Configuring the data output)을 직접 호출했다 —
  신설 도구 `Tools/sick_channel_audit/set_output_channel.py`. 활성 구성을 읽어 **목적지(IP·포트)만**
  교체하므로 데이터 블록·발행 주기·각도 범위는 원본이 보존된다.
  ⇒ **전날 「원격 복구 불가」로 적었던 제약이 실제로 해소됨을 실전에서 확인**했다(전원 재인가 불요).
- **파일**: `Tools/sick_channel_audit/set_output_channel.py`(신규, 쓰기 도구)
- **상태**: 완료 — 복구 후 실측: 활성 구성 채널 0 → `192.168.192.5`, 채널 1 → `192.168.192.10`
  (양 센서). Seer 빔 갱신 **5/5** · confidence **0.805** · **알람 소멸**. PC 쪽 `/scan_front`
  **34.044 Hz** · `/scan_rear` **34.047** · `/scan_merged` 33.513(발행자 각 1개, 15초 창).
  ⚠ 전환 직후 6초 창 측정에서 `/scan_front` 가 44.1 Hz 로 읽혔는데, 15초 재측정은 34.04 Hz 였다.
  단계 ①과 ② 사이에 채널 0·1 이 잠시 **둘 다 젯슨을 가리킨** 구간의 중복 수신으로 **추정**한다(미확증).
- **교훈**: 이 사고의 진짜 원인은 센서 설정이 아니라 **방지책을 무력한 곳에 뒀다는 것**이다.
  08-07 사고 후 만든 재발 방지(런치 주석·이설 절차서·코드 리뷰)는 **전부 내 워크트리 안에만**
  있었다. 다른 세션은 그 경고를 볼 수 없는 경로로 기동했고, 그래서 하나도 작동하지 않았다.
  ⇒ **「재발 방지를 작성했다」와 「재발 방지가 작동한다」를 같게 취급한 것**이 근본 원인이다.
  이 저장소 `docs/claude-mistake/INDEX.md` §메타 패턴의 "시험을 *추가한 것*과 시험이 *검출하는
  것*을 같게 취급한다"(2026-08-04-001)와 같은 형태다.
  부차 원인 둘: ① 하드웨어 설정 수정은 **미병합 상태가 능동적으로 해롭다**(코드 수정은 미병합이면
  그냥 안 쓰이지만, 이건 옛 값이 하드웨어에 계속 쓰인다) — 그 비대칭을 인지하지 못하고 커밋을
  다음 순서로 미뤘다. ② 여러 세션이 각자 워크트리에서 같은 실기를 구동한다는 사실을 방지책 설계에
  넣지 않았다.

- **재발 방지 (기계 강제)**: 사람이 읽어야 작동하는 방지책은 이미 두 번 실패했으므로 **기동 경로에
  기계 검사**를 넣었다 — `src/Sensors/Lidar/2D/sick_safetyscanners2/launch/channel_guard.py`(신규).
  런치가 `OpaqueFunction` 으로 노드 기동 **전에** 호출하며, 센서의 **저장 구성**(Index 177)을 읽어
  쓰려는 채널이 거기서 활성이면 `RuntimeError` 로 **런치를 중단**시킨다.
  - 판정 근거를 활성(178)이 아니라 **저장(177)** 으로 잡았다 — 활성은 우리 런타임 변경이 섞여 있어
    이미 빼앗은 상태에서 "내 것"으로 보이는 자기충족 판정이 된다.
  - 센서에 닿지 못하면 **통과**시킨다. 못 닿으면 설정도 못 바꾸므로 해를 끼칠 수 없고, 드라이버가
    곧 자기 오류로 죽는다. 없는 위험으로 기동을 막지 않는다.
  - 가드가 검사하는 값과 노드가 쓰는 값이 갈리지 않도록 `FRONT_IP`·`REAR_IP`·`CHANNEL` **상수 하나로
    묶었다**(런치 상단).
  - `launch/` 는 `CMakeLists.txt:71` 이 디렉터리째 설치하므로 **어느 워크트리에서 띄우든 따라온다.**
  - **검증(돌연변이 포함, 2026-08-08 실기)**: ① 채널 1 → 통과 ② **채널 0 → 양 센서 모두 차단**
    (수신자 주소까지 메시지에 표시) ③ 없는 채널 9 → 차단 ④ 닿지 않는 센서 → 통과. **4/4 PASS.**
    「가드를 넣었다」가 아니라 **「가드가 실제로 막는다」를 이 출력으로 말한다.**
  ⚠ 이 가드도 **병합돼야 다른 세션을 보호한다** — 같은 함정을 반복하지 않도록 즉시 커밋·푸시했다.

---

## 2026-08-07

### [Fix] 우리 라이다 드라이버가 Seer 의 스캐너 출력 채널을 빼앗아 Seer 가 라이다를 못 받음 — 채널 0 → 1 분리

- **문제**: 사용자 보고 "pc에서 연결하니 seer 가 라이다를 못받는데". 확인 결과 Seer 는 두 라이다
  모두 **마지막 프레임에 얼어붙어** 있었다 — Seer API `1009`(robot_status_laser) 응답의 빔 배열
  MD5 가 8회 폴링(≈5초) 내내 완전 동일(`5052f1aed9`/`f72f51979f`). Seer 측위 confidence 도
  정지 기준값 0.818 에서 0.689 로 내려앉아 있었다.
- **원인**: `sick_safetyscanners2` 드라이버는 기동 시 COLA2 `changeSensorSettings()` 로 **센서 쪽
  UDP 출력 채널의 목적지**를 `host_ip:host_udp_port` 로 덮어쓴다
  (`SickSafetyscanners.cpp:145`, `SickSafetyscanners.hpp:294`). 우리 런치가 **채널 0**
  (`sick_safetyscanners2_launch.py:18,46`)을 쓰고 있었고, Seer 컨트롤러도 같은 채널 0 을 자기
  자신에게 물려 두고 있어 **우리가 기동하는 순간 Seer 의 스트림을 빼앗았다.**
  게다가 드라이버에 **원복 코드가 없어** 우리 노드를 종료해도 센서 설정이 그대로 남는다 —
  실증: 우리 노드 전부 종료(bringup SIGINT, `ps` 로 0건 확인) 상태에서 `192.168.192.10:6060`·
  `:6061` 바인드 후 청취하니 스캐너 2대가 **여전히 204.2 pkt/s 로 젯슨에 송신**
  (송신자 `192.168.192.100`/`.101`).
- **해결**: **Seer = 채널 0, 우리 = 채널 1** 로 분리. `sick_safetyscanners2_launch.py` 의 전·후방
  `channel` 을 `0 → 1` 로 바꾸고, 파일 상단에 기전·실측 근거·원복 부재를 주석으로 박았다
  (다음 사람이 기본값 0 으로 되돌리지 못하게).
  **근거가 되는 실측** — 센서 `NANS3-CAAZ30AN1P02`(nanoScan3, FW(firmware) `R01.66`):
  탐침 노드를 `channel:=1`, `host_udp_port:=6070` 으로 띄우니 `/scan` 이 **34.04 Hz** 로 들어오는
  **동시에** 채널 0 → 6060 이 **204.3 pkt/s** 로 계속 흘렀다 ⇒ 이 센서는 UDP 출력 채널을
  **2개 이상 동시 지원**한다.
  ※ 멀티캐스트(사용자 제안)는 **미채택** — 드라이버 수신 측은 지원하나
  (`host_ip` 가 멀티캐스트면 `interface_ip` 로 그룹 가입, `SickSafetyscanners.cpp:156`),
  **Seer 수신 측을 그룹에 가입시킬 수단**이 확인되지 않았다(모델 스키마 `1500` 의 laser
  `deviceParams` 에 노출된 `ip` 는 1개뿐).
- **파일**: `src/Sensors/Lidar/2D/sick_safetyscanners2/launch/sick_safetyscanners2_launch.py`
  (`bringup.launch.py` → `dual_laser_merger/launch/sick_with_merger.launch.py` → 이 런치 경유.
  `channel` 을 쓰는 런치는 저장소 전수 이 파일과 미사용 `*_lifecycle_launch.py` 뿐)
- **상태**: **완료 — 양쪽 동시 수신 실증(2026-08-07 21:44).**

  | | 측정값 (동시각) |
  | --- | --- |
  | PC(젯슨) · 채널 1 | `/scan_front` **34.039 Hz** · `/scan_rear` **34.022** · `/scan_merged` **34.582** · `/odom` **33.894** |
  | Seer · 채널 0 | `1009` 빔 MD5 갱신 **5/5회** · 측위 confidence **0.658** · `1050` 알람 **없음** |

  복구 경로는 처음 예측과 달랐다. 아래 두 단계로 갈렸다:

  1. **Seer 프로그램 재시작(`5004 robot_core_restart_req` @19208, 응답 `15004`)만으로는 원복되지
     않았다.** 재시작 후에도 스캐너는 계속 젯슨으로 204.2 pkt/s 를 보냈다. ⇒ **Seer 는 센서 설정을
     쓰지 않고 수신만 한다.** 목적지는 SICK Safety Designer 로 **센서 플래시에 박아 둔 값**이고
     Seer 에게는 되돌릴 능력이 없다. (재시작 직후 Seer 가 스스로 원인을 확증해 줬다 —
     `1050` errors: **`52103 timeout receive laser data from Nanosick, IP: 192.168.192.101`**)
  2. **로봇 전원 재인가(리부팅)로 원복됐다.** 판정 근거는 「수신 0」 자체가 아니라 **스캐너가
     살아 있는데도 0** 이라는 조합이다 — 리부팅 후 `.100`·`.101` ping 정상인 상태에서
     6060/6061 청취 **0 pkt/s**(리부팅 전 동일 조건 204.2 pkt/s). `use_persistent_config=False`
     라 플래시 미기록이었으므로 전원 재인가로 플래시 값(= Seer 목적지)이 복귀했다.

  ⚠ **재발 방지 관점의 교훈**: 이 원복 수단은 **물리 전원 재인가뿐**이다. 채널 0 을 다시 건드리면
  원격으로는 되돌릴 방법이 없다(Seer 수신 IP·포트 미상 — Seer 라이다망 주소가
  **192.168.192.5**(MAC `e0:27:6c:a8:b3:a9`)인 것까지는 확인했으나 UDP 포트는 미상).
  런치 상단 주석이 이 사실을 담고 있다.

  **✓ 1차 source 대조 완료 (2026-08-07 22:0x)** — 매뉴얼 2건을 공식 사이트에서 받아
  `References/sick/nanoscan3/` 에 보관하고 대조했다. 잠정 운용 조건이던 3개 항목이 모두 닫혔다:

  | 확인 항목 | 결과 | 인용 |
  | --- | --- | --- |
  | 채널 번호 범위 | **0…3**(최대 4채널) ⇒ `channel=1` 은 규격 내 | `u8ChannelNumber` "Number of the channel to be configured (0 ... 3)" — [Data output via UDP and TCP/IP 8022708/1W29, Table 73 §6.3.2.2, page 62](../../References/sick/nanoscan3/technical_information_data_output_udp_tcpip_en_im0083701.pdf) |
  | 채널 독립성 | 채널별 설정 독립 ⇒ 채널 0 과 간섭 없음 | "Every data output channel has independent settings." — [nanoScan3 I/O Operating Instructions 8024596/1W27, page 94](../../References/sick/nanoscan3/operating_instructions_nanoscan3_io_en_im0087137.pdf) |
  | **안전 기능(OSSD) 영향** | **무관** — 데이터 출력은 애초에 안전 기능이 아니다 | DANGER "Data output may only be used for general monitoring and control tasks. → Do not use data output for safety-related applications." [8022708/1W29, §2.1 page 6 · §4 page 9]. 운영지침도 "This data is not intended for use in safety-related applications" 이며 용도로 **AGV 내비게이션 지원**을 명시 [8024596/1W27, page 94] |

  ⇒ **채널 1 운용은 「잠정」에서 「확정」으로 전환한다.** 우리가 쓰는 경로는 벤더가 명시한
  비안전 데이터 출력이고, 매뉴얼이 드는 대표 용도가 바로 우리 용도(AGV 내비게이션)다.

  **부수 확증** — 오늘 관측한 "전원 재인가로만 원복" 현상이 문서에 그대로 적혀 있다:
  "Used to configure a data output channel. **This configuration is not permanent, i.e. the
  previously saved configuration will be active again after restarting the device.**"
  [8022708/1W29, §6.3.2.2, page 62]. ⇒ 드라이버가 쓰는 설정 경로는 **영구화되지 않으며**
  Safety Designer 로 저장된 구성은 우리가 덮어쓸 수 없다. 리스크가 구조적으로 제한된다.

  **✓ 저장 구성 실판독 완료 — 미확인 1건 닫힘 (2026-08-07 22:1x)**
  CoLa 2 로 저장(Index 177)·활성(Index 178) 구성을 직접 읽었다
  (`Tools/sick_channel_audit/read_output_channels.py`, **읽기 전용**).

  | 센서 | 변수 | 채널 0 | 채널 1 | 채널 2·3 |
  | --- | --- | --- | --- | --- |
  | `.100` 전방 | 저장(177) | ● `192.168.192.5:6060` | ○ 비활성 | ○ 비활성 |
  | | 활성(178) | ● `192.168.192.5:6060` | ● `192.168.192.10:6060` | ○ 비활성 |
  | `.101` 후방 | 저장(177) | ● `192.168.192.5:6061` | ○ 비활성 | ○ 비활성 |
  | | 활성(178) | ● `192.168.192.5:6061` | ● `192.168.192.10:6061` | ○ 비활성 |

  ⇒ **채널 1 은 저장 구성에서 비어 있었다 — 우리가 남의 채널을 뺏은 것이 아니다.** 채널 2·3 도
  여유가 있다. 우리 채널 1 은 저장 구성에 없으므로 재부팅 시 사라지지만, 드라이버가 매 기동마다
  다시 설정하므로 운용상 문제가 없다.

  **✓ 「원격 복구 불가」 제약 해소** — 위 판독으로 **Seer 의 수신 주소·포트가 확정**됐다:
  전방 `192.168.192.5:6060`, 후방 `192.168.192.5:6061`. 앞서 "Seer 수신 IP·포트를 몰라 우리가
  되돌릴 수 없다" 고 적은 것은 이제 성립하지 않는다. 만약 채널 0 을 다시 덮어쓰는 사고가 나면
  드라이버를 `channel:=0 host_ip:=192.168.192.5 host_udp_port:=6060`(후방 6061)로 한 번 띄워
  **전원 재인가 없이 원복**할 수 있다. (그래도 채널 0 은 건드리지 않는 것이 원칙이다.)

  ⚠ **도구 작성 중 자체 발견한 함정 2건** (보고 전 수정 완료, 도구에 가드 내장):
  ① 두 변수의 **채널 stride 가 다르다** — 저장은 24바이트(Table 63)지만 활성은 파생값이 붙어
  **48바이트**(Table 66, page 58~59). 24 로 통일해 읽으면 활성 구성이 **채널 8개로 잘못 쪼개진다**
  (실제로 1차 실행에서 그렇게 오독했다). 도구는 나머지 바이트가 남으면 예외를 던진다.
  ② CoLa 2 세션 개설의 `ClientID` 는 **정확히 4바이트**여야 한다. 문서는 "bytestream" 이라고만
  적어 길이를 명시하지 않는데, 실기는 5바이트 ASCII 에 `0x000E FLEX_OUT_OF_BOUNDS`, 생략 시
  `0x0008 BUFFER_UNDERFLOW` 로 거부했다. [실측 2026-08-07]

  ⚠ **부수 비용**: `5004` 재시작으로 Seer 측위가 초기화됐고(confidence 0, x=y=0), 이어진 리부팅
  후 Seer 애플리케이션 기동에 **약 15분 이상** 걸렸다(OS 는 ping 응답하나 `19204` 미개방 구간이
  길다). 무선(`192.168.44.82`) 복귀는 유선(`192.168.192.5`)보다 늦었다 — 급할 때는 라이다망
  주소로 조회하는 편이 빠르다.
- ⚠ **미확정 1건**: 주행 시험(20:0x~) 중 Seer confidence 가 0.04~0.69 로 **변동**했으므로 그때는
  일부라도 수신하고 있었다. **언제 완전히 끊겼는지는 미확정**이다. 위 인과는 코드·실측으로
  확정되나, "주행 시험 내내 굶고 있었다" 는 주장은 하지 않는다.
- ⚠ **파생 영향**: 같은 날 주행 정확도 시험(`experiments/track_drive2_20260807.jsonl`, 17.77 m)의
  기준값이 이 문제로 오염됐다 — 343 샘플 중 **213개가 confidence 미달로 폐기**됐고, 남은 130개도
  중앙값(위치차 0.010 m · 각도차 0.338°)은 정지 기준선과 같으나 평균 0.355 m · 최대 2.262 m 로
  크게 벌어졌다. **Seer 복구 후 재측정 전까지 이 주행 수치로 위치추정 정확도를 판정하지 않는다.**

> 부기: 본 저장소 워킹트리에 `docs/claude_guideline/issue_fix/` 가 **미설치**여서
> (`docs/claude_guideline/` 에 `code_review`·`external_reference` 만 존재) SOP 문서를 선행 Read 하지
> 못했다. 본 entry 는 이 파일의 기존 항목 형식(문제·원인·해결·파일·상태)을 따랐다.

---

## 2026-08-06

### [Fix] SIL 런치 4종이 시작 즉시 abort — `sil_pose_adapter` 누락 (한 번도 동작한 적 없음)

- **문제**: `sil_translate_forward`·`sil_translate_reverse`·`sil_mpc`·`sil_mpc_reverse` 4종이
  목표를 받은 지 **0.0003 초** 만에 `status −3` 로 ABORTED. 로그는
  `TF2 map->base_link not available` 이었다.
- **진단**: 메시지와 달리 **TF 문제가 아니다.** `LocalizationMonitor::lookupMapToBase` 는
  TF 를 쓰지 않고 **`/robot_pose`(PoseStamped) 토픽 캐시**를 읽는다
  (`localization_monitor.cpp:137-150`, 기본 토픽 `localization_monitor.hpp:27`).
  실차는 `trnav_pose_publisher` 가 그 토픽을 내고, SIL 에선 `sil_pose_adapter` 가
  `/rtabmap/localization_pose`(PoseWithCovarianceStamped) → `/robot_pose` 로 변환해 낸다.
  `sil_crab_linear` 에는 그 어댑터가 있고 `sil_spin`·`sil_turn` 에는 **불필요 사유가 명시**돼
  있는데, 이 4종만 **사유 없이 빠져 있었다.**

  > ⚠ **2026-08-06 자기 정정** — 초판은 여기에 두 가지를 더 적었으나 **근거가 없어 철회한다**:
  > - ~~「이 4개 런치는 작성 이후 한 번도 성공한 적이 없다」~~ → 어댑터를 별도로 띄우면
  >   동작하므로 **단정할 수 없다.** 확인된 것은 「이 런치만으로는 abort 한다」뿐이다.
  > - ~~「실차 경로는 정상 — SIL 하네스만의 결함이다」~~ → **확인 불가.**
  >   `/robot_pose` 를 내는 `trnav_pose_publisher` 는 **이 저장소에 없다**
  >   (`src/Navigation/` = `icp_odometry_bringup`·`mcl2d_*` 뿐, QD 문서가 가리키는
  >   `src/Navigation/trnav_pose_publisher` 경로는 **부재**). 근거는 `sil_pose_adapter_node.cpp:8`
  >   주석 한 줄뿐이었다. **실기에서도 이 4종이 abort 할 가능성을 배제하지 못한다** —
  >   실기 브링업에서 `/robot_pose` 발행자를 확인해야 한다. **미확인.**
  >
  > ✅ **2026-08-06 해소** — 확인 결과 이 저장소에 발행자가 **없는 것이 맞았다.**
  >   `src/Navigation/seer_pose_publisher` 를 신설해 Seer 상태 API `1004` 로 그 토픽을 낸다
  >   (ADR `docs/adr/2026-08-06-seer-pose-publisher.md`). 실 Seer 대상 **읽기 전용** 검증:
  >   발행 **9.796/9.978 Hz** · 구동 중인 로봇 좌표 실시간 추종 · 맵 게이트 차단 시 수신 0건.
  >   ⚠ **구동 연동 검증 0회** — 액션과 함께 돌려본 적은 없다.
- **수정**: 4개 런치에 `sil_pose_adapter` include 추가(crab 과 동일 방식, 파라미터 불요).
- **검증** (`ROS_DOMAIN_ID=43`, 2 m 직선):

  | 액션 | status | 이동거리 | 횡오차 | 소요 |
  | --- | --- | --- | --- | --- |
  | translate_forward | 0 | 1.980 m | −0.10 mm | 12.44 s |
  | translate_reverse | 0 | 2.000 m | +0.10 mm | 11.16 s |
  | mpc | 0 | 2.000 m | +0.23 mm | 11.16 s |
  | mpc_reverse | 0 | 2.000 m | **−0.21 mm** | 11.18 s |

  **4종 전부 정상.** (mpc_reverse 는 초회 시험에서 −0.39 m 가 나왔으나 **시험 입력 오류**였다 —
  아래 [Diag] 참조.)
- **남은 것**: ① 에러 문구가 실제 기전(토픽 부재)과 다르다 ② `translate_pose_topic`·
  `mpc_pose_topic` 설정 키를 **읽는 코드가 0건**(죽은 키) ③
  `translate_forward_action_server.cpp:114` 주석 `(TF-only, topic 폐기 2026-05-18)` 이
  현재와 정반대. 셋 다 런타임 동작 변화 없음 — 별건.

### [Diag] mpc_reverse 는 정상 — 「후진 발산」은 **시험 입력 오류**였다 (초회 판정 철회)

> ❌ **본 항목의 초판(같은 날 커밋 `42c5bb4`)은 「mpc_reverse 가 후진 중 yaw 발산 —
> QD 에서 성립하던 것이 2WS 기하에서 성립하지 않는 첫 사례」로 단정했다. 그 판정은 틀렸다.**
> 원문은 이력으로 보존하지 않고 아래 사실로 대체한다(인용 금지).

- **초회 관측**: 2 m 후진에서 yaw 가 +4.4° → +18.9° → +25.0° 로 벌어지고 횡오차 −0.39 m.
- **실제 원인 — 내가 만든 목표 경로가 잘못됐다.** 액션은 경로 pose 의 **orientation 을 직접**
  쓴다(`mpc_reverse_action_server.cpp:385` 「path orientation 직접 사용」 — 인접점 방향으로
  유추하지 않는다). 그런데 −x 방향 경로의 pose orientation 을 전부 **identity(yaw 0)** 로 뒀다.
  후진 보정 `effective_yaw = robot_yaw + π = 180°` 와 비교되어 헤딩오차가 **−180°** 로 나왔고,
  `delta_f` 가 즉시 **+45.00°(클램프)** 로 포화해 옆으로 밀려난 것이다.
  forward `mpc` 가 정상이던 것도 같은 이유 — +x 경로라 identity 가 **우연히** 맞았다.
- **경로 yaw 를 진행 방향(π)으로 넣고 재측정** (플랜트 초기화 후 1회):

  | | 잘못된 목표 | 올바른 목표 |
  | --- | --- | --- |
  | 횡오차 | −0.390 m | **−0.21 mm** |
  | 헤딩오차 | −177° | **−0.033°** |
  | 소요 | 12.48 s | 11.18 s |

  `mpc_reverse_debug` 계측: CTE 가 −0.0030 m 에서 단조 감소해 −0.0002 m,
  **|CTE| 가 증가한 스텝 0/557**. 제어는 정상 수렴한다. ⇒ **제어 결함 없음.**

- **관측 사실 — `status` 는 경로 정확도를 담지 않는다** (⚠ 「결함」으로 단정하지 않는다):
  - 헤딩오차 ±180°·횡오차 0.39 m 로 끝났는데도 결과가 **`status 0`(SUCCEEDED)** 였다.
  - 코드 확인: `result->status = 0` 이 **무조건**이고(`mpc_reverse:953`),
    `final_lateral_error`·`final_heading_error` 는 **계산해 결과에 실을 뿐 판정에 쓰지 않는다.**
    **4종 전부 동일** — `translate_forward:950` · `translate_reverse:891` · `mpc:960` ·
    `mpc_reverse:953`, 각 직전 12줄에 오차 검사 **0건**.
  - **QD 원본도 동일** — 판정 블록 직접 대조 **차이 0(byte-identical)**.
  - ⚠ **이것이 결함인지 설계인지 저장소 안에서 판정할 수 없다.** 액션이 오차를 **수치로
    돌려주고 호출자가 판단하는 계약**일 수 있는데, 이 저장소에는
    **`final_lateral_error`·`final_heading_error` 를 읽는 코드가 0건**이고 액션을 호출하는
    상위 계층(미션·GUI)도 **0건**이다(각 `*_main.cpp` 는 노드 spin 뿐). 호출자는
    저장소 밖(acs_gui 등)에 있다.
  - **필요한 확인**: 외부 호출자가 이 두 필드를 검사하는가. 검사하면 설계대로이고,
    무시하면 「경로를 잘못 만들어도 성공으로 통보」가 성립한다. **미확인.**
- **부수**: `final_heading_error` 를 전진 기준으로 계산해 후진 시 ±180° 로 나온다(보고 아티팩트).
- **교훈 기록**: `docs/claude-mistake/2026-08-06-004_mpc-reverse-defect-from-bad-probe.md`

### [Fix] turn 이 잡음 조건에서 **덜 돌고도 다 돌았다고 판정** — 주 루프 각도 계상이 방향 무시

- **문제**: `turn` 이 목표 45° 를 지령받고 **44.15~44.66° 만 돌면서** 자기보고는 **45.19~45.30°**
  로 냈다. 즉 부족 회전 **0.34~0.85°** 가 액션 자신에게 보이지 않는다. 미세보정 임계
  `fine_correction_threshold_deg: 0.3` 은 「임계 안」으로 판정되어 보정도 걸리지 않았다.
- **진단**: `turn_action_server.cpp` 주 루프가
  `accumulated_angle += std::abs(delta_yaw)` 로 **방향을 보지 않는다.** 역방향 잡음 델타까지
  전진으로 계상하므로, 잡음이 좌우 대칭이어도 편향이 한 방향으로만 쌓인다. 같은 파일의
  정착 블록·미세보정 루프는 `sign * delta_deg > 0` 로 방향을 보는데 **주 루프만 예외**였다.
  - **왜 여태 안 보였나** — SIL 플랜트가 지령을 되울리고 잡음이 없어 델타 부호가 뒤집히지
    않았다. 그 조건에서는 두 식이 **완전히 같은 값**을 낸다(측정오차 0.000°). 2026-08-06 에
    플랜트에 관성(0.6 s)·조향 슬루(57.1 deg/s)·IMU yaw 잡음(0.05° 1σ)을 넣고서야 드러났다.
    **시험이 통과했지만 그 통과가 근거가 아니었던 구간**이다.
- **수정**: 주 루프를 `accumulated_angle += sign * delta_deg` (0 하한)으로. 이 식은 나머지 두
  블록의 `if/else` 와 **수학적으로 동일**하다 — 새 규칙이 아니라 주 루프만 빠져 있던 같은
  규약을 맞춘 것. ADR `docs/adr/2026-08-06-turn-angle-accounting-sign.md`.
- **검증** (목표 45° · R=1.0 m, `Tools/motion_chain_check/turn_residual_probe.py`):

  | 조건 | 종전 실제오차 | 수정 후 |
  | --- | --- | --- |
  | 즉응·무잡음 (3회) | +0.172° σ0.000 | **+0.172° σ0.000 — 완전 동일(무회귀)** |
  | 동특성·잡음 0.05° (5회) | 평균 −0.536° · \|최대\| **0.846°** · σ 0.221 | 평균 −0.211° · \|최대\| **0.298°** · σ 0.065 |

  회귀 고정: `Tools/motion_chain_check/turn_angle_accounting_check.py` ⚠ **2026-08-10 폐기됨** — 계상 세 지점을
  소스에서 재도출, 하나라도 방향 무시면 `exit 1`. **검출력 확인**: 종전 형태가 남아 있는
  QD 상류를 `--path` 로 지정하면 `:233` 을 잡고 `exit 1`(자기충족적 통과가 아님).
- **남는 한계**: 잡음 0.05° 1σ 는 **가정값**이다 — `References/` 에 iAHRS 자료가 없어 실기
  잡음 크기를 모른다. 기전과 방향(항상 부족 회전)은 확정, 실기 크기는 미확정. 또 임계 0.3°
  여유가 **0.002° 뿐**이라 실기 잡음이 조금만 커도 초과한다. 근본 해소는 `spin` 방식
  (절대 목표 yaw 대조, `spin_action_server.cpp:276`) 전환이며 구조 변경이라 별건.
  **실기 검증 0회.**

### [Fix] Tongyi CANopen 프로토콜 정본 — 적대적 감사 3인이 찾아낸 치명 13건 정정

- **문제**: `docs/tongyi_can_protocol/2026-08-05.md`(초판) 이 자체 검사기에서 **「통과 174 · 불일치 0」**
  을 내고 있었으나, 사용자 지시로 투입한 적대적 감사 3인(규격 인용 / 실측 독립 재계산 / 추론·범위)이
  **치명 13건 · 중대 28건**을 찾았다. 주요 항목:
  - **부재 주장 3건이 거짓** — `0x4670` 보드레이트 주소·DI5/DI8 호밍 기능·§6.17 PDO 동적 설정을
    「V7.0 에 없는 정보」로 단정했으나 **전부 V7.0 에 있다**(page 135 · 33 · 190). V7.0 을 조회하지 않았다.
  - **주 캡처의 12.65 s 전노드 두절을 놓쳤다** — `t=5.15–17.80`, SDO 무응답 **3,389건**, Guard 응답 4건.
    §2-2 표에 요청 121,721 / 응답 118,333 을 나란히 적고도 차이를 묻지 않았다. 이 때문에
    「두절 국면 없음」·「dropout 미관측」이 거짓이 됐고, 구동 `0x86` 106회(=**두절 중 Fault Reset 재시도**)를
    「축 준비」로 오독했으며, 버스 부하·쓰기율이 사장 구간 포함 평균이 됐다.
  - **`counts/°` 57,344 는 순환 측정** — 스윕 도구가 `orin_steer_sweep_1005.py:110` 에서
    `deg × 57344` 로 지령한 값을 되읽은 것이다. [실측] 등급을 붙일 수 없다.
  - **EDS 「통신 오브젝트 무변경」이 거짓** — 공통 섹션 내부 DefaultValue **18건** 변경,
    **TPDO2 기본 매핑에 `0x2300`·`0x2301`(온도) 추가**. 근거로 실은 스니펫이 섹션 이름 집합만 비교했다.
  - **「SYNC 0건」은 계측 불가** — 캡처 도구가 `orin_homing_capture.py:179` 에서 DLC 0 프레임을 폐기한다.
  - **`0x6098` 「알 수 없음」이 거짓** — `Log/homing_diag_260803_141949.json` 에 `=1` 리드백이 있다.
  - **이식 안전규칙 오류** — 「bit15=0 구간을 읽지 말라」로는 부족하다. `0x6064` 동결이 bit15 복귀보다
    **98~179 ms 늦게** 풀려, 그대로 구현하면 완료 후의 0 을 실위치로 읽는다.
- **원인**: 검사기가 **인쇄 수치와 인용 좌표만** 검사하는데 출력은 「모든 주장이 일치한다」였고,
  돌연변이 15건이 전부 숫자 한 자리 변조라 **서술을 검증한다는 착각**을 만들었다. 감사관이 숫자를
  그대로 둔 채 서술만 23곳 뒤집은 사본을 넣자 **통과 174 · 불일치 0 으로 한 건도 줄지 않았다.**
- **해결**:
  - 문서를 정정판으로 재작성(954줄) — §0-3 검사기 보증 범위 경고 · §0-4 계측 한계(DLC 0 필터·배치
    타임스탬프) · §2-3 두절 절 신설 · §11-1 등급을 **[설정]** 으로 강등 · 안전 절(§3-3 홀딩토크 상실,
    §9-3 이식 규칙, §9-4 무동작 사례) 추가 · 등급표에 **[설정]**·**❌ 계측 불가** 신설.
  - 프로토콜 항목마다 **파일 + 절 + 인쇄 페이지**를 병기(부록에 두 판본 쪽수 대응표).
  - `Tools/tongyi_protocol/verify_doc_claims.py` 재설계 — **부재 주장 검사**(반대편 판본 조회, 7건) ·
    **전량 대조**(`doc_values()`) · **인용 페이지 커버리지 강제**(예외 폐지) · **다중 캡처 대조** ·
    출력 문구를 보증 범위대로 정정.
  - `Tools/tongyi_protocol/mutation_check.py` 를 15 → **25건**(서술·등급·EDS 변조 포함)으로 확대.
- **검증**: `verify_doc_claims.py` **243 항목 통과 · 불일치 0**,
  `mutation_check.py` **25건 전부 검출**(복원 후 sha256 일치·재검증 통과).
  버스 부하는 CRC-15 + 비트 스터핑을 프레임마다 실제로 세어 재산출 — 정상 구간 **70.5 %**,
  스터핑 오버헤드 **+9.98 %**(초판의 「+20 % 가정」은 실제의 약 2배였다).
- **기록**: `docs/claude-mistake/2026-08-06-002_absence-claimed-without-checking-and-tool-scope-inflation.md`
  (INDEX §메타 패턴 갱신 — 「없다」 일반화 **네 번째**, 「시험 추가 = 검출」 재발).

---

## 2026-08-05

### [Fix] flash_panda.py 성공 플래시가 실패처럼 읽혔다 — LIBUSB_ERROR_BUSY traceback + EXPECT 불일치 문구

- **문제**: `python3 flash_panda.py` 로 CAN Relay 펌웨어를 정상 플래시했는데 출력이 실패로 읽혔다.
  두 가지가 겹쳤다 — ① `usb1.USBErrorBusy: LIBUSB_ERROR_BUSY [-6]` **traceback 전문**이 찍히고,
  ② 마지막 판정이 `=== 버전 문자열이 EXPECT(DEV-26524538-DEBUG)와 다름 ===` 이었다.
  **실제로는 둘 다 정상이었고 플래시는 성공**이었다(장치 version `DEV-cc5e0491-DEBUG`).
- **원인**:
  - ① traceback 은 **벤더 라이브러리의 정상 재시도 경로**다. 플래시는 장치를 재열거시키므로 직후
    첫 `claimInterface(0)` 이 BUSY 로 실패하는데, `Tools/docking_field_kit/panda/python/__init__.py:236-241`
    의 `connect()` 는 `while 1` 안에서 **예외를 print 하고 재시도**하고
    `panda/python/__init__.py:265-275` 의 `reconnect()` 가 최대 15초 재시도한다. 뒤에 `connected` 가
    찍혔다면 성공이며, 진짜 실패는 `reconnect failed` 예외로 죽는 경우뿐이다.
  - ② `Tools/docking_field_kit/flash_panda.py:109` 의 판정이 **고정 상수** `EXPECT`(2026-07-23 시점
    git short hash)와 비교하고 있었다. 재빌드하면 이 문자열은 **정상적으로 달라지므로**
    「다름」 문구가 매 정상 플래시마다 뜬다. 파일 안 주석(`flash_panda.py:37-40`)은 이미 그 사실을
    적어 뒀으나 **출력 문구는 여전히 실패처럼 읽혔다** — 주석만으로는 오독을 막지 못했다.
- **해결** (`flash_panda.py`, +38 / −3 줄):
  - 플래시 직전 안내 2줄 출력 — BUSY traceback 은 정상 재시도이고 뒤의 `connected` 가 성공 신호임을 명시.
  - 판정 기준을 고정 `EXPECT` 에서 **이미지 옆 `version` 사이드카**(`board/SConscript` 가 빌드마다 갱신)로
    이전. 신설 `read_build_version(fw)` 가 `os.path.dirname(fw)/version` 을 읽고, 없으면 `None` 을
    반환해 기존 `EXPECT` 분기로 graceful fallback 한다. 일치 시 `✅ 플래시 성공`, 불일치 시 재시도 안내.
  - 어느 분기로 가든 **비트레이트는 별도 확인 대상**임을 1줄로 항상 출력(version 문자열은 그것을 증명하지 않음).
  - **벤더 라이브러리(`panda/`)는 수정하지 않았다** — 상류 코드이고 재시도 동작 자체는 옳다.
- **검증**:
  - `python3 -m py_compile flash_panda.py` → 0 errors.
  - `read_build_version()` 3케이스 — 실제 빌드 경로 → `'DEV-cc5e0491-DEBUG'`(플래시된 장치가 보고한 값과 일치),
    없는 경로 → `None`, 디렉토리는 있고 사이드카 없음 → `None`(fallback 보존).
  - 판정 로직 시뮬레이션 — 일치 `SUCCESS` / 불일치 `MISMATCH`.
  - ⚠ **재플래시 end-to-end 는 실행하지 않았다** — 실기 쓰기 동작이라 요청 범위 밖이다. 다음 실제
    플래시 때 새 문구가 나오는지 확인할 것.
- **부수 확인 (같은 세션, 실기 판독)**: 플래시 결과를 독립 조회해 `can_rx_errs` 0 · `can_fwd_errs` 0 ·
  `faults` 0, 3초간 9,542 프레임 수신(bus0 4,771 · bus2 4,771 동일 → 릴레이 통과 상태, §A-3 과 일치),
  펌웨어 상수 `board/drivers/can_common.h:148-150` `can_speed = 2500U` ⇒ **250 kbps 정합 확인**.
  한편 `can_send_errs` 가 ~3,200/s 로 계속 오르는데 **송신 실패가 아니다** — 이 값이 증가하는 지점은
  전부 `can_push(&can_rx_q, …)` **실패**로(`board/drivers/can_common.h:222`, `board/drivers/bxcan.h:118,194`,
  `board/drivers/fdcan.h:88,172`, 노출 `board/usb_comms.h:23`) **USB 로 보낼 수신 큐 오버플로**다.
  증가율이 bus0+bus2 프레임률(1,590×2)과 일치하며, CAN 을 읽는 소비자가 없으면 정상적으로 쌓인다.
  이름이 오해를 부르므로 **이 값만으로 이상 판정 금지** — 실제 신호는 `can_rx_errs`·`can_fwd_errs`·`faults`.
- **파일**: `Tools/docking_field_kit/flash_panda.py`
- **상태**: 완료

---

## 2026-08-04

### [Fix] 시험 GUI 원본 결함 11건 — 정착 신선도·USB 락·구동 재송신 외 8건

- **문제**: `Tools/amr_test_gui/gui.py` 에 High 3 · Medium 5 · Low 3 이 남아 있었다.
  특히 ① 폴링이 죽어도 마지막 실측이 남아 **정착 판정을 통과시키고 구동에 들어갔고**,
  ② `heartbeat`(0xf3)만 `_can_lock` 밖이라 조그·호밍 스레드와 USB 핸들이 겹쳤으며,
  ③ 구동 지령이 **단발 송신**이라 프레임 1장 유실이 곧 지령 소실이었다.
- **원인**: ① `_wait_settle` 이 `self._meas_deg` 를 시각 없이 읽음(`gui.py:1007`)
  ② `controlWrite(0xf3)` 가 `with self._can_lock:` 앞에 있었음(`gui.py:1026`)
  ③ `_drive()` 가 1회 쓰고 끝, 재송신·워치독 코드 0건(`gui.py:851-854`).
  나머지 8건은 `docs/code_review/amr-test-gui/2026-08-03.md` §평가 참조.
- **해결**: ① `_set_meas` 단일 기록지점 + `MEAS_TTL_S` ② 심박을 락 안으로
  ③ 폴 루프 주기 재송신(0 포함) + **응답 끊김** 워치독(`RX_TTL_S`) — 「지령 만료」 방식은
  조그가 스스로 꺼지므로 쓰지 않았다 ④ `STEER_HOME` 을 정본 YAML 에서 런타임 로드
  ⑤ `SEER_GUI_PATH` 환경변수 ⑥ 판다 2대 이상 차단 ⑦ 반환 시 정지 실패 고지
  ⑧ 폴링 사망 시 제어권 표시 내림 ⑨ `RLock` 단일 임계구역 ⑩ `panda is None` 가드
  ⑪ 로그 경로 단일화. 같은 수정을 `can_relay/ui/backend_direct.py` 에도 반영.
- **검증**: 원본 시험 **88 → 111 passed**(신규 23건, High 3건은 **변이 주입으로 검출력 확인** —
  수정을 되돌리면 각각 3·2·3건 실패). `can_relay` **342 passed** 무회귀,
  `colcon build` 통과, 양쪽 백엔드 오프스크린 기동·SIGTERM 정상. **실기 검증 0.**
- **파일**: `Tools/amr_test_gui/gui.py` · `test/{test_settle_freshness,test_usb_serialization,
  test_drive_resend,test_medium_fixes}.py` · `src/Comm/CAN/can_relay/can_relay/ui/{backend_direct,app}.py` ·
  `test/test_steer_home_sync.py`(사본 규칙을 fallback 기준으로 갱신) ·
  `docs/code_review/amr-test-gui/2026-08-03.md`
- **상태**: 완료

## 2026-08-03

### [Fix] can_relay 노드가 호밍 중 취소·정지를 못 받는다 + 심박이 USB 핸들을 경합한다 (High 2건)

- **문제**: ① `~/home` 이 도는 동안(최대 180 s) `~/home_cancel`·`~/stop`·`estop` 이 **하나도 처리되지 않았다.**
  「진행 중 취소는 `~/home_cancel` 로 한다」는 계약이 정작 **호밍 중에만** 성립하지 않았다.
  ② 제어 스레드의 심박(`0xf3`)과 서비스 스레드의 호밍 조회(`0xeb`)·명령(`0xea`)이 **같은 USB 핸들에서 겹칠 수 있었다.**
  심박 실패는 펌웨어 fail-safe(구동 0 + 릴레이 개방)를 부르므로 주행 중 예고 없는 정지로 이어진다.
- **원인**: ① `driver_node.py:414` 가 `rclpy.spin(node)`(단일 스레드 실행기)이고 콜백 그룹 지정이 0건이라
  4개 서비스가 전부 같은 상호배타 그룹이었다. `~/home` 콜백은 `backend.py:570-588` 폴링 루프에서
  terminal 이나 `timeout_s`(기본 180.0, `backend.py:528`)까지 반환하지 않는다.
  ② `link.py:428-432` `heartbeat` 만 `self._lock` 밖이었다. `send`(`:443`)·`recv`(`:450`)·`can_health`(`:467`)·
  `_homing_cmd`(`:502`)·`homing_status`(`:511`)는 락 안이었다. 호밍 시퀀서 도입 전에는 USB 접근이
  제어 스레드 하나뿐이라 문제가 되지 않았고(`link.py:32-33` 이 그 전제를 적어 둠), 그 전제가 깨진 것을
  놓쳤다.
- **해결**: 콜백 그룹 3분리(`_cbg_home` / `_cbg_safety` / `_cbg_engage`) + `main()` 을 `MultiThreadedExecutor`
  로 교체(둘이 한 쌍 — 하나만으로는 안 막힌다). `PandaLink._ctrl()` 이 락을 직접 잡도록 하고 `Lock`→`RLock`
  (heartbeat 한 곳만 감싸지 않은 이유: `acquire`/`release`/`_rollback` 도 같은 핸들을 쓴다).
  덧붙여 심박 중단 카운터를 송신 전용으로 좁혔다(`_tx_fail_streak` ↔ 신규 `_loop_fail_streak`) — 수신 쪽
  일시 오류가 로봇을 세우면서 원인은 "송신 실패"로 표시되던 것. 4파일 소수 라인 + 신규 회귀 3파일.
- **검증**: **수정 전 재현 6건 실패**(취소 서비스 5 s 무응답 · 같은 핸들 동시 전송 2건 관측, 실패 경로 187 s).
  수정 후 `230 passed`(ROS2 소싱, 노드 회귀 3건 포함) / `227 passed, 1 skipped`(미소싱) /
  `colcon build --packages-select can_relay` Finished 3.01s. 실기 검증 0(장치 접속·플래시·실모터 구동 없음).
- **파일**: `src/Comm/CAN/can_relay/can_relay/driver_node.py` · `.../link.py` · `.../backend.py` ·
  `.../protocol.py`(존치 근거 주석) · 신규 `test/test_node_concurrency.py` · `test/test_link_concurrency.py` ·
  `test/test_backend_method35.py` · `docs/adr/2026-08-03-can-relay-node-concurrency.md`
- **상태**: 완료

### [Fix] 「호밍이 안 된다」 진단이 10회 실측으로 반증 — 하루에 세운 원인 가설 3개가 전부 뒤집혔다

- **문제**: 2026-08-03 09:58 호밍 1회가 120 s 소모 후 `ERR_TIMEOUT` 으로 끝난 것을 **「호밍이 실패한다」로
  일반화**하고, 하루 동안 원인 가설을 세 번 세워 그때마다 **「확정」이라 문서에 기록**했다. 15:33~15:40
  `orin_home_experiment.py --repeat 10` 실측 결과 **호밍은 10/10 성공**(소요 **35.0 s**, 편차 0.17 s,
  리밋 도달 10회 모두 DI `0x01`→`0x09`)했다. 09:58 이후로 보면 **12회 연속 성공**이며 실패는
  **재현되지 않는다**. ⇒ 고칠 대상이 애초에 없었고, 내가 세운 진단 3건이 전부 틀렸다.
  > ❌ **재정정 2026-08-03 17:00 (원자료 `Log/*.json*` 직접 파싱).**
  > · **[E1]** 「12회 연속 성공」 → **12회 연속 성공**. 오늘 시도 **13** / 성공 **12** / 실패 **1**
  >   (성공 12 = 15:33 런 10회 + 14:46 `homing_edge_260803_144602.json` +
  >   15:25 `homing_edge_260803_152520.json`; 실패 1 = 09:58 `final_state` 6 = `ERR_TIMEOUT`).
  >   「13」은 15:33 요약의 `baseline` 을 성공 1건으로 더한 것인데, `baseline` 은 **호밍이 아니라
  >   레지스터 스냅샷**이다(`Tools/docking_field_kit/orin_home_experiment.py:390` `snapshot()`).
  > · **[E4]** 「35.0 s」 → **평균 35.068 · 중앙 35.045 s**(범위 34.99~35.16, 폭 0.17 은 정확).
  > · **「10/10 성공」·「가설 3건이 뒤집혔다」는 결론은 그대로 유효.**
  뒤집힌 가설: ① 「`0x6040=0x86` 이라 CiA402 `Switch on disabled` 를 못 벗어나 막힌다」
  ② 「`0x6098`=0 이라 호밍 비활성 / RstStart 가 1 로 고착」 ③ 「축이 이미 홈이면 드라이브가 무동작
  즉시 완료 → `bit15` 하강 에지 미발생 → WAIT 검출기 영구 대기」.
- **원인**: 기전은 펌웨어가 아니라 **내 추론 절차**였다. (a) **단일 관측을 원인으로 승격** — ①은
  09:58 한 회차의 statusword 만 보고 단정했고, 2026-07-27 **성공** 캡처가 **같은 `0x?050`** 에서
  성공한 반례를 나중에야 확인했다. ②는 실측 없이 추정한 값이었다(실측은 `0x6098`=**1**,
  `0x60FB:04`=**0**). (b) **대조군 없이 두 변수를 동시에 바꿈** — 14:46 실험은 「조향 +10° 오프셋」과
  「11:38 리부팅으로 `0x6064` 래치 해제」가 함께 바뀐 상태였는데 **오프셋만 원인으로 귀속**해 ③을
  「확정」이라 적었다. `--offset 0` 대조군을 같이 돌렸으면 바로 갈렸다. (c) **관측 2점의 상관을
  실질 원인으로 승격** — 15:25 에 debt-036(`0x6064`=0)을 「호밍을 막는 실질 원인」으로 올렸으나,
  근거는 09:58 실패 / 15:25 성공 **2점**뿐이었다. 관련 코드 위치는
  `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:391-402`(WAIT 에지 검출)이며
  **이 로직에는 실증된 결함이 없다** — 10회 모두 정상 완료했다.
- **해결**: 코드 변경 **0줄**(펌웨어·드라이버 무수정). **반복 실측으로 진단을 대체**하고 기록을
  정정했다 — ① `orin_home_experiment.py --repeat 10` 을 접지 상태에서 실행해 10회 전수 기록
  (산출 `Log/home_experiment_260803_153319.jsonl` 10.3 MB · `_summary.json`).
  ② `docs/homing/2026-08-03-can-relay-homing-assets.md` 에 **§0(최종 확정)** 을 신설하고 §15·§16 을
  폐기 표기. ③ `docs/debt/registry.md` 를 정정 — debt-034 근거 보강 · debt-035 사유를 **「원인 미상 ·
  우선순위 낮음」으로 환원** · debt-036 **「호밍을 막는다」 단정 철회 및 우선순위 하향**,
  표 3행 인라인 정정 + 기존 절 3곳에 정정 배너 + **신규 확정 절 1개(59줄)**.
  원문은 **한 줄도 지우지 않고** 「❌ 정정 2026-08-03 15:40」 표기로 인접 배치했다.
  ⚠ 펌웨어에 앞서 추가했던 「이미 홈」 종료 조건(`SEER_HOME_ATHOME_S` · `seer_home_athome_mask`)은
  **되돌리지 않되 보험으로만 존치**한다 — 10회 실측에서 **발동조차 하지 않았고**, 필요성이 미확인이므로
  **「09:58 실패를 고쳤다」고 주장하지 않는다**(무해함만 실증됨).
- **파일**: `docs/debt/registry.md`(debt-034/035/036 표 3행 + 기존 절 3곳 + 신규 절 `:524-582`) ·
  `docs/issues_and_fixes/issues_and_fixes.md`(본 entry + 아래 「조향 0° counts 정정」 entry 인라인 정정) ·
  `docs/homing/2026-08-03-can-relay-homing-assets.md`(§0 정본) ·
  산출 `Log/home_experiment_260803_153319.jsonl` · `Log/home_experiment_260803_153319_summary.json`
- **상태**: 완료 — 실측 근거: 호밍 **10/10 DONE**, 소요 34.99~35.16 s, 정착값 node3 **7,882,021**(σ 2.8 c) ·
  node4 **7,859,065**(σ 3.2 c) ⇒ 조향 0° `[7871815, 7840086]` 대비 **+0.178° / +0.331°**, counts/°
  **57,344**(실측 기울기 1.000000), `0x6098`=**1**, 리밋 스위치 **실재**(10회 DI 전이 관측).
  펌웨어 `DEV-cc5e0491-DEBUG`, 호밍속도 2500.
  > ❌ **재정정 2026-08-03 17:00.**
  > · **[E6]** σ 2.80 / 3.21 은 **모표준편차** 기준(표본 σ 2.95 / 3.38) — 기준을 병기할 것.
  >   10회 `post` 실측: node3 7,882,021 **×8** / 7,882,014 **×2**, node4 7,859,065 **×8** / 7,859,058 **×2**.
  > · **[E5]** 「counts/° 57,344 (기울기 1.000000)」 → **node3 57,344.0 / node4 57,344.3**
  >   (`Log/steer_two_phase_260803_131305.jsonl` phase A 최소제곱 57,344.000 / 57,344.280).
  > · **[E8]** 조향 0° `[7871815, 7840086]` 은 정본(`foil_a082.yaml:134`)이라 **값 유지**하되
  >   **「공학적 채택값」**으로만 서술할 것 — 「실측 확정」 표현 금지(아래 재정정 참조).
- **확정된 부수 사실**: 정착 편차 +0.178°/+0.331° 는 **σ ≈ 3 counts(0.00005°) 로 10회 재현** ⇒
  **결함이 아니라 설계 동작**이다(호밍은 조향을 0° 가 아니라 이 지점에 놓는다 — debt-034 는
  「이름·허용오차」 부채로 유지). `ERR_TIMEOUT` 은 깔끔한 terminal 이라 **재시도로 충분** ⇒
  **운영상 이슈가 아니다.**
  > ❌ **재정정 2026-08-03 17:00. [E7]** 「**결함이 아니라 설계 동작**」은 **과잉 확정**이다.
  > 실측이 보증하는 것은 **「펌웨어 상수 `SEER_HOME_ZERO_N3/N4`
  > (`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:212-213`)에 재현성 있게
  > 정착한다」**까지다(편차 node3 +1×8 / −6×2 · node4 +3×8 / −4×2, 최대 6 counts).
  > **상수의 적정성은 실측 밖**이고 **debt-016** 이 같은 편차를 「영구 미검출 오프셋」으로
  > 등록 중이라 **정면 충돌**한다.
  > ⇒ **「재현되는 정착 동작(상수 적정성은 별건, debt-016)」**로 읽을 것.
- **미결**: (a) 09:58 `ERR_TIMEOUT` 1회의 **원인은 미상**이다 — 재현되지 않아 추적 우선순위 낮음(debt-035).
  (b) `0x6064`=0(bit15=1 동반)은 **1회 관측·재현 없음**, 인과 방향 미판정(debt-036).
  > ✅ **종결 2026-08-03 19:45 — debt-036.** 원인은 **아침에 드라이브가 죽어 있던 것**이다(`Log/home_experiment_260803_095815.jsonl` 에 node1 `BOOTUP` 1건 · 오후 캡처엔 0건 · SDO abort 0건 · 재기동 후 미재현). 「인과 미판정」 서술은 해소됐다.
  > ❌ **재정정 2026-08-03 17:00: (b) 의 「1회 관측·재현 없음」은 거짓 — 재현된다. [E2]**
  > `0x6064:00` SDO 응답 전수 집계(0 / 전체): 09:19 `home_experiment_260803_091956.jsonl`
  > **50/50 · 50/50** · 09:58 `…_095815.jsonl` **12,220/12,220 · 12,211/12,211** ·
  > 10:08 `seer_homing_260803_100813.jsonl` **10,327/10,327 · 10,327/10,327**
  > (같은 구간 `0x6041`=37968 **bit15=1** 258표본/노드 전량 = **호밍 중이 아닌데도 0**) ·
  > 11:38 리부팅 **이후** `probe_113805.jsonl` 97/1,300 · 96/1,299 ·
  > 14:43 `homing_edge_260803_144305_can.jsonl` 2/74 · 2/68.
  > ⚠ **「인과 방향 미판정」은 유지**되며, 오히려 **양쪽 다 미판정**이다 —
  > 0 이 관측된 14:43 직후의 14:46 호밍은 **성공**했으므로 「`0x6064`=0 이 호밍을 막는다」도
  > 성립하지 않는다. debt-036 의 서술도 「1회 관측」이 아니라 **「재현되나 인과 미판정」**으로 읽을 것.
  > ⚠ **「호밍 중(bit15=0)이면 `0x6064`=0」은 별개의 유효 관측**이다
  > (15:33 런 node3 **32,243/32,243**). 폐기된 것은 **「전원 사이클 래치」주장뿐**이다.
  (c) **조향 0° 는 Seer 좌표계 기준**이며 **물리적 직진과 같은지는 미확인**이다 — Seer 1005·1040 은
  **둘 다 `0x6064` 유래**라 독립 앵커가 아니다. 非-Seer 계측이 필요하다.

### [Fix] CCTV 표시 CPU 과다 — 퍼블리셔 디코드·raw 전송 제거(MJPEG 패스스루 + 웹 뷰어)

- **문제**: 사용자 제기 "cctvview CPU 점유율이 매우 높다". 실측 기준선(`Log/usb_cctv_run_2026-07-30/
  soak_samples.csv` 표본 1,330개 중앙값) 퍼블리셔 6개 **138.1%** + Qt 뷰어 **71.9%** = **210.0%**.
- **원인**: [실측] 비용의 본체가 렌더가 아니라 **디코드·전송**이었다. 퍼블리셔가 카메라 MJPEG 를
  디코드해 `bgr8` raw 로 발행하여 프레임이 2,700 KB 가 되고, 6대 30fps 면 약 498 MB/s 가 DDS 를
  통과했다. 1대 8초x2회 벤치: **디코드 6.55 ms·2,700 KB/frame vs 패스스루 0.15 ms·131 KB/frame**
  — CPU 44배·대역 20.7배 차이. 종전 기록의 "카운트 전용 구독자도 CPU 55%" 가 같은 사실을 가리켰다.
- **해결**: ① 퍼블리셔에 `publish_mode`(compressed 기본/raw/both) 신설 — `CAP_PROP_CONVERT_RGB=0`
  으로 드라이버 압축 버퍼를 받아 `CompressedImage` 로 그대로 발행(디코드·재인코딩 없음).
  ② `cctv_webview` 패키지 신설 — 압축 바이트를 **디코드 없이** multipart MJPEG 로 서빙, 브라우저가
  디코드. ③ 탐지기를 압축 구독으로 전환해 **추론하는 프레임만** 디코드(30 Hz 전량 → 실제 약 5 Hz).
  선행 확인: UVC JPEG 에 DHT 포함·`imdecode` 성공·버퍼 패딩 0%(30/30) — 브라우저가 읽는 정상 JPEG.
- **파일**: `src/Sensors/Camera/USB/usb_cam_publisher/src/usb_cam_publisher_node.cpp` ·
  `.../launch/usb_cam_cctv.launch.py` · `config/camera/camera_common.yaml` ·
  `src/Sensors/Camera/USB/ui/cctv_webview/**`(신설) · `src/AI/yolo_detector/yolo_detector/detector_node.py` ·
  `Tools/usb_cam_bench/soak_stats.py`·`test_soak_stats.py` ·
  `docs/adr/2026-08-03-mjpeg-passthrough-web-viewer.md`(신설)
- **상태**: 완료 — 실기 검증(카메라 6대). 캡처 29.70~29.73 fps·grab_failures 0,
  `/snapshot/<cam>` HTTP 200 image/jpeg 정상 이미지, `/stream/<cam>` 6개 동시 각 **정확히 10.0 fps**
  (총 60 fps·8.11 MB/s), 검출 `/cam_rr/detections` **4.99 Hz**·변환 실패 0.
  **표시 경로 CPU 210.0% → 47.9%**(퍼블리셔 25.0 + 웹 22.9, `/proc` jiffies 8초 차분).
  단위 시험 `cctv_webview` 11 passed · `soak_stats` 15 passed.
- **부수 수정**: 퍼블리셔 FPS 로그에 `decode_failures` 를 덧붙이면서 `soak_stats` 정규식이
  `(grab_failures=N)` 의 **닫는 괄호까지 고정**돼 깨질 상태였다 — 요구를 없애고 회귀 시험 추가.
- **미결**: 웹 스트림에 인증이 없고 `bind` 기본이 `0.0.0.0` 이다(같은 망 누구나 접속).

### [Change] 웹 뷰어를 차량 배치로 놓고 AI 검출 표시 추가

- **문제**: 웹 화면이 로스터 순서(`RF LF RR / F R LR`)로 흘러 어느 방향 카메라인지 화면만 보고
  알 수 없었다. 또 AI 검출 결과가 Qt 뷰어에만 표시되고 웹에는 없었다.
- **원인**: 격자가 `auto-fit` 흐름 배치였고, 웹 뷰어는 검출 토픽을 구독하지 않았다.
- **해결**: ① 여섯 위치가 모두 있으면 **차량을 위에서 내려다본 배치**(전면 위 · 좌측 왼쪽 ·
  후면 아래, 가운데는 차체 표시)로 놓고, 구성이 다르면 흐름 배치로 물러난다 — 위치를 모르는
  카메라를 임의 자리에 놓으면 방향을 오독하므로 배치를 주장하지 않는다.
  ② `/cam_*/detections` 를 구독해 `/detections` JSON 으로 좌표만 넘기고 **박스는 브라우저가
  그린다**(서버 디코드 0 유지). 나이 기준은 Qt 뷰어와 동일(신선/낡음/만료).
- **파일**: `src/Sensors/Camera/USB/ui/cctv_webview/cctv_webview/{server,frame_store,app}.py` ·
  `.../test/test_frame_store.py` · `.../README.md` · `docs/adr/2026-08-03-mjpeg-passthrough-web-viewer.md`
- **상태**: 완료 — 브라우저 실화면 확인. `/detections` 6대 응답(당시 `cam_r` 사람 2명 검출),
  단위 시험 **18 passed**. **후속 정정 1건**: 가운데 열을 `0.5fr` 로 좁혀 전면·후면 타일만
  절반 크기가 되는 것을 사용자가 지적 → `repeat(3,1fr)` 로 세 열 동일 폭 수정, 재확인 완료.
- **미결**: 타일 6개가 세로로 길어 1080p 창에서 후면 R 이 스크롤 아래로 내려간다(뷰포트 높이
  맞춤 축소 미구현). Qt 뷰어는 **사용자 결정으로 유지**(폐기하지 않음).

### [Fix] Orbbec SDK 종료 후 카메라가 V4L2 로 돌아오지 않음

- **문제**: RGB-D 스택(`surround_depth`)을 정상 종료했는데 `/dev/video*` 가 **0개**,
  `/sys/class/video4linux` 도 비어 USB CCTV 스택을 띄울 수 없었다. `lsusb` 에는 6대 모두 보였다.
- **원인**: Orbbec SDK 가 libusb 로 쓰려고 커널 드라이버를 뗀 뒤 종료 시 되돌리지 않았다.
  `uvcvideo` 는 RGB 인터페이스 6개에 바인딩된 상태였으나 비디오 장치를 하나도 등록하지 않았다.
- **해결**: `sudo modprobe -r uvcvideo && sudo modprobe uvcvideo` → **6/6 복구**.
  비-root 수단은 모두 막혀 있다(`/sys/bus/usb/drivers/uvcvideo/unbind` 쓰기 불가,
  `/dev/bus/usb/*` 가 root 소유라 `usbreset` 불가, `uhubctl` 미설치).
- **파일**: (코드 변경 없음)
- **상태**: 복구 절차 확인 완료. RGB-D 스택과 CCTV 스택을 번갈아 쓸 때마다 필요하다.

### [Fix] 조향 0° counts 정정 — raw 판독값이 0° 로 채택돼 있었다

> ❌ **정정 2026-08-03 15:40: 본 entry 의 「근거」 2건이 뒤집혔다. 결론값은 유지된다.**
> ✅ **결론값 `[7871815, 7840086]` 은 그대로 유효**하다 — 15:40 의 10회 실측에서도 조향 0° 정본으로 재확인됐다
> (`docs/homing/2026-08-03-can-relay-homing-assets.md` §0-3). `7882020 / 7859062` 가 0° 가 아니라
> **호밍 후 정착값**이고 편차가 **+0.178° / +0.331°** 라는 서술도 **10회 재현으로 굳어졌다**(§0-2).
> ❌ **뒤집힌 근거 ①** — **원인** 절의 「판다 SILENT · passthrough ⇒ **CAN 과 Seer 가 독립 경로**」는
> 성립하지 않는다. Seer **1005 · 1040 은 둘 다 `0x6064` 유래**(아핀 변환)이므로 **독립 앵커가 아니고**,
> 이 둘의 일치를 **교차검증으로 인용할 수 없다**. ⇒ 확정된 것은 **「Seer 가 0° 라 부르는 자세 ↔ CAN counts」
> 의 대응**뿐이며, **물리적 직진과 같은지는 여전히 미확인**이다(非-Seer 계측 필요).
> ❌ **뒤집힌 근거 ②** — **상태** 절의 「**회귀 319건 통과**」는 값의 정확성을 검증하지 **않는다**.
> 변이 시험에서 `steer_home_counts` 값을 바꿔도 **319건이 전부 통과**했다(§11-3 F1).
> ⇒ 값 검증의 근거는 **실측뿐**이며, 회귀 건수를 값 근거로 인용 금지.
> (아래 원문은 이력으로 보존한다.)

- **문제**: 조향 0° 정본 `steer_home_counts` 가 `[7871810, 7839894]` 로 박혀 있었으나, 2026-08-03 실측
  0° 는 **node3 7,871,816 / node4 7,840,087** 이다. node4 가 **193 counts** 어긋난다(node3 은 6 counts).
  같은 날 2026-08-02 에 「틀린 값이 아니라 **출처 없는 값**」이라며 폐기 선언했던 구값 `[7871815, 7840086]`
  이 **양 노드 모두 1 count(0.000017°) 이내로 맞았다.** ⚠ 193 counts = **0.0034°** — **거동상 무의미**하며
  안전 문제가 아니라 **정본 정확성** 문제다.
- **원인**: 0° 는 raw CAN 판독값이 아니라 Seer 각도로 역산해야 한다(`0° = CAN_0x6064 + Seer_deg × 57344`).
  2026-08-02 종결 문서가 **이 식을 §4-2 에 적어 놓고도 §1 채택값에는 적용하지 않고 raw 판독값을 그대로
  0° 로 박았다** — `docs/verified_facts/2026-08-02-steer-home-closed.md` §1 ↔ §4-2 (자기 모순).
  node3 은 그 시점 Seer 각도가 작아 오차가 6c 에 그쳐 드러나지 않았고, **node4 에서 193c 로 드러났다.**
  실측 근거: `docs/homing/2026-08-03-can-relay-homing-assets.md:375-425`(§10).
  측정 조건 — `Tools/docking_field_kit/orin_steer_crosscheck.py`, 판다 **SILENT · passthrough**(제어권
  미취득 ⇒ ~~CAN 과 Seer 가 독립 경로~~ **← 2026-08-06 반증, 인용 금지**), **송신 0건**(AST 구문트리 검사), **사용자 확인 「Seer 표시 앞바퀴
  2축 모두 0°」** 자세, 2회 독립 실행이 counts 단위까지 동일(node3 7,871,823c σ=3 / node4 7,840,052c σ=2,
  각 n=3,110). 산출물 `Log/steer_xcheck_reboot_0deg.jsonl` · `Log/steer_xcheck_reboot_0deg_confirm.jsonl`.
- **해결**: `steer_home_counts`(및 `steer_home_offset`) 값을 `[7871810, 7839894]` → **`[7871815, 7840086]`**
  로 되돌리고, 각 지점에 「══ 정정 2026-08-03 ══」 주석 블록을 인접 배치(원문 이력 보존). 정본 1곳 + 사본
  6곳의 **상수 정의 각 1줄 수정 + 정정 주석 블록 추가**, 테스트 픽스처는 값이 이미 구값이라 **라벨만 정정**.
  ⚠ `7882020 / 7859062` 는 **펌웨어 GOZERO 상수**(`SEER_HOME_ZERO_N3/N4`, 호밍 후 정착 목표)이며 0° 가
  아니다 — **본 정정 범위 밖의 별개 사안**이다. 0° 가 바뀐 만큼 편차만 재계산해 **+0.178° / +0.331°**
  (node3 +10,204 c / node4 +18,975 c)로 병기한다(→ **debt-034** 신규 등록).
- **파일**:
  - 정본 `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml:100,119,133,136`
  - 사본 `src/Actuators/motor_control/config/tongyi_amr.yaml:25,39` ·
    `src/Actuators/motor_control/motor_control/driver_node.py:70` ·
    `Tools/amr_test_gui/gui.py:31,45` · `Tools/Kinematics/chassis_kinematics.py:64,78` ·
    `Tools/docking_field_kit/docking_drive.py:63,77` · `Tools/docking_field_kit/amap2_monitor.py:100,114`
  - 테스트 픽스처 `src/Comm/CAN/can_relay/test/{test_safety,test_protocol,test_backend}.py` ·
    `Tools/Kinematics/tests/test_can_protocol.py`
  - 기록 `docs/homing/2026-08-03-can-relay-homing-assets.md`(§10 신설) · 본 파일 머리말 배너 ·
    `docs/debt/registry.md`(debt-007·016·022 정정, debt-034~036 신규)
- **상태**: 완료 — 회귀 **319건 통과**(`can_relay` 177 · `motor_control` 35 · `amr_test_gui` 88 ·
  `Kinematics` 19). 실기 재확인 2회(위 측정 조건), 송신 0건 읽기 전용.

## 2026-08-02

### 조향 홈이 저장소 곳곳에 흩어져 「기록으로 오판」하는 구조를 닫음 (debt-007 종결) ← ❌ **2026-08-03 재정정 (채택값 폐기)**

> ❌ **정정 2026-08-03**: 본 entry 의 **채택값 `[7871810, 7839894]` 과 「구값은 출처 없는 값」 판정은 반증됐다.**
> 실측 0° 는 node3 **7,871,816** / node4 **7,840,087** 이고, 폐기 선언했던 구값 `[7871815, 7840086]` 이
> **양 노드 1 count 이내로 맞다**(본 entry 채택값은 node4 에서 193c = **0.0034°**, 거동상 무의미).
> 원인은 역산식 `0° = CAN + Seer°×57344` 를 채택값에 적용하지 않고 **raw 판독값을 0° 로 박은 것**이다.
> 구값의 **출처도 있다** — Seer 의 실시간 `0x607A` 조향 목표.
> 아래 원문은 이력으로 보존한다. 상세는 위 「2026-08-03 [Fix] 조향 0° counts 정정」 및
> `docs/homing/2026-08-03-can-relay-homing-assets.md` §10.
> ✅ 본 entry 의 나머지(정본 일원화 · `DEFAULT_STEER_HOME = {}` 로 코드 기본값 제거 · `7882020/7859062` 는
> 홈이 아니라 정착값 · rclpy `dynamic_typing` 함정)는 **그대로 유효하다.**

- **증상**: 홈 재측정·재호밍 실험이 세션마다 반복됐다. 원인은 하드웨어가 아니라 **기록**이었다 —
  같은 물리량에 4개 값이 돌아다녔고(`7871815`/`7840086` 31파일, `7882020`/`7859062` 23파일,
  실측값은 2파일), 정본이 어느 것인지 문서로 확정된 적이 없어 매번 처음부터 다시 쟀다.
- **진단**: 값들끼리 실제로 얼마나 다른지 계산한 적이 없었던 것이 핵심이다. 재보니
    (⚠ **2026-08-06 삭제** — 이 대목은 폐기값 `[7871810, 7839894]` 을 「실측」이라 단정하고 「구값은 출처 없는 값」이라 판정했다. 둘 다 반증됐다: 정본은 **`[7871815, 7840086]`**, 구값의 출처는 **Seer 가 실시간으로 내는 `0x607A` 조향 목표**다.)
  진짜로 다른 것은 `7882020`/`7859062`(호밍 후 정착 목표, +0.178°/+0.331°)로, 이쪽이 「0°」로
  오인되면 조향에 상시 바이어스가 생긴다.
- **진실 기준**: 같은 자세를 **intercept off** 로 읽은 세 경로가 일치했다 —
  2026-07-27 콜드부팅 캡처(7,871,818/7,840,084) · 2026-08-01 판다 SILENT 수동청취(7,871,810/7,839,894) ·
  동시각 Seer API 1040(+0.0001°/+0.0035°). 4일·전원 인가·플래시 8회를 사이에 두고 8c/190c 재현.
- **조치**:
  1. 정본을 `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml` **하나**로 고정.
  2. **코드 기본값 제거** — `safety.DEFAULT_STEER_HOME = {}`. 값이 없으면 `UnsafeCommand` 로 거부하고,
     `driver_node` 는 아예 기동하지 않는다. 「조용한 오판」보다 정지를 택했다.
  3. 실행 자산 7곳의 구값을 실측값으로 갱신(+ 「미판정·값 변경 금지」 주석을 해소 서술로 교체, 원문 보존).
  4. `homing_method` 를 `"firmware"` 로 확정하고 ADR 을 **Superseded in part** 로 표기.
- **검증**: `can_relay` 176 passed · `motor_control` 35 passed · `Kinematics` 19 passed.
  mock 기동 2종 — 캘리브레이션 로드 시 정상 기동(홈 `[7871810, 7839894]` 반영 확인),
  미로드 시 기동 거부 메시지 확인.
- **부수 발견 (rclpy 함정)**: 「미설정」을 빈 배열로 표현하면 rclpy 가 타입을 **`BYTE_ARRAY`** 로 추론해
  YAML 의 정수 배열 로드를 **거부**한다. `ParameterDescriptor(type=...)` 지정만으로는 안 되고
  (Humble 이 기본값 타입으로 덮어씀) **`dynamic_typing=True`** 가 필요하다. 실기 기동 실패로 확인.
- **바로잡은 내 오류**: 「제어권 보유 중 판다 read 오염(emulate)」을 원인으로 적으려다 펌웨어를 열어
  확인하니 틀렸다 — `emulate` 는 **bus 라우팅만** 바꾸고 PC 자신의 수신 경로는 건드리지 않는다
  (`safety_seer_gate.h:164-193`). 남는 유력 후보는 `0x6041` bit15=0 구간의 `0x6064`=0 고정이나,
  당시 statusword 로그가 없어 **확정이 아니다**.
- **남은 것**: 「Seer 의 0°」와 물리적 직진의 일치는 육안 미확인 — 스티어링 중립 산출은 사용자 별도 진행.
  `motor_control` 의 「미설정 = 0」은 타 세션 소유라 값 갱신까지만 하고 **debt-032** 로 등록.

## 2026-08-01

### [Change] can_relay 계층 이동 — `cmd_vel` → `/motor/low_cmd` (모터 계층)

- **문제**: 신설 드라이버가 `cmd_vel`(Twist)을 구독해 **체인의 어느 노드와도 연결되지
  않았다**(2026-07-31-004). 저장소 모션 스택의 실제 계약은
  `액션서버 ─WheelSetArray→ mux ─→ translator ─MotorCmdArray→ /motor/low_cmd` 다.
  부작용으로 축별 조향각 1.0° 편차 게이트가 들어가 **최소 선회반경 68.8 m** 를 강제했고
  액션 서버 9종 중 6종의 지령이 전부 거부됐다.
- **원인**: 계층을 잘못 잡았다. `cmd_vel` 을 구독한다는 것은 "차체 속도를 휠 지령으로
  바꾸는 계층"이라는 선언인데, 그 변환은 이미 액션 서버(IK)와 translator(SI→raw)가
  소유한다. `MotorCmd.msg` 가 명시한다 — "Units are raw device units — **NOT SI**",
  "Produced by motor_cmd_translator, consumed by canopen_motor_driver".
- **해결**:
  - 구독 `/motor/low_cmd`(`trnav_msgs/MotorCmdArray`) · 발행 `/motor/low_state`
    (`trnav_msgs/MotorStateArray`). QoS 는 체인과 같은 RELIABLE·KeepLast(10)·VOLATILE.
  - `cmd_vel` 구독 · `motor_control.kinematics` 대여 · **1.0° 편차 게이트 제거**.
    선회는 기능 추가가 아니라 **계층 하강으로** 해소된다 —
    `qd_bicycle_model.hpp:24` `omega = vx(tan δf − tan δr)/L` 이므로 전·후 각이 다른 것이
    회전의 정의다.
  - 환산·기구학을 **하지 않는다**. 받은 raw 를 그대로 `0x60FF`/`0x607A` 로 낸다.
  - **안전은 raw 단위로 유지** — 조향 위치를 홈 기준 ±`steer_limit_deg` 를 counts 로
    환산해 클램프, 구동 속도 ±`vel_max_units`, 호밍 미완료 시 조향 거부, 워치독 동일.
  - 메시지를 자체 정의하지 않고 `trnav_msgs` 를 빌린다(`trnav_2ws_msgs` 중복 폐기 선례).
    import 실패 시 조용히 대체하지 않고 저수준 경로를 **열지 않는다**.
  - `package.xml`: `motor_control`·`geometry_msgs` 의존 제거, `trnav_msgs` 추가.
- **파일**: `can_relay/backend.py`(`set_motor_cmds`·`motor_states` 신설) ·
  `can_relay/driver_node.py` · `package.xml` · `test/test_backend.py`
- **상태**: 완료 — 회귀 **155 passed**(147 → +8), `colcon build` 통과.
  실제 `ros2 launch` + `ros2 node info` 로 계약 확인:
  `/motor/low_cmd: trnav_msgs/msg/MotorCmdArray`(구독) ·
  `/motor/low_state: trnav_msgs/msg/MotorStateArray`(발행).
  **선회 지령이 통과함을 회귀로 고정**(`test_low_cmd_accepts_differential_steer_angles` —
  전·후 조향각이 다르게 CAN 으로 나가는 것까지 확인).
  ⚠ 실기 검증 0 · 체인 전체 연동 미실행(상류 mux·translator 와 함께 띄운 적 없음).
- **참고**: `docs/adr/2026-07-31-can-relay-cpp-motor-layer.md`(타 세션, Proposed)는 같은
  계층 이동을 **C++ 포팅**으로 제안한다. 본 변경은 Python 현행본에 계층만 적용한 것이며
  C++ 포팅을 막지 않는다(안전 계층·판다 계약이 그대로 이식 대상으로 남는다).

### [Diag] 조향 절대위치 교차검증 도구 신설 — 3톤 차체 잭업 없이 측정하는 경로

- **문제**: `homing_method: 35` 는 "전원 재투입 후 절대 엔코더 재현"을 전제하는데
  미측정이다(debt-007 상환계획 ②). 사용자 제약: **AMR 이 3톤이라 잭업이 어렵다.**
- **정리(제가 앞서 뭉뚱그린 부분)**: 두 시험은 성격이 다르다.
  **재현성 측정은 바퀴를 움직이지 않으므로 잭업이 불필요**하다(전원 차단→재투입→읽기).
  잭업이 필요한 것은 137° 스윙이 나는 **호밍 완주 시험**뿐이다.
- **사용자 착안**: Seer API 로 조향값을 읽어 검증. **확인 결과 이미 구현돼 있었다** —
  `Tools/amr_test_gui/gui.py` `_seer_loop` 가 `cli.call("status", 1040)` 으로
  `motor_info[].position`(rad)을 받고 `_on_seer_data` 가 `× 180/π` 로 도 변환한다.
  주석도 "네트워크 읽기 전용. 제어권과 무관하다"로 명시. `RobokitClient` 경로 실재 확인.
- **⚠ 핵심 발견 — 제어권을 잡으면 이 교차검증이 무의미해진다**:
  펌웨어가 `bool emulate = cover || pc_authority;`(`safety_seer_gate.h:164`)로 제어권
  획득 시 **자동으로 emulate** 에 들어간다. emulate 중에는 모터의 SDO 응답
  (`0x581~0x584`)과 guard 가 **Seer 로 전달되지 않고**(`bus_fwd = -1`, `:188-190`)
  판다 캐시가 대신 답한다(`seer_cache_reply` `:167-172`). 전환 순간도 `cover` 가 덮는다.
  ⇒ 제어권을 쥔 채 Seer 1040 을 읽으면 **모터 실측이 아니라 판다 캐시**를 보는 것이라,
  CAN 과 값이 같아도 "같은 출처를 두 번 읽은 것"일 뿐이다.
  **이 관점은 debt-007 의 미판정 관측을 재검토하게 만든다** — 그 관측 시점에 판다가
  제어권을 쥐고 있었다면 "Seer 1040 ≈ 0" 은 독립 관측이 아니었을 수 있다.
- **해결**: `Tools/docking_field_kit/orin_steer_crosscheck.py` 신설(읽기 전용).
  - 판다 **SAFETY_SILENT 탭** — `main.c:85` 가 `can_silent = ALL_CAN_SILENT`,
    `set_intercept_relay(false)`(= passthrough, Seer↔모터 직결 유지).
    SDO 읽기 요청조차 보내지 않고 **Seer 가 이미 ~100 Hz 로 폴하는 응답을 엿듣는다.**
  - Seer 1040 을 병행 폴링해 같은 시각의 두 값을 JSONL 로 기록.
  - `--compare` 가 전원 사이클 전후를 대조해 CAN ±1000c / Seer ±0.05° 로 판정.
  - **`steer_home_offset` 을 호밍 없이 역산**한다 —
    `offset = 현재_counts − Seer각[도] × 57344`. 137° 스윙이 필요 없다.
  - 런타임 가드: `safety_mode == 30`(제어권 보유 가능성)이면 **실행 거부**.
- **구현 중 자체 결함 3건**(전부 검증 과정에서 드러나 수정):
  - 문서에 적은 감사 명령이 **자기 docstring 을 매치**해 "0건"이 거짓이 됐다 →
    구문 트리(AST) 기반 명령으로 교체하고 실제로 실행해 0건 재현 확인.
  - S6 게이트가 "송신 자체가 불가능하다"는 **근거 없는 절대형 단정**을 잡아냈다 →
    확인 범위(`can_silent` 플래그까지)로 좁히고 펌웨어 줄번호를 병기.
  - 비교 시 파일 부재에 역추적이 떴다 → 명확한 안내 + exit 2.
- **파일**: `Tools/docking_field_kit/orin_steer_crosscheck.py`(신설)
- **상태**: 완료(도구) — 합성 데이터로 3경로 검증: 재현 O `exit 0` · 재현 X `exit 2`
  (Seer 는 0° 라는데 CAN 이 137° 점프하는 기준 리셋 서명을 잡아냄) · 파일부재 `exit 2`.
  AST 기준 **송신 호출 0건**, S6 게이트 FAIL 0, `can_relay` 회귀 147 passed(영향 없음).
  ⚠ **실기 미실행** — 판다·Seer 접속 없이 로직만 검증했다.

### [Change] 조향 홈을 장비별 캘리브레이션으로 일반화 — homing method 35 (상류식)

- **문제**: 같은 조향 홈 값이 **세 곳에 박혀 있고 값도 서로 달랐다**.
  판다 펌웨어 `safety_seer_gate.h:212-213`(`7882020`/`7859062`, **컴파일 상수**) ·
  translator `..._qd.yaml:26-27`(`-1.676°`) · can_relay `safety.py:32`(`7871815`/`7840086`).
  장비를 바꾸면 펌웨어 **재빌드·재플래시**가 필요했다.
- **원인**: 홈을 "값"으로 다뤘다. 홈은 **호밍 절차의 산출물**이라 장비마다 다른 게 정상인데,
  값으로 취급하니 코드에 박히고 세 곳으로 번졌다.
- **상류 대조(2026-08-01, 원문 확인)**: `kuks2309/TR_Nav_ros2_ws` 의
  `amr_canopen_motor_driver` 는 이 일반화가 **이미 되어 있다** —
  `steer_home_offset_front/rear` 가 **드라이버 YAML 파라미터**(`amr_canopen_motor_driver.yaml:14-15`).
  절차는 `0x607A=home_offset` → 도착확인(bit10 ∧ `|fb_pos−offset|<50`) → `SDO 0x6098=35`
  (`can_open.hpp:483-489,461`). `target_pos` 는 가공 없이 `0x607A` 로 나간다(절대 raw).
- **매뉴얼 근거(1차)**: Handbook V7.0 §Home 35 — "records the current motor position as the
  home position, **sets the current angle to zero**", "**only effective when the motor is
  powered on**". ⇒ ① 호밍 후 `0x6064 ≈ 0` 이 직진이라 **홈 상수가 코드에서 사라진다**
  ② **전원 사이클마다 재호밍 필수**.
- **해결**:
  - 장비별 캘리브레이션 YAML 신설 `config/machine/foil_a082.yaml`(13키). 상류 이름을 계승하되
    상류가 **코드에 박아 둔** 두 가지를 파라미터로 올렸다 — 조향 한계(상류 `can_open.hpp:463`
    하드코딩 ±130°)와 호밍 방식(상류 코드 고정 35).
  - `homing_method: "35" | "firmware"` — 방식이 장비마다 다르므로 선택 가능. 2026-08-01 에
    구현한 판다 시퀀서 경로는 대안으로 **존치**한다.
  - `safety.DEFAULT_STEER_HOME` 을 `{3:0, 4:0}` 으로 — **debt-026 상환**.
  - 스케일(`steer_counts_per_deg`·`drive_units_per_mmps`·`drive_max_units`)도 캘리브레이션으로
    이관. ⚠ 상류 QD(Carrier AGV) 값 48,332.8 counts/도는 우리 실측 57,344 와 다르다.
  - **미측정 전제를 코드가 검출한다** — D안은 "전원 재투입 후 절대 엔코더 재현"을 전제하는데
    이는 debt-007 상환계획 ②로 **아직 측정되지 않았다**. `home_search_range` 밖이면 **바퀴가
    움직이기 전에** 거부하고, `homing_enabled: false` 가 기본이며, 호밍 완료 전 조향 지령을
    전부 막는다(상류 `home_comp` 와 같은 역할).
- **파일**: `config/machine/foil_a082.yaml`(신설) · `can_relay/protocol.py`(`home35_*` 3함수) ·
  `can_relay/safety.py` · `can_relay/backend.py` · `can_relay/driver_node.py` ·
  `launch/can_relay.launch.py` · `setup.py` · `test/test_backend.py`
- **상태**: 완료(설계·구현) — 회귀 **147 passed**(138 → +9), `colcon build` 통과.
  실제 `ros2 launch` 로 캘리브레이션 로드 확인(`기체 'Foil_A082' · 호밍 35 (활성=False)`,
  `steer_home_offset=[7871815, 7840086]`, `steer_counts_per_deg=57344.0`).
  게이트 실동작 확인: 호밍 전 조향 지령 거부 · 비활성 시 `0x607A` 송신 **0건**.
  ⚠ **실기 검증 0** — ADR §검증 게이트 4항 미통과. 특히 **절대 엔코더 재현성 측정**이
  통과해야 `homing_method: 35` 를 지면에서 쓸 수 있다.
- **근거 ADR**: `docs/adr/2026-08-01-can-relay-home-calibration-method35.md`

### [Fix] can_relay ↔ 판다 펌웨어 연동 3건 — 호밍 취소 경로 신설 · 버스 헬스 진단 · 라이브러리 사본 폴백

- **문제**: 신설 드라이버 `src/Comm/CAN/can_relay` 가 `Tools/Can_Relay/` 펌웨어의 기능 중
  셋을 쓰지 않고 있었다.
  - ① panda 파이썬 라이브러리를 `Tools/docking_field_kit` 한 곳에서만 가져와, 그 사본이
    없는 환경에서는 기동이 불가능했다.
  - ② **호밍 시작 후 소프트 중단 수단이 없었다.** `0x60FB:04=1` 을 SDO(Service Data Object)로
    직접 보내면 드라이브 내부 루틴이 시작돼 하드웨어 E-STOP 외에는 멈출 방법이 없다.
  - ③ CAN 버스 에러 상태를 관측하지 않아, 버스가 error-passive·bus-off 로 떨어져도
    지령이 나가는 것처럼 보였다.
- **원인**: 펌웨어가 제공하는 벤더 요청 3종을 미사용 — 확인 `grep -c '0xea\|0xeb\|0xc3'
  src/Comm/CAN/can_relay/can_relay/` → 0건. 펌웨어 쪽 구현은 실재한다:
  `board/usb_comms.h:411-427`(`0xea`/`0xeb`), `:223-225`(`0xc3`),
  `board/safety/safety_seer_gate.h:307-309` `seer_home_cancel_frames()`,
  `board/health.h:29-37` `can_health_t`.
  > ❌ **재정정 2026-08-03 17:00: 줄 범위가 틀렸다. [E9]**
  > `seer_home_cancel_frames()` 는 `board/safety/safety_seer_gate.h` **:312-316** 이다.
  > **:307-311 은 `seer_home_digital_in()`** 으로 다른 함수다
  > (헤더 직접 확인 — `grep -n` 결과 `:307` `static uint8_t seer_home_digital_in`,
  > `:312` `static void seer_home_cancel_frames`).
- **해결**:
  - ① `link.py` `_PANDA_SOURCES` — `docking_field_kit`(상위집합, `can_health` 보유) 우선,
    없으면 `Can_Relay/panda-firmware/python` 으로 폴백. 둘 다 없으면 사유를 모아 `LinkError`.
  - ② `home()` 을 **펌웨어 시퀀서 전용**으로 교체하고 `cancel_home()`·`~/home_cancel`
    서비스 신설. **폴백을 두지 않는다** — 시퀀서를 못 쓰면 실패로 보고하고 SDO 직접 송신으로
    내려가지 않는다(덜 안전한 경로로 미끄러지는 것이 tech-debt-shortcut).
  - ③ `_poll_bus_health()`(1 Hz) + `bus_fault()` + `diagnostics` 노출. `bus_off` >
    `error_passive` > `error_warning` 우선순위로 ERROR 승격.
  - 순수 디코더 `decode_can_health()`·`decode_homing_status()` 로 바이트 계약을 분리해
    하드웨어 없이 고정.
- **구현 중 발견해 함께 고친 결함 2건**:
  - **일시적 실패의 영구 래치** — 헬스 폴링이 첫 실패에 영구 비활성됐다. 노드 smoke 에서
    드러났다(픽스처가 늦게 붙자 영영 꺼짐). 기능 부재(`NotImplementedError`)만 영구 비활성,
    그 외 예외는 재시도하고 사유가 바뀔 때만 로그하도록 분리.
  - **낡은 서술 3곳** — "본 구현에는 취소 경로가 없다"가 구현 후에도 남아 있었다.
    S6 게이트가 1곳, grep 이 2곳을 잡았다.
- **파일**: `can_relay/link.py` · `can_relay/backend.py` · `can_relay/driver_node.py` ·
  `config/can_relay.yaml` · `README.md` · `test/test_link.py`(신설 21건) · `test/test_backend.py`
- **상태**: 완료 — 회귀 **138 passed**(84 → +54), `colcon build` 통과, S6 selftest 10/10 ·
  대상 전수 FAIL 0. 노드 mock 실행으로 ②③ 경로 확인: `bus2 error-passive (REC=140 TEC=12)` 가
  ERROR 로 승격, 호밍 `WAIT → 취소 → ERR_ABORT`, 직접 SDO `0x60FB` 송신 **0건**.
  ⚠ **실기 검증 0** — 장치 접속·모터 구동 없음. 판다 실기에서 `0xea`/`0xeb`/`0xc3` 왕복은
  미확인이며, 이는 debt-027(브링업 미검증)과 같은 잭업 시험에서 함께 확인해야 한다.

## 2026-07-30

### [Change] 카메라 이름을 장착 위치 기준으로 개명 + 로스터를 안 읽던 결합 3곳 수정

- **문제**: 카메라 6대가 `cam0`~`cam5`(발견 순서)로 이름 붙어 토픽·로그·화면에서 어느 방향
  카메라인지 알 수 없었다. 사용자가 장착 위치별 시리얼 표를 확정(2026-07-30)하고 **토픽명까지
  위치 기준 개명**을 지시했다.
- **원인**: 이름이 로스터(`config/camera/camera_common.yaml`)에서 파생되지만, **로스터를 읽지
  않고 이름 형식을 가정한 곳이 3곳** 있어 개명이 조용히 깨질 상태였다.
  - `src/AI/yolo_detector/yolo_detector/detector_node.py:38`
    `DEFAULT_TOPICS = [f"/cam{i}/image_raw" for i in range(6)]` 이고 `detect.launch.py` 가
    `camera_topics` 를 넘기지 않았다 → 개명 후 **에러 없이 검출 0**(없는 토픽 구독).
  - `Tools/usb_cam_bench/soak_stats.py` 로그 파서 정규식이 `cam\d+` 가정.
  - `Tools/usb_cam_bench/soak_monitor.py` 가 `cam{i}` 로 CSV 열 이름을 생성 → 전 열 공란.
- **해결**: 로스터 `name` 6개를 위치 코드로 개명(`cam_rf`·`cam_lf`·`cam_rr`·`cam_f`·`cam_r`·`cam_lr`).
  **순서는 바꾸지 않았다** — 그리드 순서 정렬은 사용자 결정으로 향후 별건.
  결합 3곳은 로스터를 읽도록 수정: `detect.launch.py` 에 로스터 탐색 + `camera_topics` 전달,
  파서 정규식을 `[A-Za-z0-9_]+` 로 일반화, `soak_monitor.camera_names()` 신설(로스터 우선 ·
  `--cameras` 명시 가능 · 미발견 시 경고 후 종전 관례). 뷰어 fallback 토픽도 새 이름으로 갱신.
  ADR: `docs/adr/2026-07-30-camera-position-naming.md`(Rollback Plan 포함).
- **파일**: `config/camera/camera_common.yaml` · `src/AI/yolo_detector/launch/detect.launch.py` ·
  `src/Sensors/Camera/USB/ui/vision_guard/launch/vision_guard.launch.py` ·
  `Tools/usb_cam_bench/soak_stats.py` · `Tools/usb_cam_bench/soak_monitor.py` ·
  `Tools/usb_cam_bench/test_soak_stats.py`(회귀 2건 추가)
- **상태**: 완료 — 실기 재기동 검증(2026-07-30 22:14~22:18).
  토픽 `/cam_{rf,lf,rr,f,r,lr}/image_raw` 6개 · 검출 `/cam_*/detections` 6개 발행,
  퍼블리셔 로그의 device by-id 대조로 **이름↔시리얼 6/6 일치**, 캡처 전 카메라 29.70~29.71 fps
  `grab_failures=0`, 뷰어 `6/6 cameras shown`(화면 캡처 확인), 표시 8.7~10.0 fps,
  모니터 CSV 열이 `cam_rf_capture_fps` 형식으로 생성되고 값 채워짐. 테스트 14 passed.
- **미확인**: 사용자가 2026-07-28 보고한 **cam1·cam5(현 `cam_lf`·`cam_lr`) 검은 줄무늬**는
  현재 야간·소등 상태로 화면 전체가 어두워 **판정 불가**. 조명 있는 조건에서 재확인 필요.
  퍼블리셔는 기동 시 `power_line_frequency=2`(60Hz)·`exposure auto-priority` 해제를 적용했다고
  로그에 남긴다(`Log/usb_cctv_run_2026-07-30/pub.log`). 장치 실제 컨트롤 값 직접 판독은
  `v4l2-ctl` 미설치로 하지 못했다.

---

## 2026-07-29

### [Fix] 패키지 안에 중첩 colcon 워크스페이스 생성 + 테스트가 환경 소싱 없이는 미실행

- **문제**: ① `src/Comm/CAN/can_relay/` 안에 `build/`·`install/`·`log/` 가 생겨 **중첩
  워크스페이스**가 됐다(412 KB). ② 테스트가 `PYTHONPATH=.` 또는 `source install/setup.bash`
  없이는 `ModuleNotFoundError: No module named 'can_relay'` 로 수집 단계에서 죽었다.
- **원인**: ① Bash 작업 디렉터리가 호출 간 유지되는데, 패키지 디렉터리로 `cd` 한 상태에서
  `colcon build` 를 실행했다(`src/Comm/CAN/can_relay/log/build_2026-07-29_14-02-35/…/command.log`
  가 그 경로에서 invoke 됐음을 기록). ② `test/` 에 경로 부트스트랩이 없었다 — 저장소 선례
  `src/Actuators/motor_control/test/test_protocol.py:5-8` 은 각 파일에서 `sys.path.insert` 를
  한다.
- **해결**: ① 세 디렉터리 삭제(git 추적 0건, 루트 워크스페이스에 정본 산출물 별도 존재 확인 후).
  ② `test/conftest.py` 신설(11줄) — 파일마다 3줄을 반복하는 대신 한 곳에 모았다.
- **파일**: `src/Comm/CAN/can_relay/test/conftest.py`(신설) · 산출물 디렉터리 3개 삭제
- **상태**: 완료 — 세 실행 방식 전부 확인: 저장소 루트·환경 미소싱 **84 passed** / 패키지
  디렉터리 **84 passed** / 설치 환경 소싱 **84 passed**. 재빌드 후 중첩 산출물 재발 **0건**.

### [Fix] 「호밍은 소프트웨어가 멈출 수 없다」 과장 서술 3곳 — S6 게이트가 검출

- **문제**: 오늘 신설한 `can_relay` 의 docstring 3곳이 "호밍은 시작하면 소프트웨어가 멈출 수
  없다(드라이브 내부 루틴)" 고 단정했다. 운전자가 **중단 수단이 원리적으로 없다**고 읽게 되는
  서술이다.
- **원인**: 원문 대조 없이 `Tools/amr_test_gui/gui.py:921-922` 의 확인 대화상자 문구
  ("이 **프로그램이** 중간에 멈출 수 없습니다")를 **범위를 넓혀** 옮겼다. 실제로는
  `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:307-309`
  `seer_home_cancel_frames()` 가 `0x60FB:04 = 0`(호밍 중단)을 송신하는 경로가 **실재**하며,
  USB `0xea` wValue=0 으로 기동된다. 즉 "불가능"이 아니라 **본 구현이 그 경로를 안 쓰는 것**이다.
  > ❌ **재정정 2026-08-03 17:00: 줄 범위만 정정(경로 실재라는 결론은 불변). [E9]**
  > `seer_home_cancel_frames()` 는 같은 헤더 **:312-316** 이다.
  > **:307-311 은 `seer_home_digital_in()`** 으로 다른 함수다(헤더 직접 확인).
- **해결**: 3곳을 "불가능" → "본 구현에 취소 경로가 없다(미구현)" 으로 정정하고 펌웨어 경로를
  `파일:줄` 로 병기(각 3~6줄). 주장 범위를 구현 단위로 좁힌 것이 핵심이다.
- **파일**: `src/Comm/CAN/can_relay/can_relay/backend.py`(모듈 docstring · `home()`) ·
  `src/Comm/CAN/can_relay/can_relay/driver_node.py`
- **상태**: 완료 — 검출 경로가 자동이었다는 점이 중요하다. 같은 날 추가한 S6 게이트
  (`review-claim-lint.py`)가 **도입 직후 전수 검사에서 이 3곳을 잡았다**. 사람이 다시 읽어서
  찾은 것이 아니다. 재검사 `TOTAL FAIL 0건 — PASS`, 회귀 `84 passed`.

### [Fix] review-claim-lint 에 S6 추가 + 검사 대상을 소스 주석까지 확대

- **문제**: 검증 명령 없는 절대형 부정 단정이 반복 재발하는데 기계 검사가 없었다
  (`docs/claude-mistake/2026-07-28-005`, `2026-07-29-003`). 기존 lint 는 S1~S5 뿐이고 검사
  대상도 `docs/code_review/*.md` 로 한정돼 **소스 주석·docstring 이 사각지대**였다.
- **원인**: `docs/claude_guideline/code_review/checks/review-claim-lint.py` 의 검사 항목 부재.
- **해결**: S6(절대형 부정 ↔ 근거 병기) 추가, `.md` 는 S1~S6 / 그 외는 S6 만 적용.
  설계 조정 3건은 **전부 실측으로 확정**했다 — ① 근거 인정 범위를 리뷰 SOP 룰 8 과 동일하게
  (도구 호출·결과 **또는** `파일:줄` 인용): 전자만 인정했더니 기존 통과 산출물
  `docs/code_review/can_relay_firmware/2026-07-28.md` 에 신규 FAIL 3건이 생겼고 원문 대조 결과
  **3건 전부 오탐**이었다. ② 일반형 "할 수 없다"·"알 수 없다" 제외 — 인용된 사실에서 끌어낸
  결과 서술이라 오탐이 된다(`docs/code_review/trnav-icp-odometry/2026-07-28.md:256` 실측).
  ③ 따옴표 쌍 매칭 수정 — `"된다" 만 … "안 된다·불가능하다"` 에서 짝이 어긋나 인용 안의
  부정을 놓쳤다(`docs/claude-mistake/INDEX.md:64` 오탐). 인용 **밖** 부정은 계속 잡는다.
  게이트 자체 회귀 `--selftest` 10건을 인라인 픽스처로 내장했다(S4 가 금지하는 절대경로 없이
  저장소에서 재현 가능).
- **파일**: `docs/claude_guideline/code_review/checks/review-claim-lint.py` ·
  `docs/claude_guideline/code_review/review.md`(VERSION 1.3.0 → 1.4.0, 자체 점검 8-1 추가)
- **상태**: 완료 — `--selftest` **10/10 PASS**, 저장소 리뷰 산출물 6종 + 오늘 산출물 + 소스
  전수 `TOTAL FAIL 0건 — PASS`. 사용자 승인 2026-07-29(SSOT 번들 §변경 절차).

### [Fix] can_relay 신설 중 자체 결함 3건 + 검증 명령 없는 부정형 단정 2곳

> 대상은 **오늘 신설한** `src/Comm/CAN/can_relay` 다. 기존 코드에서 발견한 결함
> (조향 클램프 부재·NaN·단발 송신·피드백 신선도)은 **이번에 고치지 않았고** 부채로 등록했다
> (debt-015~019) — 소유 세션이 다르거나 실기 검증이 선행돼야 하기 때문이다.

- **문제**:
  - ① 신설 테스트 2건 FAIL — `test_write_controlword_exact`,
    `test_write_fault_reset_enable` 이 `AssertionError: '2b4060003f000000' == '2b40603f00000000'`.
  - ② `ros2 launch` 시 파라미터 미로드 위험 — config YAML 첫 줄이 `_#` 로 시작해 주석이 아닌
    스칼라로 파싱된다.
  - ③ 제어권 반환 후 종료 시 오류 로그 2줄
    (`LinkError: 제어권 없이 프레임을 보내려 했다`)이 매번 출력. 기능은 정상이나 정지 실패로
    오독될 수 있는 노이즈.
  - ④ 부정형 단정에 확인 명령 미병기 — "gui.py 에는 이 시퀀스가 없다"를 근거 명령 없이 서술.
    이 저장소가 반복해 당한 실패 유형이다(`docs/claude-mistake/2026-07-28-005`).
- **원인**:
  - ① 기대 hex 를 원본 대조 없이 작성 — SDO(Service Data Object) 프레임 배치는
    `[cmd, idx_lo, idx_hi, **sub**, payload…]` 인데 **sub 바이트를 빠뜨린** 기대값을 썼다.
    코드가 맞고 테스트가 틀린 경우다 — 근거 `Tools/amr_test_gui/gui.py:833`.
  - ② 파일 작성 시 오타 — `config/can_relay.yaml:1`.
  - ③ `backend.stop()`·`shutdown()` 이 링크 제어권 상태를 보지 않고 무조건 송신을 시도 —
    `src/Comm/CAN/can_relay/can_relay/backend.py` `stop()`. 노드 종료 경로가
    `~/engage false` 와 겹쳐 이미 반환된 링크에 다시 쐈다.
  - ④ `protocol.py` `drive_init_frames` docstring · `config/can_relay.yaml` 주석.
- **해결**:
  - ① 기대값을 실제 배치로 정정(2줄). **코드는 바꾸지 않았다** — 인코더 28종이 실측 캡처
    `Log/homing_capture_220350.jsonl` 과 바이트 동일함을 별도 대조로 확인했다(12,958건 일치).
  - ② `_#` → `#` (1줄).
  - ③ `stop()`·`shutdown()` 에 `if self.link.engaged:` 가드 + `shutdown()` 멱등화(9줄 추가).
    지령 자체(속도 0)는 제어권과 무관하게 **항상 확정**되도록 유지 — 정지가 거부되면 안 된다.
    회귀 2건 추가(`test_stop_target_is_zero_even_without_authority`,
    `test_shutdown_is_idempotent`).
  - ④ 실행한 grep 과 결과(0건)를 인라인 병기하고 **주장의 범위 한계**까지 명시
    ("gui.py 가 controlword 를 아예 안 쓰는 것은 아니다 — `gui.py:942` 는 조향축 호밍 전용")(10줄).
- **파일**: `src/Comm/CAN/can_relay/test/test_protocol.py` ·
  `src/Comm/CAN/can_relay/config/can_relay.yaml` ·
  `src/Comm/CAN/can_relay/can_relay/backend.py` ·
  `src/Comm/CAN/can_relay/can_relay/protocol.py` ·
  `src/Comm/CAN/can_relay/test/test_backend.py`
- **상태**: 완료 — `PYTHONPATH=. python3 -m pytest test -q` → **84 passed in 1.64s**,
  `colcon build --packages-select can_relay` → **1 package finished [3.08s]**,
  YAML 파싱 확인 → 파라미터 20개 로드. ④ 는 `docs/claude-mistake/2026-07-29-003` 에 별도 기록
  (강제 메커니즘 S6 적용으로 `status: closed`. 미채택 항목은 debt-020 으로 이관).

## 2026-07-28

### [Fix] 조향 슬라이더가 먹통 — 실측 되먹임 + 78×20 px 크기

- **문제**: `앞뒤 바퀴 조정` 슬라이더를 움직여도 눈금이 제자리로 돌아오고 조향 지령이
  나가지 않았다. 같은 세션에서 조그 구동(`0x60FF`)은 정상 동작해 조향만 안 되는 비대칭이었다.
- **원인**: 두 결함이 겹쳤다.
  - ① **실측 되먹임** — `_redraw_wheel` 이 실측 각도를 슬라이더에 되썼다
    (`Tools/amr_test_gui/gui.py` 구 `_sync_sliders`). 폴링이 약 5 Hz 라 손을 뗀 뒤 0.2 초 안에
    눈금이 원위치로 튕겼다. 슬라이더는 사용자가 **목표를 넣는 명령 입력**인데 거기에 실측을
    되먹여 방금 넣은 값을 지웠다. 또 마우스 드래그가 아닌 조작(키보드·홈 클릭)은
    `sliderReleased` 가 오지 않아 **지령이 아예 나가지 않았다**.
  - ② **크기** (실제 원인) — 슬라이더가 **78×20 px** 이었다. 범위 ±90°(181 단계)이므로
    **1 px = 2.3°**, 핸들은 10 px 남짓이라 잡을 수 없었다. `앞뒤 바퀴 조정` 그룹 348 px 중
    이름 라벨 108 px · 값 라벨 144 px 가 차지하고 슬라이더에 78 px 만 남는 배치였다.
    실측 병기를 넣으며 값 라벨 폭을 46 → 120 으로 올린 것이 결정타였으나, 근본은
    **이름·슬라이더·값을 한 줄에 나란히 놓은 배치**다.
- **해결**:
  - `_sync_sliders` 삭제(20 줄). `_redraw_wheel` 은 그림만 그린다. 목표·실측은
    `_update_wheel_labels` 가 `+30°  (실측 +12.3°)` 로 나란히 보여준다.
  - 슬라이더 배선을 축별로 분리 — 드래그는 `sliderReleased` 로 1 회, 키보드·홈 클릭은
    `valueChanged` 에서 즉시 송신(`_on_wheel_changed` → `_send_steer`).
  - 레이아웃 재구성 — 슬라이더가 **자기 줄을 통째로** 쓴다. 이름·값은 위 줄에 좌우 배치.
    결과 **324×30 px**(1 px = 0.56°), `pageStep=5`.
  - 진단 계측 — `log()` 를 stdout 에도 흘리고, 버리던 SDO abort(`0x80`) 응답을 사유와 함께
    로그에 남긴다. **CAN 송신은 한 줄도 추가하지 않았다.**
- **파일**: `Tools/amr_test_gui/gui.py` · `Tools/amr_test_gui/test/test_slider.py`(신설 12건)
- **상태**: 완료 — 실기 검증(2026-07-28 21:06). 로그 `조향 지령 N4 → -34°` · `N3 → +19°`,
  판다 직독 실측 `3 F.S +18.9°` · `4 R.S -34.0°` 로 추종 확인. 테스트 88 건 통과.

## 2026-07-28

### [Fix] CCTV 뷰어·탐지기 조용한 결함 3건 (적대적 설계 검토 파생)

> ⚠ **후속 정정 (2026-07-29 감사)**
> - **③ 은 무효(superseded)** — 2026-07-29 구조 변경으로 주석 영상 발행 경로 자체가 삭제됐다
>   (`publish_annotated`·`_render()`·`/camN/detections/image` 전부). 따라서 "게이팅으로 비용
>   제거" 라는 해결도, 그 검증도 **현재 코드에서 재현 불가**하다. 아래 ③ 항은 당시 코드에
>   대한 기록이다. 현재는 탐지기가 결과만 발행하고 표시는 GUI 소관이다.
> - **① · ② 는 지금도 유효**하며 코드에 존재한다(`check_stale`, `_last_report_frames.clear()`).
> - **테스트 수 갱신** — "vision_guard 25 passed(기존 13 + 신규 12)" 는 2026-07-28 시점 값이다.
>   2026-07-29 오버레이 도입 후 **50 passed**(frame_convert 7 · layouts 7 · overlay 25 ·
>   stale_detection 11). "신규 12" 는 실제 11, "기존 13" 은 실제 14 였다.
> - **인용 줄 번호 4건 전부 dangling** — `main_window.py` 가 두 차례 대폭 이동했다. 아래
>   `:94`·`:131-133`·`:97`·`:174`·`:233` 은 **2026-07-28 시점 기준**이며 현재 파일과 맞지 않는다.
>   심볼 기준으로 읽을 것: `CameraCell.update_frame()` 의 `_fps` EMA / `_frames_rendered` 초기화 /
>   `MainWindow._last_report_frames` / `_report_display_stats()` 의 `delta == 0`.
> - ADR 참조 `§2 (F6/F9/F8)` 중 **F8 은 무효**(주석 발행 삭제로 전제 소멸). F6·F9 는 유효.

- **문제**: ① 뷰어에서 프레임이 끊겨도 헤더가 **마지막 FPS 를 영원히 표시**하고 `_pixmap` 도 지워지지
  않아 **정지 화면이 라이브처럼 보였다**(감시 기능의 조용한 실패). ② 레이아웃 변경 후 **정지 경고가
  영구히 나가지 않았다**. ③ 탐지기가 주석 영상 구독자가 **0인데도** 프레임당 약 2.8 MB 를 두 번
  복사해 27 Hz 로 발행하며 추론 예산을 깎았다.
- **원인**:
  - ① `_fps` 는 `update_frame` 안에서만 갱신되고 **0 으로 감쇠하는 경로가 없다** —
    `vision_guard/main_window.py:94,131-133`.
  - ② 새 셀은 `_frames_rendered = 0` 으로 시작(`main_window.py:97`)하는데 `_last_report_frames` 는
    초기화되지 않아(`:174`) `delta = 0 - 이전누적` 이 **음수**가 되고, `delta == 0` 정지 검사(`:233`)를
    통과하지 못했다.
  - ③ `publish_annotated` 는 기동 파라미터일 뿐 구독자 유무를 보지 않았다 —
    `yolo_detector/detector_node.py` 주석 발행 블록.
- **해결**:
  - ① `_STALE_AFTER_S = 2.0` + `CameraCell.check_stale()` 추가, `_pump()` 이 매 틱 호출. 강등 시
    `_fps = 0.0` + 헤더 `신호 없음`. 프레임 복귀 시 자동 해제. (약 30줄 추가)
  - ② `_apply_layout()` 에서 `_last_report_frames.clear()`. (1줄 + 주석)
  - ③ 발행 조건에 `get_subscription_count() > 0` 추가 — 파라미터는 유지하고 비용만 제거. (1줄 + 주석)
- **파일**: `src/Sensors/Camera/USB/ui/vision_guard/vision_guard/main_window.py`,
  `src/Sensors/Camera/USB/ui/vision_guard/test/test_stale_detection.py`(신규 12 테스트),
  `src/AI/yolo_detector/yolo_detector/detector_node.py`
- **상태**: 완료 — vision_guard 25 passed(기존 13 + 신규 12), yolo_detector 23 passed.
  ③ 은 실행 검증: 구독자 0 → 주석 발행 없음(`Subscription count: 0`, 박스 토픽은 4.36 Hz 정상),
  구독자 부착 → 4.85 Hz 로 즉시 재개. 근거·경위는
  [ADR 2026-07-28-cctv-ai-overlay-toggle](../adr/2026-07-28-cctv-ai-overlay-toggle.md) §2 (F6/F9/F8).

### [Fix] 호밍 기록의 잘못된 서술 정정 + 정오표 수립 (2회 적대적 검증)

- **문제**: 2026-07-27 호밍 조사에서 생성된 기록 다수가 (a) `0x6041` bit15 **전이 시각**을 폴 상한값으로
  확정형 서술 (b) `Tool/`(단수) 경로 인용 (c) `0x6040` 반복률 「~50 Hz」 (d) 호밍 중 write 정지 범위를
  조향축으로 과소 서술 — 로 부정확했다. 더해 **정정하려고 만든 정오표(v1) 자체가 신규 오류 7건을 심었다**
  (정확한 Handbook 인용을 「오진」으로 규정 등).
- **원인**: ① 폴링 관측값을 이벤트 시각으로 취급(직전 폴 간격 미확인) — `Log/homing_capture_220350.jsonl`
  node3 `0x6041` 최대 폴 간격 12.818 s ② 한 노드 결과를 전 노드로 일반화 ③ v1 작성 시 원문 재대조 없이
  기억·요약에 의존해 **정확한 인용을 틀렸다고 판정**(자기 표와 모순).
- **해결**: 원문(`pdftotext -f N -l N`) 재대조로 쪽 사실을 확정하고 v2 정오표로 전면 개정.
  저장소 잔여 서술 11건 정정(전이 시각 → 「0 최초 관측」 + 확정 구간 병기, `Tool/`→`Tools/`),
  `docs/debt/registry.md:146` 의 `0x6040=0x86` 「enable」 오라벨을 「fault reset(+enable voltage)」로 정정
  (Bit7 rising edge = Fault Reset, `Enable Operation`(0x0F) 아님).
  미해결 항목은 **debt-008**(Handbook 1차 source 내부 DI 번호 충돌)·**debt-009**(캡처 출처·12.62 s
  무응답 구간 미확정)로 등록.
- **검증**: 40 에이전트 적대적 재검증(wf_83c55976-efe) → v1 작성 → **10 에이전트가 v1 을 공격**
  (wf_ea102b6e-a7c, 비-CONFIRMED 51건·신규오류 7건 검출) → v2. 각 레인이 캡처를 직접 재파싱하고
  PDF 를 각자 재추출. 이전 실패 레인(`cap-digital-in`) 재수행 완료.
- **파일**: `docs/verified_facts/2026-07-28-errata.md`(신규 v2), `docs/debt/registry.md`,
  `docs/verified_facts/2026-07-27.md`, `docs/ros2_driver/2026-07-09-design-inputs.md`,
  `References/Tongyi-Motor-Controller/docs/tongyi-motor-protocol-tables.md`,
  `References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md`,
  `Tools/docking_field_kit/amap2_monitor.py`, `Tools/docking_field_kit/HANDOFF-amap2.md`
- **상태**: 완료 (미해결분은 debt-008·debt-009 로 이관)

---

## 2026-07-27

### [Fix] 로봇 단독 전원 인가 시 Seer CAN/모터 알람 지속 — 판다 부팅 기본 비트레이트 500 kbps

- **문제**: 호스트 소프트웨어를 **하나도 실행하지 않은 채** 전원만 인가하면 Seer 가 `52106 odo data lost` + `52111 motor driver connection error` + `54022 CAN1 Bit Recessive error`(10 초마다 타임스탬프 갱신 = 진행 중) + `54301 Motor is calibrating` 을 지속 발생. 판다 health 는 `safety_mode=0`·`power_save=1`·`car_harness_status=1`·`faults=0`.
- **원인**: 세 가지가 겹침 — ① `Tools/Can_Relay/panda-firmware/board/drivers/harness.h:91` `set_intercept_relay(false)`("keep busses connected by default")로 **릴레이가 버스를 물리 연결**(Seer↔모터 직결, 펌웨어 포워딩 무관) ② `board/main.c:405-406` `can_silent = ALL_CAN_LIVE` + 루프마다 `enable_can_transceivers(true)` 로 **판다가 그 버스에 live 로 부착** ③ `board/drivers/can_common.h:164-166` `.can_speed = 5000U` = **500 kbps**(버스는 250 kbps). 단위 근거: `usb_comms.h:322` 가 `wIndex` 를 그대로 저장, `panda/python/__init__.py:550` 이 `speed*10` 송신. ⇒ 250k 버스에 500k 로 붙은 live 노드가 전 프레임을 오독해 에러 프레임을 방출, 버스 파괴. **호스트 도구가 take() 에서 `set_can_speed_kbps(b,250)` 을 부르기 때문에 지금까지 가려져 있었다**(= PC 가 붙어야만 버스가 성립하는 구조).
- **해결**: `bus_config[]` 의 bus0/1/2 `can_speed` `5000U`→`2500U`(250 kbps). 함께 ① heartbeat 상실 블록(`main.c`)에 `set_intercept_relay(false)` + `pc_authority = false` 추가 — 이상 상태에서 릴레이가 intercept 로 남지 않도록(fail-open, 사용자 요구) ② `safety/safety_seer_gate.h` freeze 집합에 `0x6041` 추가(Seer SDO 폴 12초 실측으로 확정: `0x6064` 2718~2920회·`0x6041` 66~312회·`0x6078` 66회, **`0x606C` 0회 = 미폴**). 총 3 파일 소수 라인.
- **파일**: `Tools/Can_Relay/panda-firmware/board/drivers/can_common.h`, `.../board/main.c`, `.../board/safety/safety_seer_gate.h`, `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md`(신규)
- **상태**: 완료 — 빌드 `-Werror` 0 error → 플래시 → **비트레이트 미설정 상태로** 8초 29,625 프레임 수신(부팅 기본 250 kbps 확정) · Seer `errors=[]` 21초+ 유지 · `rx_errs=0 faults=0` · 현장 육안 확인("오류 안남"). ⚠ 펌웨어 version 문자열은 상위 레포 HEAD 에서 오므로(`panda-firmware` 자체 .git 없음) 커밋 전 빌드는 신구 구분 불가 — 현재 플래시본은 `DEV-d98bc1a5-DEBUG` 표기이나 내용은 본 수정 반영본이다.

> ### ⚠ [2026-07-27 감사 부기] 위 entry 의 미검증·미판정 표시 (원문 무변경 · 값/코드 무변경)
>
> **(1) "상태: 완료" 를 변경 단위로 분리** — 이 entry 의 변경은 3건인데(① `can_speed` 5000U→2500U · ② heartbeat fail-open · ③ `0x6041` freeze 추가) 인용된 증거는 전부 ① 에 대한 것뿐이다.
> - **① 비트레이트 정합 = 실측 검증 완료** (증거 상동: 비트레이트 미설정 상태 8초 29,625 프레임 · Seer `errors=[]` 21초+ · `rx_errs=0 faults=0`). 코드 반영 확인: `Tools/Can_Relay/panda-firmware/board/drivers/can_common.h:174-176`(`.can_speed = 2500U` ×3).
> - **② heartbeat fail-open = 미검증** — heartbeat 를 실제로 끊어본 시험 기록이 본 문서·ADR 어디에도 없다. 코드 반영 자체는 확인됨(`.../board/main.c:257-258`).
> - **③ `0x6041` freeze = 미검증** — `docs/can_relay/test-process.md:14` 가 요구하는 실로봇 판정(구동 중 **신규** 52111/52106/52954/54301 + 55602 = 0) 미실시. 코드 반영 자체는 확인됨(`.../board/safety/safety_seer_gate.h:170-172` `seer_is_motion_obj()` 에 `0x6041U` 포함).
>
> **(2) "fail-open → Seer 가 모터를 직접 보게 한다" = 미판정 모순** (어느 쪽으로도 고치지 않음)
> - *이쪽 기록*: heartbeat 상실 시 `set_intercept_relay(false)` + `pc_authority = false` 로 물리 통과 복귀 → Seer 직결 (`Tools/Can_Relay/panda-firmware/board/main.c:252-258` 주석·코드).
> - *어긋나는 기록*: `Tools/docking_field_kit/PINMAP.md:80` 은 "passthrough(fail-safe)는 **판다 미전원 시** 기계적 브릿지로 확실히 동작(검증됨)"이라 적고, 뒤이어 "판다 켜진 SILENT 는 트랜시버 간섭으로 불통"을 (현재 취소선 + `PINMAP.md:82-103` 의 **미판정 모순** 부기 상태로) 기록한다. heartbeat 상실 경로는 **판다가 전원 ON 인 채 SILENT 로 전환**되고(`main.c:248-250` → `main.c:88-93` `set_intercept_relay(false)` + `can_silent = ALL_CAN_SILENT`) 메인 루프가 매 회전 `enable_can_transceivers(true)` 로 트랜시버를 계속 켜 두는(`main.c:421`) 상태 — 즉 PINMAP 이 "불통"이라 적은 바로 그 조건이다.
> - ⇒ "Seer 가 모터를 직접 보게 된다"는 **아직 실증되지 않았다**. (릴레이가 물리적으로 붙는다는 점은 별개로 확인돼 있다 — `PINMAP.md:87-90`.)
> - **판정에 필요한 측정**: 250 kbps 정합 펌웨어에서 heartbeat 를 5초 이상 끊은 뒤(판다 전원 ON · SILENT · relay OFF) ⓐ Seer↔모터 SDO 왕복(요청/응답 쌍) 프레임 수 ⓑ per-bus `can_health` 에러 카운터 ⓒ Seer 알람(52111/52106/54022) 을 동시 실측. **값·코드는 변경하지 말 것.**
>
> **(3) SDO 폴 "12초 실측으로 확정" 은 창 조건 미기재** — 관측은 **12초 단일 창** 기준이며 그 창의 로봇 상태(정차/구동 · `pc_authority` engage 여부 · 호밍 진행 여부)가 기록돼 있지 않다. 특히 `0x606C`(실속도)는 정차 창에서 0회여도 구동/호밍 중에는 폴될 수 있으며 이를 배제한 측정이 없다 ⇒ **"`0x606C` 0회 = 미폴" 은 재측정 전까지 잠정**. 같은 전제가 펌웨어 주석 `.../board/safety/safety_seer_gate.h:138`("0회(Seer 미폴) → 현재 죽은 분기")에도 전파돼 있다(단 `:171-172` 가 `0x606C` 를 freeze 집합에 유지하므로 현재 동작 위험은 낮다). **판정에 필요한 측정**: 구동 중·재호밍 중 각 60초 이상 SDO 폴 카운트 재수집. **freeze 집합·값은 변경하지 말 것.**

### [Fix] vision_guard 6대 표시가 16fps로 저하 — 프레임 변환의 BGR→RGB 복사(9.2ms/대)가 렌더 병목

- **문제**: 퍼블리셔 캡처는 29.7fps인데 뷰어 표시는 16~20fps. 6대 동시 표시 시에만 발현.
- **원인**: [실측] 구간 분리 측정 결과 병목 2개. **(주)** `main_window.bgr_to_qimage` 가 `np.ascontiguousarray(frame[:, :, ::-1])`(비연속 스트라이드 복사) + `QImage.copy()` 로 2.76MB 프레임을 **두 번 복사** → 오프스크린 실측 **9.2ms/대**(변환 12.0ms/대 중 76%). 6대×30Hz면 한 틱 72ms 로 30Hz 예산(33ms) 초과 → **렌더 상한 13.9fps**. 실측 CPU도 일치: 프로세스 145%, GUI 메인 스레드 단독 83%. **(부)** raw bgr8 전송 자체 손실 — 아무 것도 안 하는 카운트 전용 구독자(CPU 55%)도 24Hz만 수신(6대 합계 166MB/s, best-effort/depth=1).
- **해결**: Qt 가 BGR 을 직접 읽는 `QImage.Format_BGR888` 로 채널 스왑 복사를 제거하고, numpy 버퍼 수명이 살아있는 함수 내부에서 `QPixmap.fromImage` 로 소유권을 옮기도록 `bgr_to_qimage` → `bgr_to_pixmap` 교체(호출부 `_pump`·`CameraCell.update_frame` 포함 3곳). 대안 비교 실측: 현재 14.3ms → **BGR888 무복사 1.1ms**(12.6배) / cv2 선축소 0.9~2.2ms.
- **파일**: `src/Sensors/Camera/USB/ui/vision_guard/vision_guard/main_window.py`, `.../test/test_frame_convert.py`(신규 — 채널 순서·크기·원본 해제 후 생존·비연속 입력 7 케이스)
- **상태**: 완료. 테스트 **14 passed**(기존 7 + 신규 7), 빌드 클린. 실측: 표시 **20.7~24.1 fps**(6/6), 뷰어 CPU **145% → 85%**. 남은 상한은 (부)의 전송 손실(~24Hz)이며 compressed transport 도입은 미적용(별건).

### [Diag] 뷰어를 kill -9 로 강제 종료하면 퍼블리셔 쓰기가 막혀 일부 카메라가 영구 "No Signal"

- **문제**: 진단 중 뷰어를 `kill -9` 로 수차례 종료한 뒤, 재기동한 뷰어에서 cam0·cam1·cam2·cam5 가 **콜백 0회**("No Signal", 에러 로그 없음). 동시에 해당 4대의 퍼블리셔 캡처 FPS 가 29.7 → 18(순간 0.8까지) 로 동반 저하. cam3·cam4 만 정상.
- **원인**: [증거] 독립 구독자(`rate_probe.py`)는 같은 시각 6토픽 모두 정상 수신 → 발행 자체는 살아있음. 즉 SIGKILL 로 정리 없이 사라진 리더의 FastDDS 공유메모리(`/dev/shm/fastrtps_*`, 40→50개로 증가) 상태가 남아 해당 라이터의 전달·쓰기가 지연된 것. 퍼블리셔는 캡처 스레드에서 `grab → convert → publish` 를 직렬 수행(`usb_cam_publisher_node.cpp:168,192`)하므로 **쓰기 지연이 곧 캡처 FPS 저하**로 나타남.
- **해결**: 퍼블리셔 재기동으로 즉시 정상화(6/6 표시, 캡처 전 카메라 29.7 복귀). 운용 규칙: 뷰어는 **Ctrl+C / SIGTERM 으로 종료**(SIGKILL 금지), 부득이 SIGKILL 한 경우 퍼블리셔도 함께 재기동.
- **파일**: (코드 변경 없음) 관련: `src/Sensors/Camera/USB/usb_cam_publisher/src/usb_cam_publisher_node.cpp`
- **상태**: 원인·회복 절차 확인 완료. ⚠ 미해결: 퍼블리셔의 publish 블로킹이 캡처 루프를 멈추는 구조(캡처·발행 스레드 미분리)는 그대로 — 재발 시 같은 증상 가능.

> ⚠ **[2026-07-27 감사 부기 — 기전은 미검증 가설]** (원문 무변경)
> 위 "원인" 절의 "SIGKILL 로 사라진 리더의 FastDDS 공유메모리 상태가 남아 해당 라이터의 전달·쓰기가 지연된 것" 은 **"…지연됐을 가능성이 크다(미검증 가설)"** 로 읽어야 한다. 제시된 근거는 (a) 독립 구독자 정상 수신 (b) `/dev/shm/fastrtps_*` 40→50 개 증가 두 정황뿐이고, 인과를 확인한 재현 시험이 없다. 실제 해결도 원인 제거가 아닌 **퍼블리셔 재기동**이었고(위 "해결" 절), 같은 entry 의 "상태" 절도 구조적 원인이 남아 있음을 스스로 적고 있다.
> 따라서 "해결" 절의 **SIGKILL 금지 운용 규칙은 "기전 미확정 — 예방적 규칙"** 으로 병기한다(규칙 자체는 유지: 비용이 낮고 회복 절차가 확인돼 있음).
> **판정에 필요한 측정**: ① SIGTERM 종료 N회 vs SIGKILL 종료 N회 후 뷰어 콜백 수신 여부 대조 ② SIGKILL 후 잔존 `/dev/shm/fastrtps_*` **정리만으로** 회복하는지(퍼블리셔 재기동 없이) 확인.

### [Fix] vision_guard 기동 즉시 abort — opencv-python 이 Qt 플랫폼 플러그인 경로를 오염

- **문제**: `ros2 launch vision_guard vision_guard.launch.py` 실행 시 `qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in ".../cv2/qt/plugins" even though it was found` 후 프로세스 abort(exit -6). 6대 카메라 퍼블리셔는 정상(29.7fps)인데 뷰어만 뜨지 않음.
- **원인**: pip 설치본 `opencv-python 4.10.0`(`~/.local/lib/python3.10/site-packages/cv2`)이 **import 시점에 `QT_QPA_PLATFORM_PLUGIN_PATH` 를 자기 번들 경로로 덮어씀**(실측: import 전 `None` → import 후 `.../cv2/qt/plugins`). 그 번들 `libqxcb.so` 는 cv2 자체 Qt 에 링크돼 시스템 PyQt5(`/usr/lib/aarch64-linux-gnu/qt5/plugins/platforms`)와 호환되지 않아 플랫폼 플러그인 초기화 실패. 발현 경로: `app.py:17` 의 `from .ros_worker import ...` → `ros_worker.py:21` `import cv2` 가 `app.py:23` `QApplication()` 보다 먼저 실행. **외부 환경변수 지정으로는 못 고침** — cv2 가 import 시 다시 덮어쓰는 것을 실측 확인.
- **해결**: `app.py` import 직후·`QApplication` 생성 전에 `os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)` 추가(주석 5줄 + `import os` + pop 1줄). 재현 스크립트로 `platform = xcb` 정상 기동 선검증 후 적용.
- **파일**: `src/Sensors/Camera/USB/ui/vision_guard/vision_guard/app.py`
- **상태**: 완료 (colcon build 성공, 6대 뷰어 `6/6 cameras shown` 실측 확인)

### [Change] USB CCTV 카메라 로스터 6대로 확장 (cam5 = AY4EC5401BT)

- **문제**: 6대 장착 상태인데 roster 에 5대만 등록돼 뷰어에 5분할만 표시.
- **원인**: `config/camera/camera_common.yaml` 로스터 미갱신 — 6번째 시리얼 `AY4EC5401BT`(/dev/video2, usb 1-3.3) 누락.
- **해결**: cam5 항목 추가 + 버스 공유 주석(cam4·cam5 는 둘 다 Bus 001). 6대 동시 구동 실측: 전 카메라 **29.7fps, grab_failures=0** — 기존 문서의 "RGB 최대 4대" 제약(tr-orin-22 단일 USB2.0 컨트롤러 기준)은 이 Tegra 호스트에 미적용임을 재확인.
- **파일**: `config/camera/camera_common.yaml`
- **상태**: 완료

> ⚠ **[2026-07-27 감사 부기 — 6대 무손실 주장은 조건부]** (원문 무변경 · 로스터 값 무변경)
> 위 "해결" 절의 "6대 동시 구동 실측 29.7fps · grab_failures=0 ⇒ 'RGB 최대 4대' 제약 미적용 재확인" 은 다음 두 이유로 **조건부**로 읽어야 한다.
> - 이 entry 가 수정한 바로 그 파일이 상반된 문구를 **미정정 상태로 유지**한다: `config/camera/camera_common.yaml:22` "HARDWARE LIMIT: 단일 USB 2.0 컨트롤러라 RGB 최대 4대", `:23` "이 호스트에 실제 연결된 Gemini E **4대**" — 실제 로스터는 `:26-38` 의 cam0~cam5 **6대**. (어느 쪽이 옳은지는 여기서 판정하지 않는다. 값·주석은 해당 파일 담당 범위.)
> - 같은 파일 `:39-40` 은 "**5대** 실측 검증", `:41-42` 는 "cam4·cam5 는 둘 다 Bus 001 공유이므로 **6대 동시 구동 시 이 두 대의 FPS/grab 실패를 우선 관찰할 것**" 이라 적어 6대 조건을 **열린 관찰 대상**으로 남겨둔다.
> - 또 본 entry 의 6대 측정에는 **조건이 기재돼 있지 않다**(해상도·픽셀포맷·측정 지속시간·동시 뷰어 유무).
> **판정에 필요한 측정**: 6대 동시 구동을 해상도·픽셀포맷(`camera_common.yaml:14-17` 기준)·지속시간을 명기해 재측정하고, cam4/cam5(Bus 001 공유)의 FPS·`grab_failures` 를 별도로 기록.

### [Fix] vision_guard(USB_CCTV 뷰어) 메모리 누수 → OOM kill (프레임별 queued signal 무한 적재)

- **문제**: CCTV 5-카메라 내구 테스트 중 GUI `vision_guard` 가 시작 ~1시간 만에 강제 종료(exit code -9=SIGKILL). 동시에 20:32~20:49 5대 publisher FPS 가 0.5~28 로 요동. `journalctl -k`: `20:49:59 Out of memory: Killed process 1195045 (vision_guard) total-vm:24.9GB anon-rss:11.2GB` — vision_guard 가 11.2GB 까지 성장해 OOM killer 가 kill, 그 메모리·스왑 압박 여파로 publisher 캡처 FPS 동반 하락(카메라/USB 결함 아님 — grab_failures=0·stall=0, GUI 사망 후 9시간+ 29.7 FPS 안정).
- **원인**: [실측·증거] `main_window.py:37` `frame_ready = pyqtSignal(str, object)` 를 ROS 스핀 스레드에서 프레임마다 emit(`ros_worker.py:102·125`), GUI 스레드 `_on_frame`(`main_window.py:189`)에 **cross-thread queued connection**(`main_window.py:154`)으로 연결. GUI 렌더(bgr_to_qimage copy+scale+setPixmap)가 유입률(5대×30=150fps, 각 ~2.7MB)을 못 따라가면 **Qt 이벤트 큐에 프레임이 무한 적재**(드롭·백프레셔 없음) → 11GB/1h → OOM. ROS 구독 QoS 는 KEEP_LAST depth=1 로 정상(ROS 큐 누수 아님). 원본 tr-orin-22 는 2대라 누수가 느려 미노출, 5대에서 발현.
- **해결**: 유입률과 렌더율 **분리**. `FrameSignals`(queued signal) → `LatestFrameStore`(스레드 안전 dict, `put`=카메라별 최신 프레임 덮어쓰기·`drain`=GUI가 당겨 비움)로 교체. ros_worker 는 `_store.put(topic, frame)`, GUI 는 `QTimer(30Hz)`로 `_pump` 드레인 렌더. 메모리 상한 = 카메라수×1프레임(구버전 무한 큐 제거). (main_window.py: 클래스 교체+QTimer+_pump, ros_worker.py: emit→put 2곳+docstring, app.py: wiring)
- **파일**: `src/Sensors/Camera/USB/ui/vision_guard/vision_guard/{main_window.py, ros_worker.py, app.py}` (원본 병기: `tr-orin-22:~/Project/Ford_CATL_AMR/src/Sensors/Camera/USB/ui/vision_guard/` 동일 3파일)
- **상태**: 양쪽 완료·검증. **tegra**: 빌드 클린·테스트 7 passed(flake8·pep257 포함)·GUI RSS **268.6MB 80초 완전 평탄(Δ=0)** 실측(구 11GB→OOM 대비 상한 고정)·5대 렌더·소크 무영향. **tr-orin-22(원본)**: 수정 3파일 rsync 전파·빌드 클린·테스트 7 passed(코드 tegra와 동일). ⚠ tr-orin-22 런타임 RSS 미실측(동일 코드라 동작 동일 판단). launch 의 카메라 하드코딩은 누수 무관이라 이번 범위 외.

---

## 2026-07-26

### [Fix] motor_control 리뷰 지적 4건 수정 (E-stop 안전 2 · 브링업 누수 1 · 테스트 레이스 1)

- **문제**: 이식된 `src/Actuators/motor_control/` 코드 리뷰([docs/code_review/motor_control/2026-07-26.md](../code_review/motor_control/2026-07-26.md), Verdict REQUEST CHANGES) High 1·Medium 3. ① `test_cold_bringup_allowed_with_permission` 이 이 Jetson(ARM)에서 8/8 결정적 실패(x86 원격은 통과). ② E-stop 중 조향축이 계속 지령받아 정지 상태에서 물리 스윙 가능. ③ 브링업 예외 시 CAN 버스·rclpy 컨텍스트 누수. ④ E-stop 중 도착한 cmd_vel 이 해제 직후 급발진.
- **원인**: ① `_tx_loop`(backend.py:258)이 생성하는 조향 write 를 tx 데몬 스레드 기동 전에 테스트가 단언 — 스케줄링 레이스(`test_backend.py:126`). ② `_tx_loop`(backend.py:257-259)가 조향 setpoint 를 `_estop` 무관하게 무조건 송신. ③ `main`(driver_node.py:206)의 `node = MotorControlNode()` 가 try/finally 밖 + `__init__` 이 버스 개방(72) 후 `start()`(83) 예외 시 정리 없음. ④ `set_command`(backend.py:131)이 `_estop` 미확인.
- **해결**: ① 테스트를 tx 첫 write 폴링 대기(≤1s)로 견고화(+회귀 테스트 2건 추가). ② `_tx_loop` 에 `estopped` 캡처 후 E-stop 시 조향 setpoint 송신 `continue`(현 위치 hold, 설계문서 §5-4 step-cut 정렬). ③ `__init__` start() 를 try 로 감싸 실패 시 `backend.shutdown()`(버스 close) 재-raise + `main()` 노드 생성 실패 시 `rclpy.shutdown()`. ④ `set_command` 진입부 `if self._estop: return`. (backend.py +5줄, driver_node.py +8줄, test_backend.py +42줄)
- **파일**: `src/Actuators/motor_control/motor_control/backend.py`, `.../motor_control/driver_node.py`, `.../test/test_backend.py` (병기: `src/Actuators/motor_control/docs/code_review/motor_control/2026-07-26.md` findings 상태 [해결])
- **상태**: 로컬 완료 · 원본 반영 **부분(검증 보류)** — 로컬 **31 passed**(원본 29 + 신규 2), 레이스 테스트 8/8 PASS(Jetson), AST 정상. ⚠ 원본과 바이트 동일했던 코드에 **의도적 divergence**. 원본 `amap@amap-2:.../T-Driver-Analysis/src/Motor_Control/` 에 3파일 **rsync 전송 성공**(backend.py·driver_node.py·test_backend.py)했으나, 직후 amap-2 **SSH 도달 불가(오프라인)** 로 원격 pytest 검증·원격 doc 기록·git commit **미완**. 재개 시: (1) 원격 `python3 -m pytest test -q` 31 passed 확인, (2) 원격 docs/issues_and_fixes 동일 기록, (3) 협업 모드 확인 후 commit.

### [Diag] emulate 내구 중 Seer 52954(zeroing/재호밍 timeout) 1회 — zeroDI 하드웨어 아님, 기동 전환 트랜지언트로 추정

- **문제**: `emulate_endurance.py` 내구(2026-07-26 09:05~13:00, emulate firmware, engage180s/diseng5s) 중 Seer API 1050 알람에 **52954 "Motor calibration/zeroing timeout"(ERROR) 1회**(desc 09:29:19). 재호밍(원점복귀) 타임아웃.
- **원인**: [실측·증거 — ⚠ 2026-07-27 감사: 인과사슬 후반부는 **[가설]** 로 하향, 아래 부기 참조] appendix 002 매뉴얼의 일반원인(zeroDI 원점스위치 손상/오설치)은 **이 런 증거로 미지지**. 실제 인과사슬 = **첫 engage 전환(09:08) 순간 emulate 인수 전 수초 모터 통신 순단** → Seer가 모터침묵 감지(동시각 52111 motor timeout·52106 odo lost·54022 stuff, `seermon_endur.log` 09:08:42~43) → 자동 재호밍(54301 calibrating) 시작 → **emulate 경로가 실 원점센서(zeroDI) 피드백 미제공** → 시작+약20분 뒤 zeroing 카운트다운 만료로 52954(09:29). 09:29 시점 판다측 모터응답 정상(endur cyc7/8 급감0)=신규 통신갭 아님=09:08 zeroing의 종착점. 이후 59사이클 급감0·무재발. 근거모델: `docs/can_relay/field-record-orin-nx-2026-07-25.md:47,137`(모터응답/guard 상실=재호밍 방아쇠).
- **해결**: [미확정·검증대기] 코드 변경 없음. zeroDI 하드웨어 고장 가설 배제 위해 **실로봇 전원사이클 재현**(emulate 없이 실 Seer 재기동 → zeroing 정상완료=52954 미발생 확인) 예정. 정상완료 시 "emulate 기동 전환 트랜지언트"로 확정, 재발 시 실 zeroDI 점검. ⚠안전: Seer 전원복구=조향 물리 재호밍 동반(field-record §5-4), 가동범위 주변 클리어 후 수행.
- **파일**: (분석) `~/docking_reliability/seermon_endur.log`, `~/docking_reliability/endur_out.log`, `T-Robot_seer_gui/references/seer/robokit-api/appendix/002-alarm-code.md:183`; (재현도구) `~/Project/CAN-Relay/docking_field_kit/seer_powercycle_repro.py`(신규 작성·검증)
- **상태**: 진단 완료 · **재현검증 미실시(다음 세션 재개 필요)**. 내구는 76사이클 완주 PASS(모터급감 0, `endur_out.log` 13:00:12 종료요약). 전원사이클 재현 모니터 2회 기동(13:01·14:52, 각 10분 창)했으나 **양 창 모두 실 전원 OFF→ON 미수행**으로 zeroDI 하드웨어 가설 확정/배제 못함. **재개 절차**: (안전-조향 재호밍 물리이동 주변 클리어) → `python3 ~/Project/CAN-Relay/docking_field_kit/seer_powercycle_repro.py 192.168.44.82 600` 실행 후 Seer 전원 OFF→수초→ON → 판정(zeroing 완료=배제 / 52954 재발=하드웨어).

> ⚠ **[2026-07-27 감사 부기 — "emulate 경로가 실 원점센서(zeroDI) 피드백 미제공" 은 코드 근거 없음]** (원문 무변경 · 값/코드 무변경)
> 본 entry 는 제목이 "…**추정**", 상태가 "[미확정·검증대기]" 인데 원인 절만 `[실측·증거]` 라벨 + "**실제 인과사슬 =**" 단정형이었다. 인과사슬 중 **09:08 통신 순단 → Seer 재호밍 개시** 까지는 로그 인용이 있으나(`seermon_endur.log` 09:08:42~43), 그 뒤의 "**zeroDI 피드백 미제공**" 은 이를 뒷받침하는 로그·캡처 인용이 없고 펌웨어 코드는 오히려 반대 방향을 가리킨다.
> - 디지털 입력 `0x6000` 은 **모션 객체가 아니어서 freeze 대상이 아니다**(`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:139` "0x603F error·0x6000 digital in 은 폴되나 모션 아님 → **freeze 금지**", 모션객체 정의 `:170-172`, freeze 적용 조건 `:203`).
>   - ⚠ **정정 (2026-07-27)** — 위 「모션 객체가 아니어서」라는 **근거 서술은 부정확**하다(원문 보존. freeze 금지라는 운영 결정 자체를 뒤집는 것은 아니며, 값·코드 변경 없음).
>     `0x6000` 은 **배열 오브젝트**이고 실제 입력값은 **sub 1** 이다(sub 0 = 항목 수 = 2). sub 1 의 비트는 **bit0 = Servo Enable, bit1 = Positive Limit, bit2 = Alarm, bit3 = Negative Limit** [Handbook V7.0 Appendix I(Object Dictionary), printed page 197]. 그리고 조향축에는 리밋 스위치가 실재하며 호밍 방식은 **Home 1(음(−)의 리밋 트리거)** 이다(전 노드 `0x6098 = 1` 실기 파라미터 판독; Handbook 기본 RstMode 도 1 [§4.6, page 116]). 즉 `0x6000` sub 1 은 위치·속도는 아니어도 **호밍 진행/완료를 간접 노출**한다.
>     실측: 조향 노드만 `0x01 → 0x09`(bit3 = −Limit 셋) t=47.0249(node3)/47.0254(node4), `0x09 → 0x01` t=49.4223/49.4227, **구동 노드(1·2)는 180 s 전 구간 `0x01` 무변화** [`Log/homing_capture_220350.jsonl`]. 구동축은 호밍하지 않으므로 예상과 정합한다.
>     ⇒ freeze 제외의 근거는 「모션 객체가 아님」이 아니라 「**위치·속도 등 연속 모션량을 노출하지 않아 현 단계에서 은닉 필요성이 낮음**」으로 정정해 읽는다. 호밍 상태 은닉이 요구되는 시나리오(PC 가 조향을 리밋까지 몰 수 있는 경우 포함)가 생기면 재검토 대상이다.
> - emulate 중 Seer 의 SDO **읽기**(cmd `0x40`)는 캐시로 즉답되면서 **모터로도 forward**(`:286-288` `bus_fwd = 2`) 되어 캐시가 갱신되므로, 비-모션 객체의 실값은 (1폴 지연으로) Seer 에 전달되는 구조다. 단 캐시에 항목이 없으면 무응답이 될 수 있다는 한계는 별도로 기록돼 있다(`:182-194`, `:212`).
> ⇒ **정정**: "emulate 경로가 zeroing 을 완료시키지 못한 기전은 **미확정**" 으로 읽는다. 후보 —
> **(a)** SDO **쓰기**가 가짜 ack 후 모터로 전달되지 않아 호밍 지령이 모터에 미도달(`safety_seer_gate.h:289-291` `seer_fake_ack()` + `bus_fwd = -1` "모터로 안 보냄"), **(b)** `pc_authority` 중 모션객체(`0x6064` 등)를 engage 스냅샷(정지값)으로 고정해 위치가 불변으로 보임(`:179-180`, `:203-211`). 둘 다 **미검증**이다.
> **판정에 필요한 측정**: 재현 시 emulate 중 bus2(모터) 방향으로 나가는 호밍 관련 SDO **쓰기** 프레임 유무를 스니핑하고, 같은 창에서 `0x6000`(digital in) 응답값 변화와 `0x6064` 실위치 변화를 동시 기록. (기존 "실로봇 전원사이클 재현" 절차는 그대로 유효.)

---

## 2026-07-24

### [Fix] amap-2 현장 CAN 버스 단절오류 다발 — Seer 끝 종단저항(120Ω) 누락

- **문제**: 실 로봇 Foil_A082에서 CAN1(모터) 버스에러 다발(2026-07-23 23:13~24 01:05, 1h52m). Seer 알람 54022(Ack 250·Bit Recessive 183·Bit Dominant 104·Stuff 7 = 544회), 52111 모터 응답타임아웃(4개 동시 302회), 52106 odo lost 408회, 54301 재캘리 347회. 로봇 정지 중 발생, 수 초 내 자동복구 반복. Seer는 "check CAN router"만 지목, 원인 특정 못함. 판다측 모니터도 트래픽만 봐서 못 잡음.
- **원인**: **CAN 버스 종단이 모터(Tongyi) 끝 120Ω 하나뿐 = under-termination.** Seer 끝(DB9 2·7번=CAN_L/H) 종단 **없음**(실측 51.6kΩ 개방). 개방단 신호반사 → Bit/Ack/Stuff 에러. 판다는 온보드 종단이 없음(CAN0 pin4·5 / CAN2 pin23·24 실측 개방) — 문서 `Tools/docking_field_kit/PINMAP.md:50`의 "CAN2 온보드 120Ω 내장"은 오기였음(초기 혼선 원인).
- **해결**: **Seer 끝(DB9 2–7번)에 120Ω 종단저항 1개 추가** → 전체 60Ω(양단 120Ω) 정상화. PINMAP.md 종단 문구를 실측대로 정정(판다 종단 없음·Seer끝 120 필수·도킹시 스위칭종단 필요 명시).
- **파일**: `Tools/docking_field_kit/PINMAP.md`(정정), (하드웨어) Seer DB9 종단 120Ω 추가
- **상태**: 완료(판다측 검증) — 종단 60Ω 확인 후 라이브 트래픽 12s(33,278프레임·2,773fps)에서 판다 CAN 에러 전부 0(can_rx/send/fwd_errs Δ0, faults 0). **잔여 확증**: Seer 자체 로그 지속 무에러(수시간~밤샘 관찰) + per-bus 에러카운터(can_health) 위한 펌웨어 보강 예정.
- **[2026-07-27 종결 append]** 위 "잔여 확증" 항목을 닫는다. 그 후로도 간헐 재발하던 Seer CAN 알람의 원인은 **종단이 아니라 판다 부팅 기본 비트레이트 500 kbps** 였다(같은 날짜 상단 entry 참조). 250 kbps 정합만으로 `52106`·`52111`·`54022` 전량 소멸이 실증됐고 펌웨어 기본값을 정정했다. ⇒ **종단 문제는 종결. 이후 CAN 계열 알람에서 종단을 원인 후보로 재제기하지 않는다**(사용자 지시 2026-07-27). 먼저 판다 비트레이트·펌웨어 버전을 확인할 것.

> ⚠ **[2026-07-27 감사 부기 — 07-23 단절오류의 원인 귀속은 미판정]** (위 두 서술 모두 무변경 · 값/하드웨어 무변경)
> **양쪽 기록을 병기한다.**
> - *종단 쪽*: 위 "원인" 절은 2026-07-24 **실측**을 기록한다 — Seer 끝 DB9 2·7번 종단 없음(**51.6kΩ 개방**), 모터 끝 120Ω 하나뿐 = under-termination. `docs/adr/2026-07-24-canhealth-firmware.md:8` 은 "근본원인은 Seer 끝 120Ω 종단 누락이었고 종단 추가(60Ω)로 해소", 같은 문서 `:48` 은 "종단 수리 후 REC/TEC=0 → 종단 수리 하드웨어 레벨 확증" 이라 적는다. (해당 ADR 에는 `:12-19`·`:55` 로 2026-07-27 정정 부기가 이미 달려 있다.)
> - *비트레이트 쪽*: 위 종결 append 와 `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md`.
> **미판정 사유**: 120Ω 종단은 **07-24 에 이미 장착**됐고(위 "해결"·"상태" 절), 07-27 검증(8초 29,625 프레임 · Seer `errors=[]`)은 **그 종단이 장착된 상태에서** 수행됐다. 두 변경(종단 추가 · 비트레이트 정합)을 **분리해 측정한 기록이 없다** — 07-27 ADR 에는 '종단/termination/120' 문자열이 0건(grep, 2026-07-27).
> ⇒ 실증된 것은 **"250 kbps 정합이 '호스트 미실행 시 잔여 알람'을 없앴다"** 까지다. **07-23 단절오류(1h52m, 54022 544회 등)의 원인 귀속(종단 vs 비트레이트, 또는 양자 복합)은 미판정.**
> **운용 지시의 유효 범위**: "종단을 원인 후보로 재제기하지 않는다"는 **원인 후보 확인 순서**(판다 비트레이트·펌웨어 버전을 **먼저** 확인)로 운용하며, **물리 종단 60Ω 상시 확인은 별개로 유지**한다(`Tools/docking_field_kit/PINMAP.md:62-71`: 판다는 온보드 종단 없음 · Seer 끝·모터 끝 각 120Ω 필요 · 도킹 intercept 시 스위칭 종단 별도 필요).
> **판정에 필요한 측정**: ① 250 kbps 정합 상태의 **현재 버스 종단 저항 실측**(60Ω 유지 여부) 기록 ② 가능하면 종단 정상·비트레이트 정합 상태에서 장시간 `can_health`(REC/TEC) + Seer 1050 알람 무에러 지속 확인.

---

## 2026-07-04

### [Fix] python 훅 전체가 한국어 Windows(cp949) 콘솔에서 UnicodeEncodeError 로 조용히 실패

- **문제**: `.claude/settings.json` 에 등록된 python reminder 훅들이 실제 런타임에서 출력 없이 실패 — 게이트 컨텍스트(user_instruction·debt·git_workflow 등)가 세션에 주입되지 않음. kuks_claude_agent_setup 업데이트(git_workflow v1.4.0) 설치 스모크 테스트 중 발견.
- **원인**: Windows 에서 stdout 이 파이프일 때 python 기본 인코딩이 cp949 — 훅 출력의 em-dash(U+2014) 등 cp949 비수록 문자가 `UnicodeEncodeError` 유발. 예: `docs/claude_guideline/git_workflow/hooks/git_workflow-reminder.py:128` 의 `print(DIRECTIVE ...)` (`[GIT-WORKFLOW SOP — 강제 게이트]` 헤더 18번째 문자). 구버전 훅에도 동일 문자 존재 → 신버전 회귀가 아닌 기존 잠재 버그. 검증: 기본 환경에서 user_instruction(exit=1)·debt(exit=1)·git_workflow(crash) 재현.
- **해결**: `.claude/settings.json` 최상위에 `"env": {"PYTHONUTF8": "1"}` 추가 (4줄 추가). 훅 파일은 저장소 원본과 동일하게 유지(diff 0) — 프로젝트 환경 레벨에서 UTF-8 모드 일괄 적용. 세션 재시작 후 발효.
- **파일**: `.claude/settings.json`
- **상태**: 완료 — 등록 훅 10종 전부 `PYTHONUTF8=1` 환경에서 exit=0 확인 (reminder 8종 + git_workflow track·stage-gate). 업스트림(kuks_claude_agent_setup) 훅에 `sys.stdout.reconfigure(encoding="utf-8")` 추가 또는 install.sh 의 settings env 등록 권고.


## 2026-08-10 — 적대적 코드 감사 5인 투입: 확정 결함 수정

사용자 지시로 5개 레인(turn 제어루프 · yaw_control 가드 · can_relay 백엔드 · 신규 시험 ·
신규 도구)에 감사를 붙였다. 보고 총 100여 건 중 **직접 재현·검증한 것만** 고쳤다.

### 고친 것 (전부 검증 완료)

| 대상 | 결함 | 근거 |
| --- | --- | --- |
| `turn`·`turn_reverse` | **전역 시한이 없다** — Stage 1 의 종료 조건은 「오차가 줄어드는 것」뿐. IMU 두절(`imu_received_` 는 내려가지 않는 래치)·차체 구속이면 조건이 영원히 불성립하고 매 주기 정상 지령을 계속 내 **무한 원호 주행**. mux 는 timeout 을 강제하지 않아 외부 방어선도 없다 | `grep -c max_timeout`: turn **0** · spin 7 · yaw_control 5 |
| 〃 | `min_speed_dps` floor 를 걸고 `max_omega_deg` 로 **재클램프하지 않는다** → R>1.44 m(v=0.05)에서 goal 의 속도 상한 초과. R=2.0 m 에서 +39.6% | 산식 확인 |
| 〃 | fine(PD) 타임아웃이 `break` 후 **`status 0`(성공)** 으로 보고 → 미수렴 기동이 성공으로 올라가 다음 기동이 틀어진 자세에서 출발 | 코드 판독 |
| 〃 | 주석 「`std::remainder` 특성으로 ±180° 정확 입력 시 −180° 로 정착」이 **거짓**. 실제 `remainder(180,360) = +180`. 저장소가 이미 한 번 정정한 문장(`spin:146-148`)의 **정정 전 판본을 복사**했다 | 실행 확인 |
| 〃 | `start_yaw_avg_samples ≤ 0` 이면 평균 루프가 안 돌아 `atan2(0,0)=0` → 상대 회전이 **절대 IMU 원점 기준**으로 바뀐다(30° 요청이 300° 원호) | 코드 판독 |
| `DirectBackend` | **호밍 중에도 조향 setpoint 를 재송신**한다 → 드라이브 내부 호밍 루틴과 외부 PP setpoint 가 같은 축을 다툰다. `RelayBackend` 는 `not self._homing and not self._estop` 로 막고 있었고 여기만 빠졌다 | `backend.py:961` 대조 |
| 〃 | `home()` 이 `_steer_counts` 를 안 비운다 — 재영점 **전** 좌표계의 목표를 들고 있는다 | 코드 판독 |
| 〃 | 브링업(내가 추가한 것)이 **fail-safe 미무장 구간 안**에 있었다. 거기서 예외가 나면 「Seer 차단 + intercept + 심박 영구 미송신」이 남아 아무도 로봇을 못 세운다. `link.acquire()` 는 같은 이유로 intercept 직후 즉시 심박을 보낸다 | `link.py:392-395` 대조 |
| 〃 | 제어권 반환 3단계가 **하나의 try** — 중간 실패 시 릴레이가 열리지 않은 채 남는다. 순서도 `link._rollback` 과 반대. 획득 실패 시 **롤백이 아예 없었다** | 코드 판독 |
| `seer_jog` | **여유 판정이 물리적으로 발화 불가**였다. 임계 0.5 m 인데 `/scan_merged` 는 배제영역(`x∈[-0.96,0.98]`)을 삭제하고 `use_inf: True` → 전방 최소 관측거리 0.98 m | `filter_config.yaml:15-18` 실조회 |
| 〃 | 스캔 없으면 `99.0` 반환(fail-open) — 라이다가 죽으면 무한히 안전해졌다 | 코드 판독 |
| 〃 | 측위 신선도 검사 없음 → 측위가 얼면 오차가 상수가 되어 **발산 가드가 영원히 발화하지 않고** 최대 19 m 맹목 주행 | 코드 판독 |
| 〃 | `SIGTERM`·`SIGHUP` 에서 `finally` 미실행 → 정지(2000) 미송신. Seer 개루프 지령에 **워치독·지속시간 필드가 없음**을 벤더 원문에서 확인 | `robotkit-netprotocol-l-1.2.1.txt:2621-2640` |
| `sil_regression` | `abs(actual) − abs(target)` 로 재서 **부호 반전을 통과**시켰다(+20 지령에 −20 회전 → 오차 0). 이 저장소가 반복해 당한 결함군이 정확히 조향·회전 부호 반전이다 | 코드 판독 |
| 〃 | 도메인 가드가 문자열 비교라 `""`·`"00"`·`" 0"` 이 빠져나갔다 | 코드 판독 |
| 신규 gtest | 돌연변이 2건이 **검출되지 않았다** — ① `computeSpin` 의 `direction = 1 → -1`(제자리 회전 **역전**)이 IK 시험 13건 전부 통과 ② `rateLimitStep` 의 정착 분기 삭제(지령이 목표에 못 닿고 영구 진동, 7개 액션 서버 공통)가 9건 전부 통과 | 감사가 실제로 돌연변이를 만들어 실행 |

### 검증

- gtest **52건**(신규 2 포함) 통과, 두 돌연변이를 **다시 넣어 각각 1건 실패** 확인 후 원복 → 52/0
- `can_relay` pytest **398 passed, 8 skipped**
- SIL 회귀 `--case all` **4/4 · exit 0** (부호를 살린 판정으로도 통과 — 방향 반전 없음 확인)

### 고치지 않고 남긴 것

보고에는 있었으나 **재현·검증하지 못했거나 범위가 큰 것**은 부채로 등록했다(debt-059~064).
특히 `yaw_control` 의 「측위 신선도 미검사 + `setMaxCmdSpeed` 미호출로 −4/−5/−6 이 전부
발화 불가」는 **선재 결함이고 −7 가드가 그 위에 얹혀 있다** — 확인이 필요하다.


## 2026-08-10 — debt-059 확인 및 상환: yaw_control 의 측위 워치독이 죽어 있었다

감사 지적을 **코드로 확정**했다.

    setMaxCmdSpeed 호출부  mpc · mpc_reverse · translate_forward · translate_reverse · crab_linear
                           yaw_control 계열 0건          ← 여기만 빠졌다
    checkLocalizationHealth  max_cmd_speed_ <= 0.01 이면 즉시 true 반환
    lookupMapToBase          신선도 검사 없음(pose_received_ 는 내려가지 않는 래치)

세 사실이 겹쳐 `yaw_control`·`yaw_control_reverse` 는 **status −4(측위 타임아웃)·−5(점프)·
−6(조회 실패)이 전부 발화할 수 없었다.** 타임아웃 검사 코드 자체는 있었고 `max_cmd_speed_`
게이트 뒤에 가려져 있었을 뿐이다.

### 파급 — 내가 넣은 −7 가드가 그 위에 얹혀 있었다

측위가 얼면 맵 yaw 만 고정되고 IMU 는 계속 돈다 → 괴리가 회전량만큼 커져 **−7 이 0.2 s 만에
발화**한다(측위 타임아웃은 yaml 2.0 s 라 −4 보다 −7 이 먼저 뜬다). 그러면 로그와 `.action`
주석이 「측위는 멀쩡한데 IMU 가 어긋났다 — IMU 점검 필요」라고 단언한다. **정반대의 정비
지시가 나간다.** `map_yaw_fresh` 라는 변수명과 주석(「이번 주기 맵 heading 이 유효」)도
사실이 아니었다 — 실제 의미는 「언젠가 1회 수신」이었다.

### 고친 것

1. `vx_profile` 확정 직후 `loc_monitor_->setMaxCmdSpeed(vx_profile)` — `translate_*` 와 같은 배선
2. `lookupMapToBase` 의 4-인자 판을 써서 stamp 를 받고, `map_yaw_fresh` 를 **0.3 s 신선도**로
   판정. 낡았으면 판단을 보류하고 `heading_diverge_cnt` 도 리셋한다

### 검증 — 음성 대조까지

SIL 회귀에 `yaw_loc` 케이스를 추가했다(주행 3 s 뒤 `sil_pose_adapter` 를 죽인다).

    배선 있음   PASS  status −4 발화 · 거리 0.131 m
    배선 제거   FAIL  status=-3          ← 시한까지 계속 주행했다(종전 상태)

`−7` 이 뜨면 실패로 판정하도록 했다 — 그것이 바로 오진 형태이기 때문이다.
전체 `--case all` **5/5 통과**.


## 2026-08-10 — debt-060·061 상환: 파라미터 콜백의 부분 적용과 스레드 레이스

### debt-060 — 「거짓 성공」을 없애려다 「거짓 실패 + 은닉 적용」을 만들었다

콜백이 검사를 통과하는 즉시 `dst = v` 로 멤버를 쓰고, 뒤의 키가 거부되면 `return` 했다.
rclcpp 는 콜백이 실패를 반환하면 **파라미터 저장소에 아무것도 반영하지 않는다.** 그런데
앞의 키는 이미 멤버에 적용돼 있다 → `ros2 param get` 이 보고하는 값과 **실제 거동이
영구히 어긋난다.** 종전(콜백 없음)에는 최소한 「둘 다 안 바뀜」으로 일치했으니 더 나빴다.

→ **검증과 반영을 분리**했다. 통과한 키의 반영을 `commits` 에 쌓아 두고, 전부 통과했을
때만 실행한다. 타입 가드도 넣었다(`p.as_double()` 을 무조건 부르던 것 — `spin` 에는 있었다).

### debt-061 — 콜백 스레드와 execute 스레드가 같은 멤버를 비-atomic 으로 만졌다

`handleAccepted` 는 `execute` 를 detach 한 스레드에서 돌리고 파라미터 콜백은 executor
스레드에서 돈다. 두 스레드가 만지는 파라미터 멤버 10개가 전부 평범한 `double`/`int`/`bool`
이었다. UB 이자, 최적화기가 루프 밖으로 로드를 끌어올리면 **hot-reload 가 진행 중 goal 에
비결정적으로 반영되지 않는다** — 이 커밋이 고치려던 증상의 재발이다. 베이스 클래스는 같은
이유로 `std::atomic` 을 쓰고 주석까지 달아 뒀다(`qd_action_server_base.hpp`).

→ 10개 멤버를 `std::atomic` 으로 바꿨다. 로그 매크로는 가변인자라 값 복사가 일어나므로
해당 인자 8곳에 `.load()` 를 붙였다(빌드가 잡아 줬다).

### 검증

SIL `yaw_guard` 케이스에 **부분 적용 회귀**를 붙였다 — 범위 밖 값(999.0)이 수용되면 실패로
판정한다. 전체 `--case all` **5/5 통과**.


## 2026-08-10 — debt-062·063 상환, 그리고 「시험이 다른 이유로 통과」한 사례

### debt-062 — turn 의 ±180° 경계에서 회전 방향이 뒤집혔다

`std::remainder` 의 round-half-even 때문에 `target_angle = 180.0` → `+180`(CCW),
`180.001` → `-179.999`(CW). **0.001° 차이로 방향이 정반대**가 된다. spin 은 이 불연속을
`kBoundaryEpsDeg`(raw 부호로 고정)와 antipode 고정 둘로 처리하는데 turn 에는 없었다.
turn 은 spin 과 달리 **원호 궤적을 규정**하므로 방향 반전은 소인 면적·주행 경로가 통째로
달라지는 일이다. 또 시작 antipode(|e|≈180°)에서 Stage 2 는 부호를 그대로 게인에 넣으므로
매 주기 부호가 반전돼 좌우 진동한다. → `spin:172-178·266-275` 를 이식했다.

### debt-063 — DirectBackend 에 지령 워치독이 없었다

`RelayBackend` 는 `cmd_timeout_s=0.3` 으로 지령을 만료시키는데 DirectBackend 에는
**RX 워치독뿐**이었다. 드라이브가 응답을 잘 주는 한 마지막 구동 지령이 영구히 재송신된다 —
조그 스레드가 죽거나 Qt 메인 스레드가 블록되면 아무도 새 지령을 안 내는데 로봇은 계속
주행하고, 남는 정지 수단이 하드웨어 E-STOP 뿐이다. 게다가 `_rx_at = 0.0` 은 falsy 라
**응답을 한 번도 못 받으면 RX 워치독조차 영원히 무장되지 않았다**(송신은 되고 수신만 죽은
경우: USB rx 큐 오버플로 등). → `CMD_TTL_S=0.5` 지령 워치독 + engage 시 `_rx_at` 무장.

### 부수 — 가짜 판다에 `can_recv` 가 없어 폴 스레드가 첫 회전에서 조용히 죽고 있었다

`_loop` 의 `except Exception` 이 `AttributeError` 를 삼켜 `_run=False` 로 내리는데
`set_engaged` 는 이미 `(True, …)` 를 반환한 뒤라 아무도 몰랐다. 즉 「가짜 판다로
`set_engaged` 를 끝까지 돌린다」는 주장의 실제 범위는 **폴 루프 1회전의 앞부분까지**였다.
`can_recv` 를 붙이고 픽스처에 `assert be._run is True` 를 넣었다 — 죽은 루프 위의 관찰은
근거가 아니다. 루프가 살아나자 기존 시험 1건이 깨졌고(폴 재송신이 프레임 목록에 섞였다),
범위를 「브링업이 맨 앞에 순서대로」로 좁히고 이름·docstring 의 과장(「`RelayBackend` 와
같은 바이트」인데 `RelayBackend` 를 부르지도 않았다)을 정정했다.

### ⚠ 새로 쓴 워치독 시험이 **다른 이유로 통과하고 있었다**

지령 워치독을 통째로 지우고 돌렸는데 **6건 전부 통과**했다. 원인: 가짜 판다가 응답을 안 줘
`_rx_at` 이 갱신되지 않으니 **RX 워치독(1.0 s)이 먼저 발화**해 구동을 0 으로 만들고 있었다.
`CMD_TTL_S=0.5 < RX_TTL_S=1.0` 이라 시험은 그 차이를 볼 수 없었다. 가짜 판다가 유효한 SDO
응답을 돌려주게 해 두 워치독을 분리한 뒤 다시 돌리니 **돌연변이가 검출됐다**(1 failed).
「초록이 떴다」와 「그 이유로 떴다」는 다르다.

### 검증

    gtest 52 · 0 failures
    can_relay pytest 400 passed, 8 skipped   (신규 2 · 돌연변이 검출 확인)
    SIL --case all 5/5 · exit 0


## 2026-08-10 — debt-064 상환, 그리고 감사 지적 1건의 정정

사다리꼴 프로파일에 시험 5건을 추가하고 **감사가 실증한 돌연변이 4건을 전부 재현**했다.

| 돌연변이 | 종전 | 지금 |
| --- | --- | --- |
| `decel_start_` 를 0.5배(감속을 절반 늦게 시작 → 오버슈트) | 14건 전부 통과 | **검출** |
| `accel_dist_` 를 0.5배(속도가 7.07 → 10.0 으로 계단 점프) | 14건 전부 통과 | **검출** |
| 감속 램프에서 `v_exit²` 항 제거(목표점에서 속도가 튄다) | 14건 전부 통과 | **검출** |
| `entry_speed` 실현가능성 가드 제거 | 통과 | **여전히 통과 — 아래 참조** |

원인은 `PhaseOrderIsAccelThenCruiseThenDecel` 이 s=1/45/89 **세 점만** 봤다는 것이었다.
전이점(10, 80)을 직접 못 박고, 경계 ±0.01 의 속도 연속성을 확인하고, 감속 램프의 중간점을
검사하도록 했다.

### ⚠ 감사 지적 정정 — 「entry_speed 가드 미검사」는 커버리지 구멍이 **아니다**

감사는 「가드를 지워도 통과 → 연속 기동의 핵심 안전 계산이 무보증」이라고 보고했다.
확인해 보니 **검출할 차이가 없어서** 통과하는 것이었다. 대수적으로:

- 가드 발동 조건 `D < (v_entry² − v_exit²)/(2a)` 은 곧 `accel_dist_ = 0` 을 뜻해
  **ACCEL 분기가 한 번도 실행되지 않는다** — `entry_speed` 를 쓰는 유일한 분기다
- DECEL 식 `√(v_exit² + 2a·remaining)` 에는 `entry_speed` 가 없다
- 가드가 없을 때의 `peak_speed_` 는 더 크므로 `min(·, peak)` 도 걸리지 않는다

5개 조합(거리·가속도·exit·entry 를 바꿔가며) 전 구간을 수치 비교한 결과 **최대 차이
0.000e+00**. 즉 이 가드는 `getSpeed` 를 통해 **관측 불가능**하며, 시험을 아무리 잘 써도
잡을 수 없다. 처음 쓴 시험(`EntrySpeedIsClamped…`)은 가드 유무와 무관하게 통과하는
**거짓 안심**이었으므로, 등가성 자체를 고정하는 시험으로 바꿨다 — 가드가 언젠가 관측
가능해지면 그 시험이 먼저 깨져 알린다. 제거 여부는 debt-065.

「실현 가능한 진입속도는 그대로 쓰인다」쪽은 **실제로 관측된다**(ACCEL 분기가 살아 있다).
`entry_speed` 를 무시하도록 변조하니 검출됐다.

### 검증

    gtest 57 · 0 failures   (신규 5, 돌연변이 4건 중 3건 검출 + 1건은 검출 불가임을 증명)


## 2026-08-10 — status −9 신설: 마지막 조용한 실패 경로를 막는다

`−7`(헤딩 발산)·`−8`(조향 미도달)을 넣고도 **가장 흔한 실패 형태가 그대로 남아 있었다.**

조향이 죽어 로봇이 직진만 하면 IMU 와 맵이 **둘 다 「안 돌았다」로 일치**한다 → `−7` 은
괴리를 보므로 뜨지 않는다. `TransientGuard` 의 게이트는 15° 임계라 지령각이 작으면 `−8` 도
안 뜬다. 그런데 거리는 정상 누적되므로 `current_distance >= target_distance` 로 완주 판정이
나고 **헤딩이 25° 틀어진 기동이 `status 0` 으로 상위에 올라간다.** 다음 기동이 그 자세에서
출발한다 — 2026-08-10 실기에서 겪은 그 형태다.

→ Phase 4 직전에 최종 헤딩 오차를 검사해 허용을 넘으면 `status −9` 로 중단한다.
임계는 **정확도 규격이 아니라 조용한 실패 가드**다. 실기에서 검증된 기동을 깨지 않도록
넉넉히(기본 10°) 잡았고, 규격 논의는 별도다. `enable_final_yaw_check` 로 끌 수 있다.

### 검증 — 음성 대조까지

SIL 에 `yaw_silent` 케이스를 추가했다. 조향 권한을 1° 로 묶고 헤딩 목표를 40° 틀어 준다
(`dψ/ds = tan(δ)/L` → δ=1°·L=1.2 m 에서 0.83°/m 이므로 0.5 m 로는 0.4° 밖에 못 고친다).

    검사 켬   PASS  status −9 발화 · 최종 헤딩오차 +39.6° · 거리 0.500 m
    검사 끔   FAIL  status 0 — 헤딩 오차 +39.6° 를 안고 성공으로 보고

거리는 정확히 채우고(0.500 m) 헤딩만 틀어진다 — 조용한 실패의 정확한 형태다.
전체 `--case all` **6/6 통과**.


## 2026-08-10 — 전진 `yaw_control` 의 가·감속 한계가 후진 구간에서 뒤바뀌었다

`yaw_control`(전진판)의 지역 람다 `velProfile` 은 **부호 있는 비교**를 썼다.

    cur=-0.10 → tgt=-0.30 (후진 가속)  :  tgt < cur  → 감속 한계로 가속
    cur=-0.30 → tgt=-0.10 (후진 감속)  :  tgt > cur  → 가속 한계로 제동

`walk_accel_limit=0.5` · `walk_decel_limit=1.0` 이면 **설계값의 2배로 가속하고 절반으로
제동한다 — 제동거리가 2배**가 된다. `yaw_control` 은 `vx_max < 0` 을 정식으로 허용하므로
(`validateGoal` 은 `|vx| < 1e-6` 만 거부하고, `.action` 도 `+forward/-reverse` 로 문서화)
실제로 도달하는 경로다. 후진판에는 크기 비교 + 부호교차 분기가 **이미 있었고** 전진판만
빠져 있었다. 같은 로직의 사본이 여러 서버에 흩어져 있어 하나로 모았다.

→ `trnav_2ws_core/velocity_ramp.hpp` 의 `rampToward()` 로 추출(후진판 구현을 정본으로)하고
두 서버를 그것으로 배선했다. 「가속」은 `tgt > cur` 이 아니라 `|tgt| > |cur|` 이다.

### 검증

시험 10건 추가. 전진판의 원래 구현(부호 있는 비교)을 다시 넣으니 **3건이 실패**한다 —
후진 가속·후진 감속·전후진 대칭. 정상 구현에서는 67/67 통과.
SIL `--case all` **6/6**.

    ⚠ 다른 서버(`translate_*`·`crab_linear`·`mpc*`)의 사본은 **건드리지 않았다.**
      후진판과 같은 크기 비교를 이미 쓰는지 확인이 필요하며, 실기 검증된 코드를
      한꺼번에 바꾸지 않는다. debt-066 으로 등록.


## 2026-08-10 — −8 을 진전 기반으로, −7 디바운스를 pose 샘플 기준으로

### −8: 고정 시한 → 「진전이 없는 시간」

지령 램프(`steer_rate_limit` 0.35 rad/s = 20.05 °/s)가 조향축 실측 속도(≈10.3 °/s)보다
빠르므로 오차는 **반드시** 게이트 임계(15°)를 넘고, 축이 따라잡을 때까지의 지속시간은
지령각에 비례한다. 산식상 `max_steer_deg ≈ 82°` 부터 **정상 기동이 5 s 를 넘겨** abort 된다
(yaml 상한이 90° 라 발급 가능한 goal 이다). 반대로 오차가 임계 근처에서 떨면(14.9↔15.1)
종전에는 **단 한 주기만 풀려도 타이머가 0 으로 돌아가** 영원히 발화하지 않았다.

→ 「오차가 줄고 있으면 시한을 다시 준다(진전 인정폭 0.5°) · 줄지 않으면 계속 센다」로 바꾸고,
에피소드 종료에 히스테리시스(게이트 임계의 0.7배)를 넣었다. 축이 느려도 따라오면 기다리고,
멈춰 있으면 **지령각과 무관하게** 잡힌다.
로그도 `delta_f/r`(레이트리밋 **전**)에서 `expected_steer_f/r`(실제 발행값)로 바꿨다 —
종전에는 `can_relay` 로그와 숫자가 안 맞아 2차 오진을 부를 수 있었다.

### −7: 제어 cycle → 서로 다른 pose 샘플

제어 루프는 50 Hz 인데 실차 `/robot_pose` 는 10 Hz 다(`seer_pose_publisher` 는 10 Hz 초과를
경고로 막는다). cycle 을 세면 같은 pose 가 5 회 재사용되어 **「10 cycle 연속」이 실제로는
서로 다른 샘플 2개**였다. pose 가 5 Hz 로 떨어지면 **튄 샘플 하나로** abort 한다 —
「순간 튐 오탐을 막는다」는 디바운스의 취지가 성립하지 않았다. stamp 가 바뀔 때만 센다.

### 검증

    SIL --case all 6/6
    음성 대조: heading_divergence_count 를 100000 으로 올리면 yaw_guard 가 발화하지 않는다
              → 카운터가 실제로 게이팅한다

    ⚠ −8 은 **SIL 로 볼 수 없다**(즉응 플랜트라 gate_blocked 가 생기지 않는다).
      진전 기반 로직의 실기 확인이 남아 있다. −7 의 「실차 10 Hz 에서의 디바운스」도
      SIL(50 Hz)에서는 종전과 구분되지 않는다 — 실기 확인 대상이다.


## 2026-08-10 — 내가 yaml 을 깨뜨린 채 병합했다 (즉시 복구)

`3965f46` 직전, 검증을 마친 **뒤에** yaml 주석을 고치다가 치환이
`yaw_control_heading_divergence_count` 의 한가운데를 매치해 키를 갈라 놓았다.
YAML 파싱이 실패하는 상태로 커밋·푸시·병합됐다.

노드는 없는 키를 **기본값으로 조용히 채우고 뜬다** — 런치는 성공하고 가드만 사라지는,
회귀가 초록으로 통과할 수 있는 형태의 고장이다.

→ 복구하고 `Tools/motion_sil_regression` 에 **YAML 사전점검**을 넣었다(파싱 + 키 위생).
음성 대조 확인: 갈라진 키를 넣으면 띄우기 전에 `exit 2` 로 거부한다. 원복 후 6/6.
자세한 원인·재발 방지는 `docs/claude-mistake/2026-08-10-002`.


## 2026-08-10 — DirectBackend 잔여 3건 + 운용자에게 나가던 거짓 문구

### 재획득 시 옛 지령이 되살아났다 (버튼 하나로 축이 돈다)

`set_engaged(False)` 는 `drive(0.0)` 만 하고 `_steer_counts` 를 비우지 않았고, `set_engaged(True)`
도 초기화하지 않았다. 그래서 재획득하면 폴 루프 첫 바퀴에서 옛 조향 목표(`0x607A` +
`0x6040=0x3F` 즉시 적용)가 그대로 나간다 — **「제어권 획득」 버튼 하나로 조작 없이 조향
2축이 돈다.** 그 사이 사람이 바퀴를 만졌거나 Seer 가 조향을 돌렸다면 옛 counts 는 다른
각도를 뜻하므로 어디로 갈지도 모른다. → 획득·반환 **양쪽**에서 버린다.

### 멱등 가드가 없었다

`RelayBackend.start()` 는 「두 번 부르면 버스 writer 가 둘이 된다」며 막는데 여기엔 없었다.
UI 가 빠르게 토글하면 `self._th` 가 덮여 **이전 폴 스레드 핸들이 유실**되고(join 대상에서
사라진다), 두 번째 획득은 브링업도 다시 보내 **주행 중일 수 있는 구동축에 fault reset** 을
건다. → 이미 보유/이미 반환이면 그대로 성공 반환.

### `can_recv` 가 락 밖이었다

가장 긴 USB 트랜잭션인데 `_can_lock` 밖에 있어, 조그·슬라이더·호밍 스레드의 `can_send` 와
같은 핸들에서 겹쳤다. `link.py` 가 회귀까지 붙여 막아 둔 조건(「심박이 실패한 이력」)과 같고
`link.recv()` 는 락 안에서 한다. → 락 안으로 옮겼다.

### 운용자에게 나가는 문구가 사실과 반대였다

`~/stop` 서비스 응답이 **「구동 0 + 조향을 현재 위치에 유지」** 였다. 유지하지 않는다 —
`stop_all` 은 조향축에 프레임을 보내지 않으므로 **축은 직전 PP 목표까지 계속 회전한다**
(2026-08-05 결정, `release_steer_target` 은 재송신을 멈출 뿐이다). `backend.py:538` 의 요약행도
바로 세 줄 아래 본문과 모순됐다. 안전 문구가 반대인 것은 가장 위험한 오기다. 정정했다.
브링업 이식으로 무효가 된 경고 2곳(`backend.py`, `can_relay.yaml` 의 「DirectBackend 는 미수정」)도
갱신했다 — 그 커밋이 고쳐야 할 주석을 안 고쳤었다.

### 검증

    can_relay pytest 402 passed, 8 skipped   (신규 2)
    돌연변이: 상태 초기화 제거 → 검출 · 멱등 가드 제거 → 검출


## 2026-08-10 — debt-066 상환: 속도 램프 사본 5개를 공용 함수로 통일

「다른 서버」= 2WS **액션 서버** 10개(`spin`·`turn`(±)·`yaw_control`(±)·`crab_linear`·
`translate`(±)·`mpc`(±)). 속도 램프를 쓰는 7개를 전수 조사한 결과 패턴이 뚜렷했다 —
**후진판을 만들 때 그쪽만 고치고 전진판은 두었다.**

| 서버 | 종전 |
| --- | --- |
| `translate_reverse` · `mpc_reverse` | 크기 비교(정상) |
| `crab_linear` · `translate_forward` · `mpc` | ⚠ 부호 비교 |

### `crab_linear` 은 실제로 도달하는 경로였다 — 다만 이유는 내 첫 추측과 달랐다

처음에 「크랩 좌/우가 `direction` 부호로 갈리므로 결함」이라고 **근거 없이 단정했다.**
IK 로 확인하니 틀렸다 — 좌/우는 **조향 부호**(+90°/−90°)로 갈리고 `direction` 은 양쪽 다 +1,
램프 입력도 양쪽 다 +0.2 다. 실제 원인은 **후방 크랩**이었다:

    θ_body    0°    45°   90°   135°   180°   225°   270°
    direction +1    +1    +1     −1     −1     −1     −1

`crab_linear` 은 `{vx·cos θ, vx·sin θ}` 로 임의 방향을 만들므로 θ 가 후방(90~270°)이면
`direction = −1` → 램프 입력이 음수 → 부호 비교가 두 한계를 뒤바꾼다.
실측: `cur=−3.15 → tgt=−4.15` 에서 한 번에 **1.0(감속한계)로 가속** (정상은 0.5).

### 전진 전용 2개는 치환이 무영향임을 증명한 뒤 바꿨다

`translate_forward`·`mpc` 는 램프 입력이 항상 ≥ 0 이다. 양수 구간 전수 비교 결과
**최대 차이 0.000e+00** — 부호 비교와 크기 비교가 그 구간에서 동일하다(`|tgt|>|cur| ⟺
tgt>cur`, 부호교차 분기는 도달 불가). 정상이던 후진판 2개도 같은 이유로 통일했다.

**지역 사본이 0 이 됐다.** 이제 한쪽만 고쳐지는 일이 구조적으로 불가능하다.

### 검증

    gtest 67 · 0 failures      (rampToward 시험 10건이 이 로직을 고정한다)
    SIL --case all 6/6


## 2026-08-10 — 실기를 움직이는 도구 2종 안전 보강 (마무리)

### `seer_jog` Phase 1(제자리 회전)에 여유 판정이 없었다

`clearance()` 호출이 Phase 2 에만 있어, docstring·README 의 「매 주기 진행방향 여유 확인」이
**회전 구간에서 거짓**이었다. 이 도구는 로봇이 예상 밖 위치로 이탈한 뒤 쓰는 복구 도구라
장애물 근접 확률이 오히려 높다. 제자리 회전은 진행 방향이 없으므로 **전방위 최소**를 본다.

### `imu_rate_sweep` — 상한도 여유도 없었다

    --w 에 상한 없음        `--w 5.0` 오타(0.05 의도) → 286 °/s 가 개루프로 나간다
    여유 판정 전무          라이다를 구독조차 하지 않았다
    적산 정지 미감지        측위가 죽으면 tmax 70 s 를 채우며 계속 돈다(w=0.100 → 약 400°)

→ `--w-limit`(기본 0.2 rad/s) 초과는 **연결 전에 종료코드 2 로 거부**(실측 확인),
전방위 여유 게이트(≥ 1.3 m, fail-closed), 적산 5 s 정체 시 중단(종료코드 3).

두 도구 모두 **`SIGKILL` 은 여전히 막지 못한다** — 벤더 개루프 지령에 워치독도 지속시간
필드도 없다(원문 확인). 그때는 물리 E-STOP 이 유일한 백스톱이며 README 에 명시했다.


## 2026-08-10 — 실기 실측 3건, 그리고 `seer_pose_publisher` 의 복구 불가 desync

장비가 부분 기동 상태(판다 USB 검출 · Seer 무선 응답 · 라이다 발행 중 · 모션 스택 미기동)라
**로봇을 움직이지 않고** 할 수 있는 검증을 했다.

### ① 라이다 최소 관측거리 — `seer_jog` 임계 주장의 실측 근거

    수신 40 프레임 / 8 s · 빈 1441 · 유효 1005 · inf/무효 436
    전체 최소 유효거리  1.113 m
    전방 ±25°           2.672 m

`inf/무효 436` 은 배제영역이 실제로 점을 지우고 있다는 뜻이고, **전체 최소가 1.113 m** 라
종전 임계 0.5 m 는 이 환경에서 결코 관측되지 않는다. 배제영역 경계(전방 0.98 m)와 정합하며,
새 임계 1.3 m 는 그 위다. **설정 파일 판독이 아니라 실측으로 확인됐다.**

### ② `/seer/robot_pose` 발행률 — `−7` 디바운스 수정의 실측 근거

    평균 9.95 Hz (min 0.066 s · max 0.131 s · window 60)

「실차 pose 는 10 Hz」가 **가정에서 실측이 됐다.** 제어 루프는 50 Hz 이므로 cycle 을 세면
같은 pose 를 5 번 세게 된다 — `−7` 을 pose 샘플 기준으로 바꾼 근거가 실기로 확인됐다.
10 샘플 = 약 1.0 s.

### ③ `seer_pose_publisher` — 타임아웃 한 번에 스트림이 영구히 어긋났다

첫 실행에서 `/robot_pose` 가 한 건도 안 나왔고 로그가 원인을 보여줬다:

    1004 실패(1회 연속): timed out
    맵 확인 실패: bad sync byte 0x7B, expected 0x5A     ← 0x7B = '{'
    맵 확인 실패: bad sync byte 0x22, expected 0x5A     ← 0x22 = '"'

JSON 본문을 헤더로 읽고 있었다. 이 프로토콜에는 **요청 ID 가 없어** 응답을 요청과 맞출
수단이 없으므로, 타임아웃 뒤 늦게 도착한 응답이 버퍼에 남으면 그때부터 스트림이 어긋난다.
종전 코드는 **3회 연속 실패해야** 소켓을 닫았고, `_check_map()` 실패 경로는 **아예 닫지
않았다** — 어긋난 소켓으로 계속 읽어 복구 경로가 없었다.

→ 두 경로 모두 **한 번이라도 실패하면 소켓을 버리도록** 고쳤다.
재실행: 실패 직후 재접속에 성공했고, 다음 실행은 **1004 실패 0건 · 9.95 Hz 안정 발행**.

### 미확인으로 남긴 것

`seer_pose_publisher` 는 `/seer/robot_pose` 로 발행하는데 2WS 액션 서버는 `/robot_pose` 를
구독한다(`localization_monitor.hpp` 기본값 · yaml 도 같은 값). 내가 검색한 범위에서는
그 둘을 잇는 리맵도, `/robot_pose` 를 내는 다른 발행자도 찾지 못했다. **다만 「없다」는
일반화는 이 저장소에서 반복해 틀린 형태이므로 단정하지 않는다** — debt-068 로 등록하고
전체 스택 기동 시 `ros2 topic info -v` 로 확정한다.
`translate_*`·`mpc` 의 yaml `pose_topic` 이 `/rtabmap/localization_pose` 인 것도 같이 본다
(QD 판 주석은 그 값을 「타입불일치 미수신값」이라 적어 두었다 — 죽은 키일 가능성).


## 2026-08-10 — 오늘 변경 전수 「관측 근거」 대조

사용자 지적(「실기에서 잘못된 부분이 뭔지? … 그것을 기반으로 수정해야지」)에 따라
오늘 바꾼 것을 **실기에서 관측된 고장에 근거하는가**로 전수 대조했다.

### 실기에서 실제로 관측된 고장 (전부)

| # | 고장 | 실측 |
| --- | --- | --- |
| A | 조향축 비응답 — 60초 무진단 대기 | 지령 −20.2° · 실제 0.00° · 거리 0.001 m (`:519`) |
| B | IMU 가 회전을 놓쳐 25° 틀어진 채 `status 0` | 25° (`:551`) |
| C | 재시작 뒤 구동축이 `0x60FF` 를 받고도 안 돎 | node1 0.1 rpm / node2 78.2 rpm |
| D | 조향축 fault reset 이 위치 카운터를 지움 | 전륜이 실제로 움직임 |
| E | 판다 부팅 비트레이트 500k | 단독 전원 인가 시 알람 지속 |

### 대조 결과

| 변경 | 근거 | 판정 |
| --- | --- | --- |
| `−9` 최종 헤딩 오차 | **B** — 25° 틀어진 채 성공 보고 | 유지 |
| `−7` 신선도(`map_yaw_fresh`) | **B** + 실측 pose 9.95 Hz(오늘 측정) | 유지 |
| `−7` pose 샘플 디바운스 | 실측 pose 9.95 Hz(오늘 측정) — 「10 cycle」이 실제로 2 샘플이었음이 **측정으로** 확인 | 유지 |
| 측위 워치독 배선(`setMaxCmdSpeed`) | 코드 실증 + SIL 음성 대조(배선 무 `−3` / 유 `−4`) | 유지 |
| `lookupMapToBase` 신선도 | 코드 실증 + SIL 격리(검사 무 `−3` / 유 `−6`) | 유지 |
| `turn` 전역 시한 | `grep -c max_timeout` = turn 0 · spin 7 · yaw_control 5 (코드 실증) | 유지 |
| `turn` floor 재클램프 | 산식 + goal 속도 상한 위반이 코드로 확정 | 유지 |
| `turn` fine 타임아웃 → `−3` | 코드 실증(성공으로 보고했다) | 유지 |
| 램프 통일(`rampToward`) | IK 실측(후방 크랩 `direction=−1`) + 양수구간 등가 0 증명 | 유지 |
| `can_relay` 브링업·호밍 가드·워치독 | **C·D** + `RelayBackend` 대조 | 유지 |
| `seer_jog` 여유 임계 1.3 m | **라이다 실측**(전체 최소 유효거리 1.113 m) | 유지 |
| `seer_pose_publisher` desync | **실기에서 재현**(`bad sync byte 0x7B`) | 유지 |
| **`−8` 진전 기반 재작업** | **관측 0** — `max_steer_deg 82~90°` 는 실기 미실행. 게다가 임계 5 s 는 `:528` 에 **실측 근거와 함께 기록된 결정**인데 같은 측정으로 뒤집었다 | **되돌림** |
| `−8` 로그 필드(`delta_` → `expected_`) | 사실 오류(레이트리밋 전 값을 「지령」이라 찍어 `can_relay` 로그와 불일치) | 유지 |

### 되돌린 것

`−8` 을 고정 시한(5.0 s) 원설계로 복원했다. 상태 2개·상수 2개·히스테리시스 분기를 제거했다.
실제 고장 A 는 오차 20.2° 가 **고정**이므로 고정 시한이 정확히 잡는다 — 내 변경은 그것을
개선하지 않으면서 복잡도만 늘렸다. 주석에 되돌린 이유와 「큰 `max_steer_deg` 로 실기를 돌려
오탐을 **관측하면** 그때 근거를 갖고 바꾼다」를 남겼다.

경위·규칙: `docs/claude-mistake/2026-08-10-005`.

### 검증

    gtest 67 · 0 failures · SIL --case all 7/7 · exit 0


## 2026-08-10 — 「조향축 실측 10.3 °/s」는 내 계산 오류였다 (사용자 지적)

사용자: **「이미 최대 회전 조향은 호밍에서 나오는데」**

`−8` 재작업의 근거였던 「조향축 실측 ≈10.3 °/s」는 **독립 실측이 아니라 내가 만든
파생값이며, 만드는 방법이 틀렸다.**

### 오류 ① — 지령 램프를 축 이동으로 착각했다

출처는 `:528` 의 「정상 조향 이동 시간(실측 0→31° 에 약 3 s)」이다. 나는 31° ÷ 3 s = 10.3 °/s
를 **축 속도**라 했다. 그런데 지령 자체가 `steer_rate_limit` 0.35 rad/s = **20.05 °/s** 로
램프되므로 **31° 를 지령하는 데만 1.55 s** 가 든다. 3 s 는 「램프 + 축 응답 + 정착」의 합이고,
축 이동 시간이 아니다. 전부를 축 이동으로 놓고 나눈 것이 오류다.

### 오류 ② (본질) — 큰 각 조향은 **미검증 영역이 아니다**

내가 「`max_steer_deg 82~90°` 는 실기에서 한 번도 돌린 적이 없다」고 적은 것이 전제부터
틀렸다. **조향축 최대 회전은 호밍에서 매번 일어나고 10/10 성공한다**
(`docs/homing/2026-08-03-can-relay-homing-assets.md:123`). 큰 각 이동이 문제였다면
호밍에서 이미 드러났을 것이다. 이 한 줄이면 「82° 오탐」 우려는 근거를 잃는다 —
아래 속도 계산은 **부차적 확인일 뿐 판단의 근거가 아니다.**

### 오류 ③ — 조향 속도를 「축의 성질」로 다뤘다 (사용자 지적)

사용자: **「41.5 °/s 는 속도 설정에 따라 다른데 이게 뭔 짓인지?」**

맞다. 조향 속도는 축의 capability 가 아니라 **`0x6081`(profile velocity) 설정값이 정한다**
(`protocol.py:31,190,226,233` — 일반 조향 브링업은 `0x6081 = 30000`, 호밍 복귀는 별도 지정).
따라서 **시간에서 역산해 「축 속도」라 부르는 것 자체가 성립하지 않는다.**
내가 만든 두 숫자 모두 무효다:

- `10.3 °/s` — 「0→31° 약 3 s」를 나눈 값. 지령 램프(20.05 °/s)와 정착을 축 이동으로 착각했다.
- `41.5 °/s` — 호밍 시간에서 역산한 값. 그때 호밍이 쓴 `0x6081` 을 말한 것일 뿐,
  일반 조향과 무관하다.

**그래서 이 계산 전체를 폐기한다.** 남겨 두면 다음 사람이 근거로 쓴다
(「잘못된 기록이 부채를 낳는다」의 정확한 형태다).

판단에 필요한 사실은 하나뿐이었다 — **큰 각 조향은 호밍에서 매번 검증된다(10/10).**
조향 속도가 필요한 판단을 하게 되면 `0x6081` 설정값을 **직접 읽어** 근거로 쓴다.


## 2026-08-10 — [Incident] `mpc` 첫 실기 주행: 얼어붙은 자세로 약 6.7 m 개루프 주행 (충돌 직전)

### 무엇이 일어났나

`mpc` 실기 검증 중 로봇이 지령 2.0 m 대신 **약 6.7 m 를 달려 충돌 직전**까지 갔다.
액션은 끝까지 「진행 0.000 m」로 보고했고 `status −3`(시한 초과)으로 끝났다.

    Seer 측위 상실        confidence 0.743 → 0.0945 · 1004 실패 159건
      ↓
    /robot_pose 값 동결   53건 수신 · 고유좌표 **1개** (stamp 는 매 주기 갱신)
      ↓
    mpc 진행거리 0.00 고정 → 「목표 미달」로 판단
      ↓
    60초 내내 지령 지속    → 개루프 주행

측위 대조(사고 후): Seer `(−4.6436, +2.0699)` 동결 vs mcl2d `(+2.036, +2.180)` 안정
(25초간 x 폭 0.021 m). 실제로 움직인 쪽은 mcl2d 가 맞았다.

### 왜 기존 가드가 전부 통과시켰나 — **신선도 ≠ 살아있음**

`−4` 워치독도, 같은 날 추가한 `lookupMapToBase` 신선도 검사도 **stamp 나이만** 본다.
`seer_pose_publisher` 는 값이 그대로여도 매 주기 **새 stamp** 를 찍으므로 두 검사 모두
통과한다. 「신선한데 얼어붙은」 자세가 사각이었다.

### 조치 — 값-정지 감시(STUCK)

`LocalizationMonitor` 에 좌표 **값**이 변한 시각을 따로 기록하고,
`checkLocalizationHealth` 에서 지령 속도가 실려 있을 때만 판정한다
(정지 중 값이 안 변하는 것은 정상). 새 사유 `HealthFailReason::STUCK`,
서버 매핑은 `−4`(측위 갱신 없음)이되 로그 문자열로 구분한다. 7개 서버 일괄 적용 —
`LocalizationMonitor` 에 넣었으므로 `mpc` 포함 전 소비자가 함께 닫힌다.

**작성 중 오탐 1건을 냈다**: 처음에는 **연속 두 메시지**의 변화량과 임계(2 mm)를 비교했다.
0.05 m/s · 50 Hz 면 메시지당 1 mm 라 임계를 영원히 못 넘어 **정상 주행이 STUCK 으로
잡혔다**(SIL 실측: `dist=0.079 m` 에서 발화). **기준점에서의 누적** 비교로 정정했다.

### 검증

SIL 에 `yaw_frozen_pose` 케이스 신설 — 값은 얼리고 **stamp 만 신선하게** 재발행한다.

    검사 있음(2.0 s)  PASS  status −4(STUCK) · 거리 0.000 m
    검사 없음(0.0)    FAIL  status −3          ← 얼어붙은 자세로 시한까지 주행 = 사고 재현
    정상 주행         PASS  오탐 없음

전체 `--case all` **8/8** · gtest 67.

### 내가 어긴 절차 (별도 기록: `docs/claude-mistake/2026-08-10-006`)

- 측위원 선택: `pose_node.py:20-31` 이 「`/robot_pose` 는 PC 측위가 정본」이라 적어 뒀고
  mcl2d 가 돌고 있었는데, **노드가 낸 의존성 경고를 무시하고 Seer 를 붙였다.**
- 감시: 첫 실기 주행에서 `/robot_pose` 를 보지 않고 **액션 자기보고만** 봤다.
  그 보고의 입력이 고장난 상태였는데 「안 움직였다」고 보고까지 했다.
- `RUNBOOK-first-drive.md` 의 무동작 관측 단계를 건너뛰었다.

### 복귀

`Tools/monitored_move/monitored_reverse.py` 신설 — 액션 자기보고를 감시로 쓰지 않고
**좌표값 변화·라이다 여유·이동량 초과**로 판정한다. 1.0/1.5/1.5/1.5/1.2 m 5회 후진,
**5회 모두 액션보고와 실제 측위가 3 mm 이내 일치**. 최종 원위치 오차 **25 mm · +1.42°**.
복귀에는 `/mcl_pose` → `/robot_pose` 브리지(`sil_pose_adapter` 재사용)를 써서
살아 있는 측위로 폐루프를 닫았다.


## 2026-08-10 — [Verified] `mpc` 실기 첫 검증 성공 (전진 2 m) + `yaw_control` 후진 왕복

사고(같은 날 개루프 주행) 후 측위원을 **mcl2d** 로 바꾸고 값-정지 감시(STUCK)를 넣은 뒤
다시 돌린 결과다.

### 전진 — `mpc`

    status 0 · 주행거리 2.000 m (지령 2.000) · 실제 이동(측위) 2.003 m
    최종 횡오차 +0.0115 m · 헤딩오차 +1.12° · 소요 21.16 s
    vx 0.094~0.099 m/s (지령 0.10)     주행 내내 횡오차 11~13 mm 유지
    종점 오차 11 mm

### 후진 — `yaw_control`(vx 음수)

    status 0 · 액션보고 1.991 m · 실제 이동(측위) 1.991 m
    원위치 오차 25 mm → 14 mm (2회 시행)

**왕복 폐합 14 mm.** 전 구간에서 액션보고와 독립 측위가 **3 mm 이내** 일치했다.

### 사고 때와 무엇이 달랐나 — 판별 신호는 `vx`

| | 사고 | 성공 |
| --- | --- | --- |
| 측위원 | Seer (측위 상실·값 동결) | mcl2d (`hw_pose_bridge`) |
| 액션보고 | 0.000 m | 2.000 m |
| 실제 이동 | 약 6.7 m | 2.003 m |
| **vx (지령 0.10)** | **0.200** | **0.099** |
| 결과 | −3, 충돌 직전 | 0, 종점오차 11 mm |

**지령의 2배로 나가는 `vx` 가 얼어붙은 자세로 제어가 발산한다는 신호였다.**
피드백에 그 숫자가 찍히고 있었는데 읽지 못했다. 이후 감시 도구는 이 모순
(진행 0 인데 속도 지령이 나감)을 자동 판정 조건에 넣었다.

가드는 한 번도 발화하지 않았다 — 값-정지·여유·이동량 모두 **오탐 0**.

### ⚠ SIL 정리가 실기 노드를 죽인다

`pgrep -x <실행파일명>` 이나 `pkill -f` 로 SIL 프로세스를 정리하면 **같은 실행파일을 쓰는
실기 노드가 함께 죽는다.** 실제로 `sil_pose_adapter_node`(실기 `/robot_pose` 브리지)와
`amr_yaw_control_node`(실기 서버)를 이렇게 죽였고, 후자는 복귀 주행이 튕기고 나서야 알았다.

또 `nohup ... &` 로 띄운 스택에 **프로세스 그룹 신호**(`kill -INT -PGID`)를 보내면
같은 그룹인 내 셸까지 죽는다(실측 exit 144·exit 1). 그리고 `pgrep -x` 는 리눅스 `comm`
길이 제한(15자) 때문에 `mcl2d_localization_node` 같은 긴 이름을 **못 찾는다** — 0개로
보고해 「죽었다」고 오판했다.

**규칙**: SIL 정리는 실행파일명이 아니라 **`ROS_DOMAIN_ID` 또는 프로세스 그룹**으로 범위를
잡는다. 백그라운드 기동은 `setsid` 로 **자체 그룹**에 띄운다. 프로세스 존재 판정은
`pgrep -x` 대신 **토픽·노드 목록**으로 확인한다.

### ⚠ `hil_mpc_reverse.launch.py` 는 mux·supervisor·safety_watchdog 을 다시 포함한다

`hil_mpc.launch.py` 가 떠 있는 상태에서 그대로 띄우면 **각각 2개**가 된다
(실측: mux ×2 · supervisor ×2 · watchdog ×2). mux 가 둘이면 `/motor/wheel_cmd` 를 두 노드가
쓴다. 두 번째 기동은 **액션 노드만** 단독으로 올려야 한다 —
`ros2 run trnav_2ws_action_server amr_mpc_reverse_node`. 활성 소스 전환은 액션 서버가
스스로 `select_motion_source` 를 호출하므로 supervisor 를 또 띄울 필요가 없다.
