# motor_control 인벤토리 — 함수표·전역변수표 (모듈 로컬 권위)

> ## ⚠ 2026-07-28 — 본 문서가 인용하는 `Tools/amr_test_gui/amr_test_gui/**` 경로는 삭제됐다
>
> 구 GUI 패키지(11 모듈 + `run_gui.py` + `test/` 84건)가 폐기되고 단일 파일
> `Tools/amr_test_gui/gui.py` 로 대체됐다 — 사유·대체표·남는 부채는 **docs/adr/2026-07-28-old-gui-removal.md**.
> 본 문서는 **작성 시점의 기록**이므로 인용을 고치지 않는다. 구 파일 실물은 커밋
> `fdc1c51`(브랜치 `session/56a709a5`)에 `Tool/amr_test_gui/`(단수) 경로로 남아 있다.


> 작성: 2026-07-09 · coding SOP §6 상태-미러형(덮어쓰기 갱신). 양식: code_review SSOT.
>
> ⚠ **정정 2026-07-27 — "모듈 로컬 권위" 문구는 유보. 2026-07-26 수정 이후 미갱신(위치·개수 stale).**
> 아래 표의 `file:line` 은 2026-07-26 후속 수정 전 스냅샷이라 **현행 코드와 어긋난다**. 반영된 수정으로
> `backend.py` 314→**352줄**, `driver_node.py` 218→**236줄**로 늘었다(2026-07-27 `wc -l` 확인).
> 확인된 어긋남(2026-07-27 `grep -n 'def '` 실측):
> - `snapshot` 문서 `backend.py:154` vs 실제 **:174** · `_preflight_read` :184 vs **:205** · `_rx_loop` :276 vs **:314** · `_send` :312 vs **:350**
>   (그 외 `start` :119→**120**, `set_command` :131→**132**, `estop` :147→**152**, `freewheel` :156→**159**, `shutdown` :166→**187**,
>    `_gate_homing_motion` :197→**218**, `_write_init_sequence` :211→**232**, `_tx_loop` :235→**256**)
> - `driver_node.py`: `_on_cmd_vel` :100→**105** · `_on_estop` :107→**112** · `_on_freewheel` :111→**115** · `_on_odom_timer` :111→**120**
>   · `_publish_odom` :136→**145** · `_on_diag_timer` :169→**178** · `destroy_node` :197→**211** · `main` :204→**218**
> - **내부 모순**: 문서상 `freewheel`(:156) 이 `snapshot`(:154) 뒤에 오는데 실제 순서는 freewheel **:159** → snapshot **:174** 로 반대다.
>   또 `_on_freewheel` 과 `_on_odom_timer` 가 둘 다 `driver_node.py:111` 로 적혀 있으나 실제는 **:115** 와 **:120** 이다.
> - **개수 주장 어긋남**: 전역표 #1 "`OBJ_*` 15종 … protocol.py:20-36" → 실제 **16개**(`protocol.py:20-35`, `grep -c '^OBJ_'` = 16).
>   형제 문서 [`docs/code_review/motor_control/2026-07-26.md:104`](code_review/motor_control/2026-07-26.md) 는 "16종"이라 적어 상호 모순이었다(그쪽이 맞다).
> 아래 위치·개수를 근거로 삼기 전에 **현행 코드에서 재확인**할 것. (본 감사는 서술만 정정하고 표의 원문 수치는 이력 보존을 위해 남긴다.)
>
> ### ⚠ 재감사 2026-07-27b — **위 정정 블록의 줄번호도 이미 무효다**(원문은 이력 보존을 위해 남긴다)
> 위 블록은 "2026-07-27 `wc -l` 확인" 으로 `backend.py` **352줄** · `driver_node.py` **236줄** 을 적었으나,
> 같은 날 재측정에서 파일이 계속 커지고 있다 — 한 세션 안에서 `backend.py` 494 → 549 → **635줄**,
> `driver_node.py` 296 → 364 → **424줄**, `protocol.py` **145줄**(모두 2026-07-27 `wc -l`).
> 즉 이 소스들은 **동시 편집 중**이라 `file:line` 인용이 수 분 단위로 밀린다.
> - 그 결과 위에 나열된 교정 좌표(`snapshot` :174, `_preflight_read` :205, `_gate_homing_motion` :218,
>   `_write_init_sequence` :232, `_rx_loop` :314, `_send` :350, `_on_cmd_vel` :105 등)는 **어느 것도 현행과 맞지 않는다.**
>   같은 시각 `grep -n 'def '` 실측 예: `_preflight_read` **:265** · `_gate_homing_motion` **:283** ·
>   `_write_init_sequence` **:385**(이 값들 역시 다음 편집에서 밀린다).
> - 개수 주장 재확인: `OBJ_*` **16개** 는 여전히 맞다(`grep -c '^OBJ_' protocol.py` = 16). 다만 인용된 범위
>   `protocol.py:20-35` 는 현재 **:30-52** 다.
> ⇒ **이 문서에서 `file:line` 으로 코드를 인용하지 말 것.** 함수명·클래스명·원문 문구 앵커를 쓰고,
>   부득이 줄번호를 쓰면 **측정 시각을 병기**하라. 표의 원문 수치는 삭제하지 않는다.

## 함수 리스트 표

| # | 함수 | 입력 | 출력 | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- | --- |
| 1 | `sdo_write` | node, index, value, size, sub | Frame | SDO expedited 쓰기 프레임 인코드 | motor_control/protocol.py:65 |
| 2 | `sdo_read` | node, index, sub | Frame | SDO 읽기 요청 프레임 | motor_control/protocol.py:73 |
| 3 | `guard_rtr` | node | Frame | Node Guarding RTR 프레임 | motor_control/protocol.py:78 |
| 4 | `parse_sdo_response` | can_id, data | SdoResponse\|None | 0x580+N 응답 파싱(write_ack/read/abort) | motor_control/protocol.py:83 |
| 5 | `DualSteerKinematics.twist_to_modules` | vx, vy, wz | list[ModuleCommand] | 역기구학(inverse_multisteer 이식): 접기+비율 포화 | motor_control/kinematics.py:36 |
| 6 | `DualSteerKinematics.modules_to_twist` | {node:(v,θ)} | (vx,vy,ω) | 정기구학 LSQ(오도메트리) | motor_control/kinematics.py:56 |
| 7 | `DiffDriveKinematics.twist_to_modules` | vx, _vy, wz | list[ModuleCommand] | 차동 IK(θ=None — DD 커버) | motor_control/kinematics.py:100 |
| 8 | `DiffDriveKinematics.modules_to_twist` | {node:(v,_)} | (vx,0,ω) | 차동 FK | motor_control/kinematics.py:110 |
| 9 | `_to_can` | Frame | can.Message | 프레임 → python-can 변환(무설치 폴백) | motor_control/backend.py:49 |
| 10 | `TongyiSdoBackend.start` | — | — (예외: BringupRefused/NodeSilent) | RX 기동→선판독→게이트→init→TX 기동 | motor_control/backend.py:119 |
| 11 | `TongyiSdoBackend.set_command` | list[ModuleCommand] | — | SI→디바이스 단위 목표 갱신+워치독 스탬프 | motor_control/backend.py:131 |
| 12 | `TongyiSdoBackend.estop` | engage | — | E-stop 래치(vel 0) | motor_control/backend.py:147 |
| 12a | `TongyiSdoBackend.freewheel` | engage | — | 구동축 servo-off(견인) 플래그 토글, TX가 전이 송신 | motor_control/backend.py:156 |
| 13 | `TongyiSdoBackend.snapshot` | — | dict | 상태 사본(진단·오도메트리용) | motor_control/backend.py:154 |
| 14 | `TongyiSdoBackend.shutdown` | — | — | vel 0 송신 후 스레드·버스 종료 | motor_control/backend.py:166 |
| 15 | `TongyiSdoBackend._preflight_read` | — | — (예외: NodeSilent) | 전 노드 0x6064 선판독 | motor_control/backend.py:184 |
| 16 | `TongyiSdoBackend._gate_homing_motion` | — | — (예외: BringupRefused) | 콜드(조향 홈 밖) 물리 스윙 게이트 | motor_control/backend.py:197 |
| 17 | `TongyiSdoBackend._write_init_sequence` | — | — | Seer 기동 init 재현(기동 캡처 실측 순서) | motor_control/backend.py:211 |
| 18 | `TongyiSdoBackend._tx_loop` | — | — | 50Hz 지령+정착게이트+20Hz RTR+피드백 폴링 | motor_control/backend.py:235 |
| 19 | `TongyiSdoBackend._rx_loop` | — | — | 응답 파싱→NodeState 갱신(유일 writer) | motor_control/backend.py:276 |
| 20 | `TongyiSdoBackend._send` | Frame | — | 버스 송신+tx 카운트 | motor_control/backend.py:312 |
| 21 | `MotorControlNode.__init__` | — | — | 파라미터 선언·kinematics/backend 조립·타이머 | motor_control/driver_node.py:33 |
| 22 | `MotorControlNode._on_cmd_vel` | Twist | — | 클램프→IK→backend 목표(비블로킹) | motor_control/driver_node.py:100 |
| 23 | `MotorControlNode._on_estop` | Bool | — | E-stop 전달 | motor_control/driver_node.py:107 |
| 23a | `MotorControlNode._on_freewheel` | Bool | — | /freewheel → backend.freewheel 전달 | motor_control/driver_node.py:111 |
| 24 | `MotorControlNode._on_odom_timer` | — | — | 0x6064 변위→FK LSQ→포즈 적분 | motor_control/driver_node.py:111 |
| 25 | `MotorControlNode._publish_odom` | steer_rad, drive_pos | — | Odometry+TF+JointState 발행 | motor_control/driver_node.py:136 |
| 26 | `MotorControlNode._on_diag_timer` | — | — | DiagnosticArray 발행(estop/error/**freewheel**/silent/settling; freewheel 은 WARN 메시지 + 독립 KeyValue 로 상시 노출) | `MotorControlNode._on_diag_timer` |
| 27 | `MotorControlNode.destroy_node` | — | — | backend 종료 후 노드 파기 | motor_control/driver_node.py:197 |
| 28 | `main` | args | — | rclpy 스핀 진입점 | motor_control/driver_node.py:204 |
| 28a | `generate_launch_description` | — | LaunchDescription | 파라미터 파일 로드 기동 | launch/motor_control.launch.py:10 |

## 전역 변수 / 모듈 상수 표

| # | 변수 | 사용처(함수) | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- |
| 1 | `OBJ_*` 15종 | protocol·backend 전역 | CANopen 오브젝트 인덱스(Handbook Appendix I) | motor_control/protocol.py:20-36 |
| 2 | `CW_DRIVE_ENABLE=0x86` / `CW_STEER_SETPOINT=0x3F` / `CW_DISABLE=0x05` | init·TX 루프 | Controlword 실측 관례값 | motor_control/protocol.py:39-41 |
| 3 | `STEER_LIMIT_RAD=2.443` | twist_to_modules | 조향 한계 ±140° — ⚠ Seer `live_models.hpp:86` **config 값(기구 한계)이지 물리 실증 범위가 아니다**. 실측 검증 범위는 **±90°** (각주2) | motor_control/kinematics.py:15 |
| 4 | `TongyiSdoBackend.GUARD_TIME_MS…HOMING_SPEED` (클래스 상수 6종) | _write_init_sequence | Seer 기동 init 실측값 | motor_control/backend.py:66-72 |
| 5 | `M_S_PER_UNIT=4.0906e-5` / `COUNTS_PER_RAD` / `COUNTS_PER_M=2670177` / `WHEEL_RADIUS=0.125` | driver_node 전역 | 실측 확정 스케일 | motor_control/driver_node.py:27-30 |

> **각주2 (append 2026-07-27) — `STEER_LIMIT_RAD` 의 "실측" 라벨 정정.**
> 원 서술 "조향 한계 ±140°(실측 config)" 는 **Seer 설정파일에서 읽은 값**이라는 뜻이며, 그 범위가 물리적으로 안전하다는 실증이 아니다.
> 코드 주석도 config 출처를 명시한다: `motor_control/kinematics.py:15` "조향 한계 ±140° (live_models.hpp:86 실측 config)".
> - **실측 검증된 가동 범위는 ±90°**: [`Tools/amr_test_gui/amr_test_gui/ramp.py`](../../../../Tools/amr_test_gui/amr_test_gui/ramp.py) 의 `STEER_LIMIT_DEG = 90.0` **바로 위 주석**(현재 :26-29)
>   "기구 한계는 ±140°(kinematics.STEER_LIMIT_RAD=2.443)이나, **실측 검증된 범위가 ±90°**(홈↔90° = 5,160,960 counts, 양 부호 정상 확인)이므로 테스트 GUI 는 ±90° 로 좁힌다".
>   - ⚠ **좌표 정정 2026-07-27b** — 원 표기는 `ramp.py:16-19` 였다. 그 줄들은 모듈 docstring 안의
>     「`pc_crab_steer*` 미존재 확인」 주석이며 ±90° 문구가 없다(2026-07-27 재대조). 내용 판정은 그대로 유효하다.
> - **범위 밖 지령이 실제 물리 손상을 냈다**: [`docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md`](../../../../docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md) **§무엇을 했는가**(현재 :19-20)
>   "node4가 **물리적으로 137°(정상 ±90° 범위 밖)로 밀려 갇혔고**, 사용자가 CAN 직결 원점 호밍으로 복구해야 했다".
>   - ⚠ **좌표 정정 2026-07-27b** — 원 표기 `:17-18` 은 「## 무엇을 했는가」 제목 줄과 그 앞 빈 줄이다.
> ⇒ IK(`twist_to_modules`)는 이 상수까지 각도를 **생성할 수 있다**. ±90° 초과 구간은 미검증 위험 구간으로 취급할 것.
> 상수 `2.443` 은 실측 없이 변경하지 않는다(본 감사 값 미변경).

공유 가변 상태(누가 바꾸나): `_vel_units`·`_steer_counts`·`_estop`·`_freewheel`(writer: set_command/estop/freewheel, reader: _tx_loop·snapshot — `_lock`) · `_nodes`(writer: _rx_loop 단독 — `_state_lock`) · `settling`(writer: _tx_loop 단독). `_tx_loop` 로컬 `fw_active`(freewheel 엣지 검출, TX 스레드 단독 소유 — 락 불요).
