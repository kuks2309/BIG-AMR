# ADR 2026-07-28 — CAN 트랜스포트 추상화 + can-relay 제어경로 (Phase 1-5)

- Status: Accepted (Phase 1-5 구현). panda 백엔드(Phase 6-9)는 별도 승인·HIL 게이트 뒤.
- Date: 2026-07-28
- 관련: docs/adr/2026-07-09-relay-authority-arbitration.md, docs/claude-mistake/2026-07-27-002(node4 물리손상),
  4인 적대적 토론 워크플로 wf_3932eb0f-bed (안 B 채택)

## Context

`Tools/Kinematics/` 헤드리스 구동 스택이 CAN 인터페이스를 `can.Bus(interface="socketcan")` 로
**하드코딩**(direct_driver.py:98, relay_authority.py:135-136)하고 있어, (a) 다른 백엔드(PCAN(Peak CAN)
직결, comma.ai panda 하드웨어 릴레이)로 제어할 수 없고, (b) python-can 미설치인 개발기(tegra)에서
무-하드웨어 검증이 불가능하다. 후자는 **미검증 조향지령으로 node4 를 물리 손상**시킨 이력
(2026-07-27-002)이 요구하는 사전 검증 게이트를 막는다.

## Decision

4인 적대적 토론(정확성/단순성/안전/테스트성/공수 5축 채점)에서 **안 B(커스텀 CanTransport ABC)**
가 3인 전원 1~2위(총점 19/19.5/19)로 채택. 안 D의 arm/preflight 안전배리어와, 저장소에 이미
검증된 `Tools/amr_test_gui/amr_test_gui/panda_can_bus.py`(PandaCanBus, safety_mode 30 SEER_GATE)
재사용(안 C)을 접목한다. python-can 네이티브(안 A)는 tegra 미설치로 mock 불가·safety_mode 오설정
함정으로 기각. panda 1급 경로(안 C)는 engage 순단이 재호밍·물리 조향 이동을 유발한 이력으로 실험
플래그 뒤로 격리.

**3계층 분리**:
1. `can_protocol.py` — stdlib 전용 `@dataclass(frozen=True) CanFrame` + SDO 코덱. 현행 can.Message
   인코딩과 **바이트 동일**(리버스 엔지니어링 제1원칙). tegra 에서 단위테스트 가능.
2. `can_transport.py` — `CanTransport(ABC)` + 안전배리어 2종: `arm()/is_armed`(비무장 send→
   `TransportNotArmed`), `preflight()`(lib import·채널·비트레이트 검증, LOUD FAIL). 백엔드:
   `MockTransport`(정본 검증), `SocketCanTransport`/`PcanTransport`(python-can lazy import).
3. `authority.py` — 권한 축 분리. `RelayAuthority`→`KernelCangwAuthority`(개명, acquire 부분실패→
   무조건 롤백 + 멱등 release 로 기존 High 버그 봉인 + gate_off rc 확인으로 Medium 봉인), `NoAuthority`.

**Phase 1-5 범위**(본 ADR): 위 3계층 + DirectDriver 리팩터(transport 주입, `import can` 제거, run()
비무장 가드) + drive_headless 기본 dry-run(mock)/`--live` 게이트. panda 백엔드·실차 승급은 범위 밖.

## Consequences

- (+) tegra 에서 stdlib MockTransport 로 DirectDriver 전체(2단계 정렬·estop·enable)를 무-하드웨어
  결정론 검증 가능 → "정렬 확정 전 vel≠0 송출 금지"를 회귀테스트로 강제(node4 부류 차단).
- (+) 백엔드 교체가 spec 문자열(`socketcan:can1`/`pcan:...`/`mock`)로 국한. 하드코딩 3곳 제거.
- (+) 기존 High(주도권 영구상실)·Medium(gate_off 은폐) 결함 동반 수정.
- (−) CanFrame 재인코딩이 회귀 위험 도입 → **바이트 동일 대조 회귀테스트**로 상쇄.
- (−) `import can` 제거로 소비자 API 변경(DirectDriver(channel)→DirectDriver(transport)) →
  `from_channel()` 하위호환 팩토리로 완충.

## Rollback Plan

순수 추가/리팩터(영속 상태·스키마·펌웨어 변경 0). 되돌리려면 신규 파일(can_protocol.py·
can_transport.py·authority.py) 삭제 + direct_driver.py/drive_headless.py 를 커밋 `5854a9c` 로 복원
(`git checkout 5854a9c -- Tools/Kinematics/direct_driver.py Tools/Kinematics/drive_headless.py`).
relay_authority.py 는 호환 재-export 로 유지(삭제 시 import 회귀).

## Alternatives (기각)

- A python-can 네이티브 최소주의: tegra 미설치로 mock('virtual')조차 불가, node4 방지 게이트 비어 단독 채택 불가.
- C panda 1급 경로: 전환 순단→재호밍→물리 조향 이동 이력(FIELD-RECORD §14 '완전해결' 철회)과 안전 최우선축 충돌.
- D 전량 강제(frame-tap 등): 이식비용 최고(effort high), 실효 배리어(arm/preflight)만 선택 접목.

## 미해결 (측정 필요 — panda Phase 이전 게이트)

panda board SILENT tx 훅 원문 대조, 전환 무중단화 근거, pcan 인터페이스 정체(socketcan 경유 vs
PCANBasic 직결), CanFrame↔can.Message 바이트 동일 회귀 증명, KIN_NODE_XY 전/후 노드 귀속 미판정.
