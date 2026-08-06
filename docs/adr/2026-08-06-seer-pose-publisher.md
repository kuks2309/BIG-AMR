# ADR 2026-08-06 — `/robot_pose` 공백을 Seer 상태 API `1004` 로 메운다

- **Status**: Accepted — 2026-08-06 (실 Seer 대상 **읽기 전용** 검증 완료. 구동 연동 검증 0회.
  최종 verdict 는 저자가 찍지 않는다 — `coding.md:88`, 외부 리뷰 패스 대기)

## Context

`trnav_2ws_action_server` 의 `translate_forward`·`translate_reverse`·`mpc`·`mpc_reverse`
네 액션은 `trnav_2ws_core::LocalizationMonitor` 로 **`/robot_pose`(PoseStamped)** 를 구독하고,
그 토픽이 없으면 목표 접수 직후 **`status −3` 로 abort** 한다. 로그 문구는
`TF2 map->base_link not available` 이지만 **TF 문제가 아니다** —
`localization_monitor.cpp:137-150` 은 TF 를 쓰지 않고 토픽 캐시를 읽는다.

**이 저장소에는 그 토픽을 내는 노드가 없다.** QD 문서
(`QD/trnav_motion_core/docs/amr_motion_core_code_updates.md:59,82`)는
`src/Navigation/trnav_pose_publisher` 를 가리키나 **그 경로는 부재**다
(`src/Navigation/` = `icp_odometry_bringup`·`mcl2d_core`·`mcl2d_map`·`mcl2d_ros2`).

⇒ 실기 구동 시 이 4종이 즉시 abort 한다. (`spin`·`turn` 은 이 토픽을 쓰지 않아 무관.)

**대안 조사** — Seer 상태 API 에 위치 조회가 있다. 벤더 원문
`References/Seer-Driver/github_sdk/robotkit-netprotocol-l-1.2.1.txt:806-840` (v1.2.1, p.20):

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `x` · `y` | number | 로봇 좌표, **단위 m** (필수) |
| `angle` | number | **단위 rad** (필수) |
| `confidence` | number | 측위 신뢰도 [0,1] (필수) |

**좌표계** — 본 저장소는 Seer 맵을 그대로 가져다 쓴다(사용자 확인). smap 파서도 좌표를
미터 그대로 보관하고 원점을 이동하지 않는다(`mcl2d_map/include/mcl2d_map/smap.hpp:29-32`).
따라서 변환이 필요 없다. **단, 그 동일성은 Seer 에 같은 맵이 올라와 있을 때만 성립한다.**

## Decision

**D1.** 신규 패키지 `src/Navigation/seer_pose_publisher` 를 만들어 `1004` 를 폴링하고
`/robot_pose`(PoseStamped, `map`)로 발행한다. 신뢰도는
`/seer/localization_confidence`(Float64)로 분리 발행한다.

**D2. 폴링 기본 주기는 10 Hz** 로 한다. 액션 제어 주기는 20 Hz 지만
`References/Seer-Driver/seer_api_guide.md:28` 이 **「요청 간격 ≥100~200 ms 권장, 과빈번 시
로봇이 연결 정리 → 실효 폴링 ~5–10 Hz」** 라고 명시한다. `LocalizationMonitor` 의 신선도
임계는 `localization_timeout_sec: 0.5` 이므로 10 Hz 면 **5배 여유**로 충족한다.
`rate_hz > 10` 이면 노드가 경고한다.

**D3. 맵 게이트를 둔다.** 기동 시와 `map_recheck_sec`(기본 5 s)마다 `1000` 의
`current_map_md5` 를 `expected_map_md5` 와 대조하고, **불일치면 발행하지 않는다.**
좌표계 어긋남을 조용한 오차가 아니라 **시끄러운 실패**로 바꾸는 것이 목적이다.
기본값은 빈 문자열(비활성 + 경고) — 아래 Consequences 의 md5 취약성 참조.

**D4. stamp 는 수신 시각(ROS clock)** 을 쓴다. 응답에서 `create_on` 이 관측되나 Seer 와 본
호스트의 시계 동기가 확인되지 않았고, 신선도 판정이 시계 오프셋에 오염되면 정상 데이터를
stale 로 오판하거나 그 반대가 된다.

**D5. 프레이밍은 `csm.seer_client` 를 재사용**한다(복제하지 않는다). 그 모듈이 **읽기 전용
포트 허용목록을 접속 시점에 강제**하기 때문이다 — 복제하면 그 안전 가드도 복제되고, 한쪽만
고쳐지는 순간 성질이 갈라진다. Navigation → MES 방향 의존이 층위상 어색하나, **안전 가드
단일화가 층위 정결성보다 우선**한다고 판단했다.

## Alternatives (기각·보류)

- **Push API(포트 19301)** — 로봇이 능동 push 하여 폴링 부담이 없다. **이것이 옳은 방향**이나
  `seer_api_guide.md:166` 이 **「구독 항목 설정 방법은 미열람(⚠)」** 이라고 명시한다.
  사양 없이 만들 수 없어 **보류**. 사양 확보 시 이 노드를 그쪽으로 옮기는 것이 맞다.
- **`trnav_pose_publisher` 를 이식** — 원본이 이 저장소에 없고 어느 저장소에 있는지 확인되지
  않았다.
- **TF 로 바꾼다** — `LocalizationMonitor` 를 고쳐야 하고, 그러면 QD 와 갈라진다.
- **20 Hz 폴링** — 10초 200/200 실측이 있으나 벤더 권장을 4배 초과한다. 지속 운용 안전의
  근거가 아니다.

## Consequences

**이득** — 실기에서 4종 액션이 abort 하던 원인이 제거된다. Seer 측위를 그대로 쓰므로 별도
측위 스택·캘리브레이션이 불요하고, `confidence` 라는 품질 지표가 덤으로 생긴다.

**비용·제약**
- Navigation 이 MES(`csm`)에 exec_depend 한다.
- 자세가 **10 Hz**, 제어가 20 Hz — 제어 루프가 같은 자세를 두 번 쓴다. 0.2 m/s 에서 100 ms =
  2 cm. **실기 추종 오차 영향 미측정.**
- 무선 경유다(`ssid T-Robotics3f_3_5g`). 0.5 s 이상 끊기면 `LocalizationMonitor` 워치독이
  액션을 중단시킨다 — 안전 측 동작이나 **주행 중 무선 품질은 미측정**.

**⚠ 맵 md5 취약성 (실측)** — 같은 세션 안에서 30분 만에 md5 가 바뀌었다:

```
19:47  260709_test  md5 0d0a479f583b2b84f9f45a6de87eead7
20:13  260709_test  md5 79e59a5ac112551ab7f1dea192230a94
```

그 사이 타 세션이 맵 읽기 작업을 했다. **맵을 다시 저장·업로드하면 이름이 같아도 md5 가
바뀐다.** 따라서 게이트는 엄격하되 취약하며, 맵 갱신 때마다 설정값을 함께 갱신해야 한다.
기본값을 비활성(경고)으로 둔 이유다. 이름만 보는 완화안은 채택하지 않았다 — 이름이 같아도
내용이 다를 수 있어 게이트 목적을 달성하지 못한다.

**남는 위험** — 장시간 연결 유지 미검증, `min_confidence` 임계값 근거 없음(정지 상태 0.83
관측이 전부, 기본 0=비활성), **구동 연동 검증 0회**(본 노드는 읽기 전용으로만 확인).

## Rollback

가역. 노드를 띄우지 않으면 종전 상태(= `/robot_pose` 없음)로 즉시 돌아간다 — 다른 노드의
동작을 바꾸는 변경이 아니다. 패키지 자체를 되돌리려면 `src/Navigation/seer_pose_publisher`
삭제 후 `colcon build`. **영속 상태·스키마·펌웨어 변경 없음.**

로봇에 대한 부작용도 없다 — 상태 포트 19204 만 열고 명령 API 번호가 코드에 등장하지 않는다.

## 검증 근거

`docs/function_table.md` §검증 참조. 요약: 발행 **9.796/9.978 Hz**, 구동 중인 로봇 좌표를
실시간 추종((−11.85, 2.40) → (−12.24, 2.27)), confidence 0.8426,
**맵 게이트 차단 시 `ros2 topic hz` 12초간 수신 0건**.
