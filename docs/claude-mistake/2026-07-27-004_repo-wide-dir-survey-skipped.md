---
id: 2026-07-27-004
type: mistake
category: context-missing
status: closed
reflected_assets:
  - README.md#디렉토리-배치-규약-2026-07-27-확정
  - ~/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-repo-layout.md
---

# 2026-07-27 21:45 (KST) — 디렉토리 병합 지시에 저장소 전수 조사 없이 지목된 2개만 처리

## 무엇을 했는가

사용자의 `tools/` + `Tools/` → `Tool/` 병합 지시에 대해, 지목된 두 최상위 디렉토리만
`find`/`ls` 로 확인한 뒤 합집합 이동을 수행하고 경로 참조를 갱신했다. 저장소 전체에서
같은 성격(tool 류) 디렉토리가 더 있는지는 조사하지 않았고, 완료 보고에도 언급하지 않았다.

## 무엇이 잘못이었나

`src/Tools/`(CameraCalibration, USB_CCTV) 가 존재한다는 사실을 사용자에게 전혀 알리지
못했다. 그 결과 "Tool 로 병합 완료"라는 보고가 저장소 전체 관점에서는 **부분 정리**에
불과했고, 사용자는 병합 후에도 `src/Tools/` 를 직접 발견해야 했다. 배치 결정에 필요한
정보(USB_CCTV 는 colcon 빌드 대상 ROS2 패키지, CameraCalibration 은 순수 python)를
결정 시점에 제공하지 못한 것이 실질 손해다.

## 사용자 지적

> "/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/src/Tools 아 짜증나네 왜 src 폴더 안에
> 있는지? 폴더 전체 구조 안보는지>"

## 원인 분석

category: `context-missing`. 지시문이 절대경로 2개를 명시했다는 이유로 조사 범위를 그
2개로 스스로 한정했다. "A 와 B 를 C 로 병합" 이라는 지시는 *배치 규약을 정하는 작업*이므로
같은 규약의 적용 대상 전체가 컨텍스트인데, 이를 단순 이동 작업으로 축소 해석했다.

병합·이동·이름변경은 저장소 배치 규약을 바꾸는 작업 유형인데, 본 프로젝트에는 이 유형에
대한 사전조사 규칙이 없다(coding SOP §2 사전조사는 함수표·전역변수표 = 코드 대상). 규칙
공백 영역에서의 판단 착오이므로 `rule-violation` 이 아니라 `mistake` 로 판정한다.

동시에 다른 세션이 같은 워킹트리에서 `Tools/amr_test_gui/` 를 추가하고 있었다는 점도
놓쳤다(병합 시점 `ls Tool` 5개 → 이후 6개). 전수 조사를 했다면 `Tool/` 규약이 이미
다른 세션에서 통용 중임을 근거로 제시할 수 있었다(그 폴더명은 이후 `Tools` 로 확정).

## 재발 방지

- **지식 자산 반영(완료)** — 프로젝트 메모리 `biguamr-repo-layout.md` 에 (1) `src/` =
  colcon 워크스페이스 소스 루트(ROS2 패키지 전용), 루트 `Tools/` = 비-ROS2 독립 도구,
  (2) **디렉토리 이동·병합·이름변경 지시를 받으면 지목된 경로만 보지 말고
  `find . -type d -iname '<이름>*'` 로 저장소 전수 조사 후 목록을 사용자에게 먼저 제시**
  를 기록했다.
- **저장소 자산 반영(완료)** — `README.md` §디렉토리 배치 규약 에 (1) colcon 대상 = `src/<도메인>/`,
  비-ROS2 도구 = 루트 `Tools/`, (2) 센서 드라이버 ↔ UI 분리 및 **UI 는 독립 도메인이 아니라 해당
  패키지 아래 `ui/` 로 종속**, (3) 루트 폴더명 `Tools`(복수) 확정, (4) 이동·병합 시 전수 조사 의무를
  표로 명문화했다. 사용자 결정(2026-07-27: `src/UI` 신설안 → 패키지 종속으로 정정, 폴더명 `Tools` 확정)
  을 반영한 것이다.
