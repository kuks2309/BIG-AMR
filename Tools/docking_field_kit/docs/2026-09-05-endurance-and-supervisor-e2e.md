# 최종 펌웨어 100사이클 내구 + 배포 감시자 복귀 E2E — 2026-09-05 (세션 67ed5a48)

## 1. 100사이클 내구 — 펌웨어 md5 c04e7b07 (핸드오버 시퀀서 + 보드 이름 검증 최종 이미지)

도구 `e3_100.py 100 4.0`(take 4 s → release → Seer 조향·알람·passthrough·safety 판정, 어제 100/100 과 동일 절차). 11:10~11:30.

| 항목 | 결과 |
|---|---|
| PASS | **100/100** (|steer| 최대 0.000 rad, 재호밍 0) |
| engage 중 Seer 재init 쓰기 | 0건 (100사이클 합) |
| EMCY | 0 |
| 신규 알람 | 0 (100사이클 전부 `new_alarms=[]`) |
| release 뒤 passthrough·safety | 매 사이클 ok·0 (ABORT 0) |

원자료 `logs/e3_100_final_c04e7b07.log`. 사용자 종결 기준(100회)을 시퀀서 이후 최종 이미지로 다시 충족.

## 2. 배포 감시자 복귀 E2E — `orin_supervisor_e2e.py` (도메인 125, 유닛 그대로, 노드 프로세스 SIGKILL)

| 경로 | 관측 | 판정 |
|---|---|---|
| A 드라이버 사망 → 자동 복귀 | RUNNING → DEAD(3.3 s) → WAIT(프로세스 재기동) → RESTORE(복귀 지시 1/3) → RUNNING, 새 pid 1659466, kill 뒤 10.4 s. 수동 해제 → IDLE 유지 | PASS |
| B 드라이버+감시자 동시 사망 | 새 감시자 저널 `감시자가 없는 사이 대상이 재기동했다(pid 1659466 → 1660202)` → RESTORE(2/3) → RUNNING, 10.6 s | PASS |
| C 감시자만 재기동(부정 대조) | 새 감시자 WAIT → RUNNING(복귀 호출 0, 드라이버 pid 불변) → 수동 해제 → IDLE → 감시자 재기동 → IDLE 유지, 복귀 호출 0 | PASS |

- 1차 실행(`logs/orin_supervisor_e2e_run1.json`)의 C 는 죽은 감시자의 마지막 메시지(1 s 잔상)로 `sup_back_running` 이 참이 된 **측정 결함**이 있었다. 그때 실제로 관측된 것은 「감시자 부재 중 수동 해제 → 새 감시자 IDLE(비복귀)」로, 그 자체가 유효한 부정 대조다. 잔상을 지우고 새 감시자의 `감시 시작` 저널까지 요구하도록 고쳐 C 만 재실행(`logs/orin_supervisor_e2e_C.json`).
- Seer 알람 52111 없음(A·B). 조향·구동 지령은 넣지 않았다.
