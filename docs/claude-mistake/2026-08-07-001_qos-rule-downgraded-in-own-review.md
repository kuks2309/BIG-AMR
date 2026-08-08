---
id: 2026-08-07-001
type: rule-violation
category: verify-skip
status: closed
reflected_assets:
  - src/Navigation/mcl2d_ros2/src/mcl2d_localization_node.cpp
  - src/Navigation/mcl2d_ros2/config/mcl2d.yaml
  - docs/code_review/mcl2d-localization-chain/2026-08-07.md
---

# 2026-08-07 19:53 (KST) — 같은 리뷰 안에서 같은 QoS 결함을 한쪽은 High 로 고치고 한쪽은 Low 로 남김

## 무엇을 했는가

`mcl2d_localization_node` 의 `/odom` 구독이 QoS 불일치로 **한 건도 수신하지 못하는** 결함을 찾아
BEST_EFFORT 로 고치고, 코드에 원인·근거를 주석으로 박았다(2026-08-02). 같은 노드의
`/scan_front`·`/scan_rear` 구독은 depth 숫자만 준 **기본 RELIABLE** 상태로 두었고,
2026-08-07 코드리뷰에서 이를 `#L1`(Low)로 적으며 "현재 SICK 드라이버가 RELIABLE 발행이라
**지금은 정합한다**" 로 정리하고 넘어갔다.

## 무엇이 잘못이었나

`docs/claude_guideline/code_review/domains/ros2-review.md` §2 평가 카테고리 `[QoS]` —
"pub/sub 호환성 불일치 (A-6 매트릭스 기반). **offered(pub) < requested(sub)** 인 축이 있으면
연결 실패" 및 §1 A-6 "같은 토픽의 pub(offered) QoS 와 **모든** sub(requested) QoS 를 대조" 위반.

구체적으로:

- 센서 스트림을 RELIABLE 로 구독하는 것 자체가 규칙이 막는 형태다. "현재 발행자가 우연히
  RELIABLE 이라 지금은 붙는다" 는 **조건부 정합**이지 정합이 아니다. 실제로 사용자가 지시한
  `/scan_merged`(merger 가 `SensorDataQoS`=BEST_EFFORT 로 발행) 로 바꾸는 순간 **한 건도 오지
  않는** 상태가 됐을 것이다 — `/odom` 에서 이미 겪은 그 실패다.
- 같은 리뷰 문서 안에서 **동일한 결함 유형을 두 등급으로 갈랐다.** `/odom` 은 실증했으니 고치고,
  스캔은 "현재 조건에서 안 터지니" Low 로 내렸다. 판정 기준이 결함의 성질이 아니라 **그 순간
  터졌는지 여부**였다.

## 사용자 지적

> "진행 qoS 코딩 규칙을 또 어겼네요."
> "ros2 도메인 규칙에서 qos 준수 규칙을 어겼네요"

직전 지적("당연히 mergered 로 해야 합니다")으로 스캔 구독을 바꾸는 작업 중이었는데, 그 변경에서도
QoS 를 명시하지 않을 뻔한 것을 짚었다.

## 원인 분석

규칙은 설치돼 있었고(`domains/ros2-review.md`), 내가 그 규칙으로 **A-6 매트릭스를 직접 작성**했으며,
같은 노드에서 같은 결함을 이미 한 번 고쳤다. 즉 지식 공백이 아니다.

어긴 이유는 **severity 판정에 "현재 터지는가" 를 넣었기 때문**이다. 리뷰 SOP 는 결함의 성질로
등급을 매기라고 하지, 관측 시점의 운 좋은 조합으로 감면하라고 하지 않는다. "지금은 정합한다" 는
관측은 참이었지만 그것을 **등급 감면 사유**로 쓴 것이 위반이다. 이 저장소 INDEX §메타 패턴의
"검증했는데 대상이 틀린 것" 과 같은 계열 — 검증 대상이 *결함의 성질* 이어야 하는데 *현재 조합* 이었다.

가중 요인: `/odom` 수정 때 남긴 주석이 "BEST_EFFORT 구독자는 RELIABLE 발행자와도 연결되므로
이쪽이 항상 넓다" 라고 **정답을 이미 적어 두고 있었다.** 같은 파일 12줄 아래 스캔 구독에 그 결론을
적용하지 않았다.

## 재발 방지

- `mcl2d_localization_node.cpp` — 스캔 구독을 `rclcpp::SensorDataQoS()`(BEST_EFFORT) 로 명시하고,
  "센서 스트림은 BEST_EFFORT" 라는 규칙과 이번 위반 사실을 주석에 함께 박았다. 다음 사람이 같은
  자리에서 기본값으로 되돌리지 못하도록 이유를 남긴다.
- 병합 스캔 단일 구독으로 전환하며 `laser_mounts` 기본값을 무변환 `[0,0,0]` 으로 바꾸고,
  `config/mcl2d.yaml` 에 "값의 정본은 merger 캘리브레이션" 을 실측 근거와 함께 명시했다.
- 코드리뷰 문서 `docs/code_review/mcl2d-localization-chain/2026-08-07.md` 의 `#L1` 을 정정한다
  (아래 §후속 조치에 등급 재판정 기록). **"현재 조합에서 안 터진다" 는 등급 감면 사유가 아니다** 를
  판정 원칙으로 명시한다.

### 부수 성과 — 이 위반을 고치자 계통 오차가 드러났다

스캔을 `/scan_merged` 단일 구독으로 바꾸면서, 같은 좌표 변환을 merger 와 mcl2d 가 **서로 다른
값으로 두 번** 하고 있었다는 사실이 확인됐다(TF vs Seer 설정: front yaw 0.573°, rear yaw 0.197°·
y 9.6 mm). 정지 상태 실측 대조:

| | 개별 스캔 + mcl2d 마운트 | 병합 스캔 단일 구독 |
| --- | --- | --- |
| 위치차 (mcl2d ↔ Seer) | 중앙값 0.029 m | **0.008 m** |
| 각도차 | **4.498°** (편차 폭 0.09° = 고정 편향) | **0.350°** |

QoS 규칙을 제대로 지켰다면 스캔 소스를 바꾸는 시점에 이 이중 변환을 더 일찍 만났을 것이다.
