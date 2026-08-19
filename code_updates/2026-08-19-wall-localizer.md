# 2026-08-19 — 벽 3면 라이다 정밀 측위 신설 (wall_localizer_core + wall_localizer_ros2)

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다.
> 약어: TLS(Total Least Squares) · SIL(Software In the Loop) · TF(Transform)

- 사용자 지시: 2026-08-18 세션 목적 "라이다 정밀 위치 추종 구현" →
  "3개의 벽(직선)으로부터 라이다로부터 거리를 추정하는 것, bluebotics 에서 이렇게 구현" →
  문답 확정: ① 스테이션 국소 정밀 위치 ② 기준 벽 수동 YAML ③ 제어 결합은 후속
  (LGIT AMR docking_action 참조 예정, "먼저 측위 개발 부터") + "References/Bluebotics 참조"
- 사전승인: `docs/adr/2026-08-18-wall3-precision-localizer.md` (BlueBotics ANT 매뉴얼
  원문 대조 절 포함 — 최소 세그먼트 40cm·X/Y 방향별 기준·CAD 좌표 경고 등 반영)
- 인벤토리(계획 단계 선작성 → 구현 후 앵커 확정): `docs/code_review/wall-localizer/2026-08-19.md`
  (루트 정본, 패키지 병기 2곳)

## 신설 내용

`src/Navigation/wall_localizer_core/` — 순수 C++17 코어 (ROS 의존 0, mcl2d_core 관례):

- `types.hpp` 공용 자료형·파라미터·SE(2) 기하 유틸. 직선 법선형 `n·p=d, d≥0` 원점 정향
  규칙으로 무방향 직선의 π 모호성 제거
- `line_extractor` 스캔→점군(거리/섹터 게이트)→간격 클러스터링→split-and-merge→공선
  병합→TLS 적합. 결정론(난수 0)
- `wall_matcher` 기준 벽 정향 고정(orientWall)·라이다 투영(predictWallsInLidar)·
  각도/거리/겹침 게이트 + 점수순 탐욕 1:1 대응(matchWalls)
- `pose_solver` yaw=가중 원형평균, 병진=2×2 가중 정규방정식, Σnnᵀ 최소고유값 가관측성
  검사(평행 벽만이면 해 거부)
- `wall_localizer` 파사드: 대응→해석 반복(≤3), 잔차·점프 게이트, OK/DEGRADED/LOST 판정,
  연속 기각 한도 초과 시 초기 추정 복귀
- 테스트 3본 + `sim_scan.hpp`(레이캐스트 합성 스캔·CHECK 매크로)

`src/Navigation/wall_localizer_ros2/` — ROS2 Humble 어댑터:

- `wall_localizer_node.cpp`: scan(LaserScan, SensorDataQoS) → `/wall_pose`(PoseStamped,
  frame_id=station, 유효 해일 때만) + `/wall_localizer/diagnostics`(벽별 잔차·매칭·사유).
  라이다 외부 파라미터는 첫 스캔 frame_id 의 정적 TF 1회 lookup(평면 yaw), 폴백 파라미터.
  기준 벽 YAML `wall_names` + `walls.<name>=[x1,y1,x2,y2]`, 형식 오류는 기동 실패
- `config/wall_localizer.yaml`(예시 U자 스테이션 — 실측 교체 필요 경고 포함) ·
  `launch/wall_localizer.launch.py`(scan_topic 기본 `/scan_front`)

## 개발 중 발견·수정

- **겹침비 기준 결함**: 초기 구현은 겹침비를 선분 자기 길이 기준으로 재서, 잡음으로 토막난
  짧은 조각이 비율 1.0 으로 본선분을 이기고 대응을 가로챘다(σ=10mm 합성에서 y 오차
  5.45mm 실측). 예측 벽 구간 길이 기준으로 교체 + split 임계 0.02→0.03m,
  병합 각도 2°→5° 조정 후 해소
- **tf2::getYaw 링크 오류**: geometry_msgs 쿼터니언 오버로드가 tf2_geometry_msgs 링크를
  요구 — 의존 추가 대신 평면 yaw 추출식 직접 계산(뒤집힘 장착은 `use_tf_extrinsic:=false`
  경로로 명시)

## 검증 (이 장비 aarch64 / gcc 11.4 / Humble)

- 코어 ctest **3/3 PASS**. 변이 검증: solvePose 병진 우변 부호 고의 파괴 → 2/3 실패 →
  원복 3/3 (테스트 실효성 증명)
- 합성 정밀도: 무잡음 오차 35µm/0.007°, σ=10mm 단발 <5mm/0.3°, 연속 추적 21스텝 유지
- `colcon build --packages-select wall_localizer_ros2` 성공
- SIL 스모크(전용 토픽 `/wl_smoke_scan`, 기존 그래프 무접촉): `/wall_pose` =
  (0.500035, 0.099981, 2.006°) vs 참값 (0.5, 0.1, 2°), 진단 OK·벽 3면 전부 대응
- **실기 미검증** — 실 스테이션 벽·SICK 라이다 정밀도 측정과 `pose_topic` 리맵 연동
  (LocalizationMonitor 소비)은 후속

## 남은 일 (후속 과제)

1. 실기 검증: 실 스테이션 벽 3면 실측 → YAML 작성 → 정밀도·반복성 측정
   (ros2 도메인 §5 기동 규율 적용)
2. 티치 보정 도구: 벤더가 CAD/도면 좌표를 명시적으로 경고("Small differences are always
   present") — 실측 스캔에서 벽 좌표를 뽑아 YAML 을 채우는 오프라인 도구
3. 추종(제어) 결합: LGIT AMR docking_action 참조 + ANT "Adjusted stop"(이중 감속 램프)
   반영 검토. `/wall_pose` 는 기존 2WS 액션의 `pose_topic:=` 리맵으로 소비 가능
