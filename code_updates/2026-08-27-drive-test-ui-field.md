# 2026-08-27 — drive_test_ui 현장 수정 3건 (10왕복 실기 중)

대상: `Tools/drive_test_ui/drive_test_ui.py` (반영은 UI 재기동 시 — 실행 중 인스턴스는 구판).

## 1. 탭① wall 항목을 저장 티치 파일로 기동

어제 wall 티치가 세션 임시폴더에서 증발해 오늘 LOST 를 유발("티칭 값 저장이 안 되는
것 같은데" 지적). 티치를 `Tools/wall_teach/walls_lm1_live.yaml`(2026-08-27 사용자
지정 특징점: topwall rms 2.0 mm + dockface rms 2.8 mm)로 저장소에 영속하고, 탭①
wall 항목 명령을 launch 기본값 대신 `ros2 run … --params-file <저장 티치>`
(+scan_merged 리맵·초기 추정)으로 교체.

## 2. 외부 기동 노드도 램프·버튼 "실행 중"(파랑) 표시

전역 중복 검사는 외부 기동을 감지해 거부하면서 램프는 회색이라 모순("외부에서
실행되면 파란색이 나와야" 지적). `_refresh` 가 자기 자식 외에 `ps -eo args` 1회
스냅샷에서 marker+CHILD_PATTERNS 매칭으로 외부 인스턴스를 감지해 동일 표시.

## 3. 도착 PGV 산포 점을 공차 판정색으로

마지막 점만 빨강이라 공차 초과로 오독됨. 점 색을 공차 3 mm 원 기준 판정
(안=초록·밖=빨강)으로 바꾸고 마지막 점은 테두리 강조로 구분.

검증: py_compile · 실기 반영은 현재 10왕복 종료 후 재기동 시(실험 중 재기동 금지).
관련 운영 기록: `Log/translate_gain_tuning_260827.md`(라이브 게인 튜닝),
`Log/dock_target_teach.json`(PGV 6회 평균 보정 이력 문자열).

## 4. 무정지 도킹 전환 (사용자 설계: 출구속도=입구속도 + mux 전환)

게이트 완전 정지 후 도킹이 시작되던 것을 속도 연속 체이닝으로 교체.
- UI: 전진 leg 에 exit_speed=dock_speed 부여(_goal 시그니처에 exit_speed 추가),
  게이트 기본 0.25 → 1.0 m (속도 연속 조건 gate ≥ dock_speed/0.8).
- dock 서버(trnav_2ws_dock_ros): `skip_settle_if_aligned`(기본 false, yaml true) —
  yaw 공차 내·스핀 미경유 진입이면 2 s settle 생략, 즉시 접근. 스핀 경유(조향
  ±90°)는 settle-then-drive 유지. 전환 갭은 하류 유지(can_relay cmd_timeout 0.3 s)
  내로 실측 검증 예정 — 첫 실기는 저속 진입 권고.

## 5. 전환 단절 0.22 s 제거 — 체이닝 leg 는 hold_steer=True (2026-08-28)

rosbag(run_072920) 실측: 전환부에 0 지령 11건(0.22 s) — translate 도달 후
Phase 4(조향 복귀) 루프가 속도 0 을 반복 발행한 것이 원인. 출구속도>0 인
체이닝 leg 는 hold_steer=True 로 Phase 4 를 생략(조향은 도킹이 즉시 인수).
출구속도=0 leg(후진 등 정지 종단)는 기존대로 조향 복귀 유지.

## 6. 사전 대기(armed) 도킹 + 정지 대기 (2026-08-28, 사용자 설계)

"도킹 노드는 이미 실행되고 그 다음에 전환" — 도킹 goal 을 전진 전에 발행(armed),
서버가 wall 실거리로 게이트 진입 순간 mux 를 인수한다. 전환 지령 공백이 원천
제거되고(잔여 스파이크 2~3표본의 원인이던 결과왕복·전이 틱 소멸), 게이트 판정이
wall 기준이라 mcl 랙 오버런도 무효화.
- 서버: `arm_engage_dist_m`(0=즉시 인수, goal 수락 시 재독) + kArmed 대기(무지령)
  + 전방 전이(kPreYaw→kPreAlign→kApproach) 동일 틱 재실행(전이 틱 0 지령 제거)
  + mux 응답 대기 기준을 요청 시각(mux_req_time_)으로 교정.
- UI: 전진 leg 를 전 구간(dist)으로 보내고 handoff_fut(도킹 결과)로 회수,
  _dock_goal 을 _dock_send/_dock_wait 로 분리, arm 거리 = 게이트 스핀박스
  (실험 시작 시 ros2 param set).
- 정지 대기: '정지 대기 s' 스핀박스(기본 1.0, 0~5) — 후진 정지 후·도킹 완료 후
  재출발 전 대기(모터 부담 완화, 사용자 지시).
