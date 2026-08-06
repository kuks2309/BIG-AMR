# ADR 2026-07-31 — 체인 상류 2노드(mux · translator) 이식 + 메시지 패키지 통합

- **Status**: Proposed — 2026-07-31. 사용자가 「깃에서 찾아서 진행」 → 「QD·2WS 둘 다」 →
  「`trnav_msgs` 로 통합」 순으로 지시했다. 빌드 검증까지 수행하며 **실기 구동 0**.
  최종 verdict 는 저자가 찍지 않는다(coding SOP 룰 7).
- **Supersedes(부분)**: `docs/adr/2026-07-26-2ws-motion-from-qd-refactor.md` §기각안의
  「공유 패키지(interfaces/msgs/core) 는 QD 재사용 … → 전 패키지 리네임(자립)」 중 **msgs 부분만**.
  나머지(kinematics·core·motion·action_server 리네임, geometry 교체)는 유효하다.

## Context

### 문제 1 — 체인 상류 2노드 부재 (debt-021)

액션 서버 9종은 `/motion/wheel_cmd/<action>` 까지만 내보내고, 그 뒤 `trnav_motion_mux`(중재) ·
`amr_motor_cmd_translator`(SI→raw) 가 없어 `/motor/low_cmd` 를 발행하는 노드가 없었다
(확인 2026-07-31, 이식 전:
`find src -type d \( -iname '*mux*' -o -iname '*translator*' -o -iname '*canopen*' -o -iname '*arbitration*' \)` → **0건**;
`grep -rl "MotorCmdArray" src --include=*.cpp --include=*.hpp` → 발행 노드 **0건**, launch 참조만 존재).
저장소의 `sil_*.launch.py` 들이 이 노드를 참조하므로 **현 상태로는 launch 가 성립하지 않는다.**
`docs/adr/2026-07-31-can-relay-cpp-motor-layer.md` 가 can_relay 를 `/motor/low_cmd` 구독자로
내리기로 정했으므로, 상류가 없으면 체인이 이어지지 않는다.

### 상류 원본 조사 (2026-07-31)

`kuks2309/TR_Nav_ros2_ws` HEAD `ad7520981d500fa5881e548ef22fc92d0d7fe4a1` 얕은 클론 대조.

| 패키지 | 원본 경로 | 규모 | 의존 |
|---|---|---|---|
| `trnav_motion_mux` | `src/Control/AMR-Arbitration/` | hpp 43 + cpp 227 + yaml 131 + pytest 192 | `rclcpp`, `trnav_msgs` |
| `amr_motor_cmd_translator` | `src/Control/AMR-Motor/` | hpp 61 + cpp 220 + main 10 | `rclcpp`, `trnav_msgs` |

**의존 폐포가 닫혀 있다** — 두 패키지 모두 `rclcpp` + `trnav_msgs` 외 의존 0. 신규 시스템 패키지 **불요**.

### 문제 2 — 메시지 패키지가 둘로 갈려 있었다

본 저장소는 `trnav_msgs`(QD 아래) 와 `trnav_2ws_msgs`(2WS 아래)를 병존시켰다. `.msg` 파일은
**바이트 동일**(`diff -rq` 0건)이지만 패키지명이 달라 **ROS2 타입이 서로 호환되지 않았다.**
그래서 상류 2노드를 그대로 이식하면 QD 에만 붙고 **2WS(실물 Foil_A082 inline dual-steer)에는
붙지 않는다.**

> **플랫폼 귀속 (사용자 확인, 2026-08-07)** — 「이 AMR 의 휠 구조는 **2WS** 이고, **QD 는 이미
> 다른 곳에서 검증된 내용**이다.」 ⇒ 본 저장소의 검증·개발 대상은 **2WS** 이고 QD 스택은 검증된
> 참조(reference)로 둔다. 따라서 이후 실기 검증·파라미터 정렬(debt-025)·can_relay 연동은
> **2WS 경로를 기준**으로 하며 QD 는 대조용으로만 쓴다.

「QD 쪽을 `trnav_qd_msgs` 로 개명해 대칭을 맞추자」는 안이 검토됐으나 **조사 결과 기각**했다:

- **`trnav_msgs` 는 QD 전용이 아니다.** 상류에서 이 패키지를 의존하는 패키지가 **20개**이고
  QD 뿐 아니라 **DD 스택(`trnav_motion_dd`, `trnav_dd_kinematics`)** · 중재 · 모터 · 도킹 ·
  로컬라이제이션 · 안전 · SIL · ACS GUI 가 모두 공유한다.
- **메시지 자신이 플랫폼 무관을 선언한다** — `WheelSet.msg:1` 「Per-wheel motion command
  (**platform-agnostic**)」 이며 QD diagonal / DD / 4WS / Ackermann 해석을 나란히 적는다.
- ⇒ 플랫폼명을 붙이면 **사실과 어긋나고**, 향후 `Motion_Control/{4IS,DD}` 를 채울 때마다
  내용 동일·타입 비호환 사본이 계속 늘어난다.

## Decision

### 1. 메시지 패키지를 `trnav_msgs` 하나로 통합한다

- `src/Control/Motion_Control/QD/trnav_msgs` → **`src/Control/Motion_Control/Common/trnav_msgs`** 이동.
  QD 하위에서 꺼냄으로써 2026-07-26 ADR 이 우려한 **「2WS 가 QD/ 빌드에 종속」이 성립하지 않게 된다** —
  그 ADR 의 기각 사유 자체가 해소되므로 부분 supersede 가 정당하다.
- `src/Control/Motion_Control/2WS/trnav_2ws_msgs` **폐기**(디렉터리 삭제).
- 2WS 전 참조를 `trnav_2ws_msgs` → `trnav_msgs` 로 치환. 코드·`CMakeLists.txt`·`package.xml`·
  `launch/*.launch.py`·패키지 내 구조 문서까지 **34 파일**.

### 2. 상류 2노드를 `Common/` 에 이식한다 (원본명 유지, 2패키지)

| 배치 | 패키지명 | 바인딩 |
|---|---|---|
| `src/Control/Motion_Control/Common/trnav_motion_mux/` | `trnav_motion_mux` (원본명) | `trnav_msgs` |
| `src/Control/Motion_Control/Common/amr_motor_cmd_translator/` | `amr_motor_cmd_translator` (원본명) | `trnav_msgs` |

msgs 통합으로 **QD·2WS 가 같은 타입을 쓰므로 노드 사본이 불필요**하다 — 직전 검토안의 4패키지가
2패키지로 줄었다. 리네임·네임스페이스 변경 **0건**이라 upstream 대조가 그대로 유지된다.

### 3. 배치 근거

`README.md` §디렉토리 배치 규약 — ROS2 패키지는 `src/<도메인>/…`. QD 이식 ADR(2026-07-26)의
선례는 `Motion_Control/QD/` **바로 아래 평면 배치**였다(상류 `AMR-Motion/` 중간 폴더는 이미 접혔다).
본 이식도 상류의 `AMR-Arbitration/`·`AMR-Motor/` 를 재현하지 않고 `Common/` 바로 아래 둔다.
`Common/` 은 **플랫폼 무관 자산**(공유 msgs + 플랫폼 무관 노드) 전용 폴더로 신설한다.

### 4. 코드 로직은 변경하지 않는다

리네임·바인딩 외 **알고리즘·상수·파라미터 기본값 수정 0**. 특히 다음은 그대로 둔다:

- `kReservedRules` 12행 (Source ID ↔ name 계약, V-01~V-19 규칙 id 포함)
- 환산식 (`v * 60 * gear_walk * 10 / (r * 2π) * dir`,
  `(s - offset) * ppr * gear_steer / 2π * dir`)
- QoS `KeepLast(10).reliable().durability_volatile()`
- `amr_motor_cmd_translator_qd.yaml` 의 실측 파라미터 (`steer_offset_*_deg: -1.676` 등)

## Alternatives (기각)

- **`trnav_qd_msgs` 로 개명해 대칭** — 이름은 일관되나 플랫폼 무관 계약에 플랫폼명이 붙고,
  4IS·DD 확장 시 사본이 더 늘어난다. **기각**(§Context 문제 2 근거).
- **현상 유지 + 4패키지 이식**(QD 원본본 + 2WS 리네임본) — 기존 ADR 번복이 없어 범위가 작다.
  그러나 동일 코드 2벌이 영구화되고 msgs 중복도 남는다. **기각**(사용자 선택).
- **QD 전용 이식만 / 2WS 전용 이식만** — 한쪽 체인이 끊긴 채 남는다. **기각.**
- **상류 폴더 구조(`AMR-Arbitration/`·`AMR-Motor/`) 재현** — QD 이식 선례가 이미 상류 중간
  폴더를 접었으므로 일관성이 깨진다. **기각.**

## Consequences

### 이득

- **debt-021 해소** — `/motor/low_cmd` 발행자가 생겨 체인이 이어진다.
- **구조적 중복 제거** — 바이트 동일 msgs 2벌이 1벌이 됐다. 이식 노드도 4→2패키지.
  `Motion_Control/{4IS,DD}` 를 채울 때 msgs 사본 추가가 **0** 이다.
- **upstream 대조 회복** — 이식 2노드는 리네임 0건이라 상류와 파일 단위 대조가 가능하다.
- 신규 시스템 의존 0 — `rclcpp` + 기존 msgs 뿐이라 빌드 환경 변경이 없다.

### 비용 / 남는 위험

① **2026-07-26 ADR 의 「2WS 자립」이 부분 번복됐다.** 2WS 는 이제 `Common/trnav_msgs` 에
   의존한다. 원래 우려(“QD/ 빌드에 종속”)는 msgs 를 QD 밖으로 꺼내 해소했으나, **QD·2WS 가
   같은 메시지 패키지를 공유한다는 사실 자체는 남는다** — 한쪽 요구로 msg 를 바꾸면 다른 쪽에
   파급된다. 상류가 20패키지 공유로 운영해 온 구조이므로 수용 가능하다고 판단했다.

② **QD·2WS 동시 기동 불가.** 토픽명(`/motor/low_cmd`, `/motor/wheel_cmd`)·서비스명
   (`/select_motion_source`)이 두 스택에서 동일하고, 이제 타입까지 같아져 **조용히 섞인다**
   (통합 전에는 `trnav_msgs` vs `trnav_2ws_msgs` 타입 불일치가 우연한 차단막이었다).
   배타 장치는 확인되지 않는다 — `grep -rniE 'flock|lockfile|pidfile|singleton|mutex_file'
   src/Control/Motion_Control --include=*.{cpp,hpp,py,yaml}` → **0건**(2026-07-31 실행).
   debt-018 과 같은 부류이며 그쪽은 CAN 계층, 이쪽은 모션 계층이다.
   **↑ 통합의 부작용으로 위험이 오히려 커진 지점이다. 신규 부채로 등록한다.**

③ **`amr_motor_cmd_translator` 는 2륜 pack 경로다.** `onWheelCmd` 가 `wheels.size() < 2` 를
   거부하고 `wheel_index_front/rear` 로 2개만 집는다. inline dual-steer 는 휠 2개라 동작하나
   경고 문자열이 `"QD: expect 2 wheels"` 로 남는다(로직 무변경 원칙에 따라 문구도 유지).

④ **파라미터 값이 QD 실측 기준이다.** `amr_motor_cmd_translator_qd.yaml` 의
   `wheel_radius_m: 0.08` · `gear_walk: 20.0` 은 상류 QD 플랫폼 값이고, 본 저장소 2WS 기하는
   `wheel_radius = 0.125` · `gear_walk = 32.0`(`trnav_2ws_core/config/robot_geometry_2ws.yaml`)로
   **다르다.** 본 ADR 은 값을 옮기지 않는다(실측 근거 없이 변경 금지 — debt-007 상환계획 ③ 준용).
   **실기 적용 전 정렬 필수.** 신규 부채로 등록한다.

⑤ **잔여 부재 노드**: `trnav_motion_supervisor` · `translate_sim_odom` 은 여전히 없다.
   `sil_*.launch.py` 는 아직 완전히 성립하지 않는다.
   > **⚠ 2026-08-07 후속 — 위 ⑤ 는 이미 해소됐다(원문은 이력 보존).** 본 ADR 작성(7/31) 이후
   > 다른 세션이 `Common/trnav_motion_supervisor` 를 이식하고 전 체인 SIL 런치를 추가했다 —
   > `origin/main` `bf6ba92`(체인 중간 노드 3패키지 git 추적 시작) · `1de6d9f`(전 체인 SIL 런치 +
   > 런북, 2026-08-06). 본 ADR 이 만든 `Common/` 3패키지도 그 커밋들로 이미 커밋돼 있다.
   > 따라서 **debt-026 은 낡았다** — 상태 갱신은 registry 소유 세션 소관이며 본 세션은 손대지 않는다.

⑥ **`can_relay` 와의 환산 이중 적용 위험은 그대로** — debt-022. 본 이식은 경계를 확정하지 않는다.

⑦ **stale 참조 1건(의도적 미수정)**: `src/Comm/CAN/can_relay/docs/code_review/can_relay_ros2/2026-07-29.md:303`
   이 `trnav_2ws_msgs/WheelMotor` 를 인용한다. **날짜 박제 리뷰 산출물이라 수정하지 않았다**
   (저장소 규약: 과거 시점 인용은 역사적 사실). 해당 리뷰를 다음에 갱신할 때 함께 정정할 것.

## Rollback

되돌림은 **디렉토리 조작 + colcon 산출물 제거**로 완결된다. 비가역 변경 없음(영속 상태·스키마·
펌웨어 무접촉). `Motion_Control` 은 git 미추적이므로(`git ls-files` 0건) git revert 가 아니라
파일 조작으로 되돌린다.

```bash
MC=src/Control/Motion_Control
# 1) 이식 2노드 제거
rm -rf $MC/Common/{trnav_motion_mux,amr_motor_cmd_translator}
# 2) msgs 통합 원복 — trnav_msgs 를 QD 아래로 되돌리고 2WS 사본 재생성
mv $MC/Common/trnav_msgs $MC/QD/trnav_msgs
cp -r $MC/QD/trnav_msgs $MC/2WS/trnav_2ws_msgs
#    2WS 사본의 패키지명·참조를 되돌린다(치환 방향 반대)
sed -i 's/trnav_msgs/trnav_2ws_msgs/g' $(grep -rl trnav_msgs $MC/2WS)
sed -i 's/trnav_msgs/trnav_2ws_msgs/g' $MC/2WS/trnav_2ws_msgs/{package.xml,CMakeLists.txt}
rmdir $MC/Common 2>/dev/null
# 3) 빌드 캐시 제거 후 재빌드 (경로 이동 캐시는 반드시 지워야 한다 — 본 작업 중 실제 실패 사례)
for p in $(find $MC -name package.xml -exec grep -oP '(?<=<name>)[^<]+' {} \;); do rm -rf build/$p install/$p; done
colcon build --base-paths $MC
```

debt-021 을 「미해결」로 되돌리고 본 ADR 을 `Status: Superseded` 로 표기한다.

## Verification

실행 명령·출력을 그대로 적는다. **실기 구동 0 · 판다 접속 0 · 실모터 0.**

### 1. 통합 치환 전수 확인

```
$ grep -rl "trnav_2ws_msgs" src/Control/Motion_Control/2WS | xargs sed -i 's/trnav_2ws_msgs/trnav_msgs/g'
[3] 치환 완료: 34 파일
$ grep -rc 'trnav_2ws_msgs' src/Control/Motion_Control/2WS | grep -v ':0$' | wc -l
0
```

### 2. 빌드 (13/13, error 0, stderr 0)

```
$ colcon build --base-paths src/Control/Motion_Control --cmake-args -DCMAKE_BUILD_TYPE=Release
Summary: 13 packages finished [1min 46s]
$ grep -cE "stderr|warning|Warning" build.log
0
```

13 = 기존 11(QD 6 − trnav_msgs 이동 + 2WS 5) + 신규 2. `trnav_2ws_msgs` 폐기로 12 → 11 이 됐고
mux·translator 2개가 더해져 13 이다. 설치 실행체 확인:
`install/trnav_motion_mux/lib/trnav_motion_mux/trnav_motion_mux_node`,
`install/amr_motor_cmd_translator/lib/amr_motor_cmd_translator/amr_motor_cmd_translator_node`.
`install/trnav_2ws_msgs` 부재 확인(폐기 반영).

⚠ **경로 이동 시 빌드 캐시를 반드시 지워야 한다** — 본 작업 중 실제로 실패했다:
`CMake Error: The source directory ".../QD/trnav_msgs" does not exist`.
`build/<pkg>`·`install/<pkg>` 제거 후 정상 빌드됐다(Rollback 절에 동일 절차 기재).

### 3. 런타임 배선 (mock 없음 — 두 노드만 기동, `ROS_DOMAIN_ID=77` 로 타 세션 격리)

```
$ ros2 run trnav_motion_mux trnav_motion_mux_node --ros-args --params-file <shipped yaml>
[INFO] [trnav_motion_mux]: Loaded 11 motion source(s).
[INFO] [trnav_motion_mux]: Config validation passed. 11 sources registered.
[INFO] [trnav_motion_mux]: MotionMuxNode started. output=/motor/wheel_cmd, default_id=0

$ ros2 run amr_motor_cmd_translator amr_motor_cmd_translator_node --ros-args --params-file <shipped yaml>
[INFO] [amr_motor_cmd_translator]: amr_motor_cmd_translator started. radius=0.0800 gear_walk=20.0 gear_steer=265.5 ppr=65536
```

토픽 타입이 **전부 `trnav_msgs`** 로 통일됐음(통합 성공의 직접 증거):

```
$ ros2 topic list -t | grep -E "motor|motion"
/motion/wheel_cmd/{joystick,translate_forward,translate_reverse,spin,crab_linear,turn,
                   yaw_control,yaw_control_reverse,mpc,mpc_reverse,dock} [trnav_msgs/msg/WheelSetArray]
/motor/wheel_cmd            [trnav_msgs/msg/WheelSetArray]
/motor/low_cmd              [trnav_msgs/msg/MotorCmdArray]
/motor/low_state            [trnav_msgs/msg/MotorStateArray]
/wheel_motor_state          [trnav_msgs/msg/WheelMotor]
/wheel_motor_state_detailed [trnav_msgs/msg/WheelMotorState]

$ ros2 topic info /motor/wheel_cmd
Type: trnav_msgs/msg/WheelSetArray · Publisher count: 1 · Subscription count: 1   ← mux → translator 연결됨
$ ros2 topic info /motor/low_cmd
Type: trnav_msgs/msg/MotorCmdArray · Publisher count: 1 · Subscription count: 0   ← can_relay 가 들어갈 자리
```

### 4. 이식본 회귀 시험

```
$ colcon test --packages-select trnav_motion_mux --base-paths src/Control/Motion_Control
$ colcon test-result --verbose --test-result-base build/trnav_motion_mux
Summary: 12 tests, 0 errors, 0 failures, 2 skipped
```

skip 2건은 **상류가 의도한 skip** 이며 본 이식의 회귀가 아니다 —
V-04(`source_ids=[0,1,3,3]` 중복 id 는 `std::unordered_map<uint8_t,...>` 가 흡수) ·
V-09(음수 id 는 `uint8_t` 캐스트로 도달 불가). 둘 다 C++ 타입 보장이라는 사유가 테스트 파일에 명시돼 있다.

### 5. 하지 않은 것 (반드시 남길 것)

장치 접속 0 · 판다 0 · 실모터 0 · SIL/HIL launch 미수행(`trnav_motion_supervisor`·
`translate_sim_odom` 부재로 성립 불가) · 액션 서버 → mux 실제 지령 흐름 미관측
(발행자를 띄우지 않았다 — 배선만 확인). **따라서 본 ADR 의 어떤 문장도 실차 거동을 확정하지 않는다.**
