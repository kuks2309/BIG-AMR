---
id: 2026-08-30-002
type: mistake
category: wrong-assumption
status: closed
reflected_assets:
  - docs/issues_and_fixes/issues_and_fixes.md
  - Tools/camera_service/run_manager.sh
  - Tools/camera_service/run_camera.sh
---

# 2026-08-30 21:05 (KST) — systemd 래퍼를 클린 환경 실행 없이 출하 — `set -u` × ROS setup.bash 고전 함정 재생산

## 무엇을 했는가

카메라 관리 모드의 systemd 래퍼 `run_manager.sh` 를 신설하며 기존 `run_camera.sh` 의
`set -euo pipefail` + ROS source 패턴을 그대로 복사했다. 검증은 `bash -n`(문법)·
`systemd-analyze verify`(유닛 문법)·대화형 셸 스모크(노드 직접 실행)로 했고,
"남은 한 단계는 sudo 설치뿐"이라고 보고했다.

## 무엇이 잘못이었나

사용자가 `install.sh` 를 실행하자 유닛 7개 전부가 5초 크래시 루프에 들어갔다(관리자 재시도
1,656회). 원인은 `-u`(nounset)가 nounset-비호환인 ROS setup.bash 를 죽이는, ROS 커뮤니티에
수없이 보고된 고전 함정. 기존 래퍼의 잠복 결함(2026-07-28 작성, systemd 실행 0회)을
그대로 재생산했고, 내 검증 어느 것도 **래퍼를 실제 배포 조건(빈 환경)에서 실행**하지 않았다.

## 사용자 지적

> "set -u가 nounset 비호환인 ROS setup.bash를 죽이는 문제로, ← 이부분은 수없이 많이 나온 실수이지?"

(설치 실행 확인 요청 후 크래시 루프 발견 과정에서.)

## 원인 분석

`wrong-assumption` — "대화형 셸에서 노드가 돌았으니 systemd 로도 돈다"고 가정했다.
대화형 셸은 이미 ROS 가 source 된 상태라 래퍼의 source 경로 자체가 실행되지 않았다.
`bash -n` 은 문법만, `systemd-analyze verify` 는 유닛 파일만 본다 — **셋 다 래퍼의 런타임을
한 번도 통과시키지 않는 검증**이었다. 널리 알려진 함정임에도 패턴 복사 시 의심하지 않았다.

## 재발 방지

- `docs/issues_and_fixes/issues_and_fixes.md` 2026-08-30 entry 에 교훈 명문화:
  **systemd 용 스크립트는 클린 환경(`systemd-run` 또는 `env -i`)에서 1회 실행 검증 후 출하** —
  대화형 셸의 성공은 증거가 아니다.
- 두 래퍼에 금지 사유 주석 고정(`-u` 재도입 차단): `run_camera.sh`·`run_manager.sh` 의
  `set -eo pipefail` 위 2줄.
