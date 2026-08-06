# can_relay_gui — CAN relay 시험 GUI 독립 런처

> 2026-08-06 사용자 지시 「원격(Big-AMR) Tools 폴더에 can relay gui 도 이식해서 주행 설정에
> 맞도록」 의 산출물. 작성 세션: LGIT 개발 PC sess:02319e57 (원격 이식).

## 무엇인가

`src/Comm/CAN/can_relay/can_relay/ui/`(UI 1벌 + 백엔드 2종, ADR
`docs/adr/2026-08-04-amr-test-gui-swappable-backend.md`)를 **colcon/ROS2 소싱 없이**
`python3` 로 즉시 띄우는 Tools 런처다. CLAUDE.md 배치 규약(비-ROS2 독립 도구 → `Tools/`,
UI 실체는 패키지 아래 종속)에 따라 **UI 를 복제하지 않고** sys.path 주입으로 같은 코드를 쓴다.

```bash
python3 Tools/can_relay_gui/can_relay_gui.py                  # 기본(both — ros2 실패 시 direct 만)
python3 Tools/can_relay_gui/can_relay_gui.py --backend direct # 판다 직결(시험 전용)
python3 Tools/can_relay_gui/can_relay_gui.py --backend ros2   # 드라이버 경유(운용, ROS2 소싱 필요)
python3 Tools/can_relay_gui/can_relay_gui.py --machine lgit_moma_qd  # QD 기체 설정으로 기동
```

## 기체 선택 (`--machine`, 2026-08-06)

`config/machine/<이름>.yaml` 을 골라 기동한다(기본 `foil_a082` = Big-AMR 2WS). env
`CAN_RELAY_MACHINE` 으로도 동일. **기본기체가 아니면 YAML 로드 실패 시 foil 코드 사본으로
폴백하지 않고 즉시 중단**한다 — 타 기체에 foil 조향 홈·스케일을 조용히 적용하면 물리
오동작이기 때문.

`lgit_moma_qd.yaml`(LGIT-MOMA QD 주행, ⚠ 기체명 가칭): 스케일은 TR_Nav 정본에서 채웠고
(counts/° **48,332.8** — foil 57,344 와 다름, 서로 바꿔 쓰면 안 됨), **`steer_home_counts`
는 미실측(빈 값 → 기동 거부)**. 채우는 기준은 사용자 확정(2026-08-06) — **Seer API
조향값**으로 크로스체크(선례: `docs/homing/2026-08-03-can-relay-homing-assets.md`,
`Tools/docking_field_kit/orin_steer_crosscheck.py`, 역산 기울기는 48,332.8 사용).
LGIT-MOMA 실기에도 panda 장착 확인(사용자 2026-08-06) — 실기에서 크로스체크 실행 가능.

## 주행 설정 정합 (이번 이식에서 함께 정리)

주행 설정 정본은 `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml` 하나다.

| 값 | 정본 키 | 이전 상태 → 현재 |
|---|---|---|
| 조향 0° counts | `steer_home_counts` | 이미 YAML 로드 (`_load_steer_home`, 2026-08-04 리뷰 Medium ②) |
| 조향 counts/° | `steer_counts_per_deg` (57344.0) | **하드코딩(backend_direct.py:47) → YAML 로드** (`_load_drive_scale`, 2026-08-06) |
| 구동 units/mmps | `drive_units_per_mmps` (24.447) | 상동 (:49 → YAML) |
| 구동 상한 units | `drive_max_units` (4889 ≈0.2 m/s) | 상동 |
| 조향 한계 ° | `steer_limit_deg` (90.0) | 상동 (backend 클램프. ⚠ 슬라이더 범위 `app.py:45` 는 별도 리터럴 90 유지) |

로드 실패 시 코드 사본으로 폴백하고 출처 문자열(`DRIVE_SCALE_SOURCE`)에 ⚠ 를 남긴다 —
`STEER_HOME_SOURCE` 와 같은 패턴. 기체가 바뀌면 yaml 만 갈아끼우면 direct/ros2 양 백엔드가
같은 주행 설정을 본다.

## 하지 않은 것 (정직 고지)

- `Tools/amr_test_gui/gui.py`(비교 기준선, debt-039)는 **무수정** — 기준선 보존.
- `app.py:45` 슬라이더 범위 리터럴(90)은 미변경 — 현 정본값과 일치라 거동 차 0. UI 파일은
  타 세션 WIP 활성 상태라 접촉 최소화.
- 실기 검증 0 — 오프스크린 import 스모크만 수행(아래). 실기 GUI 기동·구동 검증은 사용자 수행.
