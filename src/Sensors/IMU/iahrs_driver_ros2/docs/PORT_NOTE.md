# iahrs_driver_ros2 이식 노트 (패키지 병기)

정본: `kuks2309/TR_3D_Nav_ros2_ws` → `TR-Nav3d_ros2_ws/src/Sensor/IMU/iahrs_driver_ros2` (2026-07-26 이식).
루트 정본 기록: `docs/sw_structure/imu-iahrs-port/2026-07-26.md`.

## 빌드
```bash
cd <ws_root> && source /opt/ros/humble/setup.bash
colcon build --packages-up-to iahrs_driver   # interfaces 먼저 → iahrs_driver
```

## udev (IMU 연결)
`iahrs_driver/udev/99-imu.rules` (CP2102 10c4:ea60 serial 0001 → /dev/imu).
현재 시스템엔 이미 설치·작동 중. 타 머신 설치:
```bash
sudo cp iahrs_driver/udev/99-imu.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## Big-AMR 조정 필요
- `launch/iahrs_driver.py` 의 base_link→imu_link static TF `(-0.37,0,0.29)` 는 TR-AMR 실측값 → Big-AMR 로 재측정. **→ debt-002**(`docs/debt/registry.md`).
- `interfaces` 패키지명 범용 → 충돌 주의. 리네임 안 함(원본 유지).
