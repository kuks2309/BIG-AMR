# lidar_merger_sync_check

`dual_laser_merger` 가 **정말로 쌍을 맞춰 발행하는지**, 그리고 **그 쌍이 시간적으로 얼마나
벌어져 있는지**를 재는 도구. colcon 패키지가 아니므로(= `package.xml` 없음) `Tools/` 아래에 둔다.
**실행에는 ROS2 런타임이 필요하다**(`import rclpy`).

리뷰: [docs/code_review/lidar-merger-sync-check/](docs/code_review/lidar-merger-sync-check/)

```bash
source /opt/ros/humble/setup.bash && source install/setup.bash
python3 Tools/lidar_merger_sync_check/merger_sync_check.py --help
```

## 왜 필요한가

「입력 34 Hz 인데 출력이 40 Hz」 같은 관측은 `ros2 topic hz` 하나로는 판정할 수 없다.
`ros2 topic hz` 는 **BEST_EFFORT 구독자가 실제로 받은 건수**를 세므로, 큰 메시지일수록
측정 프로세스가 더 많이 흘린다. 실제로 `/scan_front` 는 `ranges` + `intensities` 각 1592개
(≈12.7 KB), `/scan_merged` 는 `ranges` 1441개(≈5.8 KB)로 **입력이 2.2배 크다** — 같은 도구로
재도 입력이 더 낮게 나올 수 있다.

그래서 이 도구는 언제나 **세 가지 수치를 분리해서** 낸다.

| 수치 | 무엇에 취약한가 |
|---|---|
| 도착률 (수신 시각) | 구독자 유실에 취약 — `ros2 topic hz` 가 보는 값 |
| 스탬프률 (`header.stamp` 차분 중앙값) | 유실에 강함 — 발행자가 실제로 낸 간격 |
| 센서신고 (`LaserScan.scan_time`) | 센서 자기신고 주기, 유실과 무관 |

셋이 어긋나면 어긋나는 방식이 곧 진단이다. 도착률만 낮으면 **재는 쪽이 흘린 것**이고,
merger 자기보고(`~/sync_skew`, `sync:` 로그)와도 다르면 발행자가 둘 이상인지 본다.

## 모드

### observe — 돌고 있는 실기 관측 (34/40 판정용)

```bash
python3 Tools/lidar_merger_sync_check/merger_sync_check.py observe --duration 20
```

토픽별 세 수치 + **발행자 수와 QoS** 를 낸다. `/scan_merged` 발행자가 2개면 여기서 잡힌다.
merger 가 `publish_sync_diagnostics:=true`(기본값)로 돌고 있으면 `~/sync_skew` 도 함께 집계한다.

### inject — 하드웨어 없이 구조 검증

정확히 지정한 주기로 합성 스캔을 내고, 실제 merger 노드를 자식 프로세스로 띄운 뒤
**생산자측 계수**(merger 로그의 `sync:` 줄)와 **소비자측 계수**를 나란히 낸다.
위반이 있으면 `exit 1`.

```bash
# 기본 구조 확인: 34 Hz 넣으면 34 Hz 나온다(입력을 넘지 않는다)
... inject --rate 34 --duration 15

# rear 를 반주기 늦춤 — max_pair_skew=0(기본)에서는 14.7 ms 쌍이 경고 없이 발행된다
... inject --rate 34 --phase 0.5

# 스탬프 출처가 설정대로 나오는지까지 본다
... inject --rate 34 --phase 0.5 --output-stamp latest

# 음성 대조: merger 에 경계를 주지 않고 판정만 3 ms 로 두면 FAIL 이 떠야 한다
... inject --rate 34 --phase 0.15 --max-pair-skew 0 --assert-skew-under 0.003
```

마지막 줄이 중요하다. **「검사를 붙였다」와 「검사가 결함을 잡는다」는 다른 명제**이므로,
경계를 뺀 merger 를 이 검사가 실제로 FAIL 시키는지 확인한 뒤에만 「고정했다」고 말한다.

### inject 가 실제로 판정하는 것 (5종)

| 판정 | 근거 | 성격 |
|---|---|---|
| 산출 ≤ 입력 | 같은 관측 창에서 센 주입 수 대 수신 수 | **필요조건만** — 비동기 구현도 통과한다 |
| 생산자 발행률 ≤ 실측 주입률 | merger 자기보고 `sync:` | 필요조건 |
| 스탬프 출처 = `--output-stamp` | merged 스탬프의 front/rear 정확 일치율 | 충분조건 쪽 |
| 주입 위상 = 관측 skew 중앙 | `--phase` 를 준 무지터 실행에서만 | 충분조건 쪽 |
| 발행 쌍이 경계 이내 | `--assert-skew-under` 또는 `--max-pair-skew` | 음성 대조로 판별력 확인됨 |

**재현성**: `--seed`(기본 0)로 지터 난수를 고정한다. 지터는 명목 격자에 **비누적**으로 얹으므로
`--phase` 가 통제변수로 유지된다(누적시키면 ±4 ms·510 스텝에서 위상 표준편차가 70 ms 로 발산한다).

⚠ **`--expect-drops` 의 한계**: 게이트가 실제로 버렸는지를 콜백 카운터로 확인하려 했으나,
`setMaxIntervalDuration` 이 **콜백보다 먼저** 후보를 폐기하므로(`approximate_time.h:728-731`)
대부분의 경우 `dropped 0` 이 나온다. 게이트 동작의 진짜 증거는 **출력률 저하**다.

### bag — 녹화본 오프라인 분석

```bash
... bag /path/to/rosbag2_dir
... bag /path/to/bag_0.db3 --topics /scan_front /scan_rear /scan_merged
```

실시간 구독이 아니므로 BEST_EFFORT 유실이 끼지 않는다. 토픽별 건수·스탬프 간격과
**쌍 어긋남 분포(중앙/p95/최대)**, merged 스탬프가 front·rear 중 어느 쪽을 물려받았는지를 낸다.

## 판정 규칙 (실증됨)

| 관측 | 원인 | 실증 (2026-08-08, Big-AMR 실기 · SICK 2대) |
|---|---|---|
| 도착률 ≫ 스탬프률 + 발행자 2개 | **중복 발행자** — hz 가 합산을 본다 | `/scan_merged` 에 두 번째 발행자를 붙이고 `observe --duration 18` → 도착률 **67.44 Hz**, **스탬프률은 34.13 Hz 불변**, 「발행자 2개」 경고 출력 |
| 도착률 < 스탬프률, 발행자 1개 | **재는 쪽이 흘림** | `observe --duration 300` → merged 수신 10117 vs front/rear 각 10178 |
| 셋 다 일치 | 정상 | `observe --duration 300` + merger `sync:` 로그 102구간 전부 34.04~34.06 pairs/s |

> 위 수치의 원자료는 이 세션의 실행 로그이며 저장소에 커밋돼 있지 않다. 재현하려면 표의
> 명령을 그대로 실행하면 된다(SICK 2대 기동 필요). 아래 bag 예시만 저장소 밖 경로의 녹화본을 쓴다.

## 읽는 법 — 실측 예

`ldb/T-AMR_ros2_ws/rosbag/0528_speed_1.5_test_20260530_125451` (Foil_A082, 1.5 m/s, 47.26 s):

```
/scan_front : 1610 msg → 스탬프 34.10 Hz | 센서신고 30.00 ms → 33.33 Hz
/scan_rear  : 1610 msg → 스탬프 34.06 Hz | 센서신고 30.00 ms → 33.33 Hz
/scan_merged: 1610 msg → 스탬프 34.10 Hz | 센서신고 67.00 ms → 14.93 Hz   ← scan_time 이 실제와 다름
쌍 어긋남: 중앙 4.74 ms · p95 5.99 ms · 최대 8.75 ms
```

- **1610 = 1610 = 1610** — merger 는 쌍당 1회만 낸다. 출력이 입력보다 많을 수 없다.
- **쌍 어긋남 4.74 ms** — 1.5 m/s 에서 7 mm, 최대 8.75 ms 에서 13 mm 의 계통 변위.
  두 SICK 은 자유구동이라 상대 위상이 표류하므로 장시간에는 **최대 반주기(≈15 ms)** 까지 벌어진다.
- **merged 의 `scan_time` 0.067 s** 는 런치 파라미터 값이며 실제 발행 주기(29 ms)와 다르다.

### 실기 507초 연속 관측 (2026-08-08, SICK 2대 실기동)

`sync:` 로그를 시계열로 보면 skew 는 고정값이 아니라 **맥놀이(beat)** 로 순환한다.

```
  t[s]  pairs/s  skew_mean        t[s]  pairs/s  skew_mean
     0    33.91      3.42          151    33.84      9.66
    50    34.04      8.82          201    34.04      4.04
    95    32.96     13.80          236    34.05      0.48   ← 동위상 (최소)
   100    29.75     14.13  ← 역위상 정점에서 발행률 −13.5 %
   105    29.47     14.17          301    34.05      7.09
   116    33.84     13.51          357    33.85     13.10   ← 다음 정점
```

- **주기 ≈ 260초(4.3분)**, 진폭 `0.48 ms ↔ 14.21 ms`(= 주기의 절반).
- **역위상 정점에서 `pairs/s` 가 34.05 → 29.47 로 처진다.** ApproximateTime 이 짝을 못 만드는 구간이다.
- ⇒ **정적 보정으로 상쇄할 수 없다.** 같은 도킹 동작을 반복해도 시도 시각에 따라 다른 오프셋을 본다.
- ⇒ 그래서 `max_pair_skew` 를 좁게 거는 것은 해법이 아니다 — 주기의 상당 구간에서 발행이 멈춘다.
