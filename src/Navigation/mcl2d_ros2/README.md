# mcl2d_ros2 — Seer 2D MCL 위치추정 스택

## 구동 한 줄

```bash
ros2 launch mcl2d_ros2 bringup.launch.py map_path:=/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/map/260709_test.smap
```

라이다 2대(sick) + dual_laser_merger + icp_odometry(/odom) + **mcl2d 측위**(lifecycle,
autostart) + smap_map_server(/map latch) 가 전부 이 한 줄로 뜬다.

| 옵션 | 기본 | 설명 |
| --- | --- | --- |
| `rviz:=true` | false | rviz2(mcl2d_check.rviz) 동시 기동 — DISPLAY 필요, 로봇 화면에서만 |
| `map_server:=false` | true | /map 발행 생략 |
| `lidar:=false` / `icp:=false` / `localization:=false` | true | 계층별 끄기(이미 떠 있는 것 중복 기동 방지) |
| `params_file:=<yaml>` | 동봉 config/mcl2d.yaml | 측위 파라미터(재측위 임계 포함 — 맵 바꾸면 재실측) |

⚠ 전제 — **라이다 네트워크**: 센서는 eth1 유선이며 호스트 라우트 설정이 재부팅 시 사라진다.
절차: `docs/network/seer_network_access.md`. 없으면 sick 드라이버가 timeout 으로 죽는다.

## 운용 조작

```bash
ros2 lifecycle get /mcl2d_localization              # 상태 확인 (정상 = active)
ros2 lifecycle set /mcl2d_localization deactivate   # 측위 일시 정지(구독·TF 완전 중단)
ros2 lifecycle set /mcl2d_localization activate     # 재개
# 맵 교체: deactivate → cleanup → (param set map_path) → configure → activate
```

- **초기 위치**: RViz 「2D Pose Estimate」(→ `/initialpose`). 받은 자세를 정답이 아니라
  **탐색 중심**으로 써서 주변을 재탐색(relocalize)한다 — **실제 위치 ~1 m 이내**로 찍으면
  확실히 수렴하고, 크게 어긋났으면 한 번 더 찍는다(찍을 때마다 재탐색).
- 출력: `/mcl_pose`(PoseWithCovarianceStamped) + TF `map→odom`.
  `odom→base_link` 는 오도메트리 소유 — 이 노드는 발행하지 않는다.

## 문서

- 함수표(권위본): `docs/code_review/mcl2d-ros2/2026-08-16.md`
- 수정 이력: `docs/mcl2d_ros2_code_updates.md`
- lifecycle 설계 결정: `docs/adr/2026-08-16-mcl2d-lifecycle-node.md` (저장소 루트)
