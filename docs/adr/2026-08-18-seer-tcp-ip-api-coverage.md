# ADR 2026-08-18 — Seer TCP/IP API 커버리지 확장과 제어권 세션 자산화

- **Status**: Accepted — 2026-08-18 (단위 검증 완료 / **쓰기 API 대부분 실기 미검증** — §Verification 범위 한정)
- 관련: ADR [2026-08-07-seer-api-tcp-hal](2026-08-07-seer-api-tcp-hal.md) (패키지 신설·배치·포트 정책)

## Context

### 사실 1 — 지금 커버리지는 17편호이고, 모션은 **작동하지 않는 상태**다

`src/Comm/seer_tcp_ip/seer_tcp_ip/api.py` 가 가진 편호는 17개다(1000·1004·1005·1007·1009·1013·
1020·1050·1100·1300·1400·2000·2002·2010·3051·4011·6001). 그런데 **모션 지령이 그대로는 거부된다** —
Seer 는 지령 전에 **제어권(4005)** 을 요구하고, 없으면
`ret_code=40020 "control is preempted... can't execute any standalone operation"` 로 거부한다
(2026-08-14 실기 확정, 메모리 `biguamr-seer-tcpip-api`). 우리 패키지에 **4005/4006/1060 래퍼가 없다.**

### 사실 2 — 참조 정본이 불완전하다. 실사용 클라이언트가 더 많이 안다

`References/Seer-Driver/robokit_tcp_api.md` 의 편호 표는 4000~4004 까지만 싣고
**4005(제어권 획득)·4006(반납)·1060(소유자 조회)·1040(모터)·1302(맵 md5)·1500(로봇 모델)·
3066(지정 경로)·4010(맵 업로드)·4200(모델 업로드)·6004(소프트 비상정지)·6100/6101(SLAM)** 이 없다.
이들은 사용자 저장소 `T-Robot_seer_gui/seer_core/client.py`(로컬 `/home/nvidia/T-Robot_seer_gui`,
485줄)에 **요청 JSON 형태까지** 들어 있다.

이 저장소의 반복된 실패 형태가 정확히 여기 있다 — 동봉 문서만 보고 「없다」고 판단한 사건이
네 건이다(`docs/claude-mistake/2026-08-07-002` §원인 분석). 그래서 **본 작업의 편호·요청 형태
정본은 그 클라이언트**이고, 참조 문서는 보조로 쓴다.

### 사실 3 — `open_loop_move` 에 `duration` 이 없다 (안전 결함)

참조 클라이언트는 `open_loop(vx, vy, w, duration=400)` 으로 보내며 docstring 이
"duration ms bounds how long the robot keeps this velocity **if no new command arrives**
(0 = keep indefinitely)" 라고 적는다. 즉 **`duration` 이 사실상 dead-man 타이머**다.
`Tools/amr_test_gui/gui.py` 는 이 성질을 정지 수단으로 쓴다 — 600 ms 를 실어 200 ms 마다 재송신하므로
GUI 가 죽으면 0.6초 안에 로봇이 선다(메모리 `biguamr-seer-tcpip-api`).

우리 `open_loop_move` 는 `{"vx","vy","w"}` 만 보낸다. **필드 부재를 로봇이 어떻게 해석하는지는
미확인**이다(0=무한으로 볼 여지가 있다). 확인되지 않았다는 사실 자체가 문제다 — 프로세스가 죽었을 때
로봇이 서는지 우리가 말할 수 없다.

> **2026-08-24 추가 관측 — 여전히 미확인이나, 「0=무한」쪽 추측은 약해졌다.**
> `[존재]` 실기 1400 과 원본 하드 `robot.param` 이 일치하여 파라미터
> **`NetProtocol.ControlMotionDuration` = 500**(기본 500, 범위 0~5000)이 있음을 확인했다.
> 이름·단위·범위가 2010 의 `duration` 과 정확히 겹친다.
> `[동작]` **그것이 필드 부재 시의 대체값인지는 확인하지 못했다.** `libNetProtocol.so` 에 문자열은
> 있으나 `nm -C | grep -i controlMotionDuration` 이 멤버 심볼을 하나도 내지 않아 참조 지점을
> 짚지 못했다. 갈래를 가르는 유일한 실측은 **`duration` 없이 2010 을 보내고 지령을 끊은 뒤 로봇이
> 500ms 안에 서는지 보는 것**인데, 이는 로봇을 움직이므로 잭업·승인 후에만 한다(debt-111).
> 따라서 본 ADR 의 결정(§2 `duration_ms` 필수화)은 **바뀌지 않는다** — 대체값이 있든 없든
> dead-man 시간은 호출자가 고르는 편이 맞고, 500ms 라는 값에 기대는 것 자체가 미확인 전제다.

### 사실 4 — 편호 2022 의 뜻이 두 자료에서 어긋난다

| 자료 | 2022 |
|---|---|
| `References/Seer-Driver/robokit_tcp_api.md:133` | `robot_control_scan_req` — 스캔 시작 |
| `T-Robot_seer_gui/seer_core/client.py:50,239` | `API_SWITCH_MAP` — 활성 지도 전환, `{"map_name":…}` |

같은 클라이언트가 SLAM 시작을 **6100** 으로 따로 갖고 있어 정황은 클라이언트 쪽이지만,
**실기 확인 없이 어느 쪽도 채택하지 않는다.** 2022 는 본 ADR 범위에서 **제외**한다.

## Decision

### 1. 제어권 세션을 별도 모듈로 만든다 — `control.py`

얇은 편호 래퍼가 아니라 **동작(behavior)** 이므로 `api.py` 에 섞지 않는다.

- `SeerControlSession` — 컨텍스트 매니저. 진입 시 1060 으로 현 소유자를 남기고 4005 로 획득,
  이탈 시 **정지(2000) 후** 4006 반납. 예외로 빠져나가도 `finally` 로 반납한다.
- `JogKeepalive` — `duration` 을 실은 2010 을 주기적으로 재송신하는 dead-man 루프.
  `interval < duration` 을 **생성 시 검증**한다(그 반대면 로봇이 매 주기 섰다 갔다 한다).
- 두 클래스 모두 **자체 스레드를 만들지 않는다.** 호출자의 타이머/루프가 `tick()` 을 부른다 —
  ROS 노드의 단일 스레드 executor 에 그대로 얹히고, 시험에서 시계를 주입할 수 있다.

**4005 는 남의 제어권을 뺏는다**(실기에서 `operator-0.1` @192.168.44.49 를 뺏은 기록). 그래서
진입 시 이전 소유자를 반환값으로 남기고, 반납해도 원 소유자에게 자동 복귀하지 않는다는 사실을
docstring 에 박는다.

### 2. `open_loop_move` 에 `duration_ms` 를 **필수 인자로** 추가한다 (호출 호환 파괴)

기본값을 주지 않는다. 기본값을 주면 호출자가 dead-man 시간을 **생각하지 않고** 지나가고,
그것이 정확히 지금 상태다. 저장소 내 호출자는 0건이므로 파괴 비용이 없다.

### 3. 편호 바인딩을 확장한다 — **요청 형태에 근거가 있는 것만**

근거는 ① 참조 클라이언트의 실제 요청 JSON ② 참조 문서의 무파라미터 조회.
근거가 없으면 **넣지 않는다**(추측으로 바디를 만들지 않는다).

| 계열 | 추가 편호 |
|---|---|
| 조회(19204, 무파라미터) | 1002 run · 1003 mode · 1006 blocked · 1008 brake · 1010 path · 1011 area · 1012 estop · 1021 reloc 상태 · 1022 loadmap 상태 · 1040 motor · 1101·1102 배치 · 1111 init · 1301 station · 1500 robot model |
| 조회(19204, 바디 있음) | 1025 slam 상태 `{"return_resultmap":bool}` · 1302 맵 md5 `{"map_names":[…]}` |
| 제어(19205) | 2001 gyro · 2003 confirmloc |
| 작업(19206) | 3001 pause · 3002 resume · 3003 cancel · 3050 gopoint · 3052 patrol · 3055 translate · 3056 turn · 3066 지정경로 `{"move_task_list":[…]}` |
| 설정(19207) | 4000 setmode · 4001 setparams · 4002 saveparams · 4003 reloadparams · 4004 clearfatal · **4005 seize** · **4006 release** · 4010 맵 업로드 |
| 기타(19210) | 6000 speaker · 6004 소프트 비상정지 `{"status":bool}` |

`go_target`(3051)은 참조 클라이언트에 맞춰 `source_id`(기본 `"SELF_POSITION"`)와 임의 옵션
통과를 더한다 — 현재는 `{"id"}` 만 보내고 있어 참조 구현과 다르다.

**제외**: 2022(사실 4 의 충돌) · 3055/3056 의 세부 필드명(아래 참조) · Push 19301(구독 설정 방법
미열람) · 4200 모델 업로드(스키마 로봇별).

⚠ **3055 `translate` · 3056 `turn` 은 편호만 근거가 있고 필드명이 없다.** 참조 문서 표에 이름만
있고 참조 클라이언트에는 메서드가 없다. 따라서 **임의 dict 를 그대로 싣는 저수준 형태**
(`translate(body)`)로만 노출하고, 편의 인자를 만들지 않는다 — 필드명을 발명하지 않는다.

### 4. 게이트 정책은 그대로 — 새 쓰기 API 도 전부 `allow_guarded` 뒤에 둔다

새로 추가하는 2xxx·3xxx·4xxx·6xxx 는 모두 `GUARDED_PORTS` 포트로 나가므로 기존 게이트가 그대로
막는다. 4005/4006 은 19207(설정)이라 **제어권 획득 자체가 게이트 대상**이다 — 의도된 동작이다
(제어권을 잡는 것이야말로 중재가 필요한 행위다).

## Alternatives (기각)

| 안 | 기각 사유 |
|---|---|
| 제어권 획득을 `SeerApi` 메서드로만 노출 | 획득→사용→반납의 **짝**을 코드가 강제하지 못한다. 예외 경로에서 제어권이 남는다 — 다음 클라이언트가 40020 으로 막히고 원인이 안 보인다. |
| `open_loop_move(duration_ms=600)` 기본값 부여 | 기본값이 있으면 호출자가 dead-man 시간을 고르지 않고 지나간다. 지금 결함이 정확히 "아무도 안 골랐다"이다. |
| `JogKeepalive` 가 스레드를 소유 | ROS 노드에 얹으면 executor 와 두 스레드가 되고, 시험에서 시계를 못 잡는다. `tick()` 호출자 주도로 두면 둘 다 해결된다. |
| 전 편호를 다 감싼다(2022·3055 필드 포함) | 요청 형태 근거가 없는 것을 감싸면 **발명**이다. 이 저장소의 반복 실패 형태다. 근거 없는 것은 저수준 `call()` 로 열어 두고 감싸지 않는다. |
| 참조 클라이언트를 그대로 복사 | 그 저장소는 별개이며 전송 계층(재연결·seq 대조·스로틀·한도 예외)이 우리 것과 다르다. 편호·요청 형태만 인용하고 전송은 우리 `transport.py` 를 쓴다. |

## Consequences

**이득**
- 모션 경로가 **처음으로 실행 가능**해진다(제어권 → 지령 → 정지 → 반납).
- `duration` 이 필수가 되어 dead-man 시간을 호출자가 반드시 고른다.
- 편호 커버리지 17 → 50+. 다음 작업이 전송 계층을 다시 만들 이유가 사라진다.

**비용**
- `open_loop_move` 시그니처 파괴(저장소 내 호출자 0건이라 실비용 0).
- `api.py` 가 커진다(약 240 → 450줄). 층은 그대로다(편호 바인딩 하나).

**남는 위험 / 미해결**
- **쓰기 API 대부분이 실기 미검증**이다(→ **debt-111**). 단위 시험은 "우리가 올바른 편호·포트·JSON 을
  만든다"까지만 보증한다 — 로봇이 그것을 받아들이는지는 별개다. §Verification 이 경계를 명시한다.
- 2022 편호 충돌 미해소(→ debt-110).
- Push(19301) 미구현(→ 기존 ADR §Consequences 에 이미 기록).
- broker 미착수(debt-072) — 제어권 세션이 생겼으므로 **두 주체가 동시에 4005 를 잡는 사고**가
  이제 실제로 가능하다. 그 위험은 커졌다(→ debt-112).

## Verification (2026-08-18)

| 무엇 | 결과 | 근거 |
|---|---|---|
| 단위 회귀 | **100 passed** | `python3 -m pytest test/ -q` |
| **회귀 검출력** | **57/57 검출**(신규 C1~C12 제어권·dead-man, N1~N12 편호) | `python3 src/Comm/seer_tcp_ip/mutation_check.py` |
| flake8 / 금지패턴 | 0건 / 0건 | `--max-line-length=110`, `checks/banned-pattern.sh` |
| colcon 빌드 | `seer_tcp_ip`·`seer_lidar_tf` 성공 | `--packages-select` |
| **실기 조회**(192.168.44.82 Foil_A082) | 1002·1003·1006·1012·1021·1022·1040·1060·1111·1301 응답, 키 실측 | 인벤토리 §6 |
| **1302 실측 2건** | ① `.smap` 확장자 필수 — 없으면 `ret_code 40051`. 붙이면 md5 가 1300 의 `current_map_md5` 와 일치 ② **all-or-nothing** — 없는 지도가 섞이면 요청 전체 거부 | 인벤토리 §6 |

⚠ **검증 경계** — 위가 보증하는 것은 "이 목록의 동작이 회귀로 고정돼 있고, **조회 경로**가 실기에서
돈다"까지다. **쓰기 API 24종과 `control.py` 전체는 실기에서 한 번도 호출하지 않았다**(가짜 소켓
단위 시험만). 로봇을 움직이거나 설정을 바꾸므로 승인 없이 호출하지 않았다 — debt-111 이 그 목록과
확인 절차를 갖는다.

**설계 가정 하나가 실기에서 뒤집혔다**(기록 목적): `get_map_md5` 를 처음엔 「없는 지도는 빼고
돌려준다」로 설계하고 그 가정대로 가짜 소켓 시험을 썼다 — **시험은 통과했다.** 실기 호출에서
로봇이 요청 **전체**를 거부하는 것을 보고서야 틀린 것을 알았다. 가짜는 내 가정을 그대로 되돌려
줄 뿐이라는 것이 이 건의 교훈이고, 그래서 조회 경로만이라도 실기로 돌린 것이 값을 했다.

## Rollback

가역. `git revert` 또는:

1. `src/Comm/seer_tcp_ip/seer_tcp_ip/control.py` 와 `test/test_control.py` 삭제.
2. `api.py` 를 이전 리비전으로 복원 — `git checkout <이전> -- src/Comm/seer_tcp_ip/seer_tcp_ip/api.py`.
3. `__init__.py` 의 `SeerControlSession`·`JogKeepalive` export 제거.
4. `mutation_check.py` 의 신규 항목(C·N 계열) 제거.
5. `colcon build --packages-select seer_tcp_ip` 재실행.

영속 상태·스키마·펌웨어 변경 없음. **로봇에 쓰기 동작을 수행하지 않았다**(§Verification 참조).
