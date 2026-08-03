# ADR 2026-08-03 — amr_test_gui 를 ROS2 로 이식(동일 구현): can_relay 패키지 안의 UI 노드

- **Status**: Accepted — 2026-08-03 (사용자 승인 「승인하고 테스트」). 구현·회귀 완료 · **실기 검증 0**
  — §Verification 게이트 1~3 충족, **게이트 4(잭업 실기 바이트 대조)는 미실행**이다.

## Context

세션 목적은 **「can relay GUI 구현을 ROS2 로 동일하게 구현」** 이다. 「동일」을 판정하려면 원본의
함수·전역·흐름이 표로 있어야 하므로 기준선을 먼저 만들었다 —
`docs/code_review/amr-test-gui/2026-08-03.md` (함수 56 전수 · 전역 G1~G15 · 전체 흐름도).

**원본**: `Tools/amr_test_gui/gui.py`(md5 `7a043e4c`, 1,157줄). PyQt5 단일 파일이 판다 USB 를 직접 열고
(`gui.py:783`) safety_mode 30·auth 0xe9·intercept 0xe8 를 잡은 뒤(`gui.py:812-817`) SDO 를 만들어 보낸다
(`gui.py:840-849`). ROS2 를 전혀 쓰지 않는다(`grep -c rclpy gui.py` → 0).

**이미 있는 것**: `src/Comm/CAN/can_relay` 가 같은 일을 ROS2 노드로 한다 — 같은 판다 계약(0xe9/0xe8/0xf3),
같은 SDO 인코더, 같은 안전 게이트. 2026-08-03 리뷰·조치로 회귀 230건이 붙어 있다.

**핵심 제약 — 판다는 한 프로세스만 연다.** GUI 와 `can_relay_node` 가 **각자** USB 를 열면 둘 다
제어권을 주장하고 heartbeat 가 겹친다(같은 날 H2 가 스레드 수준에서 보인 문제의 프로세스 수준 판). 따라서
이식본은 **판다를 직접 열지 않는다** — CAN 접근은 `can_relay_node` 가 단독 소유하고 UI 는 토픽·서비스만 쓴다.

**배치 제약**: 저장소 규약이 「UI 는 독립 `src/UI/` 를 만들지 말고 **대상 패키지 아래 `…/ui/` 에 종속**」
이라고 못박는다(`CLAUDE.md` §저장소 디렉토리 배치). ROS2 패키지이므로 `Tools/` 도 아니다.

## Decision

**① 위치**: `src/Comm/CAN/can_relay/can_relay/ui/gui_node.py` (신규 패키지를 만들지 않는다).
`setup.py` 의 `console_scripts` 에 `can_relay_gui = can_relay.ui.gui_node:main` 을 추가한다.

**② 역할 분리**: UI 노드는 **CAN·USB 를 만지지 않는다.** `panda` import 0, `can_send` 0.
모든 구동은 `can_relay_node` 의 토픽·서비스를 통한다. UI 가 소유하는 것은 화면·조그 시퀀스·Seer 조회뿐이다.

**③ 인터페이스 대조표 (원본 기능 → ROS2)**

| 원본 기능 (함수 #) | ROS2 인터페이스 | 동일성 |
| --- | --- | --- |
| 판다 검색 `#39 scan` | (없음 — 드라이버가 열거·검증) | **다름** ⓐ |
| USB 개폐 `#40 _on_usb` · 제어권 `#41 _on_take` | `~/engage`(`std_srvs/SetBool`) 1개 | **다름** ⓐ — 3단계가 1단계로 |
| 조그 8방향 `#45 _jog`·`#46 _jog_run` | UI 노드가 시퀀스 소유: `~/stop` → `~/steer_deg` → `joint_states` 정착 확인 → `~/drive_mmps` | 같음 |
| 정지 `#45("정지")` | `~/stop`(`std_srvs/Trigger`) | **개선** — 원본은 구동만, `stop_all` 은 조향까지 |
| 축별 조향 슬라이더 `#17 _send_steer`·`#18 _steer_axis` | **현재 대응 없음** → 신설 `~/steer_axis_deg` 필요 | **간극** ⓑ |
| 2축 동일 조향 `#44 _steer_to` | `~/steer_deg`(`std_msgs/Float64`) | 같음 |
| 호밍 `#47`·`#48`·`#49` | `~/home`(`Trigger`) + **`~/home_cancel`** | **개선** — 원본에 취소 없음 |
| 모터 표(각도·회전·전류) `#22`·`#23` | `/motor/low_state`(`trnav_msgs/MotorStateArray`) 구독 | 같음 (단 ⓒ) |
| 바퀴 그림 `#31`·`WheelView` | `joint_states`(`sensor_msgs/JointState`) 구독 | 같음 |
| 상태·경보 (제어권·심박·버스·abort) | `diagnostics`(`diagnostic_msgs/DiagnosticArray`) 구독 | **개선** — 원본에 없던 버스 헬스·워치독 노출 |
| Seer 비교 표 `#26`·`#28`·`#29` | 변경 없음 — UI 노드가 그대로 네트워크 조회 | 같음 |
| Seer Fatal 리셋 `#37` | 변경 없음 (Seer config 4300) | 같음 |
| 로그 창 `#38`·`log_line` | `rclpy` 로거 + 화면 append | 같음 |
| 종료 해제 4경로 `#11 safe_release` | `~/engage false` + `destroy_node()`; SIGINT/SIGTERM·atexit 배선은 **그대로 유지** | 같음 |

ⓐ **의도된 차이**: 「판다를 직접 열지 않는다」는 결정의 귀결이다. 원본의 scan/USB/제어권 3버튼은
   ROS2 에서 `~/engage` 하나가 된다(드라이버가 열거·중복 판다 거부·롤백까지 소유). UI 는 결과만 표시한다.
ⓑ **간극(해소 필요)**: `can_relay` 의 `~/steer_deg` 는 **두 축 동일각**이다(`backend.py` `set_steer_deg` 가
   `steer_nodes` 전체를 돈다). 원본의 축별 슬라이더를 동일하게 재현하려면 축별 지령 경로가 있어야 한다.
   → **`~/steer_axis_deg`(`std_msgs/Float64MultiArray`, `data=[node, deg]`) 를 드라이버에 신설**한다.
   같은 안전 게이트(클램프·호밍 완료 요구·E-stop)를 통과시키고, 회귀를 붙인다.
ⓒ `/motor/low_state` 는 `trnav_msgs` 가 있어야 발행된다(`driver_node.py` `_load_msgs`). 없으면 UI 표는
   `diagnostics` 의 node 항목으로 대체한다 — **조용히 빈 표를 보이지 않는다.**

**④ 원본 High 4건의 처리** (`docs/code_review/amr-test-gui/2026-08-03.md` §평가):

| 원본 결함 | 이식본에서 |
| --- | --- |
| 정착 판정에 신선도 없음 | **구조적 해소** — `joint_states` 는 신뢰 불가 축을 아예 발행하지 않는다(`steer_angles_deg`) |
| heartbeat 만 락 밖 | **구조적 해소** — `PandaLink._ctrl()` 락(2026-08-03 조치) |
| 단발 송신·워치독 부재 | **구조적 해소** — `RelayBackend` 20 Hz 재송신 + `cmd_timeout_s` |
| 호밍 취소 불가 | **해소** — `~/home_cancel` 버튼 신설 |

**⑤ 원본은 남긴다.** `Tools/amr_test_gui/gui.py` 를 삭제하지 않는다 — 이식본이 실기에서 원본과 같은
동작을 낸다는 것이 확인되기 전까지 **비교 대상이 필요**하다. 폐기 시점은 별도 결정.

## Alternatives (기각)

- **`Tools/amr_test_gui_ros2/` 신규 폴더** — ROS2 패키지는 `src/` 아래여야 colcon 이 발견한다.
  또한 저장소 규약이 UI 를 대상 패키지에 종속시키라고 명시한다. 기각.
- **독립 ROS2 패키지 `can_relay_gui`** — `package.xml` 이 하나 더 늘고 버전이 갈린다. UI 는 드라이버
  인터페이스에 100 % 종속이라 함께 버전이 움직이는 편이 옳다. 기각.
- **UI 가 `/motor/low_cmd` 로 직접 raw 지령** — 축별 조향은 되지만 `trnav_msgs` 필수가 되고, 시험 GUI 가
  상류 모션 스택과 같은 층에서 지령하게 된다(계층 혼선). 또 `require_homed_for_steer` 때문에 호밍 전에는
  아무 것도 못 한다 — 원본은 호밍 전에도 슬라이더를 쓸 수 있었다. 기각, ⓑ 로 대체.
- **UI 가 판다를 직접 열고 드라이버는 안 띄운다** — 원본과 같아 「동일」하지만, 2026-08-03 조치로 얻은
  워치독·신선도·취소·버스 헬스를 전부 버린다. 기각.

## Consequences

**이득**: 원본 High 4건 중 3건이 코드를 안 짜도 해소된다(드라이버 재사용). 진단이 `diagnostics` 로
표준화돼 `rqt`·`ros2 topic echo` 로도 볼 수 있다. 조그·호밍이 CLI(`ros2 service call`)로도 재현 가능해진다.

**비용 · 남는 위험**:
- 드라이버에 **신규 공개 인터페이스 1개**(`~/steer_axis_deg`)가 생긴다 — 안전 게이트를 통과시키는
  회귀를 반드시 함께 붙인다(코딩 SOP §5: 변경 공개함수마다 테스트 ≥ 1).
- **두 프로세스가 됐다.** 드라이버가 죽으면 UI 는 조작 불가 상태로 남는다 — `diagnostics` 수신 끊김을
  화면에 명시해야 한다(원본의 「폴링 사망인데 제어권 획득으로 보임」 Medium 을 되풀이하지 않는다).
- **실기 동등성은 미검증으로 남는다.** 본 ADR 은 설계뿐이고, 「원본과 동일하게 움직인다」는 잭업 상태
  실기 대조 전까지 주장하지 않는다.
- 원본 존치로 `STEER_HOME` 사본(G4)이 당분간 유지된다 — 정본은 `config/machine/foil_a082.yaml`.

## Rollback

가역. 되돌리는 절차:

1. `setup.py` 의 `can_relay_gui` entry point 1줄 제거.
2. `can_relay/ui/` 디렉터리 삭제(드라이버 코드는 무영향 — UI 는 드라이버를 import 하지 않는다).
3. `~/steer_axis_deg` 구독 생성 3줄 + 콜백 1개 + 회귀 제거.
4. 원본 `Tools/amr_test_gui/gui.py` 는 손대지 않았으므로 그대로 계속 쓴다(⑤).

펌웨어·영속 상태·스키마 변경 없음.

## Verification

**게이트 1 — 빌드 + 무회귀 ✅**

```
$ colcon build --packages-select can_relay --symlink-install
Finished <<< can_relay [1.98s]
$ ls install/can_relay/lib/can_relay/
can_relay_gui  can_relay_node

$ PYTHONPATH=.:$PYTHONPATH python3 -m pytest test -q      # ROS2 소싱
250 passed in 17.91s                                      # 이식 전 230 → +20
$ PYTHONPATH=. python3 -m pytest test -q                  # 미소싱(ROS 회귀 skip)
235 passed, 2 skipped in 8.67s
```

**게이트 2 — `~/steer_axis_deg` 회귀 8건 ✅** (`test/test_backend_method35.py`)
축만 이동 · ±90° 클램프 · 비-조향축 거부 · 호밍 중 거부 · E-stop 거부 · 호밍 미완료 거부 ·
홈 미설정 거부 · 단일 목표각 미주장. 토픽 계층 4건은 `test/test_gui_node.py`(형식 오류 거부 포함).

**게이트 3 — mock 기동 스모크 ✅** (`test/test_gui_node.py` 12건 + 실제 2프로세스 기동)

```
$ ros2 node list        → /can_relay_gui · /can_relay_node
$ ros2 topic list       → /can_relay_node/{steer_deg,steer_axis_deg,drive_mmps} · /joint_states · /diagnostics · /estop
$ ros2 service list     → /can_relay_node/{engage,stop,home,home_cancel}
$ ros2 service call .../engage       → success=True '제어권 획득 — 판다 intercept, fail-safe 무장'
$ ros2 topic pub .../steer_axis_deg [3, 12.0]  → 진단 rejected_commands='0' · steer_target_deg=None(설계대로)
$ ros2 service call .../home_cancel  → success=True '취소 요청 수리'
$ ros2 service call .../stop         → success=True '구동 0 송신 · ⚠ 조향 정지 실패(실측 위치 미확보)'
$ kill -TERM <gui>      → 0.5 s 내 종료. 로그: 「정지 신호(SIGTERM) 수신」→「해제 시작」→「해제 완료」
                          드라이버 로그에 「정지 — 서비스 요청」 도달 확인
```

원본 `gui.py` 가 2026-07-28 실측으로 고정한 **SIGTERM 계약(핸들러 실행 → 해제 → 정상 종료)**이
이식본에서도 성립한다. `pump` 타이머를 그대로 옮긴 것이 근거다.

> ⚠ 시험 방법 주의 — `ros2 run can_relay can_relay_gui` 의 **래퍼 프로세스**에 SIGTERM 을 보내면
> 파이썬 자식에게 전달되지 않아 해제가 돌지 않는 것처럼 보인다. 실행 파일을 직접 띄워 시험할 것
> (`install/can_relay/lib/can_relay/can_relay_gui`). 스크립트: `scratchpad/smoke.sh`.

**구현 중 회귀가 잡은 결함 1건**: `meas_angle` 이 TTL 을 기동 시 스냅샷(`self.cfg`)에서 읽어
`ros2 param set` 이 조용히 무시됐다. 파라미터를 매번 읽도록 고쳤다
(`test_gui_node.py::test_measured_angle_expires` 가 수정 전 실패 → 수정 후 통과).

**게이트 4 — 바이트 대조: 무동작 부분 ✅ / 실기 부분 ❌**

게이트 4 는 두 부분으로 나뉜다. **지령 생성의 바이트 동등성은 모터를 움직이지 않고 판정할 수 있고,
그 부분은 끝냈다.** USB·릴레이·드라이브 응답은 여전히 실기 몫이다.

**4-a. 무동작 바이트 대조 ✅** — `test/test_port_equivalence.py` **44건 통과**
(원본 `gui.py` 를 모듈로 로드해 두 구현의 프레임을 직접 대조. USB 미개방·송신 0건):

| 대조 항목 | 건수 | 결과 |
| --- | --- | --- |
| 축별 조향 `~/steer_axis_deg` (노드 2 × 각도 9) | 18 | 바이트 동일 |
| 조향 범위 밖 클램프 | 3 | 바이트 동일 |
| 전축 조향(crab) `~/steer_deg` | 4 | 바이트 동일 |
| 구동 속도·부호 | 7 | 바이트 동일 |
| 구동 상한 클램프(4889) | 1 | 바이트 동일 |
| **조그 8방향 전체**(원본 `JOG` 표를 그대로 사용) | 8 | 바이트 동일 |
| 상수 정합(홈·counts/도·mm/s 환산·상한) | 1 | 동일 |
| 대역이 원본 조립 규칙과 같은지(위양성 차단) | 1 | 원문 대조 |
| **호밍은 다르다는 것을 고정**(의도된 차이) | 1 | 이식본은 `0x60FB` 직접 송신 0건 |

경로는 다른데(원본은 raw 부호를 직접 만들고, 이식본은 mm/s 로 보내 드라이버가 환산) **나오는
바이트가 같다**는 것이 요지다.

**변이 주입으로 이 대조에 이빨이 있음을 확인**했다 — 조향 홈을 **1 count**, counts/도를 **1** 어긋내면
둘 다 즉시 불일치로 검출된다(위양성 아님).

**4-b. 잭업 실기 ❌ 미실행** — 남은 것은 **버스에 실제로 나가는 프레임**과 드라이브 반응이다:
① 잭업 상태에서 원본·이식본으로 같은 조작을 수행하며 CAN 캡처 ② 두 캡처의 프레임 바이트 대조
③ 호밍 취소가 실기에서 실제로 축을 세우는지. 판다는 연결돼 있으나(`lsusb` → `bbaa:ddcc`)
**바퀴가 도는 작업이라 사용자 입회·잭업 확인 없이 시작하지 않는다.**
그때까지 이식본을 실기 운용에 쓰지 않으며 원본을 존치한다(§Decision ⑤ · debt-039).
