# sick_safetyscanners2 Code Updates

2026-07-25 / (pending commit) / 추가: Ford-CATL-AMR/Big-AMR 로 재이식
- 원본 TR_Nav_ros2_ws(github.com/kuks2309/TR_Nav_ros2_ws) src/Sensor/Lidar/2D → 본 워크스페이스 src/Sensors/Lidar/2D 통째 복사
- 변경: 없음 (rsync bit-identical 검증 완료 — 34 파일, diff 0)
- 함께 이식: dual_laser_merger, lidar_calibration_2d (2D LiDAR 스택 3종 전부)
- 의존 `sick_safetyscanners_base`, `sick_safetyscanners2_interfaces` 는 apt 설치 필요 (ROS humble/jammy) — 이식 시점 미설치, 설치·빌드는 사용자 수행
- ⚠ 함께 넘어온 운영 critical 문서(UDP 버퍼·DDS 격리) 신규 머신 세팅 시 반드시 적용할 것

2026-07-09 / (pending commit) / 운영 설정: UDP 수신 버퍼 증설 (코드 무변경, 🔴 중요)
- 소켓 :6060/:6061 커널 기본 208KB 오버플로우 (드랍 559/608 실측) → partial frame → 도킹 이상 기동 (#29)
- `/etc/sysctl.d/99-lidar-udp.conf` (rmem_max 8MB / rmem_default 2MB) 적용 — 드라이버 재시작 후 유효
- 상세·재발 점검: [2026-07-09_udp_rcvbuf_critical.md](2026-07-09_udp_rcvbuf_critical.md)

2026-04-26 / (pending commit) / 추가: 본 레포 이식 (LiDAR Wave A)
- T-Robot_nav_ros2_ws/src/Sensor/Lidar/2D/sick_safetyscanners2 통째 복사 (33 파일, 1.3 MB)
- 변경: 없음 (외부 ROS2 드라이버, 원본 라인별 동일 유지)
- 의존 `sick_safetyscanners_base` (apt 1.0.3-1jammy), `sick_safetyscanners2_interfaces` (apt 1.0.0-2jammy) 시스템 설치 확인
- 빌드 검증: `colcon build --packages-select sick_safetyscanners2` 성공 (1min 34s, 경고 없음)

참조 원본: /home/tc/T-Robot_nav_ros2_ws/src/Sensor/Lidar/2D/sick_safetyscanners2
계획: docs/plan/2026-04-26_lidar_port.md
결정: docs/request/2026-04-26_lidar_port.md
