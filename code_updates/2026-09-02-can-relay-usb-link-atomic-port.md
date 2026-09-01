# 2026-09-02 — `can_relay` USB 링크 안전 수정 2건 이식 (개방 원자화·획득 트랜잭션)

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다.
> 약어: SIL(Software-In-the-Loop) · HIL(Hardware-In-the-Loop)

- 계기: LGIT-C6 저장소의 engage USB 재개방(LIBUSB_ERROR_BUSY) 결함 수정(LGIT 커밋
  005cf76, 2026-09-02) 중 외부 검토(Codex)가 잡은 **경계 결함 2건**이 본 저장소
  `link.py` 에도 자구 동일하게 존재함을 대조로 확인(수정 전 `open`:394 · `acquire`:417,
  LGIT 수정 전 판과 동일). 사용자 승인(sess:336c1015 "승인 진행") 후 패치 선별 이식.
- 본 저장소에 LGIT 의 원 결함(engage 마다 재개방)은 **부재** — 기동 시 관측 핸들이 없고
  disengage 가 링크를 닫는 구조. 따라서 멱등 open·프로브·dirty 복구는 이식하지 않았다
  (해당 구조가 없는 곳에 불필요 복잡도).

## 변경

| 파일 | 변경 |
| --- | --- |
| `can_relay/link.py` | ① `open()` 원자화 — `Panda()` 생성·`health()` 검증을 지역 변수로 수행하고 성공 후에만 `_panda` 공표. 실패 시 부분 생성 핸들 close, `_panda` 는 None 유지 ② `acquire()` 트랜잭션화 — 마지막 heartbeat 까지 try 안으로, 실패 시 `_rollback()`+`engaged=False` 후 `LinkError`(intercept 를 무장한 채 두지 않는다) |
| `test/test_link.py` | 회귀 2건 신설(`test_open_failure_is_atomic_no_partial_handle` · `test_acquire_rolls_back_when_final_heartbeat_fails`) + `_FakeHandle`/`_FakePanda` 대역 |
| `docs/function_table.md` | §6 `link.py` 부분 등재(open:394 · acquire:425, 수정 후 589줄) + 미등재 표 갱신 |

## 검증 (SIL — 개발 PC amap-1)

- red→green 실측: 이식 시험 2건, 수정 전 **2 failed** → 수정 후 **2 passed**.
- 전체 회귀(test_ui_supervisor 는 rclpy 부재로 수집 제외): 수정 전 432 passed/6 failed/
  14 skipped → 수정 후 **434 passed/6 failed/14 skipped**. 실패 6건 이름 집합 동일
  (stash 왕복 대조 실측): test_backend_swap 4건(ModuleNotFound) ·
  test_failed_home_is_visible… · test_panda_source_candidates_exist_when_vendored
  — 전부 선행 환경성, **신규 실패 0**.
- HIL(Orin 실기)은 미실시 — 2026-09-02 08:2x 개발 PC→Orin(100.92.214.74) ssh 타임아웃
  실측으로 도달 불가. 배포·재기동·실기 확인 절차는
  `docs/remote_instruction/2026-09-02-001.md` 로 이관.

## 후속

- Orin 배포: `docs/deployment/2026-08-16-can-relay-supervision-deploy.md` 절차
  (Big-AMR-deploy fetch → detach origin/main → colcon build → `install_service.sh --apply`
  는 sudo 필요 → 유닛 재기동).
- Orin 벤더 panda 의 송신 재시도 상한(`CAN_SEND_RETRY_MAX`) 존재 확인 — LGIT 벤더 판에는
  있음(실측 `vendor/panda/python/__init__.py:584`), 본 저장소 dev 미러의 can_relay 에는
  vendored panda 자체가 없어(`test_panda_source_candidates_exist_when_vendored` 실패와
  정합) Orin 실물에서 확인해야 한다.
