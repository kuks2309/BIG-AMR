# 2026-08-24 — 노드 간 주행 실행기 신설 + SIL 완주 (FAT 시나리오 1 조립 계층)

> 약어: FAT(Factory Acceptance Test) · SIL(Software-In-the-Loop)

- 사용자 지시: "도킹 전에 주행이 진행되어야 합니다. translate 는 검증했지만 node 를
  정의하고 그 node 간의 주행은 아직" + FAT 시나리오 원문 제시(`Remote_instruction/
  FAT_Test/FAT 시나리오_티로보틱스_초안.pptx`) — "2개의 노드를 진행하다가 가까워지면
  정밀 도킹으로 전환"
- 사전승인: `docs/adr/2026-08-24-waypoint-nav.md` · 인벤토리:
  `docs/code_review/waypoint-nav/2026-08-24.md`

## 사전조사 (재사용 확정 — 신규 제어 코드 0)

- 노드: Seer smap `advancedPointList` 에 LM1~LM4 + StraightPath 6간선 기존재
- 주행: `AMRMotionSpin`(상대각)·`AMRMotionCrabLinear`(map 직선+yaw 유지) — 검증된 액션,
  **각 서버가 mux 소스를 스스로 전환**(전 서버 select_motion_source 호출 확인)
- 자세 브리지: `sil_pose_adapter` 가 PoseWithCovariance→PoseStamped 변환기 —
  실기에서 `/mcl_pose` 리맵으로 재사용(debt-068 공백 해소 경로)
- FAT 시나리오 1: 레그 1-2 전후방 ≥10 m·1.0 m/s·0.3 m/s² / 레그 2-3 측방 ≥4 m·
  0.5 m/s / 레그 3-4 0.6 m/s → 도킹 노드 정밀 도킹(Laser Tracker·PGV 측정)

## 신설 — `Tools/waypoint_nav/`

- `run_route.py`: 레그별 spin(헤딩 정렬, `heading: keep` 이면 생략)→crab_linear
  (레그별 속도·가속) 시퀀서 + 경로 끝 `AMRMotionDockApproach` 전환(dock 스펙 —
  스테이션 프레임임을 명시). `--dry-run`·`--skip-dock`·smap/yaml 노드 소스.
  실패 시 즉시 중단. 액션명은 `_abstract` 접미가 정본(서버 소스 확정).
- `route_sil.yaml`(SIL 3레그) · `route_fat.yaml`(FAT 템플릿 — 좌표 자리표시,
  현장 확정 전 실기 사용 금지 명기) · `run_sil_route.sh`(공유 플랜트 스택+spin 서버
  조립, 무모터)

## 검증

- dry-run 계획 출력 정상 → **SIL 완주**: 전방 4 m(1.0 m/s)→측방 2 m(0.5 m/s)→
  전진 2 m(0.6 m/s), 21 s, 플랜트 참값 최종 오차 **41 µm/2 µm**
- 실기 지령 경로 무접촉(플랜트가 지령 소비) — 실모터 구동 금지 상태 유지

## 남은 일

- 실기: mcl2d+브리지로 smap LM 노드 간 저속 주행(입회) → FAT 좌표 확정 →
  경로 끝 도킹 전환 통합 리허설(주행 map 프레임 ↔ 도킹 스테이션 프레임 인계 검증)
- 루트 `docs/sw_structure/function_table.md` 등재는 타 세션 동시 수정 경보로 보류
