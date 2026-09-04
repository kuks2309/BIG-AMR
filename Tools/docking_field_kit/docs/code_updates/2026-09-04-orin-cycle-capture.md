# 2026-09-04 — `orin_cycle_capture.py` 신설 (세션 67ed5a48)

- **무엇을**: take(4 s)→release 1사이클을 돌리며 판다 양 버스(bus0·bus2, TX echo 128/130 포함)를 필터 없이
  jsonl 로 기록하고, 단계별 health(`car_harness_status`·`safety_mode`)·Seer steer·알람 차분·bus 별 프레임
  서명(req/resp/guard/emcy)을 출력한다. release 뒤 최대 45 s 동안 재호밍 스윙 시작·복귀 시각을 찍는다.
- **왜**: 기존 `Rig` 로그는 bus2 만·drain 시각 타임스탬프라 release 전이 판정이 불가했다.
  debt-129 잔여 13% 와 debt-130(하네스 방향 랜덤) 검증은 "어느 버스에 무엇이 실렸는가" 가 관건이다.
- **검증**: 2026-09-04 15:26 E1 실행 — FLIPPED 부팅에서 engage 브리징 루프 폭주(node4 EMCY 0x8110)·
  release 뒤 Seer↔모터 절단을 캡처로 확정(`Log/e1_all_260904_152648.jsonl`,
  `docs/can_relay/debt-129-rehoming-cause-analysis-2026-09-04.md` §6).
- **주의**: 조향 137° 스윙을 유발할 수 있다. 이동 구역 확보 후 실행.
