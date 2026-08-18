# ADR 2026-08-16 — mcl2d 측위 노드 lifecycle 화

- **Status**: Accepted — 2026-08-16 (실기 검증 완료 — 전이 전체 사이클·autostart 성공/실패
  경로·실데이터 처리, 근거: `src/Navigation/mcl2d_ros2/docs/mcl2d_ros2_code_updates.md`)

## Context

- `mcl2d_localization_node` 는 일반 `rclcpp::Node` 로, 생성자에서 파라미터 선언·맵 로드·
  로컬라이저 생성·pub/sub/TF 생성을 전부 수행한다. 기동 = 즉시 가동이며, 맵 교체·재초기화·
  일시 정지 같은 운용 조작은 프로세스 재시작으로만 가능하다.
- 사용자 요구: localization 을 lifecycle 화(세션 목적 2026-08-16). 상위 시스템(작업 관리·
  헬스 감시)이 측위를 상태 기계로 다루려면 표준 `lifecycle_msgs` 인터페이스가 필요하다.
- 저장소 선례: `sick_safetyscanners2` 가 lifecycle 노드를 동봉(vendored). ROS Humble 의
  `rclcpp_lifecycle` 표준 사용 가능. nav2 는 이 저장소에 없다 — nav2_util·lifecycle_manager
  의존은 추가하지 않는다.
- 범위: **측위 노드만.** 같은 패키지의 `smap_map_server` 는 맵 제공 전용(latch 1회 발행)이라
  lifecycle 상태 관리의 실익이 없고, localization launch 체인에도 포함되어 있지 않다.
- 확정 범위(사용자 2026-08-16): 향후 추가·변경 예정은 **encoder odom**(오도메트리 소스)뿐,
  나머지 구성은 현재 확정. 노드는 `/odom` 을 토픽 remap 으로 받으므로 소스 교체는 이
  노드 무수정 — launch 의 `odom_topic` 인자만 바뀐다.

## Decision

`Mcl2dLocalizationNode` 를 `rclcpp_lifecycle::LifecycleNode` 로 전환한다.

| 전이 | 하는 일 |
| --- | --- |
| 생성자 | 파라미터 **선언만**(값 읽기·검증 없음). cleanup→configure 재진입 시 재선언 예외를 피하기 위해 선언은 1회로 고정 |
| `on_configure` | 파라미터 읽기·검증, 맵 로드, 로컬라이저 생성, lifecycle publisher·TF 브로드캐스터/버퍼 생성. 실패(맵 부재·파손, laser_mounts 형식 오류) 시 **FAILURE 반환**(unconfigured 잔류) — 종전 throw 기반 기동 실패를 lifecycle 계약으로 대체 |
| `on_activate` | publisher 활성화, 구독 3종(/odom·/scan·/initialpose) 생성, 증분 기준점(prev_odom_ 등) 리셋 — 비활성 구간을 건너뛴 거대 증분 유입 차단 |
| `on_deactivate` | publisher 비활성화, 구독 해제 — 콜백·TF 발행 완전 정지 |
| `on_cleanup` / `on_shutdown` | 로컬라이저·publisher·TF 자원 해제 → 재 configure 로 **맵 교체 가능** |

autostart 는 **노드 파라미터**(기본 `true`)로 구현한다 — `main` 이 spin 전에
`configure()`→`activate()` 를 동기 구동하고, 실패 시 FATAL 로그 + exit 1 로 프로세스를
종료한다(종전 "맵 없으면 기동 실패" 거동을 정확히 보존). launch 는 `autostart` 인자를
bool 로 변환해 넘기기만 한다. `autostart:=false` 면 unconfigured 로 떠 있고 전이는 전부
`ros2 lifecycle` (또는 향후 외부 관리자) 수동 조작.

## Alternatives

- **nav2_lifecycle_manager 도입** — 기각: nav2 스택 미사용 저장소에 대형 의존을 끌어온다.
  상위 관리자가 생기면 그 시점에 표준 lifecycle 서비스로 붙으면 된다(이번 전환이 그 전제).
- **launch 이벤트 기반 autostart**(`ChangeState` emit + `OnStateTransition` 핸들러) — 기각:
  노드 서비스 디스커버리 전에 보낸 전이 요청은 유실될 수 있고(요청은 재전송되지 않는다),
  전이가 실패해도 launch 는 성공으로 끝나 조용한 unconfigured 잔류를 만든다. 노드측
  autostart 는 경쟁이 없고 실패를 exit code 로 알린다.
- **구독을 on_configure 에서 만들고 콜백에서 active 게이트** — 기각: 비활성 중에도 콜백이
  돌아 스캔 캐시가 갱신되고, 게이트 한 줄이 전 콜백에 흩어진다. 구독 생성/해제가 상태와
  1:1 이라 추적이 쉽다.

## Consequences

- 이득: 맵 교체·일시 정지·재초기화가 프로세스 재시작 없이 가능. 상위 감시가 표준
  `lifecycle_msgs` 로 상태를 질의·제어할 수 있다.
- 인터페이스 변화: 노드가 lifecycle 서비스(`~/change_state` 등)를 추가로 제공. 토픽·TF 계약은
  불변(/mcl_pose, map→odom). `bringup.launch.py` 는 수정 불요(포함하는 localization.launch.py
  가 autostart 기본값으로 종전 거동 유지).
- 실패 모드: autostart(기본) 경로는 **종전과 동일** — 맵 부재·파손이면 FATAL + exit 1 로
  프로세스가 죽는다. 외부 관리(autostart:=false) 경로만 configure FAILURE 로 unconfigured 에
  남고, 관리자가 전이 실패로 감지한다. 어느 경로든 조용한 (0,0,0) 발행은 없다
  (코드리뷰 2026-08-07 H2 의 방어 목적 유지).
- 비용: rclcpp_lifecycle 의존 추가(Humble 표준, 외부 취약점 표면 증가 없음).

## Rollback

가역 — `git revert` 로 노드·CMakeLists·package.xml·launch 4파일 원복이면 끝(영속 상태·
스키마·펌웨어 접촉 없음). 부분 롤백 불가(노드만 되돌리면 launch 의 LifecycleNode 액션이
전이 실패) — 4파일을 한 커밋으로 묶는다.
