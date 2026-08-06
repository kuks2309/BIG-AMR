# ADR 2026-07-28 — ICP 오도메트리 bringup 패키지 신설 (휠 오도 부재 대체)

- Status: Accepted (구현·기동 검증 완료). 실주행 검증은 미완 — 라이다 스캔 확보 후.
- Date: 2026-07-28
- 관련: docs/code_review/trnav-icp-odometry/2026-07-28.md (이식 대상 리뷰),
  docs/claude-mistake/2026-07-28-010 (기존 자산 조사 누락)

## Context

Big-AMR 은 모터 제어가 미완성이라 **엔코더 휠 오도메트리가 없다.** 그런데
`src/Navigation/mcl2d_ros2` 의 `mcl2d_localization_node` 는 `/odom` 콜백에서만 파티클필터를
갱신하므로(`mcl2d_localization_node.cpp:47-48`, `onOdom`), 오도메트리가 없으면 위치추정 자체가
한 번도 돌지 않는다. 맵 로드까지는 검증됐으나(Seer `260709_test.smap`, 장애물 19,744점) 그 위에서
아무 일도 일어나지 않는 상태다.

대체 수단으로 ICP(Iterative Closest Point) 스캔 정합 오도메트리를 쓴다. 신규 구현·rf2o 도입을
검토했으나, **사용자 저장소 `kuks2309/TR_Nav_ros2_ws` 에 동일 센서 구성(듀얼 SICK →
`dual_laser_merger` → `/scan_merged`)으로 실주행한 `rtabmap_odom/icp_odometry` 설정이 이미
존재**한다. 그 launch 를 리뷰한 결과 High 4건이 나왔고, 원본을 그대로 가져오는 것은 불가하다고
판정했다(TR_Nav 전용 결합 3건으로 기동 불가, `use_sim_time` 기본값 역전으로 TF 미발행).

## Decision

**`icp_odometry` 노드 구성만 추출**해 Big-AMR 전용 bringup 패키지
`src/Navigation/icp_odometry_bringup` 을 신설한다. rtabmap 측위(`rtabmap_slam`) 절반은 가져오지
않는다 — 그쪽은 `.db` 맵 기반이고 Big-AMR 의 측위는 Seer `.smap` + mcl2d 가 담당한다.

리뷰에서 지적한 3건을 설계에 반영한다.

| 리뷰 항목 | TR_Nav 원본 | 본 패키지 |
| --- | --- | --- |
| `publish_tf` 가 `use_sim_time` 에 묶여 실차에서 TF 미발행 (High) | `icp_publish_tf = not is_sim` | **독립 launch 인자** `publish_tf`(기본 true) |
| `Reg/Force3DoF` 부재 → 평면 스캔에 6자유도 ICP (High) | 미설정(rtabmap 기본 false) | launch 인자 `force_3dof`, **기본 true** |
| `Odom/ResetCountdown` 부재 → 상실 후 자가복구 없음 (High) | 미설정(기본 0=비활성) | launch 인자 `reset_countdown`, **기본 0 유지** |
| ICP 파라미터 3개 파일 복제 (Medium) | launch 마다 하드코딩 | `config/icp_odometry.yaml` 단일 파일 |
| `package.xml` 이 실행 패키지 미선언 (Info) | `rtabmap_odom` 누락 | `exec_depend` 로 명시 |

`Reg/Force3DoF` 만 기본값을 바꾸고 `Odom/ResetCountdown` 은 기본 0 을 유지하는 이유: 전자는
**튜닝 값이 아니라 기체 사실**이다(2D 라이다·평면 주행이므로 z/roll/pitch 자유도가 애초에 없다).
후자는 복구 동작이 실제로 어떻게 나타나는지 측정 대상이므로, 원저자의 "prior 와 동시 투입 시 원인
분리 불가 → 순차 진행" 지시를 준용해 기준선을 먼저 잡는다.

## Consequences

**얻는 것**: 휠 오도 없이 `/odom` 이 생겨 mcl2d 파이프라인 전체를 실데이터로 돌릴 수 있다.
파라미터가 YAML 1개로 모여 드리프트가 없다.

**감수하는 위험 (미해결)**: TR_Nav 의 2026-07-13 실차 사고 2건(처리 공백 876 ms → 등속 외삽 실패
→ 대응점 전멸 → yaw +147.17° 국소최소 수렴)의 처방은 `guess_frame_id: odom_dr`, 즉 **엔코더+IMU
순수 DR(Dead Reckoning) prior** 다. Big-AMR 은 바로 그 엔코더가 없어 **이 해독제를 쓸 수 없다.**
기동 로그에서도 `guess_frame_id = `(공란)으로 확인된다. 남은 완화책은
① 저속·수동 주행으로 한정 ② IMU(iAHRS) 전용 guess — 단 ②는 TR_Nav 에 전례가 없어 Big-AMR 에서
새로 검증해야 하는 미검증 경로다.

**부작용**: `publish_tf` 기본 true 이므로, 나중에 휠 오도가 완성되어 같은 `odom→base_link` 를
발행하면 TF 부모 충돌이 난다. 그때는 본 패키지를 `publish_tf:=false` 로 내리거나 prior 구조
(`guess_frame_id`)로 재편해야 한다.

## Rollback Plan

패키지 삭제만으로 원복된다 — 기존 파일을 하나도 수정하지 않았고(신규 4파일뿐), 다른 패키지가
본 패키지를 참조하지 않는다.

```bash
rm -rf src/Navigation/icp_odometry_bringup install/icp_odometry_bringup build/icp_odometry_bringup
```

TF 충돌만 급히 끊고 싶으면 실행 인자로 즉시 무력화: `ros2 launch ... publish_tf:=false`.

## 검증 (2026-07-28, 이 장비)

- `colcon build --packages-select icp_odometry_bringup` 성공
- `ros2 launch icp_odometry_bringup icp_odometry.launch.py` 기동 → `/icp_odometry` 노드 생성 확인
- 실행 중 파라미터 실물 조회: `frame_id=base_link`, `odom_frame_id=odom`, `publish_tf=True`(bool),
  `qos=2`(int), `topic_queue_size=10`, `Reg/Force3DoF=true`, `Odom/ResetCountdown=0`,
  `Icp/MaxCorrespondenceDistance=0.1`, `Odom/ScanKeyFrameThr=0.6` — YAML·launch 오버라이드 모두 반영
- 토픽 결선: 구독 `/scan_merged`(LaserScan) / 발행 `/odom`(Odometry) — `ros2 node info` 확인
- QoS 정합: 우리 merger 가 `SensorDataQoS()`=BEST_EFFORT 로 발행(`dual_laser_merger.cpp:25-26`),
  본 노드 `qos: 2`(BEST_EFFORT) → offered ≥ requested 성립
- **미검증**: 실제 스캔 입력으로 `/odom` 이 나오는지, 정합 품질 — 라이다 기동 후 확인 필요
  → **2026-08-02 해소** (아래)

## 실주행 검증 (2026-08-02, 실기 라이다 기동)

Status 갱신: 정지 상태 검증까지 완료. **이동 중 추종 정확도는 여전히 미검증.**

네트워크 복구(eth1 `192.168.192.10/24` + `/32` 라우트 `src` 고정) 후 실측:

| 항목 | 실측값 |
| --- | --- |
| `/scan_front`·`/scan_rear`·`/scan_merged` | 각 34 Hz (2026-07-25 기준값 일치) |
| 병합 스캔 | 360°(±π), 1441점 중 유효 1101점, 1.06–28.6 m |
| `/odom` | 34.1 Hz — 스캔 1프레임당 1회, 누락 없음 |
| ICP inlier ratio | 0.70 (`Odom/ScanKeyFrameThr` 0.6 위) |
| update time | 3.7 ms / 29 ms 예산 — 연산 여유 큼 |
| 정지 60초 드리프트 (1990샘플) | 위치 **0.6 mm**, 각도 **−0.0011°**, 프레임간 최대 점프 1.55 mm |
| `Reg/Force3DoF` 실효 확인 | 최대 \|z\|=0.000000 m, 최대 \|roll,pitch\|=0.000000 rad |

TR_Nav 사고의 전제였던 연산 포화(876 ms 공백)와는 거리가 멀다 — 3.7 ms/29 ms.

### 실행으로 드러난 결함 2건 (문서 검토로는 안 나왔다)

**① `/odom` QoS 불일치 — mcl2d 에 메시지 0건 전달**

`rtabmap_odom` 의 `qos` 파라미터는 구독뿐 아니라 **발행에도 적용**된다. 스캔 입력을 BEST_EFFORT 로
맞추려 `qos: 2` 를 준 결과 `/odom` **발행도** BEST_EFFORT 가 됐고(`ros2 topic info -v` 확인),
`mcl2d_localization_node` 는 기본 RELIABLE 로 구독해 `offered < requested` → 연결 실패:

```
New publisher discovered on topic '/odom', offering incompatible QoS.
No messages will be sent to it. Last incompatible policy: RELIABILITY_QOS_POLICY
```

`icp_odometry` 쪽은 손댈 수 없다 — 발행 전용 QoS 파라미터가 없고(`qos_overrides` 는 tf·
parameter_events 만 지원), `qos: 1` 로 바꾸면 `/scan_merged` 입력이 끊긴다. 따라서 **소비자 쪽**을
BEST_EFFORT 구독으로 변경(`mcl2d_localization_node.cpp:50-58`). BEST_EFFORT 구독자는 RELIABLE
발행자와도 연결되므로 항상 더 넓다. 재빌드 후 경고 0건.

> 본 ADR 초판과 리뷰 문서는 `/scan_merged` 의 QoS 정합만 소스로 확인하고 **`/odom` 소비자 쪽을
> 확인하지 않았다.** 실행하지 않았으면 발견하지 못했을 결함이다.

**② `mcl2d_ros2` 가 파티클필터를 `-O0` 으로 컴파일 — 위치추정 주기 33배 손실**

`mcl2d_ros2/CMakeLists.txt` 에 `CMAKE_BUILD_TYPE` 이 없어 ament 기본값(빈 값)으로 최적화 플래그가
붙지 않았다. 형제 `mcl2d_core/CMakeLists.txt` 는 Release 를 강제하는데 ROS2 쪽만 누락.

`if(NOT CMAKE_BUILD_TYPE) set(CMAKE_BUILD_TYPE Release)` 추가. build/install 삭제 후 순수 기본
빌드로 `-O3` 적용 재확인.

**A/B 실측** — 최적화 외 조건을 동일하게 두고(같은 맵·같은 라이다 스트림·**노드 인스턴스 정확히 1개**)
각 30초 측정:

| 빌드 | 플래그 | `/odom` | `/mcl_pose` | 갱신 간격(중앙/최대) | 처리 비율 |
| --- | --- | --- | --- | --- | --- |
| 수정 전 | `-g -Wall -Wextra` (최적화 없음) | 32.7 Hz | **4.83 Hz** | 206 / 213 ms | 0.15 |
| 수정 후 | `-O3 -DNDEBUG -Wall -Wextra` | 31.3 Hz | **29.6 Hz** | 33 / 36 ms | **0.95** |

**6.1배**. 수정 후에는 오도메트리 입력의 95% 를 처리하며 간격도 33~36 ms 로 안정적이다.

> ⚠ **측정 오염 주의(실제로 겪음)**: 이 A/B 이전에 기록했던 수치(0.81 / 14.6 / 21.4 / 26.7 Hz)는
> **노드 인스턴스가 2개 떠 있는 상태에서 측정**한 것이라 폐기했다. `ros2 topic hz` 는 토픽의 모든
> 발행자 메시지를 합산하므로 인스턴스가 겹치면 발행률이 부풀고, 동시에 CPU 경합으로 간격 편차가
> 커진다(그때 관측된 210 ms 스파이크·큰 std 는 필터 특성이 아니라 경합이었다).
> **측정 전 `ros2 topic info <토픽>` 의 `Publisher count` 가 1인지 확인할 것.**

**남은 특성(미해결 아님, 사실 기록)**: 노드는 **단일 스레드**로 동작한다 — 스레드 11개 중 main 1개가
99.7 %CPU 를 쓰고 나머지는 0.5 % 내외다(8코어 중 1코어만 사용). `onOdom` 콜백이 파티클필터 전체
갱신을 동기로 수행하므로 처리율 상한 = 1코어 성능이다. 더 올리려면 `max_particle_number`(3000)·
`beams_used`(541) 조정이나 병렬화가 필요하지만, 현재 29.6 Hz / 처리비율 0.95 로 입력을 거의 따라가므로
**당장 조치가 필요한 병목은 아니다.**

참고로 최적화 없는 빌드에서는 CPU 포화가 `icp_odometry` 에도 영향을 줘 `/odom` 최대 간격이 354 ms 로
튀었다(수정 후 48 ms). 위치추정 노드의 부하가 오도메트리 품질까지 끌어내린다는 뜻이다.

### 여전히 미검증

- **이동 중 추종 정확도** — 정지 드리프트만 쟀다. 수동 주행 시험 필요.
- **위치추정 결과의 정확도** — `/mcl_pose` 가 나오지만 라이다 장착 위치가 mcl2d 노드에 Roll_A084
  값으로 하드코딩돼 있고 초기 자세도 `(0,0,0)` 이다. 로봇의 맵 내 실제 위치를 모르므로 "맞게
  추정한다"고 말할 수 없다.
