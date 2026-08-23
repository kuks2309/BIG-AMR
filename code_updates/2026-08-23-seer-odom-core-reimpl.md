# Seer OdoCalculator 재구현 — `seer_odom_core` 신설

## 무엇을

원본 `libOdoCalculator.so` 의 `MultiSteersOdometer` 를 ROS 무의존 코어로 재구현했다.
**원본과 대조하기 위한 것**이지 제품 코드가 아니다 — 우리 휠 오도 발행기는
`motor_control/driver_node.py` 로 별개다.

| 파일 | 내용 |
| --- | --- |
| `include/seer_odom_core/types.hpp` | `MotorParam`·`MotorVitalInfo`·`OdometerOutput` |
| `include/seer_odom_core/multisteer_odometer.hpp` · `src/multisteer_odometer.cpp` | 코어 |
| `test/test_odometer.cpp` | 회귀 14항목 |

## 원본에서 그대로 옮긴 것

- 계수행렬 **(AᵀA)⁻¹Aᵀ** 사전 계산 — 행 구조 `[1, 0, −(y+cpy)]` / `[0, 1, (x+cpx)]`
- 같은 계수행렬을 **속도**(`v_enc`)와 **변위**(`dpos`)에 각각 적용하는 대칭 구조
- `caldPose` 는 증분만 만들고 **속도를 항상 0으로 지운다**
- 자세 누적은 각을 **먼저** 갱신·정규화하고 **그 각으로** 회전(end-point)
- `normalize` 는 **`floor` 1회** 방식, 치역 `[−π, π)`
- 첫 입력 게이트(`flagFirstInputGot`) · 일관성 임계(`thresConsistent`)

## 의도적으로 이탈한 것

특이 행렬이면 굳히지 않고 거짓을 돌려준다(원본은 검사하지 않는다). 로그·파일 덤프는
옮기지 않았다 — 대조 대상이 아니다.

## 검증

- 회귀 **14항목** 통과 · `colcon build`/`test` 통과
- **돌연변이 8/8 검출**: 회전 순서(start/end-point) · 정규화 방식 · 속도 소거 ·
  첫입력 게이트 · 계수 부호 · 보정항 · 입력 슬롯 · 일관성 임계

첫 판본은 **3/8 밖에 못 잡았다.** 살아남은 다섯을 분석해 시험을 고쳤다:

| 살아남은 이유 | 고친 방법 |
| --- | --- |
| 스핀만 시험해 병진이 0 → 회전 순서가 결과를 안 바꿈 | 호(arc) 주행 추가 |
| 작은 각만 시험 → 두 정규화 방식이 같은 값 | 큰 각(1e6) 추가 |
| 증분이 0 인 상태로 게이트 시험 | 증분을 만든 뒤 플래그를 내림 |
| `y=0`·`cp=0` 기하만 시험 → 부호·보정항이 결과에 안 나타남 | **왕복 시험** 추가(대각 기하 + 보정항) |

## 그 과정에서 잡은 것

**FMA(Fused Multiply-Add) 축약이 값을 바꾼다.** `-O2` 에서 `x − two_pi*floor(...)` 가
`fma` 로 합쳐져 `normalize(1e6)` 이 참조값과 **3.3e−11** 갈렸다. 비트 대조가 목적인
코드라 `-ffp-contract=off` 를 빌드에 넣었다. 시험도 상수를 박지 않고 **「반복 감산과
다르다」는 성질**로 바꿨다 — 상수를 박으면 컴파일러·libm 차이에 흔들려 무엇을 지키는지
흐려진다.

## 남은 것

- **원본과의 수치 대조는 아직 안 했다.** 정적 분석으로 확정한 구조적 성질만 고정된 상태다.
  오라클 하니스(원본 `.so` 를 `dlopen` 해 직접 구동)가 다음 단계다.
- `calSpeed` 의 잔차 산식은 우리 재구성이다 — 원본은 잔차를 절대값으로 취합해 임계와
  비교한다는 것까지만 확정했고(§11), 취합 방식 자체는 미확정이다.
