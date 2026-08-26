---
id: 2026-08-26-002
type: mistake
category: intent-guess
status: closed
reflected_assets:
  - /home/nvidia/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-experiment-set-names.md
---

# 2026-08-26 22:31 (KST) — "단거리 4종·주행 3개"를 bag 폴더명으로 오해석

## 무엇을 했는가

사용자의 "a 단거리 4종 B 주행 3개가 있어야 합니다. 압축해주세요"를 **rosbag
폴더 단위**로 해석 — A=도킹 bag 4개(dock04·dock07·dock3mm·dockspeed),
B=주행 실험 3건(roundtrip bag+spin_return+turn_rev jsonl)로 묶어 압축·전달했다.

## 무엇이 잘못이었나

사용자가 원한 것은 **어제 PGV ±3 mm 정밀 도킹 실험(33회)의 원자료**였고, 그
안의 실험 설계가 A 단거리 4종(접근 속도 0.1×3, 0.6/0.7/0.8×각5 = 18회) +
B 주행 3개(1.57 m 주행 후 도킹, 속도 0.6/0.7/0.8×각5 = 15회)다. 무관한 오전
왕복주행 bag(1.5 GB)을 B 로 넣고, "주행 bag 이 1개뿐"이라는 엉뚱한 결손 보고까지
붙였다.

## 사용자 지적

"또 이해못하고 이상한거 했네.. 어제 pgv 사용하여 3mm이내 들어간 실험에 대한
데이터를 요구하는 것입니다" / "정신좀 차리고 요구하는 것 정확히 주세요"

## 원인 분석

intent-guess — 직전 대화 맥락(rosbag 유무 질문)에 끌려 "4종·3개"를 파일 개수로
붙였고, **개수 불일치(주행 bag 1개뿐)라는 반증 신호를 해석 오류의 증거로 쓰지
않고 "데이터 결손"으로 뒤집어 보고**했다. 원자료의 speed/leg_dist 필드를 먼저
집계했으면 4종(0.1/0.6/0.7/0.8)·3개(0.6/0.7/0.8)가 정확히 드러났다 — 실제로
지적 후 그 집계 한 번으로 즉시 확정됐다.

## 재발 방지

실험 데이터 요청의 집합 명칭("N종·M개")은 파일·폴더 개수가 아니라 **원자료
레코드의 조건 필드(speed·leg_dist 등) 집계로 먼저 대조**하고, 개수가 안 맞으면
결손 보고가 아니라 해석 재검토가 우선이다 — 메모리
`biguamr-experiment-set-names.md` 에 등재.
