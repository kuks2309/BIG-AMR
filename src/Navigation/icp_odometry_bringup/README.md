# icp_odometry_bringup — 2D ICP 오도메트리 (휠 오도 부재 대체)

모터 제어 미완성으로 엔코더 오도메트리가 없는 동안, 듀얼 SICK 병합 스캔으로
`odom→base_link` 를 만들어 `mcl2d_localization_node` 를 돌린다.

```
sick_safetyscanners2 ×2 → dual_laser_merger → /scan_merged → icp_odometry → /odom → mcl2d
```

- 설계 근거: [ADR 2026-07-28](../../../docs/adr/2026-07-28-icp-odometry-bringup.md)
- 원본 리뷰: [docs/code_review/trnav-icp-odometry/2026-07-28.md](../../../docs/code_review/trnav-icp-odometry/2026-07-28.md)

## 실행

```bash
# 1) 라이다 + 병합 (본 패키지가 띄우지 않는다 — 없으면 조용히 스캔 대기만 한다)
ros2 launch dual_laser_merger sick_with_merger.launch.py

# 2) ICP 오도메트리
ros2 launch icp_odometry_bringup icp_odometry.launch.py

# 3) 위치추정 (Seer 맵)
ros2 run mcl2d_ros2 mcl2d_localization_node \
  --ros-args -p map_path:=$PWD/map/260709_test.smap
```

`mcl2d_localization_node` 는 `/scan_front`·`/scan_rear` 를 따로 구독하므로 병합 스캔과 별개로
원본 두 토픽이 살아 있어야 한다(merger launch 가 둘 다 띄운다).

## launch 인자

| 인자 | 기본 | 의미 |
| --- | --- | --- |
| `scan_topic` | `/scan_merged` | 입력 LaserScan |
| `odom_topic` | `/odom` | 출력 Odometry (mcl2d 가 구독하는 이름) |
| `publish_tf` | `true` | `odom→base_link` TF 발행. 다른 오도 소스와 충돌 시 `false` |
| `force_3dof` | `true` | `Reg/Force3DoF` — 평면 3자유도 강제(z/roll/pitch=0) |
| `reset_countdown` | `0` | `Odom/ResetCountdown` — 연속 실패 N 프레임 후 자동 리셋. 0=비활성 |

그 외 ICP 파라미터는 [config/icp_odometry.yaml](config/icp_odometry.yaml).

## 알려진 한계 (읽고 쓸 것)

**모션 prior 가 없다.** 출발점이 `Odom/GuessMotion`(등속 외삽)뿐이다. TR_Nav 실차에서 이 구성이
처리 공백(876 ms) + 가감속 회전 조합으로 **yaw 를 +147° 튀게** 만든 사고가 2건 있었다. 처방은
엔코더+IMU 순수 DR 을 `guess_frame_id` 로 물리는 것인데, **Big-AMR 은 엔코더가 없어 그대로 쓸 수
없다.** 따라서 당분간:

- 저속·수동 주행으로 한정한다. 급회전·급가감속을 피한다.
- `/odom` 과 함께 `/odom_info` 를 기록해 inlier·대응점·처리시간을 남긴다.
  (rtabmap 의 `odom_info` 는 `Odom/FillInfoData` 가 켜지면 포인트클라우드까지 담겨 bag 이 커진다)
- 이상 시 `Icp/MaxRotation`(기본 0.78 rad ≈ 44.7°)·`Icp/MaxTranslation`(기본 0.2 m) 가 실제로
  걸렸는지 함께 확인한다 — TR_Nav 사고에서 이 가드가 왜 147° 를 못 막았는지는 원저자도 미규명이다.

## 다음 단계

1. 라이다 기동 후 실스캔으로 `/odom` 발행 확인 (**현재 미검증**)
2. `Odom/ResetCountdown` 을 1 이상으로 올려 복구 동작 측정 (한 번에 하나씩)
3. IMU(iAHRS) 전용 guess 실험 — TR_Nav 전례 없음, 별도 검증 필요
