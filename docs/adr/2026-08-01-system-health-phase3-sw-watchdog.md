# ADR 2026-08-01 — `system_health` Phase 3: SW 이상유무 워치독

Status: Proposed (사용자 지시 sess:9988218d 2026-08-01 "둘다 진행" — Phase 3 착수 승인)

관련: `docs/adr/2026-07-28-system-health-monitor.md` (Phase 1, Accepted)

---

## Context (배경)

Phase 1 은 PC(Personal Computer) **자원**(온도·CPU·GPU·전력·메모리·디스크)을 감시한다.
최초 요청(sess:9988218d 2026-07-28)의 나머지 절반인 **"향후 sw이상유무까지 점검"** 이 남아 있다.

### 사전조사 실측 (2026-08-01, 재부팅 8분 후)

설계 전에 **감시 대상이 실제로 존재하는지** 확인했다. 결과가 설계를 바꿨다:

| 대상 | 실측 | 근거 |
| --- | --- | --- |
| CAN 인터페이스 | **없음** | `ip -br link show type can` 0건, netdev = eth0·eth1·l4tbr0·lo·tailscale0·usb0·usb1·wlan0 |
| `can0-setup.service` | **inactive** | `systemctl is-active` |
| ROS 노드 | **0개 실행 중** | `ps` 에 `_node`·`component_container`·`rclpy` 0건 |
| FastDDS 공유메모리 | **0 세그먼트** | `/dev/shm` 113 항목 중 fastrtps/fastdds 패턴 0 |
| launch 파일 | 20개 이상 | `trnav_2ws_action_server` 만 15개 |
| USB CAN 어댑터 | comma.ai panda 연결됨 | `lsusb` — 단 **socketcan 인터페이스를 만들지 않는다**(USB 직결 경로) |

### 이 조사가 뒤집은 것

**"기대 노드 목록"을 코드가 알 수 없다.** 운영 시나리오마다 띄우는 launch 가 다르고, 조사 시점에는
아무것도 돌고 있지 않았다. 목록을 **지어내면** 이 저장소가 이미 겪은 실패
(`docs/claude-mistake/` §메타 패턴 — 상류 미조사로 신설 노드가 체인 어디와도 연결되지 않음)를
반복한다.

→ **기대 목록은 선언(config)으로 받는다. 선언이 없으면 그 판정을 하지 않는다.**

---

## Decision (결정)

### 1. 범위 — Phase 3a(ROS 무의존)만. Phase 3b(ROS 구독)는 분리

| | Phase 3a (본 ADR) | Phase 3b (별건) |
| --- | --- | --- |
| 실행 위치 | 기존 `sampler`(ROS 무의존) | Phase 2 브리지 노드 |
| 감시 항목 | 프로세스 생존·재시작 · CAN 인터페이스 · DDS 세그먼트 | 토픽 최신성(헤더 타임스탬프) |
| 근거 | `/proc`·`/sys` 만으로 읽힌다 | 구독이 필요하다 |

**토픽 최신성을 Phase 3a 에 넣지 않는다.** 구독 없이는 측정할 수 없고, `ros2 topic hz` 는
호출마다 DDS(Data Distribution Service) participant 를 만들어 전체 노드에 discovery 트래픽을
유발하므로 Phase 1 §Decision 3 이 금지한다. 구독은 ROS 에 의존하므로 Phase 1 의 ROS 무의존
불변식(`test_no_rclpy_import`)과 충돌한다 — 그래서 브리지 쪽 일이다.

### 2. 기대 프로세스는 **선언으로 받는다** — 기본값 없음

임계값 설정 파일에 `expected_processes` 를 둔다(기본 **빈 목록**).

- 선언이 비어 있으면 **프로세스 생존 판정을 하지 않는다.** 감시기가 "무엇이 정상인지" 를
  스스로 정하지 않는다.
- 선언된 이름이 `/proc` 순회 결과에 없으면 `process_missing` 경보.
- 선언된 이름의 PID(Process Identifier)가 바뀌면 `process_restarted` 경보 —
  **조용한 crash-loop 를 잡는 유일한 지표**다. 프로세스가 죽고 즉시 되살아나면 생존 검사만으로는
  아무 일도 없어 보인다.

### 3. CAN 은 **인터페이스가 생기면** 자동 감시. 없으면 조용

- 판별: `/sys/class/net/*/type == 280`(`ARPHRD_CAN`, 이 장비 `/usr/include/linux/if_arp.h:56`
  에서 확인). 이름을 `can*` 로 가정하지 않는다.
- 카운터: `statistics/{rx,tx}_{packets,errors,dropped}` — 실측으로 필드 존재 확인.
- **에러는 누계가 아니라 증가율(errors/s)로 판정한다.** 누계는 한 번 오르면 계속 남아, 스왑
  사용량 기준이 표본 97 % 를 WARN 으로 만들었던 것과 같은 경보 피로가 된다
  (2026-07-31 실측 — Phase 1 에서 이미 겪고 고친 실패다).
- `operstate` 가 `up` 이 아니면 `can_down` 경보.
- 인터페이스가 하나도 없으면 **경보하지 않는다.** 지금 이 장비가 그 상태이고, CAN 을 안 쓰는
  운영도 정상이기 때문이다. "CAN 이 있어야 한다"는 선언은 `expected_processes` 와 같은 성격이라
  필요해지면 별도 항목으로 받는다.

### 4. DDS 세그먼트 수는 **기록만** 한다

`/dev/shm` 의 FastDDS 세그먼트 수를 센다. 판정하지 않는다 — 정상 개수를 모르고, 노드 수·QoS 에
따라 달라진다. 사후 분석에서 "그때 DDS 가 살아 있었나"를 가리는 용도다.

### 5. 임계값은 **전부 기본 비활성**

Phase 1 에서 GPU·입력전류를 기본 비활성으로 둔 것과 같은 이유다. 기준선을 모르는 상태에서
임계를 지어내면 경보 피로만 만든다. `expected_processes` 는 빈 목록, CAN 에러율 임계는 값이
주어질 때만 판정한다.

### 6. 의존성 추가 없음

표준 라이브러리만. `ip` 등 외부 명령을 호출하지 않는다 — sysfs 로 충분하고, 서브프로세스는
5초마다 도는 상주 프로세스에 불필요한 비용이다.

> CAN 버스 상태(error-active / error-passive / bus-off)는 netlink 전용이라 sysfs 에 없다.
> 본 ADR 은 그것을 **읽지 않는다** — 필요해지면 `ip -d link` 호출 비용과 함께 별도로 판단한다.
> 대신 에러 카운터 증가율로 대리한다(버스 이상은 카운터에 나타난다).

---

## Consequences (결과)

### 얻는 것

- crash-loop·프로세스 소실이 기록에 남는다. 지금은 아무도 모른다.
- CAN 을 쓰기 시작하면 **설정 변경 없이** 감시가 붙는다.
- Phase 1 의 구조·불변식(ROS 무의존·표준 라이브러리·읽기 전용)을 그대로 유지한다.

### 치르는 비용 / 남는 위험

- **선언이 없으면 프로세스 감시가 아무것도 하지 않는다.** 사용자가 `expected_processes` 를
  채워야 값이 생긴다. 이것은 결함이 아니라 의도된 설계이지만, **채우지 않으면 Phase 3 의
  핵심 기능이 잠들어 있다**는 점을 문서와 대시보드에 드러내야 한다.
- **토픽 최신성이 빠진다.** "노드는 살아 있는데 발행이 멈춘" 상태를 Phase 3a 는 못 잡는다.
  Phase 3b(브리지)에서만 가능하다.
- 프로세스 이름 매칭은 `/proc/<pid>/stat` 의 `comm`(15자 제한)을 쓴다. 긴 실행파일명은
  잘리므로 선언도 잘린 이름으로 써야 한다 — 이 제약을 문서에 명시한다.

### 후속

- Phase 3b — 토픽 최신성(브리지 구독)
- `expected_processes` 실제 값 — 운영 시나리오 확정 후 사용자가 선언

---

## Rollback (되돌림 계획)

가역이다. 본 변경은 **기존 동작을 바꾸지 않는다** — 추가 항목은 전부 기본 비활성이라,
설정을 손대지 않으면 판정 결과가 이전과 같다.

1. 코드 되돌림: 해당 커밋 revert. 다른 패키지가 import 하지 않으므로 파급 0.
2. 설정: `expected_processes`·CAN 임계를 지우면 판정이 다시 꺼진다.
3. 기록 스키마: `can`·`dds_segments`·`process_*` 키가 추가되지만, 소비자(`report`·`webview`)는
   키 부재를 이미 견디도록 만들어져 있어 구버전 로그도 그대로 읽힌다.

비가역 요소 없음 — 시스템 설정·펌웨어·외부 상태 변경 0.
