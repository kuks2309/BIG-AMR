# imu_rate_check — IMU 회전 추종의 유효 회전율 구간 측정

제자리 회전시키며 **IMU** 와 **맵 기준 측위(mcl2d)** 의 회전량을 동시 적산해
`IMU/맵` 비를 실측 회전율별로 낸다. 비가 1 에서 멀어지는 구간이 **IMU 를 믿을 수 없는 구간**이다.
비-ROS2 독립 도구이므로 `Tools/` 에 둔다.

## 왜 필요했나

`turn`·`spin`·`yaw_control` 이 **전부 IMU 로 루프를 닫는다.** 2026-08-10 실기에서
`yaw_control` 이 실제 회전 +24.7° 를 +1.7° 로만 읽고 **25° 틀어진 채 `status 0`(성공)** 을
반환했다(`debt-054`). 그 기동의 회전율이 약 0.6 °/s 였다. 「IMU 를 언제까지 믿을 수 있나」를
숫자로 답해야 나머지 기동의 유효 범위를 말할 수 있다.

## 실측 (Foil_A082, 2026-08-10)

| 실측 회전율 | IMU/맵 비 | 표본 |
| --- | --- | --- |
| 0.280 °/s | 0.013 | n=1 |
| 0.564 °/s | 0.049 · 0.065 | n=2 (독립 2회 sweep 일치) |
| 1.130 °/s | 0.363 · 0.539 | n=2 |
| 2.84 °/s | 0.988 · 0.991 · 0.992 · 0.995 | n=4 |
| 5.69 °/s | 0.988 · 0.994 | n=2 |

**약 2.8 °/s 이상에서 정확(≈0.99), 그 아래로 급락, 0.3 °/s 에서 사실상 실명.**

- 첫 sweep 에서 나온 `2.823 °/s → 1.350` 은 **이상치였다** — 같은 조건 4회 반복에서 전부
  0.99 로 재현되지 않았다. 단일 표본으로 결론 내지 말 것.
- 어젯밤 `spin` 대조(2.8 dps → 1.015, 10 dps → 0.991)와 정합한다.
- `yaw_control` 실패 건(0.6 °/s)이 이 곡선 위에 정확히 놓인다.

## 운용 규칙 (실측에서 도출)

```
ω ≥ 2.8 °/s   IMU 폐루프 신뢰 가능
ω ≲ 1  °/s    IMU 폐루프 금지 — 맵 측위로 교차검증하거나 다른 수단을 쓸 것
```

`turn` 은 `ω = v / R` 이므로 **큰 반경이 위험 구간**이다. `v = 0.05 m/s` 기준
`R ≳ 1.0 m` 에서 이미 2.86 °/s 로 경계에 있고, `R ≳ 3 m` 면 1 °/s 아래로 떨어진다.

## 사용

```bash
# can_relay 는 반드시 반납 상태 (Seer 가 버스를 써야 한다)
ros2 service call /can_relay_node/engage std_srvs/srv/SetBool "{data: false}"

python3 Tools/imu_rate_check/imu_rate_sweep.py
python3 Tools/imu_rate_check/imu_rate_sweep.py --w 0.05 -0.05 0.05 -0.05   # 반복 측정
```

`--w` 는 부호를 교대시켜 원점 근처를 유지한다. 제자리 회전이므로 위치 이동은 수십 mm 수준이다.

## 계측 함정 — 반드시 연속 적산

끝점 두 샘플의 차이에 `wrap()` 을 걸면 **|Δ| > 180° 에서 앨리어싱**되어 큰 회전이 작은 값
(심하면 반대 부호)으로 접힌다. 2026-08-10 첫 시도가 이 함정에 빠져 `w=+0.200` 이
`−0.512 °/s` 로 나왔다(실제 약 +345° 회전). 본 도구는 매 샘플 델타를 unwrap 해 누적한다.

정지 후에도 `--settle`(기본 4 s) 만큼 더 적산한다 — AHRS 는 정지 직후 수 초간 자세추정이
되돌아가므로(기동 후 완화, 실측 0.8°) 그것까지 포함해야 「기동 1회의 총 판독」이 된다.

## 함수표

| # | 함수 | 인자 | 반환 | 역할 | 위치 |
| --- | --- | --- | --- | --- | --- |
| 1 | `pack` | `seq`, `code`, `payload` | `bytes` | Seer NetProtocol 프레임 조립. 정본 `References/Seer-Driver/robokit_tcp_api.md` §4-2 | `imu_rate_sweep.py:46` |
| 2 | `wrap` | `deg` | `float` | 각도를 (−180, +180] 로 정규화 | `imu_rate_sweep.py:51` |
| 3 | `main` | — | `int` | 인자 파싱 → 구독 → w 목록 순회(적산·정지·완화 적산) → 회전율별 비 출력. 0 정상 / 2 토픽 미수신 | `imu_rate_sweep.py:55` |
| 3-1 | `main.yaw_of` | `quaternion` | `float` | 쿼터니언 → yaw[deg] | `imu_rate_sweep.py:76` |
| 3-2 | `main.pump` | `sec` | — | 지정 시간 ROS 스핀 | `imu_rate_sweep.py:84` |
| 3-3 | `main.send` | `w` | — | `2010` 개루프 회전 1프레임 | `imu_rate_sweep.py:97` |
| 3-4 | `main.stop` | — | — | `2000` 정지 | `imu_rate_sweep.py:106` |

전역 상수: `REQ_MOTION 2010` · `REQ_STOP 2000` (`imu_rate_sweep.py:42-43`). 가변 전역 없음.

## 관련

- `debt-054` — 본 도구가 규명한 항목
- `Tools/seer_jog/` — 같은 Seer 개루프 API 를 쓰는 복구 도구
- `docs/issues_and_fixes/issues_and_fixes.md` 2026-08-10
