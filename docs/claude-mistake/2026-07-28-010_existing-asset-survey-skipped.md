---
id: 2026-07-28-010
type: mistake
category: context-missing
status: closed
reflected_assets:
  - ~/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-icp-odometry-assets.md
  - ~/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/MEMORY.md
---

# 2026-07-28 17:21 (KST) — ICP 오도메트리를 사용자 기존 자산 조사 없이 "없다"고 단정하고 신규 구현·외부 GPL 패키지를 권고

## 무엇을 했는가

"모터 제어 미완성이라 ICP 오도메트리로 대체 가능한가" 라는 질문에 대해, 이 장비의 apt 저장소에서
`rf2o_laser_odometry`·`laser_scan_matcher`·`mola`·`mp2p-icp` **4종만** 조회한 뒤
"2D 용 ICP 계열 패키지가 없다"고 서술하고, ① 2D ICP 노드 직접 작성 ② rf2o 소스 빌드
③ 스캔 데이터 수집 ④ 오도 0 입력 을 선택지로 제시했다. 이어 rf2o 를 추천으로 정정하며
GPL v3 라이선스·합성 스캔 가정을 논점으로 삼았다.

## 무엇이 잘못이었나

두 가지가 사실과 달랐다.

1. **패키지 부재 단정이 틀렸다.** `ros-humble-rtabmap-odom`(=`icp_odometry` 노드)이 이 장비 apt 에
   `Candidate: 0.23.7-1jammy.20260622.101306` 로 **설치 가능**하다. 4종만 조회하고 "ICP 계열 없음"
   이라는 일반화를 했다.
2. **사용자 기존 자산을 조사하지 않았다.** 같은 세션에서 이미 `gh` 로 사용자 저장소를 검색해
   Seer API 문서를 찾아 썼음에도, ICP 오도메트리에 대해서는 같은 조사를 하지 않았다. 실제로는
   `kuks2309/TR_Nav_ros2_ws`·`FITO_AMR_ros2_ws` 등에 **동일 센서 구성(dual SICK →
   `dual_laser_merger` → `/scan_merged`) + 휠 오도 미사용 + iAHRS IMU guess** 로 `icp_odometry` 를
   운용한 launch 와, 2026-07-13 실차 사고 2건의 원인분석·대책 설계 문서까지 존재했다.

그 결과 사용자는 **이미 검증된 자산을 두고 신규 구현/GPL 패키지 도입을 검토하는 잘못된 선택지**를
받았다.

## 사용자 지적

> "또 엉터리 정보를 제공헀네"
>
> "내 깃에 icp odom 구현한 것을 찾아서 검토하면 어떨까?"

## 원인 분석

조사 범위를 **현재 저장소 + 이 장비의 apt** 로 좁게 잡고, 사용자의 다른 저장소를 후보 소스로
아예 고려하지 않았다. 이 프로젝트는 여러 AMR 워크스페이스(TR_Nav / FITO_AMR / T-Robot / T-AMR)가
같은 사람 소유로 병존하고 센서 스택도 겹치는데, 그 구조를 조사 대상으로 인지하지 못했다.

또한 apt 4종 조회라는 **부분 표본에서 "없다"는 전체 부정**을 도출했다. `docs/claude-mistake/INDEX.md`
§메타 패턴이 지적하는 "부정형 단정도 확정형 보고와 같은 뿌리"(2026-07-27-003, 2026-07-28-005)의
재발이다. `2026-07-27-004`(저장소 전수 조사 누락)와도 같은 계열 — 조사 범위를 지목된 것으로
한정하는 습관.

## 재발 방지

- 신규 메모리 `biguamr-icp-odometry-assets.md` 에 **정본 자산 위치**(TR_Nav_ros2_ws dual-lidar launch,
  FITO_AMR_ros2_ws 2D launch, 2026-07-13 사고 원인분석 문서)와 검증된 파라미터, 그리고
  **Big-AMR 은 엔코더 DR 이 없어 모션 prior 해독제를 그대로 쓸 수 없다**는 제약을 기록했다.
- 같은 메모리에 **"기능 도입 검토 시 사용자 저장소(`gh search code --owner kuks2309`)를 먼저
  조사한다"** 를 명시해, 외부 패키지·신규 구현 권고 전에 기존 자산 조사가 선행되도록 했다.
- "없다"는 결론은 조사 범위를 함께 적어 부분 표본임을 드러낸다(예: "apt 4종 조회 기준").
