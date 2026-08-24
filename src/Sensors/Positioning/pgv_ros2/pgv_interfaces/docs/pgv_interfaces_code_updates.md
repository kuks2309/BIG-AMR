# pgv_interfaces — 수정 이력 (code updates)

## 2026-08-24 — 최초 작성

- `msg/PgvPosition.msg` — PGV 위치 응답 21바이트의 전 필드(모드 플래그·스케일 적용
  위치·원시값·태그/제어코드·방향선택·WRN/ERR)를 1메시지로 노출.
- `srv/SetDirection.srv` — 상수값을 장치 응답 비트 배치(LL<<1|RL)와 동일하게 고정.
- `srv/SetColor.srv` — 상수값을 장치 응답 비트 배치(R<<2|G<<1|B)와 동일하게 고정.
- 근거: References/pepperl-fuchs/pgv/tdoct3707d_eng.pdf §5.1.2–5.1.4 (ADR 2026-08-24-pgv-driver).
