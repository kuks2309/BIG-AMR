# seer_pose_publisher — 함수표 · 변수표 (모듈 로컬 권위본)

> 양식 권위는 `docs/claude_guideline/code_review/review.md` §Core 인벤토리 3·4.
> 이중 기록 — 루트 집계는 `docs/sw_structure/function_table.md`.
> **신규 파일이므로 `coding.md:45` 에 따라 구현 전 계획 단계에서 작성**하고, 구현 후
> 실제 시그니처·줄 앵커로 갱신했다.

## 목적

Seer(SRC) 로봇 컨트롤러의 상태 API `1004`(`robot_status_loc_req`)를 폴링해
**`/robot_pose`(`geometry_msgs/PoseStamped`, map frame)** 로 발행한다.

`trnav_2ws_action_server` 의 `translate_forward`·`translate_reverse`·`mpc`·`mpc_reverse`
네 액션은 `trnav_2ws_core::LocalizationMonitor` 를 통해 이 토픽을 구독하며, **토픽이 없으면
목표 접수 직후 `status −3` 로 abort** 한다(에러 문구는 `TF2 map->base_link not available`
이지만 실제로는 TF 가 아니라 이 토픽 부재다 — `localization_monitor.cpp:137-150` 은 TF 를
쓰지 않고 토픽 캐시를 읽는다).

⚠ 이 저장소에는 `/robot_pose` 를 내는 노드가 **없었다**. QD 문서는
`src/Navigation/trnav_pose_publisher` 를 가리키나 그 경로는 **부재**다
(`src/Navigation/` = `icp_odometry_bringup`·`mcl2d_*`). 본 패키지가 그 공백을 메운다.

## 좌표계 — 왜 변환이 없는가

본 저장소는 **Seer 맵을 그대로 가져다 쓴다**(사용자 확인, 2026-08-06). smap 파서도 좌표를
미터 그대로 보관하고 원점을 이동하지 않는다(`mcl2d_map/include/mcl2d_map/smap.hpp:29-32`
— `normalPosList (m)`, `min_x/min_y` 는 헤더값). 따라서 `1004` 의 `x`·`y`·`angle` 은
액션이 받는 경로와 **같은 프레임**이며 변환이 필요 없다.

⚠ **단, 그 동일성은 코드가 아니라 운용 상태에 달려 있다** — Seer 에 다른 맵이 올라오면
조용히 어긋난다. 그래서 §맵 게이트를 둔다.

## 함수 리스트 표

| # | 함수 | 입력 | 출력 | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- | --- |
| 1 | `main` | `argv` | `int` | rclpy 초기화·spin·종료 | `seer_pose_publisher/pose_node.py:246` |
| 2 | `SeerPosePublisher.__init__` | 없음(생성자) | — | 파라미터 선언, 발행자 2개·타이머 2개 생성, 최초 접속·맵 게이트 수행 | `pose_node.py:74` |
| 3 | `SeerPosePublisher._declare` | 없음 | `void` | 파라미터 선언·읽기(host·rate·frame·expected_map_md5·min_confidence 등) | `pose_node.py:96` |
| 4 | `SeerPosePublisher._connect` | 없음 | `bool` | Seer 상태 포트(19204) 접속. 실패 시 False 반환하고 다음 주기에 재시도 | `pose_node.py:130` |
| 5 | `SeerPosePublisher._check_map` | 없음 | `bool` | `1000` 조회 → `current_map_md5` 를 `expected_map_md5` 와 대조. **불일치면 발행 금지** | `pose_node.py:149` |
| 6 | `SeerPosePublisher._on_pose_timer` | 없음(타이머) | `void` | `1004` 폴링 → PoseStamped·confidence 발행. 예외 시 재접속 예약 | `pose_node.py:181` |
| 7 | `SeerPosePublisher._on_map_timer` | 없음(타이머) | `void` | 주기적 맵 재확인 — 운용 중 맵 교체를 잡는다 | `pose_node.py:236` |
| 8 | `SeerPosePublisher.destroy_node` | 없음 | `void` | 소켓 정리 후 상위 호출 | `pose_node.py:240` |

**중복/유사 함수**: 없음. `_check_map` 과 `_on_map_timer` 는 전자가 판정, 후자가 주기 호출
래퍼로 역할이 다르다.

## 전역 변수 / 모듈 상수 표

| # | 이름 | 사용처(함수) | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- |
| 1 | `API_INFO` (상수) | 5 | `1000` — 로봇 정보(맵 md5 포함) | `pose_node.py:66` |
| 2 | `API_LOCATION` (상수) | 6 | `1004` — 위치 조회 | `pose_node.py:67` |
| 3 | `PORT_STATUS` (상수) | 4 | `19204` — **상태 포트 전용**. 제어·내비 포트는 열지 않는다 | `pose_node.py:68` |

가변 모듈 전역 없음 — 상태는 전부 노드 인스턴스 멤버다.

## 인스턴스 상태 표

| # | 멤버 | 사용처 | 기능 |
| --- | --- | --- | --- |
| 1 | `_sock` | 4·5·6·8 | Seer TCP 소켓. `None` 이면 미접속 |
| 2 | `_seq` | 4·5·6 | 요청 시퀀스(16bit). 응답 대조에 쓴다 |
| 3 | `_map_ok` | 5·6·7 | 맵 게이트 통과 여부. **False 면 발행하지 않는다** |
| 4 | `_fail_streak` | 6 | 연속 실패 수. 임계 초과 시 소켓을 버리고 재접속 |
| 5 | `_last_warn_ns` | 6 | 경고 throttle |

## 공개 인터페이스 (ROS)

| 종류 | 이름 | 타입 | 비고 |
| --- | --- | --- | --- |
| 발행 | `/robot_pose` | `geometry_msgs/PoseStamped` | **RELIABLE depth 10**. `LocalizationMonitor` 가 `pose_qos` 0/1(RELIABLE)·2(BEST_EFFORT) 중 무엇을 쓰든 RELIABLE 발행자는 양쪽 모두와 호환된다 |
| 발행 | `/seer/localization_confidence` | `std_msgs/Float64` | Seer 측위 신뢰도 [0,1]. PoseStamped 에 실을 자리가 없어 분리 발행 |
| 파라미터 | `host` | string | 기본 `192.168.44.82` |
| 파라미터 | `rate_hz` | double | 기본 `20.0` — 액션 제어 주기와 일치 |
| 파라미터 | `frame_id` | string | 기본 `map` |
| 파라미터 | `expected_map_md5` | string | 기본 `""`(미설정). 설정 시 불일치하면 **발행 금지** |
| 파라미터 | `map_recheck_sec` | double | 기본 `5.0`. 0 이하면 주기 재확인 없음 |
| 파라미터 | `min_confidence` | double | 기본 `0.0`(비활성). 초과 설정 시 미만 표본은 발행하지 않는다 |
| 파라미터 | `timeout_sec` | double | 기본 `0.3` — 소켓 타임아웃 |

## 설계 결정 — stamp 는 Seer 시각이 아니라 수신 시각을 쓴다

`1004` 응답에 `create_on`(예 `2026-08-06T19:45:20.519+0900`)이 관측되나 **이 값을 stamp 로
쓰지 않는다.** Seer 와 본 호스트의 시계 동기가 확인되지 않았고, `LocalizationMonitor` 는
`localization_timeout_sec: 0.5` 로 **신선도**를 판정하므로 시계 오프셋이 있으면 정상 데이터를
stale 로 오판하거나 그 반대가 된다. 수신 시각(ROS clock)이 보수적으로 안전하다.

⚠ `create_on` 은 **제가 조회한 벤더 문서 v1.2.1(p.20)에 없는 관측 필드**다. 문서가 보증하는
필드는 `x`·`y`·`angle`·`confidence`·`ret_code`·`err_msg` 뿐이다.

## 의존성 3-tier

| Tier | 대상 | 버전/제약 | 부재 시 동작 | 근거 |
| --- | --- | --- | --- | --- |
| 빌드 | `rclpy`·`geometry_msgs`·`std_msgs` | ROS 2 Humble | 빌드 실패 | `package.xml` |
| 런타임 필수 | Seer 상태 API `192.168.44.82:19204` | netprotocol v3.0.0 (실측) | **접속 실패 시 발행 없음**. 주기적으로 재접속 시도하며 경고를 throttle 로 남긴다. 하류 액션은 `LocalizationMonitor` 워치독(0.5 s)으로 abort 한다 | 실측 2026-08-06 |
| 런타임 선택 | 없음 | — | — | — |

## 안전 — 읽기 전용

상태 포트 `19204` **만** 연다. 제어(19205)·내비(19206)·설정(19207) 포트는 코드에 등장하지
않으며, 명령 API 번호(`2xxx`·`3xxx`·`4xxx`)도 등장하지 않는다. 본 노드는 Seer 의 상태를
바꿀 수 없다.

## ⚠ 맵 md5 는 이름이 같아도 바뀐다 — 실측

2026-08-06 같은 세션 안에서 **30분 간격으로 md5 가 달라졌다.** 맵 이름은 동일했다.

```
19:47  current_map 260709_test   md5 0d0a479f583b2b84f9f45a6de87eead7
20:13  current_map 260709_test   md5 79e59a5ac112551ab7f1dea192230a94
```

그 사이 타 세션이 Seer 맵 읽기 작업을 했다. 즉 **맵을 다시 저장·업로드하면 이름이 같아도
md5 가 바뀐다.** 운용상 귀결:

- `expected_map_md5` 게이트는 **엄격하지만 취약**하다 — 맵을 손대면 정상 상황에서도 막힌다.
- 그래서 기본값을 빈 문자열(비활성 + 경고)로 두었다. 운용 투입 시 **그 시점의 md5 를 넣고,
  맵을 갱신할 때마다 함께 갱신**해야 한다.
- 이름(`current_map`)만 보는 완화 옵션은 넣지 않았다 — 이름이 같아도 내용이 다를 수 있어서
  게이트의 목적(좌표계 어긋남 차단)을 달성하지 못한다.

## 검증 (2026-08-06, `ROS_DOMAIN_ID=43`, 실 Seer 대상 읽기 전용)

| 항목 | 방법 | 결과 |
| --- | --- | --- |
| 빌드 | `colcon build --packages-select csm seer_pose_publisher` | 통과 |
| 접속·맵 조회 | `ros2 launch seer_pose_publisher seer_pose.launch.py` | 접속 성공, `260709_test` 인식 |
| 발행 주기 | `ros2 topic hz /robot_pose` | **9.796 / 9.978 Hz** (min 0.079 s · max 0.119 s · σ 0.007) |
| 좌표 추종 | `ros2 topic echo /robot_pose` | (−11.85, 2.40) → (−12.24, 2.27) — 타 세션이 구동 중인 로봇을 실시간 추종 |
| 신뢰도 | `ros2 topic echo /seer/localization_confidence` | `0.8426` |
| **맵 게이트 차단** | `-p expected_map_md5:=deadbeef…` 로 기동 | ERROR 로그 반복 + **`ros2 topic hz` 12초간 수신 0건** |

⚠ **미검증**: 장시간(수 시간) 연결 유지, 주행 중 무선 품질 저하 시 거동, `min_confidence`
임계값(주행 중 confidence 분포 미측정), 20 Hz 제어 루프가 10 Hz 자세를 쓸 때의 추종 오차.

⚠ **최종 verdict 는 저자가 찍지 않는다**(`coding.md:88`). 위는 실행 관측이며 승인이 아니다.
