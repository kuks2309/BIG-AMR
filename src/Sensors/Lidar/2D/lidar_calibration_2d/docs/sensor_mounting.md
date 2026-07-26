# LiDAR Sensor Mounting Information

## 휴머노이더 AMR - SICK nanoScan3 장착 정보

### scan_front (IP: 192.168.192.100)
- 물리적 위치: 앞 왼쪽
- base_link 기준 위치: x=0.32, y=0.39, z=0.2865
- 장착 상태: 정방향 (바닥면이 아래)
- yaw: 0.785398 rad (45.0 deg)

### scan_rear (IP: 192.168.192.101)
- 물리적 위치: 뒤 오른쪽
- base_link 기준 위치: x=-0.32, y=-0.39, z=0.2865
- 장착 상태: 정방향 (바닥면이 아래)
- yaw: -2.356194 rad (-135.0 deg)

## 센서 배치도 (top-down, X=전방)

```
        X (전방)
        ^
        |
   F(+) +-------+
        |       |
  Y <---+ base  |
        | _link |
        +-------+ R(-)

  F: scan_front (0.32, 0.39) yaw=45°
  R: scan_rear (-0.32, -0.39) yaw=-135°
```

## 캘리브레이션 결과 (2026-03-17 14:45:43, ICP 보정 후)
- scan_rear 보정값: tx=-0.251, ty=-0.371, yaw=-134.73°
- ICP 보정량: dx=0.067m, dy=0.020m, dyaw=0.27°
- 대응 거리: 0.018m
