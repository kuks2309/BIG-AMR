# can_relay — systemd 유닛 실장비 검증 (2026-08-16)

## 조건

| 항목 | 값 |
| --- | --- |
| 일시 | 2026-08-16 10:11~10:30 (KST) |
| 기체 | Foil_A082 (판다 실링크) |
| 유닛 | `amr-can-relay.service`(드라이버) · `amr-can-relay-supervisor.service`(감시자) — `install_service.sh --apply`(사용자 실행, sudo) |
| 코드 | 최종 검증 시점 main `297ed13` |
| 안전 | 구동·조향 지령 없음, 실제 축 움직임 0 |

## 발견 1 — 세션 브랜치 워크트리에서 설치하면 overlay 가 낡는다

최초 설치는 본 저장소 워크트리에서 실행됐는데, 그 워크트리는 다른 세션 브랜치에
체크아웃되어 있었고 `install/` overlay 는 감시자 등재 전 빌드였다 — 감시자 유닛이
「`relay_supervisor.launch.py` not found」로 **2초 간격 crash-loop**(재기동 계수 16+ 관측).
드라이버 유닛은 떴지만 낡은 코드였고 `~/engage` 서비스가 응답하지 않았다.

**조치**: main 고정 배포 워크트리 `~/Project/Ford-CATL-AMR/Big-AMR-deploy` 를 신설
(detached, 갱신은 `git fetch && git checkout --detach origin/main` + `colcon build` +
`install_service.sh --apply` 재실행). 유닛의 `@REPO@` 가 이 경로로 치환된다.
판다 라이브러리는 git 미추적이라 본 워크트리 사본에 심볼릭 링크로 연결.

## 발견 2 — 노드 크래시에 `Restart=on-failure` 가 발동하지 않는다 (수정: `always`)

드라이버 노드 `kill -9` 시 `ros2 launch` 가 required-프로세스 종료를 정상 셧다운으로
처리해 **exit 0** 으로 내려간다 — systemd 는 실패로 보지 않아 `on-failure` 는 영영
발동하지 않고 유닛이 `inactive` 로 끝났다(실측). `Restart=always` 로 정정한 뒤
동일 kill 에서 **4초 만에 소생**을 확인했다. `systemctl stop` 은 `always` 에서도
재기동을 만들지 않으며, crash-loop 차단은 `StartLimitIntervalSec=120`/`Burst=3` 이 유지.

## 발견 3 — 유닛 도메인은 설치 시점 셸의 `ROS_DOMAIN_ID` 로 구워진다

이 기체의 운용 도메인은 **125**(사용자 셸 export)다. 유닛도 125 로 설치되어 로봇
스택과 정합하나, 도메인 미설정 셸(0)의 CLI 로는 유닛의 서비스가 보이지 않는다 —
CLI 조작 시 `ROS_DOMAIN_ID=125` 를 명시할 것.

## 본시험 — kill → systemd 소생 → 감시자 자동 복귀 (전 체인)

engage 로 RUNNING·`/run/can_relay/state.json` 에 `engaged: true` 기록 후 노드 `kill -9`:

| 시각 | 사건 |
| --- | --- |
| +0.0 s | `kill -9` (@10:29:28) |
| +3.4 s | 감시자 `RUNNING → DEAD — 진단 두절 3.4s · 프로세스 없음` |
| +3.6 s | systemd `Scheduled restart` (재기동 계수 2, `RestartSec=3`) |
| +4~5 s | 새 노드 기동 — 「대기 — 제어권 미획득」 (설계: 유닛은 engage 하지 않는다) |
| +5.4 s | 감시자 `DEAD → WAIT — 프로세스는 있다` |
| +9.5 s | 안정화 창 경과 → `WAIT → RESTORE` · 복귀 지시(창 내 1/3회) |
| **+9.6 s** | **복귀 완료 — 제어권 획득** · `engaged: true` 재기록 |

이후 수동 `engage false` → `RUNNING → IDLE — 수동 해제로 본다`(불개입) 확인.
유닛 두 개는 enabled 로 상주(재부팅 시 자동 기동·대기).

## 판정

| 주장 | 판정 |
| --- | --- |
| systemd 오버레이 소싱·`RuntimeDirectory`(`/run/can_relay`) 기록 | **실기 PASS** |
| 노드 크래시 → `Restart=always` 소생 (4 s) | **실기 PASS** (`on-failure` 는 반증 — exit 0) |
| 소생 후 감시자 자동 복귀 (kill→복귀 9.6 s) | **실기 PASS** |
| 수동 해제 불개입 · 유닛 미-engage 기동 | **실기 PASS** |
| 감시자 crash-loop 시 systemd 재기동(`Restart=always`) | **실기 관측** (낡은 overlay 국면에서 16회+) |

## 관측의 한정

- 배포 워크트리를 갱신하지 않으면 유닛은 낡은 main 을 계속 돈다 — 갱신 절차(위 §발견 1)가
  운용 수칙이다. 유닛 파일 자체의 갱신(템플릿 변경 시)도 `--apply` 재실행이 필요하다.
- 펌웨어 fail-safe(심박 상실 시 구동 0·릴레이 개방)의 **버스 수준 직접 관측**은 여전히
  미실시 — CAN 캡처 장비가 필요하며 debt-075 의 마지막 잔여 항목이다.
