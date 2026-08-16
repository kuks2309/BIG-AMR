# mcl2d_ros2 — code updates

2026-08-16 / 21:00 - (pending commit) / **측위 노드 lifecycle 화** (ADR `docs/adr/2026-08-16-mcl2d-lifecycle-node.md`)

- **수정** `src/mcl2d_localization_node.cpp` — `rclcpp::Node` → `rclcpp_lifecycle::LifecycleNode` 전환:
  - 생성자: 파라미터 **선언만**(재 configure 시 재선언 예외 방지). `autostart`(bool, 기본 true) 신설
  - `on_configure`: 파라미터 읽기·검증 + 맵 로드 + 로컬라이저·lifecycle publisher·TF 자원 생성.
    실패는 throw → **FAILURE 반환**으로 교체(unconfigured 잔류)
  - `on_activate`: publisher 활성화 + 구독 3종 생성 + 증분 기준점·스캔 캐시 리셋(비활성 구간 대증분 차단)
  - `on_deactivate`: publisher 비활성화 + 구독 해제(콜백·TF 완전 정지)
  - `on_cleanup`/`on_shutdown`: 전 자원 해제 → 재 configure 로 **맵 교체 가능**
  - `main`: autostart 면 spin 전 `configure()`→`activate()` 동기 구동, 실패 시 FATAL + exit 1
    (종전 "맵 없으면 기동 실패" 거동 보존). launch 이벤트 방식은 서비스 디스커버리 경쟁으로 기각
  - `declareTuned` → 선언(생성자)과 읽기+WARN(`readTuned`, on_configure)으로 분리
  - 주석의 날짜·리뷰 ID 인용 10건 제거(comment-gate, 주석은 현재 사실만 — 이력은 본 문서·ADR 소관)
- **수정** `CMakeLists.txt` · `package.xml` — `rclcpp_lifecycle`·`lifecycle_msgs` 의존 추가
- **수정** `launch/localization.launch.py` — `autostart` 인자 신설(기본 `'true'`,
  `ParameterValue(value_type=bool)` 로 노드 bool 파라미터와 타입 정합). 헤더 주석을 lifecycle
  상태 계약으로 갱신. `bringup.launch.py` 는 무수정(autostart 기본값으로 종전 거동 유지)
- **신규** `docs/code_review/mcl2d-ros2/2026-08-16.md` — 패키지 전수 함수표·멤버변수표
  (모듈 로컬 권위본, 루트 `docs/sw_structure/function_table.md` 에 등재)
- **범위 확정**(사용자): 향후 변경 예정은 encoder odom(오도메트리 소스)뿐 — 노드는 `/odom`
  remap 으로 소스 무관, 소스 교체 시 이 패키지 무수정

**영향**: 토픽·TF 계약 불변(/mcl_pose, map→odom). 노드가 lifecycle 서비스(`~/change_state` 등)를
추가 제공 — 맵 교체·일시 정지·재초기화가 프로세스 재시작 없이 가능. autostart 기본값이라
기존 launch 사용법 그대로 동작. 실패 모드: autostart 시 종전과 동일(프로세스 종료),
외부 관리(autostart:=false) 시 configure FAILURE 로 unconfigured 잔류.

**검증** (실기 tegra, ROS Humble):

- 빌드: `colcon build --packages-select mcl2d_ros2` PASS (42.6s)
- 맵 없이 autostart 기동 → `[ERROR] map_path 는 필수` + `[FATAL] autostart: configure 실패` + **exit 1**
- 실맵(260709_test.smap, 17,711 장애물) autostart 기동 → `active [3]` 도달
- `deactivate` → `inactive [2]`, 구독 전부 해제 확인(`ros2 node info`: /parameter_events 만 잔존)
- autostart:=false 수동 사이클: `unconfigured [1]` 기동 →
  configure→activate→deactivate→cleanup(`unconfigured [1]`)→configure→activate 전부
  `Transitioning successful`, 최종 `active [3]`. 로그의 `loaded map` **2회** = 재 configure 가 맵 재적재
- `ros2 launch mcl2d_ros2 localization.launch.py map_path:=…` → YAML 파라미터 적용 WARN 확인
  (`init_dist_scatter = 0.3`, `init_angle_scatter = 0.1`), 장비에 흐르던 실 /odom·/scan_merged 로
  **활성 상태 실데이터 처리 확인**(mode=4 진단 로그, stopped 0↔1 전환)
- 회귀: `compare_impls 260709_test.smap` → `[PASS] 원본↔non-ROS↔ROS2 일관 (배관 무손실, ≤1e-9)`
