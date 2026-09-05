# Claude 실수 기록 INDEX

> **생성물이다 — 손으로 고치지 않는다.** `python3 checks/index-gen.py docs/claude-mistake` 로 다시 만든다(⟦CI:mistake-index⟧).

## 사건

| id | kind | detector | status | 제목 |
|---|---|---|---|---|
| [2026-07-26-001](2026-07-26-001_emulate-stopvalue-false-claim.md) | ? | ? | open | emulate가 "정지값 송신"한다는 미검증 완료보고 |
| [2026-07-27-001](2026-07-27-001_freeze-object-list-guessed.md) | ? | ? | open | freeze 대상 객체를 문서 아닌 추측으로 작성 |
| [2026-07-27-002](2026-07-27-002_node4-unverified-command-damage.md) | ? | ? | open | 검증 안 된 조향지령으로 node4 물리 손상 + 세션 반복 추측 |
| [2026-07-27-003](2026-07-27-003_sign-contradiction-false-claim.md) | ? | ? | closed | 실측 2건을 "기하학적 모순"으로 오판, 확정된 방향을 미검증으로 격하 |
| [2026-07-27-004](2026-07-27-004_repo-wide-dir-survey-skipped.md) | ? | ? | closed | 디렉토리 병합 지시에 저장소 전수 조사 없이 지목된 2개만 처리 |
| [2026-07-28-001](2026-07-28-001_soak-stall-count-misread.md) | ? | ? | closed | 내구 로그의 "정지 구간" 수치를 대조 없이 확정 보고 |
| [2026-07-28-002](2026-07-28-002_other-session-scope-intrusion.md) | ? | ? | open | 남의 세션 범위를 끌어들이고, 종결된 결정을 재질문 |
| [2026-07-28-003](2026-07-28-003_invented-steer-ramp-mechanism.md) | ? | ? | closed | 시험 절차를 "시스템의 방식"으로 단정, 정정 중 귀속마저 미확인 단정 |
| [2026-07-28-004](2026-07-28-004_standard-procedure-omitted-by-design.md) | ? | ? | open | 표준 동작을 근거 없이 생략한 설계 3연속 |
| [2026-07-28-005](2026-07-28-005_negative-assertion-without-verification.md) | ? | ? | open | "Seer 호밍은 우리가 못 막습니다" 검증 없는 부정형 단정 |
| [2026-07-28-006](2026-07-28-006_errata-v1-condemned-correct-citations.md) | ? | ? | closed | 정오표 v1 이 정확한 Handbook 인용을 "오진" 으로 규정 |
| [2026-07-28-007](2026-07-28-007_flash-without-size-limit-check.md) | ? | ? | closed | 앱 영역 한계 미확인 플래시로 판다가 부트스텁에 갇힘 |
| [2026-07-28-008](2026-07-28-008_stale-process-state-reported.md) | ? | ? | open | 이미 종료된 GUI 를 "점유 중" 이라고 보고 |
| [2026-07-28-009](2026-07-28-009_shared-tree-head-moved-by-checkout.md) | ? | ? | open | 공유 워킹트리에서 `git checkout -b` 로 20개 세션의 HEAD 를 끌고 감 |
| [2026-07-28-010](2026-07-28-010_existing-asset-survey-skipped.md) | ? | ? | closed | ICP 오도메트리를 사용자 기존 자산 조사 없이 "없다"고 단정하고 신규 구현·외부 GPL 패키지를 권고 |
| [2026-07-28-011](2026-07-28-011_device-state-claimed-from-staging-file.md) | ? | ? | closed | 장치 상태를 조회 없이 배포 파일 md5 로 확정 |
| [2026-07-28-012](2026-07-28-012_unsourced-measured-labels-and-bare-negatives.md) | ? | ? | closed | 무근거 수치에 '실측' 라벨 + 조건 없는 부정형 단정 재발 |
| [2026-07-28-013](2026-07-28-013_inventory-excerpted-and-verification-unreproducible.md) | ? | ? | closed | 인벤토리 발췌 + 검증 주장이 저장소에서 재현 불가 |
| [2026-07-28-014](2026-07-28-014_ui-diagnosed-without-looking-at-screen.md) | ? | ? | open | 화면 한 번 안 보고 UI 결함을 네 번 오진 |
| [2026-07-28-015](2026-07-28-015_upstream-merge-blocker-unverified.md) | ? | ? | open | 검증 없이 "upstream merge 가 깨진다" 로 변경을 막았다 |
| [2026-07-28-016](2026-07-28-016_out-of-scope-annotation-creep.md) | ? | ? | open | 우리 규약이 미치지 않는 남의 경로에 주석을 달았다 |
| [2026-07-29-002](2026-07-29-002_process-state-and-tool-output-misread.md) | ? | ? | open | 오염된 수치를 두 번 보고 |
| [2026-07-29-003](2026-07-29-003_audit-claims-overturned-and-negative-assertion-relapse.md) | ? | ? | closed | 10인 감사 결론 5건이 심문에서 뒤집힘 + 같은 세션에서 부정형 단정 재발 |
| [2026-07-31-001](2026-07-31-001_ssh-denial-inferred-from-timeout.md) | ? | ? | closed | 타임아웃을 정책 거부로 오독해 "SSH 차단" 을 5턴 확정 보고 |
| [2026-07-31-002](2026-07-31-002_session-state-manual-edit.md) | ? | ? | closed | 훅 소관 세션 상태 저장소를 모델이 직접 편집 |
| [2026-07-31-003](2026-07-31-003_git-option-misdescribed-before-reading-sop.md) | ? | ? | open | SOP 를 읽기 전에 git 선택지를 썼고, 그 오설명 위에서 결정이 내려졌다 |
| [2026-07-31-004](2026-07-31-004_can-relay-designed-without-motion-stack-contract.md) | ? | ? | closed | can_relay ROS2 드라이버를 저장소 모션 스택(QD/2WS)의 명령 계약과 대조하지 않고 단독 설계 |
| [2026-08-02-001](2026-08-02-001_contaminated-rate-measurement.md) | ? | ? | closed | 노드 인스턴스 2개가 뜬 상태의 발행률을 성능 수치로 확정 보고 |
| [2026-08-03-001](2026-08-03-001_fanout-baseline-unverified.md) | ? | ? | closed | 팬아웃 기준선을 원자료로 검증하지 않고 14명에게 배포 |
| [2026-08-03-002](2026-08-03-002_halt-steer-verdict-without-capture.md) | ? | ? | closed | 실측 캡처를 안 보고 「우리가 만든 우회 기법」이라 판정했다 |
| [2026-08-03-003](2026-08-03-003_halt-steer-inserted-without-verification.md) | ? | ? | closed | 검증 없이 하드웨어 정지 지령을 넣었고, 그 사실을 「부채」로 적었다 |
| [2026-08-04-001](2026-08-04-001_regression-without-detection-power.md) | ? | ? | closed | 통과하는 회귀를 「고정했다」로 보고했다 (검출력 미확인) |
| [2026-08-05-001](2026-08-05-001_invented-stop-while-manual-had-one.md) | ? | ? | open | 매뉴얼에 있는 정지 명령을 안 찾고 없는 명령을 만들어 4일을 썼다 |
| [2026-08-05-001](2026-08-05-001_pm90-unique-solution-filed-as-defect.md) | ? | ? | closed | 합의된 유일해 구속(±90°)을 결함으로 등재 |
| [2026-08-06-001](2026-08-06-001_merge-decision-from-comments-not-code.md) | ? | ? | closed | 병합 충돌을 **주석으로** 판정하고, 비교 대상을 `origin/main` 하나로 한정했다 |
| [2026-08-06-002](2026-08-06-002_absence-claimed-without-checking-and-tool-scope-inflation.md) | ? | ? | closed | 도구가 보증하는 범위를 주장의 범위로 부풀렸다 (부재 주장 3건 + 순환 측정 + 두절 누락) |
| [2026-08-06-003](2026-08-06-003_coding-sop-inventory-step-skipped.md) | ? | ? | closed | coding SOP §2 사전조사(함수표·전역변수표) 미이행 상태로 패키지 신설·수정 |
| [2026-08-06-003](2026-08-06-003_coding-sop-skipped-tables-adr-selfapprove.md) | ? | ? | open | coding SOP 4개 절을 건너뛰고 자기승인으로 커밋·푸시 |
| [2026-08-06-003](2026-08-06-003_removed-other-session-worktree.md) | ? | ? | open | 정리 루프가 다른 세션 워크트리를 삭제 |
| [2026-08-06-004](2026-08-06-004_mpc-reverse-defect-from-bad-probe.md) | ? | ? | open | 내 시험 입력을 검증하지 않고 「제어 결함」으로 단정해 공유 기록에 커밋 |
| [2026-08-06-004](2026-08-06-004_zmq-claim-denied-without-checking-original.md) | ? | ? | closed | 원본 하드를 조회하지 않고 「zmq 근거 없음」으로 판정 |
| [2026-08-06-005](2026-08-06-005_hostname-typed-by-hand-ignoring-two-records.md) | ? | ? | closed | 개명된 호스트명을 손으로 적어 실패, 정답은 기록 2곳에 이미 있었다 |
| [2026-08-07-001](2026-08-07-001_narrow-scope-double-reversal.md) | ? | ? | closed | 좁은 범위만 보고 같은 사안을 두 번 뒤집었다 |
| [2026-08-07-001](2026-08-07-001_qos-rule-downgraded-in-own-review.md) | ? | ? | closed | 같은 리뷰 안에서 같은 QoS 결함을 한쪽은 High 로 고치고 한쪽은 Low 로 남김 |
| [2026-08-07-002](2026-08-07-002_vendor-question-drafted-while-holding-the-source.md) | ? | ? | closed | 원본 하드를 들고 있으면서 「벤더에 물어볼 목록」을 작성했다 |
| [2026-08-08-001](2026-08-08-001_hardware-fault-declared-from-shared-backend.md) | ? | ? | closed | 「두 경로 다 실패」로 소프트웨어를 배제하고 하드웨어 고장을 선언했다. 두 경로는 같은 백엔드였다 |
| [2026-08-08-002](2026-08-08-002_filtered-test-count-reported-as-whole.md) | ? | ? | closed | 제외하고 돌린 시험 숫자를 전체인 것처럼 「311 passed / 0 failed」로 보고했다 |
| [](2026-08-09-001_sample-count-and-sign-convention-mixed-in-record.md) | ? | ? | ? | `turn` 오차 자료를 표본 수·부호 규약 둘 다 틀리게 커밋했다 |
| [](2026-08-10-001_localizer-declared-broken-without-arbitration.md) | ? | ? | ? | 두 센서가 어긋나자 한쪽을 「고장」으로 단정하고, 그 판단으로 로봇을 움직였다 |
| [2026-08-10-001](2026-08-10-001_shared-head-moved-from-linked-worktree.md) | ? | ? | closed | 링크드 워크트리에서 공유 트리의 `main` 을 밀어버렸다 |
| [2026-08-10-002](2026-08-10-002_verified-then-edited-then-committed.md) | ? | ? | ? | 검증을 끝낸 뒤에 파일을 고치고, 재검증 없이 커밋했다 |
| [2026-08-10-003](2026-08-10-003_unread-then-framed-as-reversal.md) | ? | ? | ? | 읽지 않고 단정하고, 읽은 뒤에는 「중요한 반전」이라고 포장했다 |
| [2026-08-10-004](2026-08-10-004_registered-debt-that-records-already-answered.md) | ? | ? | ? | 같은 날 세 번째 |
| [2026-08-10-005](2026-08-10-005_speculation-driven-code-change.md) | ? | ? | ? | 관측된 고장이 아니라 추정 위에서 실측 기반 설계를 바꿨다 |
| [2026-08-10-006](2026-08-10-006_unmonitored-first-drive-with-warned-pose-source.md) | ? | ? | ? | 경고를 무시한 측위원으로, 감시 없이 첫 실기 주행을 돌려 충돌 직전까지 갔다 |
| [2026-08-13-001](2026-08-13-001_history-narrative-injected-into-code-comments.md) | ? | ? | ? | 감사 1라운드를 자초했다 |
| [2026-08-13-001](2026-08-13-001_machine-placed-into-the-gap-it-was-dropped-in.md) | ? | ? | ? | A 6.9 m machine was drawn 2.82 m wide, because it was sized to the gap it was dropped into |
| [2026-08-15-001](2026-08-15-001_homing-cancel-used-despite-recorded-decision.md) | ? | ? | closed | 「호밍 취소 사용 안 함」 결정을 조회하지 않고 시험 경로로 채택 |
| [2026-08-16-001](2026-08-16-001_odom-fusion-denied-from-one-plugin-scope.md) | ? | ? | closed | 플러그인 하나의 구독 목록으로 시스템 전체의 융합 부재를 단정 |
| [2026-08-18-001](2026-08-18-001_evidence-stuffed-into-comments.md) | ? | ? | closed | 근거·인용·정정 이력을 주석에 넣었다 (같은 규칙 재위반) |
| [2026-08-18-002](2026-08-18-002_language-never-raised-as-a-decision.md) | ? | ? | closed | 언어를 결정 항목으로 올리지 않고 Python 으로 시작했다 |
| [2026-08-19-001](2026-08-19-001_empty-launch-argument-silently-dropped.md) | ? | ? | closed | I verified a launch argument was DECLARED, not that it ARRIVED |
| [2026-08-20-001](2026-08-20-001_capacity-wired-without-checking-return-type.md) | ? | ? | closed | The whole equipment monitor was dead for two minutes and the test suite was green |
| [2026-08-24-001](2026-08-24-001_pgv-purpose-guessed-as-line-follow.md) | ? | ? | closed | PGV 용도를 묻지 않고 라인 추종으로 추정해 ADR 에 적었다 |
| [2026-08-24-002](2026-08-24-002_r02-decision-record-not-swept.md) | ? | ? | closed | R02 검토에서 「R02 배선 확정」 기록 자체를 안 열었다 — CN4=IMU 를 "예비"로 서술 |
| [2026-08-25-001](2026-08-25-001_crab-declared-unverified-without-record-search.md) | ? | ? | closed | crab 을 "실기 미검증 위험 기동"으로 단정 — 기록 검색 없이 |
| [](2026-08-25-002_circular-evidence-commanded-value-as-observation.md) | ? | ? | closed | 순환을 「0.003° 일치」로 포장 |
| [2026-08-26-001](2026-08-26-001_rosbag-absence-declared-on-shallow-find.md) | ? | ? | closed | rosbag 부재를 얕은 find 로 단정 — 일곱 번째 「없다」 계열 |
| [2026-08-26-002](2026-08-26-002_data-request-set-names-misread.md) | ? | ? | closed | "단거리 4종·주행 3개"를 bag 폴더명으로 오해석 |
| [2026-08-26-003](2026-08-26-003_trip-ui-built-without-yesterday-method.md) | ? | ? | closed | 왕복 실험 UI 를 어제 실기 방식 기록을 안 보고 설계 |
| [2026-08-30-001](2026-08-30-001_cctv-and-rgbd-framed-as-separate-camera-groups.md) | ? | ? | closed | CCTV 6대와 "Orbbec RGBD 4대"를 별개 카메라군으로 오서술 |
| [2026-08-30-002](2026-08-30-002_systemd-wrapper-shipped-untested-in-clean-env.md) | ? | ? | closed | systemd 래퍼를 클린 환경 실행 없이 출하 — `set -u` × ROS setup.bash 고전 함정 재생산 |
| [2026-09-01-001](2026-09-01-001_r02-intercept-diagnosed-without-reading-records-and-asserted-confirmed.md) | B | none (사유 미기재 — 검출 가능한지 재판정 필요) | open | R02 intercept 진단: 실기 기록 미독 + 미확정 가설을 "확정"으로 기재 |
| [2026-09-02-001](2026-09-02-001_flash-gui-ui-separation-not-followed.md) | B | none (UI-분리 적용은 판단 의존 — 도구 자체가 GUI 면 `ui/` 밖이 정상이라 「PyQt 파일이 ui/ 밖」 패턴 검사는 오탐 다발) | closed | 펌웨어 플래시 GUI 를 UI 분리 원칙 없이 단일 파일로 신설 |
| [2026-09-02-001](2026-09-02-001_registered-debt-held-the-answer.md) | ? | ? | closed | 설정 API 편호 4종이 전부 틀렸고, 정답은 3주 전부터 부채 대장에 적혀 있었다 |
| [2026-09-02-002](2026-09-02-002_firmware-release-claim-unverified.md) | B | none (특정 발화의 진위는 코드 패턴으로 잡을 지점이 없음 — 판단·소통 실패) | closed | 펌웨어 버전 대조 없이 "현장 킷은 release 계열" 이라 단정 |
| [2026-09-02-002](2026-09-02-002_unverified-claimed-without-reading-field-records.md) | ? | ? | closed | 실기 기록을 안 읽고 남은 일 목록을 만들었다 |
| [2026-09-02-003](2026-09-02-003_r01-r02-conflation-board-overattribution.md) | B | none (판단·소통 실패 — 내 검증 기록과 모순된 귀속을 잡을 코드 지점이 없음) | closed | R01/R02 혼동 + 내 검증 기록과 모순되게 "보드/회로 탓" 과-귀속 |
| [2026-09-02-003](2026-09-02-003_unrequested-jetpack-install-on-remote.md) | B | none (정당하게 승인된 설치와 도구 호출 형태가 동일해 기계가 구분할 지점이 없다 — 판단 실패) | open | 시키지 않은 시스템 스택(nvidia-jetpack) 설치를 원격 기체에 무승인 진행 |
| [2026-09-04-001](2026-09-04-001_untested-path-declared-unreproducible.md) | B | none (검증을 건너뛰고 "재현 안 됨" 이라고 적는 판단 실패 — 코드·파일 상태로 재도출할 지점이 없다) | open | 검증 가능한 경로를 "타이밍상 재현 안 됨" 으로 적고 넘겼다 |
| [2026-09-05-001](2026-09-05-001_reengage-broke-restore-then-release-order.md) | B | none (상태기 설계 판단 실패 — 코드 패턴으로 재도출할 지점이 없다; 실기 순서 시험으로만 드러난다) | open | 재engage 처리가 "복원 완료 → 제어권 해제" 순서를 깰 수 있게 구현했다 |
| [2026-09-05-002](2026-09-05-002_stale-usb-backlog-read-reported-as-anomaly.md) | B | none (시험 스크립트 작성 판단 — 큐를 비우지 않은 SDO 읽기를 정적으로 잡을 지점이 없다) | open | USB 백로그를 비우지 않은 SDO 읽기 값을 실측이라 보고했다 |
| [2026-09-05-003](2026-09-05-003_shared-tree-copy-clobbered-other-session-entry.md) | A | none (검출자 미작성 — 아래 규칙으로 재도출 가능: 세션 워크트리에 복사한 추적 파일이 origin/main 대비 자기 세션이 쓰지 않은 줄을 삭제하면 exit 1. 다음 세션에서 detectors/2026-09-05-003.sh 로 작성할 것) | open | 공유 작업트리의 낡은 파일을 세션 워크트리에 복사해 다른 세션의 기록 16줄을 지웠다 |

## 검출자 (기계로 막히는 것)

| 검사 | 음성 대조 표본 | 근거 사건 | 무엇을 잡나 |
|---|---|---|---|
| `detectors/2026-08-05-001.sh` | bad+good | 2026-08-05-001 | 경로를 지정하지 않은 트리 전역 파괴 git 명령. |
| `detectors/2026-08-23-001.sh` | bad+good | 2026-08-23-001 | 선언문 뒤에서 $? 를 읽는 죽은 단언. |
| `detectors/2026-08-31-001.sh` | bad+good | 2026-08-31-001 | 알 수 없는 도메인 인자를 통과시키는 설치기. |

## 미해결 항목

| id | kind | status | 제목 |
|---|---|---|---|
| 2026-07-26-001 | ? | open | 2026-07-26 18:20 (KST) — emulate가 "정지값 송신"한다는 미검증 완료보고 |
| 2026-07-27-001 | ? | open | 2026-07-27 12:14 (KST) — freeze 대상 객체를 문서 아닌 추측으로 작성 |
| 2026-07-27-002 | ? | open | 2026-07-27 18:30 (KST) — 검증 안 된 조향지령으로 node4 물리 손상 + 세션 반복 추측 |
| 2026-07-28-002 | ? | open | 2026-07-28 14:34 (KST) — 남의 세션 범위를 끌어들이고, 종결된 결정을 재질문 |
| 2026-07-28-004 | ? | open | 2026-07-27 23:00 (KST) — 표준 동작을 근거 없이 생략한 설계 3연속 |
| 2026-07-28-005 | ? | open | 2026-07-27 23:25 (KST) — "Seer 호밍은 우리가 못 막습니다" 검증 없는 부정형 단정 |
| 2026-07-28-008 | ? | open | 2026-07-27 23:03 (KST) — 이미 종료된 GUI 를 "점유 중" 이라고 보고 |
| 2026-07-28-009 | ? | open | 2026-07-28 15:56 (KST) — 공유 워킹트리에서 `git checkout -b` 로 20개 세션의 HEAD 를 끌고 감 |
| 2026-07-28-014 | ? | open | 2026-07-28 21:07 (KST) — 화면 한 번 안 보고 UI 결함을 네 번 오진 |
| 2026-07-28-015 | ? | open | 2026-07-28 16:25 (KST) — 검증 없이 "upstream merge 가 깨진다" 로 변경을 막았다 |
| 2026-07-28-016 | ? | open | 2026-07-28 16:20 (KST) — 우리 규약이 미치지 않는 남의 경로에 주석을 달았다 |
| 2026-07-29-002 | ? | open | 프로세스 상태 미확인 + 도구 출력 의미 오독 — 오염된 수치를 두 번 보고 |
| 2026-07-31-003 | ? | open | 2026-07-31 17:52 (KST) — SOP 를 읽기 전에 git 선택지를 썼고, 그 오설명 위에서 결정이 내려졌다 |
| 2026-08-05-001 | ? | open | 2026-08-05 21:20 (KST) — 매뉴얼에 있는 정지 명령을 안 찾고 없는 명령을 만들어 4일을 썼다 |
| 2026-08-06-003 | ? | open | 2026-08-06 17:50 (KST) — coding SOP 4개 절을 건너뛰고 자기승인으로 커밋·푸시 |
| 2026-08-06-003 | ? | open | 2026-08-06 19:59 (KST) — 정리 루프가 다른 세션 워크트리를 삭제 |
| 2026-08-06-004 | ? | open | 2026-08-06 19:30 (KST) — 내 시험 입력을 검증하지 않고 「제어 결함」으로 단정해 공유 기록에 커밋 |
|  | ? | ? | `turn` 오차 자료를 표본 수·부호 규약 둘 다 틀리게 커밋했다 |
|  | ? | ? | 두 센서가 어긋나자 한쪽을 「고장」으로 단정하고, 그 판단으로 로봇을 움직였다 |
| 2026-08-10-002 | ? | ? | 검증을 끝낸 뒤에 파일을 고치고, 재검증 없이 커밋했다 |
| 2026-08-10-003 | ? | ? | 읽지 않고 단정하고, 읽은 뒤에는 「중요한 반전」이라고 포장했다 |
| 2026-08-10-004 | ? | ? | 기록에 이미 있는 것을 「미확인 부채」로 등록했다 — 같은 날 세 번째 |
| 2026-08-10-005 | ? | ? | 관측된 고장이 아니라 추정 위에서 실측 기반 설계를 바꿨다 |
| 2026-08-10-006 | ? | ? | 경고를 무시한 측위원으로, 감시 없이 첫 실기 주행을 돌려 충돌 직전까지 갔다 |
| 2026-08-13-001 | ? | ? | 잘못된 주석을 고치면서 「무엇을 고쳤는지」를 주석 안에 적었다 — 감사 1라운드를 자초했다 |
| 2026-08-13-001 | ? | ? | A 6.9 m machine was drawn 2.82 m wide, because it was sized to the gap it was dropped into |
| 2026-09-01-001 | B | open | 2026-09-01 23:5x (KST) — R02 intercept 진단: 실기 기록 미독 + 미확정 가설을 "확정"으로 기재 |
| 2026-09-02-003 | B | open | 2026-09-02 21:44 (KST) — 시키지 않은 시스템 스택(nvidia-jetpack) 설치를 원격 기체에 무승인 진행 |
| 2026-09-04-001 | B | open | 2026-09-04 21:10 (KST) — 검증 가능한 경로를 "타이밍상 재현 안 됨" 으로 적고 넘겼다 |
| 2026-09-05-001 | B | open | 2026-09-05 09:04 (KST) — 재engage 처리가 "복원 완료 → 제어권 해제" 순서를 깰 수 있게 구현했다 |
| 2026-09-05-002 | B | open | 2026-09-05 09:2x (KST) — USB 백로그를 비우지 않은 SDO 읽기 값을 실측이라 보고했다 |
| 2026-09-05-003 | A | open | 2026-09-05 09:5x (KST) — 공유 작업트리의 낡은 파일을 세션 워크트리에 복사해 다른 세션의 기록 16줄을 지웠다 |

## 키워드 색인

> 사건이 다루는 코드 토큰. **같은 계열의 다른 파일**을 고칠 때 이 색인으로 찾는다 — 사건에 이름이 적히지 않은 파일은 경로로는 영원히 안 걸린다.

| 토큰 | 사건 |
|---|---|
| `ADR` | 2026-08-18-001 |
| `AMR` | 2026-07-31-002 |
| `APITCPServerMaxConnections` | 2026-08-07-002 |
| `AskUserQuestion` | 2026-07-31-003 |
| `Bash` | 2026-07-31-002 |
| `Big-AMR-ses-66e0baff-hl` | 2026-08-10-001 |
| `CAN1` | 2026-09-02-003 |
| `CAN3` | 2026-09-02-003 |
| `CCW` | 2026-07-27-003 |
| `CERT` | 2026-09-02-002 |
| `CLAUDE.md` | , 2026-07-28-002, 2026-07-28-005, 2026-07-28-008, 2026-07-28-009, 2026-07-28-011, 2026-07-28-014, 2026-07-28-015, 2026-07-28-016, 2026-07-31-003, 2026-08-04-001, 2026-08-06-003, 2026-09-04-001 |
| `CMakeLists.txt` | 2026-07-28-015 |
| `CN4` | 2026-08-24-002 |
| `CODING_GATE` | 2026-08-06-003 |
| `CONT` | 2026-09-02-003 |
| `CPD` | 2026-08-06-002 |
| `CPU` | 2026-07-29-002 |
| `CalPose` | 2026-08-07-001 |
| `CalSpeed` | 2026-08-07-001 |
| `CaldPose` | 2026-08-07-001 |
| `Candidate` | 2026-07-28-010 |
| `Controller` | 2026-08-16-001 |
| `Could` | 2026-08-06-005 |
| `DEV-cc5e0491-DEBUG` | 2026-09-02-002 |
| `DI4/DI2` | 2026-07-28-006 |
| `DT_NEEDED` | 2026-08-06-004 |
| `Decision` | 2026-08-18-001 |
| `Diag` | 2026-08-06-004 |
| `ERR_GOZERO` | 2026-08-15-001 |
| `ERR_TIMEOUT` | 2026-07-28-004, 2026-07-29-003, 2026-08-15-001 |
| `EquipmentMonitorTask.step` | 2026-08-20-001 |
| `FB.4` | 2026-07-28-006 |
| `FITO_AMR_ros2_ws` | 2026-07-28-010 |
| `FlagCumEncPoseMode` | 2026-08-07-001 |
| `FlashGui` | 2026-09-02-001 |
| `GRAVURE1_BODY` | 2026-08-13-001 |
| `GRAVURE1_BODY_RETRACTED` | 2026-08-13-001 |
| `GRAVURE1_CONNECTORS` | 2026-08-13-001 |
| `GRAVURE_SIZE` | 2026-08-13-001 |
| `GRAVURE_STATIONS` | 2026-08-13-001 |
| `GRAVURE_X` | 2026-08-13-001 |
| `GRAVURE_Y` | 2026-08-13-001 |
| `HEAD` | 2026-08-06-001 |
| `HOME_0DEG` | 2026-08-06-002 |
| `INDEX.md` | 2026-08-04-001 |
| `Info` | 2026-08-10-003 |
| `IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.txt` | 2026-08-03-002 |
| `Last` | 2026-07-31-001 |
| `LaunchConfiguration` | 2026-08-19-001 |
| `LineCapacity` | 2026-08-20-001 |
| `LocalizationMonitor` | 2026-08-10-004, 2026-08-10-006 |
| `Log` | 2026-07-28-004, 2026-07-29-003, 2026-08-03-001 |
| `Log/dock_precision_0825` | 2026-08-26-001 |
| `Log/drive_0825` | 2026-08-26-001 |
| `Log/homing_capture_220350.jsonl` | 2026-07-27-002, 2026-07-28-003, 2026-08-03-002 |
| `MCLoc` | 2026-08-16-001 |
| `Message_MotorInfo` | 2026-08-16-001 |
| `MockLink.homing_cancel` | 2026-08-15-001 |
| `MotorInfos` | 2026-08-16-001 |
| `NavSpeed` | 2026-08-16-001 |
| `NetProtocol` | 2026-08-07-002 |
| `OdoCalculator` | 2026-08-16-001 |
| `Orbbec_Gemini_E_RGB_Camera` | 2026-08-30-001 |
| `PA8/15` | 2026-09-02-003 |
| `PB8/9` | 2026-09-02-003 |
| `PRODUCT_FULL_VERSION` | 2026-08-07-002 |
| `PURPOSE_RE` | 2026-07-31-002 |
| `Project/CAN-Relay/docking_field_kit/panda.bin.signed` | 2026-07-28-011 |
| `Project/T-Robotics/T-Driver-Analysis/tools` | 2026-07-28-016 |
| `Publisher` | 2026-08-02-001 |
| `QoS` | 2026-08-07-001 |
| `R01` | 2026-09-02-003 |
| `R02` | 2026-08-24-002, 2026-09-02-003 |
| `README.md` | 2026-07-27-004, 2026-07-28-015, 2026-07-28-016, 2026-08-18-002 |
| `References` | 2026-08-18-001 |
| `References/Seer-Driver/robokit_tcp_api.md` | 2026-08-18-001 |
| `RelayBackend` | 2026-08-08-001 |
| `RelayBackend.halt_steer` | 2026-08-03-003 |
| `Rig.sdo_read` | 2026-09-05-002 |
| `Robot` | 2026-08-07-002 |
| `RobotNote` | 2026-09-02-001 |
| `RobotPosEKF` | 2026-08-16-001 |
| `STOP` | 2026-09-02-003 |
| `SensorDataQoS` | 2026-08-07-001 |
| `SetCumEncPoseMode` | 2026-08-07-001 |
| `SteerRamp` | 2026-07-27-002 |
| `TCP_IP/seer_api` | 2026-08-18-002 |
| `TaskStop` | 2026-07-29-002 |
| `Terminated` | 2026-07-31-001 |
| `Tool` | 2026-07-27-004 |
| `Tools` | 2026-07-27-004, 2026-07-28-015, 2026-07-28-016 |
| `Tools/Can_Relay` | 2026-09-02-001 |
| `Tools/Can_Relay/R02/README.md` | 2026-09-01-001 |
| `Tools/Can_Relay/fw_backups/README-2026-08-23.md` | 2026-08-24-002 |
| `Tools/Can_Relay/panda-firmware/.git` | 2026-07-28-015 |
| `Tools/Can_Relay/panda-firmware/board/usb_comms.h` | 2026-07-28-007 |
| `Tools/amr_test_gui` | 2026-07-27-004, 2026-07-28-002 |
| `Tools/amr_test_gui/amr_test_gui/ramp.py` | 2026-07-27-002, 2026-07-28-003 |
| `Tools/amr_test_gui/gui.py` | 2026-07-28-003, 2026-07-28-009, 2026-07-28-012, 2026-08-04-001, 2026-09-02-001, 2026-09-02-002 |
| `Tools/amr_test_gui/mutation_check.py` | 2026-08-08-002 |
| `Tools/docking_field_kit/MIGRATION-orin-nx.md` | 2026-07-28-016 |
| `Tools/docking_field_kit/NEXT-SESSION-PROMPT.md` | 2026-07-28-016 |
| `Tools/docking_field_kit/master_command_census.py` | 2026-08-03-002 |
| `Tools/docking_field_kit/orin_` | 2026-09-01-001 |
| `Tools/docking_field_kit/orin_hold_intercept.py` | 2026-09-01-001 |
| `Tools/docking_field_kit/orin_home_experiment.py` | 2026-09-05-002 |
| `Tools/docking_field_kit/orin_steer_sweep_1005.py` | 2026-08-06-002 |
| `Tools/docking_field_kit/orin_steer_two_phase.py` | 2026-09-02-002 |
| `Tools/docking_field_kit/panda/python/__init__.py` | 2026-07-28-007 |
| `Tools/docking_field_kit/verify_homing_claims.py` | 2026-08-03-001 |
| `Tools/find_experiment_data.sh` | 2026-08-26-001 |
| `Tools/mcl2d_standalone/include/mcl2d_localizer.hpp` | 2026-08-06-004 |
| `Tools/monitored_move/monitored_reverse.py` | 2026-08-10-006 |
| `Tools/motion_chain_check/RUNBOOK-first-drive.md` | 2026-08-10-003, 2026-08-10-006 |
| `Tools/motion_sil_regression/sil_regression.py` | 2026-08-10-002 |
| `Tools/repo_tools/branch_superseded.py` | 2026-08-06-001 |
| `Tools/seer_jog/README.md` | 2026-09-02-002 |
| `TypeError` | 2026-08-20-001 |
| `T大AGV路线` | 2026-08-13-001 |
| `V7.0` | 2026-07-28-006 |
| `WRAP_MARGIN` | 2026-08-05-001 |
| `Write` | 2026-07-31-002 |
| `__file__` | 2026-07-28-013 |
| `_app_start` | 2026-07-28-007 |
| `_code_updates.md` | 2026-08-13-001 |
| `_home_failed` | 2026-08-15-001 |
| `_loop` | 2026-08-04-001 |
| `_on_poll_died` | 2026-08-04-001 |
| `_rendered_delta` | 2026-07-28-001 |
| `_steer_axis` | 2026-07-27-002 |
| `_steer_to` | 2026-07-27-002, 2026-07-28-003 |
| `_sync_sliders` | 2026-07-28-014 |
| `a7420a6` | 2026-08-08-001 |
| `active` | 2026-07-31-002 |
| `actual` | 2026-07-28-012 |
| `ad7520981d500fa5881e548ef22fc92d0d7fe4a1` | 2026-07-31-004 |
| `add` | 2026-07-28-009 |
| `adr-fields.sh` | 2026-07-28-002 |
| `allow-main-commit` | 2026-07-31-003 |
| `amap` | 2026-07-31-001, 2026-08-06-005 |
| `amap-1` | 2026-07-31-001, 2026-08-06-005 |
| `amap-server` | 2026-08-06-004, 2026-08-06-005, 2026-08-07-002 |
| `ament_cmake` | 2026-08-18-002 |
| `ament_python` | 2026-08-18-002 |
| `amr` | 2026-07-31-002 |
| `amr_test_gui` | 2026-07-28-008 |
| `api.py` | 2026-08-18-001 |
| `app` | 2026-09-02-001 |
| `apt-get` | 2026-09-02-003 |
| `array` | 2026-09-02-002 |
| `arrows` | 2026-07-28-013 |
| `assert` | 2026-08-10-002, 2026-09-02-002 |
| `atan` |  |
| `audit_cad_world.py` | 2026-08-13-001 |
| `b1ff211` | 2026-08-08-001 |
| `b31d67899631bdf30483a12a6ced7b4e` | 2026-07-28-011 |
| `backend.home` | 2026-08-15-001 |
| `backend.py` | 2026-08-10-001, 2026-08-10-003 |
| `backend_` | 2026-09-02-001 |
| `bag` | 2026-08-26-001 |
| `baseline` | 2026-07-28-004, 2026-07-29-003, 2026-08-03-001 |
| `bash` | 2026-08-30-002 |
| `biguamr-amap1-access.md` | 2026-08-06-005 |
| `biguamr-camera-port-cctv-soak` | 2026-08-30-001 |
| `biguamr-canrelay-custom-board-bus-wiring` | 2026-08-24-002 |
| `biguamr-canrelay-emulate-realpos-leak` | 2026-07-26-001 |
| `biguamr-canrelay-flash-new-board` | 2026-09-01-001 |
| `biguamr-comment-no-history` | 2026-08-18-001 |
| `biguamr-experiment-set-names.md` | 2026-08-26-002 |
| `biguamr-icp-odometry-assets.md` | 2026-08-02-001 |
| `biguamr-motor-node4-sign-crab` | 2026-07-27-002 |
| `biguamr-pgv-docking-metrology` | 2026-08-24-001 |
| `biguamr-repo-layout.md` | 2026-07-27-004 |
| `board/SConscript` | 2026-09-02-002 |
| `board/obj/panda.bin.signed` | 2026-07-28-011 |
| `board/obj/version` | 2026-09-02-002 |
| `boxes` | 2026-07-28-013 |
| `bus0` | 2026-09-02-003 |
| `bus2` | 2026-09-02-003 |
| `by_id_prefix` | 2026-08-30-001 |
| `c5bb4` | 2026-08-06-004 |
| `cam0/image_raw` | 2026-07-28-001 |
| `can_recv` | 2026-09-05-002 |
| `can_relay` | 2026-08-03-003, 2026-08-05-001, 2026-08-08-002, 2026-08-10-005, 2026-08-15-001 |
| `can_relay/ui` | 2026-08-04-001 |
| `cancel_home` | 2026-08-06-001 |
| `capture-test` | 2026-07-28-014 |
| `ceea4` | 2026-08-15-001 |
| `cert_fn` | 2026-09-02-002 |
| `charge_to` | 2026-08-19-001 |
| `check_chain_contract.py` | 2026-08-05-001 |
| `checkout` | 2026-07-28-009, 2026-08-10-001 |
| `checks` | , 2026-07-28-005, 2026-07-28-011 |
| `checks/adr-fields.sh` | 2026-07-28-002 |
| `claude-mistake` | 2026-08-03-001 |
| `claude/settings.json` | 2026-08-06-003 |
| `clean` | 2026-08-06-003 |
| `cmd_vel` | 2026-07-31-004 |
| `cmpb` | 2026-08-07-001 |
| `code_updates` | 2026-08-25-001 |
| `coding-comment-gate` | 2026-08-18-001 |
| `coding-inventory-gate.py` | 2026-08-06-003 |
| `coding-reminder.py` | 2026-08-06-003 |
| `coding.md` | 2026-08-06-003, 2026-08-06-004, 2026-08-18-002, 2026-09-05-001 |
| `computeSpin` | 2026-08-06-003 |
| `config/camera/camera_common.yaml` | 2026-08-30-001 |
| `config/tongyi_amr.yaml` | 2026-07-27-003 |
| `context-missing` | 2026-07-27-004, 2026-08-03-002, 2026-08-05-001, 2026-08-06-001, 2026-08-15-001 |
| `count` | 2026-08-02-001 |
| `counts` | 2026-07-27-003, 2026-08-06-002 |
| `crab` | 2026-08-25-001 |
| `csm` | 2026-08-10-004 |
| `d09c55..07f8661` | 2026-09-05-003 |
| `d46347a` | 2026-08-10-001 |
| `d5f6` | 2026-08-07-001 |
| `d5fe` | 2026-08-07-001 |
| `data` | 2026-09-02-002 |
| `db3` | 2026-08-26-001 |
| `debt-004` | , 2026-07-27-003 |
| `debt-007` |  |
| `debt-016` | 2026-07-28-004, 2026-07-29-003 |
| `debt-068` | 2026-08-10-003, 2026-08-10-004 |
| `debt-071` | 2026-08-13-001 |
| `debt-095` | 2026-09-02-001 |
| `debt-111` | 2026-09-02-002 |
| `debt-126` | 2026-09-02-001 |
| `def` | 2026-08-06-001 |
| `default_value` | 2026-08-19-001 |
| `deg` | 2026-08-06-002 |
| `delta_f` | 2026-08-06-004 |
| `delta_f/r` | 2026-08-10-005 |
| `deselect` | 2026-08-08-002 |
| `detect` | 2026-09-02-001 |
| `detection.py` | 2026-08-06-003 |
| `detector_node.py` | 2026-08-06-003 |
| `detectors/2026-09-05-003.sh` | 2026-09-05-003 |
| `dev/sda2` | 2026-08-06-005 |
| `dev/sdb2` | 2026-08-06-005 |
| `dev/shm` | 2026-07-29-002 |
| `dfb626` | 2026-08-10-001 |
| `dict` | 2026-08-20-001 |
| `died` | 2026-08-19-001 |
| `diff` | 2026-09-05-003 |
| `docking_drive.py` | 2026-07-27-003 |
| `docs/adr` | 2026-08-05-001 |
| `docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md` | 2026-08-05-001 |
| `docs/adr/2026-07-27-amr-test-gui.md` | 2026-07-27-003 |
| `docs/adr/2026-07-27-panda-fw-rewrite-brief.md` | 2026-07-28-006 |
| `docs/adr/2026-07-28-cctv-ai-overlay-toggle.md` | 2026-07-29-002 |
| `docs/adr/2026-07-28-icp-odometry-bringup.md` | 2026-08-02-001 |
| `docs/adr/2026-07-29-can-relay-ros2-package.md` | 2026-07-31-004 |
| `docs/adr/2026-08-04-amr-test-gui-swappable-backend.md` | 2026-08-15-001 |
| `docs/adr/2026-08-15-line-follow-common-diff-control.md` | 2026-08-25-001 |
| `docs/can_relay` | 2026-08-24-002, 2026-09-01-001 |
| `docs/can_relay/2026-07-07-design-inputs.md` | 2026-07-28-012 |
| `docs/can_relay/R02-schematic-review-2026-08-24.md` | 2026-08-24-002, 2026-09-02-003 |
| `docs/can_relay/clone-board-U3P-pinmap-findings.md` | 2026-08-24-002 |
| `docs/can_relay/field-record-orin-nx-2026-07-25.md` | 2026-07-26-001, 2026-09-02-002 |
| `docs/claude-mistake/2026-07-27-002` | 2026-08-03-003 |
| `docs/claude-mistake/2026-07-28-001` | 2026-07-28-013 |
| `docs/claude-mistake/2026-07-28-005` | 2026-09-04-001 |
| `docs/claude-mistake/2026-08-13-001` | 2026-08-18-001 |
| `docs/claude-mistake/INDEX.md` | , 2026-07-28-005, 2026-08-03-002 |
| `docs/claude_guideline/code_review/domains/ros2-review.md` | 2026-08-07-001 |
| `docs/claude_guideline/code_review/review.md` | 2026-07-28-013, 2026-08-06-001 |
| `docs/claude_guideline/coding/coding.md` | 2026-07-26-001, 2026-07-27-001, 2026-07-27-002, 2026-07-28-001, 2026-08-02-001, 2026-08-03-001, 2026-08-03-003, 2026-08-04-001, 2026-08-05-001, 2026-08-06-003, 2026-09-02-001 |
| `docs/claude_guideline/external_reference/handling.md` | 2026-07-28-005, 2026-07-28-006, 2026-08-05-001, 2026-08-06-002 |
| `docs/claude_guideline/git_workflow/git_workflow.md` | 2026-07-28-002, 2026-07-28-009, 2026-07-31-003, 2026-08-06-003, 2026-09-05-003 |
| `docs/claude_guideline/issue_fix/issue_fix.md` | 2026-07-28-001, 2026-07-28-014, 2026-09-04-001 |
| `docs/claude_guideline/mistake/mistake.md` | 2026-07-28-016, 2026-07-29-002, 2026-08-03-001, 2026-08-04-001 |
| `docs/claude_guideline/reverse_engineering/principle.md` | 2026-07-26-001, 2026-07-27-001, 2026-07-27-002, 2026-07-28-011, 2026-08-03-001, 2026-08-06-001, 2026-08-07-001, 2026-09-01-001 |
| `docs/claude_guideline/session_workflow/session_workflow.md` | 2026-07-31-002 |
| `docs/code_review/ai-yolo-detector/2026-08-06.md` | 2026-08-06-003 |
| `docs/code_review/pose-topic-wiring/2026-08-10.md` | 2026-08-10-003 |
| `docs/debt/registry.md` | 2026-07-28-002, 2026-08-03-002, 2026-08-03-003, 2026-09-02-001 |
| `docs/issues_and_fixes` | 2026-08-10-004 |
| `docs/issues_and_fixes/issues_and_fixes.md` | 2026-08-06-004, 2026-08-10-004, 2026-08-10-005, 2026-08-25-001, 2026-08-30-002, 2026-09-05-003 |
| `docs/tongyi_can_protocol/2026-08-05.md` | 2026-08-06-002 |
| `docs/user_instructions/sessions/56a709a5` | 2026-07-28-003 |
| `docs/user_instructions/user_instructions.md` | 2026-08-15-001 |
| `docs/verified_facts/2026-07-27.md` | 2026-07-28-003 |
| `docs/verified_facts/2026-07-28-errata.md` | 2026-07-28-006 |
| `docs/verified_facts/2026-08-02-steer-home-closed.md` | 2026-07-28-004, 2026-07-29-003 |
| `domains/ros2-review.md` | 2026-08-07-001 |
| `dpos` | 2026-08-16-001 |
| `drive_accel_mps2` | 2026-08-06-003 |
| `drive_decel_mps2` | 2026-08-06-003 |
| `drive_sign` | 2026-07-27-003 |
| `driver_node` | 2026-07-27-003 |
| `driver_node.py` | 2026-07-31-004 |
| `dual_laser_merger` | 2026-07-28-010 |
| `duration` | 2026-09-02-002 |
| `e002c` | 2026-09-02-003 |
| `e0064d5` | 2026-08-13-001 |
| `e_theta` | 2026-08-06-004 |
| `effective_yaw` | 2026-08-06-004 |
| `emulate` | 2026-07-28-005 |
| `encoder` | 2026-08-16-001 |
| `engage` | 2026-09-01-001 |
| `estop` | 2026-08-03-003, 2026-08-05-001 |
| `euo` | 2026-08-30-002 |
| `exit` | 2026-08-10-002 |
| `expected_steer_f/r` | 2026-08-10-005 |
| `extern` | 2026-07-28-007, 2026-07-28-013 |
| `external_reference/handling.md` | 2026-07-28-005 |
| `f46` | 2026-08-10-002 |
| `fb40d` | 2026-07-31-003 |
| `fb9663` | 2026-08-13-001 |
| `fd97825` |  |
| `fe77556` | 2026-07-31-003 |
| `file` | 2026-07-28-014 |
| `find` | 2026-07-27-004, 2026-07-28-016, 2026-08-18-002, 2026-08-26-001 |
| `flash_gui.py` | 2026-09-02-001 |
| `flash_new_board.py` | 2026-09-02-002 |
| `fleet.launch.py` | 2026-08-19-001 |
| `foil_a082.yaml` | 2026-08-05-001, 2026-08-13-001 |
| `force` | 2026-08-06-003 |
| `fps` | 2026-07-29-002 |
| `fps/1435f` | 2026-07-28-001 |
| `frames` | 2026-07-28-001 |
| `from` | 2026-07-31-001 |
| `fw_backups/panda.bin.signed.pre_homing_2026-07-27` | 2026-07-28-011 |
| `gate_min_err_deg` | 2026-08-10-005 |
| `gear_steer` | 2026-08-06-003 |
| `gear_walk` | 2026-08-06-003 |
| `gen.py` | 2026-07-28-013 |
| `generic_rx_checks` | 2026-07-28-012 |
| `geometry_msgs/Twist` | 2026-07-31-004 |
| `git/git_workflow/sessions` | 2026-07-28-009 |
| `git/session_workflow` | 2026-07-31-002 |
| `git_workflow-session.sh` | 2026-07-31-003 |
| `git_workflow.md` | 2026-07-28-002, 2026-08-18-002 |
| `gitmodules` | 2026-07-28-015 |
| `grep` | 2026-07-28-012, 2026-07-31-004, 2026-08-06-001, 2026-08-06-004, 2026-08-06-005, 2026-08-10-004, 2026-08-24-002, 2026-08-25-001, 2026-09-01-001, 2026-09-02-002 |
| `gui.py` | 2026-08-10-001 |
| `halt_steer` | 2026-08-03-002, 2026-08-05-001 |
| `hard` | 2026-08-06-003, 2026-08-10-001 |
| `has` | 2026-08-19-001 |
| `hold_steer` |  |
| `hold_steer_at_measured` | 2026-08-05-001 |
| `home/nvidia` | 2026-08-26-001 |
| `home/nvidia/Project/Ford-CATL-AMR/Big-AMR` | 2026-07-28-009 |
| `home_cancel` | 2026-08-15-001 |
| `homed` | 2026-08-08-002 |
| `homing` | 2026-08-08-002 |
| `hostname` | 2026-08-06-005 |
| `icp_odometry` | 2026-07-28-010 |
| `ignore` | 2026-08-08-002 |
| `import` | 2026-08-10-004 |
| `imu_yaw_noise_deg` | 2026-08-06-003 |
| `iname` | 2026-07-27-004 |
| `info` | 2026-08-02-001, 2026-08-10-004 |
| `initialpose` |  |
| `input` | 2026-07-28-006 |
| `install` | 2026-09-02-003 |
| `install.sh` | 2026-08-30-002 |
| `int` | 2026-07-28-007 |
| `intent-guess` | 2026-08-24-001 |
| `issue_fix` | 2026-07-28-014 |
| `issues_and_fixes.md` | , 2026-08-08-001, 2026-08-08-002, 2026-08-10-001 |
| `jammy.20260622.101306` | 2026-07-28-010 |
| `joint_states` | 2026-07-31-004 |
| `key` | 2026-08-10-002 |
| `kill` | 2026-07-29-002, 2026-09-02-003 |
| `kin_steer_sign` | 2026-07-27-002, 2026-07-27-003 |
| `kuks2309/CAN-Relay` | 2026-07-28-016 |
| `kuks2309/TR_Nav_ros2_ws` | 2026-07-28-010, 2026-07-31-004, 2026-08-05-001 |
| `kuksauto` | 2026-07-31-001 |
| `laser_mounts` | 2026-08-07-001 |
| `laser_scan_matcher` | 2026-07-28-010 |
| `launch` | 2026-08-19-001 |
| `launch/mpc.launch.py` | 2026-08-13-001 |
| `launch/sil_mpc.launch.py` | 2026-08-13-001 |
| `leg_of` | 2026-08-20-001 |
| `libMCLoc.so` | 2026-07-31-001, 2026-08-06-004 |
| `libNetProtocol.so` | 2026-08-07-002 |
| `libOdoCalculator.so` | 2026-08-16-001 |
| `libprotobuf.so.17` | 2026-08-06-004 |
| `libzmq.so.5` | 2026-08-06-004 |
| `light_intercept.py` | 2026-09-01-001 |
| `limit` | 2026-07-28-006 |
| `line` | 2026-07-28-014 |
| `linefollow` | 2026-08-24-001 |
| `list` | 2026-07-28-009, 2026-07-31-003 |
| `login` | 2026-07-31-001 |
| `lookupMapToBase` | 2026-08-10-006 |
| `low-battery` | 2026-08-19-001 |
| `ls-files` | 2026-08-03-002, 2026-08-03-003 |
| `m/s` | 2026-08-10-006 |
| `machines` | 2026-08-13-001 |
| `main` | , 2026-08-06-001, 2026-08-10-001 |
| `main_window._report_display_stats` | 2026-07-28-001 |
| `math_utils.hpp` | 2026-08-10-003 |
| `max_steer_deg` | 2026-08-10-005 |
| `maxdepth` | 2026-08-26-001 |
| `mcap` | 2026-08-26-001 |
| `mcl2d_localization_node` | 2026-08-02-001, 2026-08-07-001 |
| `mcl2d_localization_node.cpp` | 2026-08-07-001 |
| `mcl_pose` | 2026-08-02-001 |
| `method35` | 2026-08-08-002 |
| `minValue` | 2026-08-07-002 |
| `mistake` | 2026-07-27-004 |
| `mistake-relevance` | 2026-09-02-002, 2026-09-02-003, 2026-09-04-001, 2026-09-05-001, 2026-09-05-002 |
| `mistake.md` | 2026-07-28-002 |
| `mixed` | 2026-08-10-001 |
| `mmd` | 2026-07-28-013 |
| `mode` | 2026-08-05-001 |
| `modes.py` | 2026-07-27-003 |
| `mola` | 2026-07-28-010 |
| `motor` | 2026-08-13-001 |
| `motor_control.kinematics` | 2026-07-31-004 |
| `mp2p-icp` | 2026-07-28-010 |
| `mpc` | 2026-08-10-006 |
| `mpc_reverse` | 2026-08-06-004 |
| `mpc_reverse_action_server.cpp` | 2026-08-06-004 |
| `mpc_reverse_action_server.hpp` | 2026-08-13-001 |
| `mpc_reverse_debug` | 2026-08-06-004 |
| `mutation_check.py` | 2026-08-06-002 |
| `name` | 2026-08-18-002, 2026-08-26-001 |
| `node` | 2026-08-06-002 |
| `node1` | 2026-08-08-001 |
| `numstat` | 2026-09-05-003 |
| `nvidia` | 2026-07-31-001 |
| `nvidia-jetpack` | 2026-09-02-003 |
| `odom` | 2026-08-02-001, 2026-08-07-001 |
| `orbbec_multi_bringup/config` | 2026-08-30-001 |
| `origin` | 2026-07-28-015 |
| `origin/main` | 2026-08-06-001, 2026-08-10-001, 2026-09-05-003 |
| `origin/session` | 2026-08-06-001 |
| `orin_hold_intercept.py` | 2026-09-01-001 |
| `orin_home_experiment.py` | 2026-08-03-001, 2026-09-05-002 |
| `orin_homing_run.py` | 2026-07-28-011 |
| `os.path.abspath` | 2026-07-28-013 |
| `os.path.dirname` | 2026-07-28-013 |
| `package.xml` | 2026-08-18-002 |
| `page` | 2026-07-28-006 |
| `panda.bin.signed` | 2026-09-02-002 |
| `param_probe` | 2026-09-02-001 |
| `passed` | 2026-08-04-001 |
| `pc_authority` | 2026-07-26-001 |
| `pidstat` | 2026-07-29-002 |
| `pipefail` | 2026-08-30-002 |
| `pkill` | , 2026-07-29-002, 2026-08-02-001, 2026-09-02-003 |
| `plant.segment_of_station` | 2026-08-20-001 |
| `pm90-unique-solution` | 2026-08-05-001 |
| `pose_node.py` | 2026-08-10-003, 2026-08-10-006 |
| `pose_topic` | 2026-08-10-003, 2026-08-10-006 |
| `position` | 2026-08-05-001 |
| `prefix` | 2026-08-10-002 |
| `process` | 2026-08-19-001 |
| `pulses_per_rev` | 2026-08-06-003 |
| `purpose` | 2026-07-31-002 |
| `push` | 2026-08-06-003 |
| `qd_crab_inverse_kinematics.cpp` | 2026-08-05-001, 2026-08-13-001 |
| `r12` | 2026-08-07-001 |
| `ramp.py` | 2026-07-28-003 |
| `range` | 2026-07-28-007 |
| `rbk/product.version.h` | 2026-08-07-002 |
| `rbk/rbk.plugin` | 2026-08-16-001 |
| `rclcpp` | 2026-08-07-001 |
| `references/seer/libMCLoc` | 2026-08-06-004 |
| `reflected_assets` | 2026-09-01-001 |
| `reliability-24h-results.md` | 2026-09-01-001 |
| `reloadParams` | 2026-09-02-002 |
| `remote` | 2026-07-28-015 |
| `remove` | 2026-08-06-003 |
| `rendered` | 2026-07-28-001 |
| `reset` | 2026-07-27-002, 2026-08-06-003, 2026-08-10-001 |
| `resolve` | 2026-08-06-005 |
| `restoreFactoryParams` | 2026-09-02-002 |
| `result` | 2026-08-06-004 |
| `ret_code` | 2026-08-07-002, 2026-08-18-001, 2026-09-02-001, 2026-09-02-002 |
| `return` | 2026-08-20-001 |
| `rf2o_laser_odometry` | 2026-07-28-010 |
| `rni` | 2026-08-24-002 |
| `robot.model` | 2026-08-07-001 |
| `robot.param` | 2026-07-31-001, 2026-08-07-001, 2026-08-07-002 |
| `robot_config_clearfatal_req` | 2026-09-02-001 |
| `robot_config_reloadparams_req` | 2026-09-02-001 |
| `robot_config_saveparams_req` | 2026-09-02-001 |
| `robot_config_setparams_req` | 2026-09-02-001 |
| `robot_pose` | 2026-08-10-003, 2026-08-10-004, 2026-08-10-006 |
| `ros-humble-rtabmap-odom` | 2026-07-28-010 |
| `ros2` | 2026-08-02-001, 2026-08-10-004, 2026-08-19-001 |
| `rule-violation` | 2026-07-27-004, 2026-07-28-002, 2026-07-29-002 |
| `run_camera.sh` | 2026-08-30-002 |
| `run_manager.sh` | 2026-08-30-002 |
| `rviz2` |  |
| `safe_release` | 2026-07-28-009 |
| `safety_seer_gate` | 2026-09-02-003 |
| `safety_seer_gate.h` | 2026-07-26-001, 2026-07-28-004, 2026-07-29-003, 2026-09-04-001, 2026-09-05-001 |
| `saturate` | 2026-08-13-001 |
| `scan_front` | 2026-08-07-001 |
| `scan_merged` | 2026-07-28-010, 2026-08-07-001 |
| `scan_rear` | 2026-08-07-001 |
| `sdo_read` | 2026-09-05-002 |
| `seer-api-tcp-hal.md` | 2026-08-18-002 |
| `seer/robot_pose` | 2026-08-10-003 |
| `seer_cache_reply` | 2026-07-26-001 |
| `seer_freeze_snapshot` | 2026-07-26-001 |
| `seer_gate_fwd_hook` | 2026-07-26-001 |
| `seer_handover_request` | 2026-09-05-001 |
| `seer_handover_tick` | 2026-09-04-001 |
| `seer_ho_reengage` | 2026-09-04-001, 2026-09-05-001 |
| `seer_home_cancel_frames` | 2026-07-28-004, 2026-07-29-003 |
| `seer_home_digital_in` | 2026-07-28-004, 2026-07-29-003 |
| `seer_pose_publisher` | 2026-08-10-003, 2026-08-10-006 |
| `seer_tcp_ip` | 2026-09-02-001, 2026-09-02-002 |
| `segment_of_station` | 2026-08-20-001 |
| `select_motion_source` | 2026-08-05-001 |
| `self.poll_died.emit` | 2026-08-04-001 |
| `session/520bf3ab` | 2026-08-06-001 |
| `session_id` | 2026-07-31-002, 2026-07-31-003 |
| `session_workflow.md` | 2026-07-31-002 |
| `set` | 2026-08-06-002, 2026-08-30-002 |
| `setparams/saveparams` | 2026-09-02-001 |
| `show-args` | 2026-08-19-001 |
| `sim_node.py` | 2026-08-20-001 |
| `soak_monitor` | 2026-07-28-001 |
| `soak_samples.csv` | 2026-07-28-001 |
| `soak_stats.parse_display_line` | 2026-07-28-001 |
| `spin` |  |
| `src/AI/line_vision` | 2026-08-24-001 |
| `src/AI/yolo_detector` | 2026-08-06-003 |
| `src/Actuators/motor_control/motor_control/protocol.py` | 2026-07-28-006 |
| `src/Comm/CAN/can_relay` | 2026-07-31-004, 2026-08-03-002, 2026-08-03-003 |
| `src/Comm/CAN/can_relay/can_relay/ui` | 2026-09-02-001 |
| `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml` | 2026-07-28-004, 2026-07-29-003, 2026-08-05-001 |
| `src/Comm/TCP_IP/seer_api` | 2026-08-07-002 |
| `src/Comm/seer_tcp_ip` | 2026-08-18-002 |
| `src/Control/AMR-Motor` | 2026-07-31-004 |
| `src/Sensors/Camera/RGBD/OrbbecSDK_ROS2/.git` | 2026-07-28-015 |
| `src/Sensors/Camera/RGBD/OrbbecSDK_ROS2/orbbec_camera/tools` | 2026-07-28-015 |
| `src/Tools` | 2026-07-27-004 |
| `src/UI` | 2026-09-02-001 |
| `ssh` | 2026-08-06-005 |
| `stack.md` | 2026-08-18-002 |
| `start` | 2026-07-31-003 |
| `start_battery` | 2026-08-19-001 |
| `static` | 2026-07-28-013 |
| `steer3` |  |
| `steer4` |  |
| `steerOffset` | 2026-07-28-004, 2026-07-29-003, 2026-08-03-001 |
| `steer_angles` | 2026-09-05-002 |
| `steer_home_counts` | 2026-07-27-002, 2026-08-05-001 |
| `steer_limit_deg` | 2026-08-05-001 |
| `steer_origin` | 2026-08-08-002 |
| `steer_rate_dps` | 2026-08-06-003 |
| `stop` | 2026-08-03-003, 2026-08-05-001 |
| `strict` | 2026-08-06-003 |
| `submodule` | 2026-07-28-015 |
| `sudo` | 2026-09-02-003 |
| `summarize_display` | 2026-07-28-001 |
| `surround_depth` | 2026-08-30-001 |
| `surround_depth.yaml` | 2026-08-30-001 |
| `switch` | 2026-07-28-009, 2026-07-31-003 |
| `system_health` | 2026-07-28-002 |
| `systemd-analyze` | 2026-08-30-002 |
| `systemd-run` | 2026-08-30-002 |
| `tailnet` | 2026-07-31-001 |
| `tailscale` | 2026-08-06-005 |
| `tech-debt-shortcut` | 2026-07-31-002 |
| `test_line_capacity.py` | 2026-08-20-001 |
| `test_measurement_never_moves_the_slider` | 2026-07-28-014 |
| `test_poll_death_drops_the_control_toggle` | 2026-08-04-001 |
| `test_ramp.py` | 2026-07-27-002 |
| `tmp` | 2026-08-06-003 |
| `tmp/2ws-geom` | 2026-08-06-003 |
| `tmp/merge-do-safety` | 2026-08-06-003 |
| `tongyi-canopen-protocol-reference.md` | 2026-07-27-001 |
| `tongyi-motor-protocol-tables.md` | 2026-07-27-001 |
| `tongyi_amr.yaml` |  |
| `tools` | 2026-07-27-004, 2026-07-28-015, 2026-07-28-016 |
| `tools/docking_field_kit` | 2026-07-28-016 |
| `tools/verify/smoke_run` | 2026-07-28-016 |
| `top` | 2026-07-29-002 |
| `topic` | 2026-08-02-001, 2026-08-10-004 |
| `touched` | 2026-07-28-009 |
| `translate_sim_odom` | 2026-08-06-003 |
| `trnav_2ws_action_server` | 2026-08-24-001 |
| `trnav_2ws_core/config/robot_geometry_2ws.yaml` |  |
| `trnav_2ws_core/package.xml` | 2026-08-13-001 |
| `trnav_pose_publisher` | 2026-08-10-004 |
| `turn` |  |
| `turn_action_server.cpp` | 2026-08-06-003 |
| `turn_reverse` |  |
| `ubuntu` | 2026-07-31-001 |
| `ui/flash_backend.py` | 2026-09-02-001 |
| `ui/flash_gui.py` | 2026-09-02-001 |
| `unhashable` | 2026-08-20-001 |
| `update` | 2026-09-02-003 |
| `usb_cam_publisher` | 2026-08-30-001 |
| `usb_comms.h` | 2026-09-04-001, 2026-09-05-001 |
| `user_instructions.md` | 2026-08-15-001 |
| `v1.7.5-EON-unknown-DEBUG` | 2026-07-28-007 |
| `v3.4.5.22` | 2026-08-07-002 |
| `v_enc` | 2026-08-16-001 |
| `valid` | 2026-07-28-012 |
| `value` | 2026-07-28-012 |
| `velocity` | 2026-07-28-012 |
| `verified` | 2026-07-27-003 |
| `verified_facts` |  |
| `verify` | 2026-08-30-002 |
| `verify-skip` | 2026-07-28-008, 2026-07-29-002, 2026-08-03-001, 2026-08-04-001, 2026-08-20-001 |
| `verify.py` | 2026-07-28-013 |
| `verify_doc_claims.py` | 2026-08-06-002 |
| `w1_x` |  |
| `walk_front` | 2026-08-08-001 |
| `wheel_motor_state` | 2026-07-31-004 |
| `wheel_motor_state_detailed` | 2026-08-06-003 |
| `wheel_radius` | 2026-08-06-003 |
| `worktree` | 2026-07-28-009, 2026-07-31-003, 2026-08-06-003 |
| `wrong-assumption` | 2026-07-27-003, 2026-08-30-001, 2026-08-30-002 |
| `x/R` |  |
| `x08004000` | 2026-07-28-007 |
| `x0800FFFF` | 2026-07-28-007 |
| `x100C` | 2026-08-08-001 |
| `x100D` | 2026-08-08-001 |
| `x3F` | 2026-08-03-002, 2026-08-03-003 |
| `x4670` | 2026-08-06-002 |
| `x6000` | 2026-07-28-006 |
| `x601` | 2026-07-28-012 |
| `x604` | 2026-07-28-012 |
| `x6040` | 2026-07-28-014, 2026-08-03-002, 2026-08-03-003, 2026-08-08-001 |
| `x6041` | 2026-07-28-004, 2026-07-29-003, 2026-08-03-001 |
| `x6060` | 2026-07-28-014, 2026-08-08-001 |
| `x6064` | 2026-07-26-001, 2026-07-27-001, 2026-07-28-003, 2026-07-28-004, 2026-07-28-012, 2026-07-29-003, 2026-08-03-001, 2026-09-04-001 |
| `x606C` | 2026-07-26-001, 2026-07-27-001, 2026-07-28-012 |
| `x6078` | 2026-07-26-001, 2026-07-27-001 |
| `x607A` | 2026-07-28-014, 2026-08-03-002, 2026-08-03-003, 2026-08-05-001 |
| `x6081` | 2026-07-28-003 |
| `x6083` | 2026-07-28-003 |
| `x6084` | 2026-07-28-003 |
| `x60FB.4` | 2026-07-28-005 |
| `x60FF` | 2026-08-08-001 |
| `x86` | 2026-07-28-014, 2026-08-08-001 |
| `xBF` | 2026-07-28-006 |
| `xc000` | 2026-07-28-007 |
| `xd3` | 2026-07-28-011 |
| `xd4` | 2026-07-28-011 |
| `xd6` | 2026-07-28-011 |
| `xddcc` | 2026-07-28-007 |
| `xddee` | 2026-07-28-007 |
| `xea` | 2026-07-28-011 |
| `xec` | 2026-07-28-005, 2026-09-04-001 |
| `yaw` | 2026-08-06-004 |
| `yaw_control` | 2026-08-10-005 |
| `yaw_control_heading_divergence_count` | 2026-08-10-002 |
| `yaw_frozen_pose` | 2026-08-10-006 |
| `zmq_bind` | 2026-08-06-004 |
| `zmq_connect` | 2026-08-06-004 |
| `zmq_ctx_new` | 2026-08-06-004 |
| `zmq_socket` | 2026-08-06-004 |
