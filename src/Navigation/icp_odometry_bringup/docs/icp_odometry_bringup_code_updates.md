# icp_odometry_bringup — code updates

2026-08-23 / (pending commit) / **launch 에 respawn — icp_odometry 자동 재기동** (본 파일 신설)

- **수정** `launch/icp_odometry.launch.py` — icp_odometry Node 에 `respawn=True, respawn_delay=2.0`.
- **주의(주석에도 명기)**: 재기동한 icp 는 odom 을 원점(항등)부터 다시 적산하므로 odom→base_link
  가 점프한다 — 하류 mcl2d 는 재수렴이 필요할 수 있다(initialpose 재지정).
- **검증(실기 2026-08-23)**: `kill -9` → launch 가 died 감지·자동 재기동(pid 2420404→2421026),
  `/odom` 34.1 Hz 회복.
- **내구(실기 2026-08-23, 120분 순환 kill)**: icp proc 2.15 s / `/odom` 3.8 s 회복.
