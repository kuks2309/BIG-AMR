# trnav_2ws_dock_control — LGIT 도킹 코어 이식 (W1)

**출처**: `github.com/kuks2309/LGIT-C6-Cobot` 커밋 `7a2df9842a121b97fbdf93fe1b4dd5596cf20ea2`
(2026-08-23) 의 `src/Skills/Docking_Control/dock_control`. 코어·검증 자산은 **무수정 복사**다
(md5 대조로 확인) — 수정하려거든 먼저 상류와의 재동기화 전략을 정할 것.

- 사전승인: `docs/adr/2026-08-23-2ws-dock-port.md` (저장소 루트)
- 함수 상세: [docs/function_table.md](docs/function_table.md) (원본 표 승계 — 정본
  `phase1_gui.py` 대응 줄번호 포함)
- 정본(실차 검증 파이썬)은 LGIT 저장소에만 있다 — `test/golden/golden.tsv` 는 그 정본에서
  생성된 벡터이고, 여기서는 대조만 한다(`gen_golden.py` 는 정본이 있어야 돌므로 미복사).

## 빌드·검증 (plain cmake — colcon 무시)

```bash
cd src/Control/Motion_Control/2WS/trnav_2ws_dock_control
cmake -B build -S . && cmake --build build -j6 && ctest --test-dir build
```

## 이 패키지가 아직 아닌 것

- 관측(`/feature_pose` → 거리·수평·자세축) 어댑터 — W2
- 2WS IK steer-hold 어댑터(`trnav_2ws_kinematics` 기반, 원본 `dock_ik` 대응) — W2
- 액션 서버·지령 체인 결합 — W3
- 게인·`arm_m` 은 QD 기체 값 — 2WS 실기 재튜닝 전 미검증
