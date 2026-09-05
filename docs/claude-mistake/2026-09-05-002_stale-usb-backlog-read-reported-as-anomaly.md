---
id: 2026-09-05-002
kind: B
detector: none (시험 스크립트 작성 판단 — 큐를 비우지 않은 SDO 읽기를 정적으로 잡을 지점이 없다)
status: open
---

# 2026-09-05 09:2x (KST) — USB 백로그를 비우지 않은 SDO 읽기 값을 실측이라 보고했다

## 무엇을 했는가
직접 USB 시험(ho_reengage_direct.py)에서 0xec 를 20 ms 로 폴링하는 동안 `can_recv()` 를 부르지 않아 판다 수신 큐에 백로그가 쌓였고, 그 뒤 `Rig.sdo_read()` 가 큐의 옛 프레임을 응답으로 집어 "node3 +82°·node4 +28°" 를 돌려줬다.
같은 시각 Seer API 는 0.0 rad 을 보였는데도 "시퀀서 도달 판정이 잘못됐다" 고 보고했다. 사용자가 "Seer API 로 반환 후 검증할 수 있다" 고 짚었고, 큐를 계속 비우는 재실험에서 판정과 엔코더가 일치했다.

## 무엇이 잘못이었나
- `Tools/docking_field_kit/orin_home_experiment.py` `Rig.sdo_read` 의 docstring 이 이미 경고한 오인 채집(2026-08-03 정정)을 반복했다.
- 두 독립 관측(Seer 0.0 rad vs 직접 읽기 82°)이 모순인데 모순을 해소하지 않고 한쪽을 채택했다(issue_fix §Step 2 증거 대조 위반).

## 원인 분석
폴링 루프에 `sdo_read` 를 섞을 때 큐 배수 조건을 생각하지 않았다. 모순 관측을 "이상" 으로 라벨링하고 넘어갔다.

## 재발 방지
B류. `mistake-relevance` 가 `orin_home_experiment.py`·직접 USB 시험 스크립트 편집 시 본 사건을 낸다(토큰 `sdo_read`·`can_recv`).
처방: 판다 SDO 직접 읽기는 (1) 직전에 큐를 빌 때까지 비우거나 (2) 요청 뒤 도착한 프레임만 채택하고, 반환 뒤 최종 판정은 Seer API `steer_angles` 로 한다. 두 관측이 모순이면 보고 전에 해소한다.
