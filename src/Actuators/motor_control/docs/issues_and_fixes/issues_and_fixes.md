# 이슈 및 수정 기록 (Issues and Fixes)

---

## 2026-07-26

### [Fix] motor_control 리뷰 지적 4건 수정 (E-stop 안전 2 · 브링업 누수 1 · 테스트 레이스 1)

- **문제**: 이식된 `src/Actuators/motor_control/` 코드 리뷰([docs/code_review/motor_control/2026-07-26.md](../code_review/motor_control/2026-07-26.md), Verdict REQUEST CHANGES) High 1·Medium 3. ① `test_cold_bringup_allowed_with_permission` 이 이 Jetson(ARM)에서 8/8 결정적 실패(x86 원격은 통과). ② E-stop 중 조향축이 계속 지령받아 정지 상태에서 물리 스윙 가능. ③ 브링업 예외 시 CAN 버스·rclpy 컨텍스트 누수. ④ E-stop 중 도착한 cmd_vel 이 해제 직후 급발진.
- **원인**: ① `_tx_loop`(backend.py:258)이 생성하는 조향 write 를 tx 데몬 스레드 기동 전에 테스트가 단언 — 스케줄링 레이스(`test_backend.py:126`). ② `_tx_loop`(backend.py:257-259)가 조향 setpoint 를 `_estop` 무관하게 무조건 송신. ③ `main`(driver_node.py:206)의 `node = MotorControlNode()` 가 try/finally 밖 + `__init__` 이 버스 개방(72) 후 `start()`(83) 예외 시 정리 없음. ④ `set_command`(backend.py:131)이 `_estop` 미확인.
- **해결**: ① 테스트를 tx 첫 write 폴링 대기(≤1s)로 견고화(+회귀 테스트 2건 추가). ② `_tx_loop` 에 `estopped` 캡처 후 E-stop 시 조향 setpoint 송신 `continue`(현 위치 hold, 설계문서 §5-4 step-cut 정렬). ③ `__init__` start() 를 try 로 감싸 실패 시 `backend.shutdown()`(버스 close) 재-raise + `main()` 노드 생성 실패 시 `rclpy.shutdown()`. ④ `set_command` 진입부 `if self._estop: return`. (backend.py +5줄, driver_node.py +8줄, test_backend.py +42줄)
- **파일**: `src/Actuators/motor_control/motor_control/backend.py`, `.../motor_control/driver_node.py`, `.../test/test_backend.py` (병기: `src/Actuators/motor_control/docs/code_review/motor_control/2026-07-26.md` findings 상태 [해결])
- **상태**: 로컬 완료 · 원본 반영 **부분(검증 보류)** — 로컬 **31 passed**(원본 29 + 신규 2), 레이스 테스트 8/8 PASS(Jetson), AST 정상. ⚠ 원본과 바이트 동일했던 코드에 **의도적 divergence**. 원본 `amap@amap-2:.../T-Driver-Analysis/src/Motor_Control/` 에 3파일 **rsync 전송 성공**(backend.py·driver_node.py·test_backend.py)했으나, 직후 amap-2 **SSH 도달 불가(오프라인)** 로 원격 pytest 검증·원격 doc 기록·git commit **미완**. 재개 시: (1) 원격 `python3 -m pytest test -q` 31 passed 확인, (2) 원격 docs/issues_and_fixes 동일 기록, (3) 협업 모드 확인 후 commit.

> ⚠ **좌표 주의 (부기 2026-07-27b — 위 기록은 무변경)**: 위 **원인** 절의 코드 좌표
> (`backend.py:258` · `:257-259` · `:131`, `driver_node.py:206`, `test_backend.py:126`)는 **2026-07-26 수정 시점 기준**이며 현재는 맞지 않는다.
> 해당 소스는 그 뒤로도 계속 편집돼 같은 2026-07-27 세션 안에서 `backend.py` 494 → 549 → **635줄**, `driver_node.py` 296 → 364 → **424줄** 로 늘었다(`wc -l`).
> 수정 **내용**(`_tx_loop` 의 E-stop 시 조향 setpoint 송신 중단, `set_command` 진입부 `if self._estop: return` 등)은 현행 코드에 그대로 남아 있으므로 **판정은 유효**하다.
> 재확인할 때는 줄번호가 아니라 **함수명 + 원문 문구**로 찾을 것.

### [Diag] emulate 내구 중 Seer 52954(zeroing/재호밍 timeout) 1회 — zeroDI 하드웨어 아님, 기동 전환 트랜지언트로 추정

- **문제**: `emulate_endurance.py` 내구(2026-07-26 09:05~13:00, emulate firmware, engage180s/diseng5s) 중 Seer API 1050 알람에 **52954 "Motor calibration/zeroing timeout"(ERROR) 1회**(desc 09:29:19). 재호밍(원점복귀) 타임아웃.
- **원인**: [실측·증거] appendix 002 매뉴얼의 일반원인(zeroDI 원점스위치 손상/오설치)은 **이 런 증거로 미지지**. 실제 인과사슬 = **첫 engage 전환(09:08) 순간 emulate 인수 전 수초 모터 통신 순단** → Seer가 모터침묵 감지(동시각 52111 motor timeout·52106 odo lost·54022 stuff, `seermon_endur.log` 09:08:42~43) → 자동 재호밍(54301 calibrating) 시작 → **emulate 경로가 실 원점센서(zeroDI) 피드백 미제공** → 시작+약20분 뒤 zeroing 카운트다운 만료로 52954(09:29). 09:29 시점 판다측 모터응답 정상(endur cyc7/8 급감0)=신규 통신갭 아님=09:08 zeroing의 종착점. 이후 59사이클 급감0·무재발. 근거모델: `docs/can_relay/field-record-orin-nx-2026-07-25.md:47,137`(모터응답/guard 상실=재호밍 방아쇠).
- **해결**: [미확정·검증대기] 코드 변경 없음. zeroDI 하드웨어 고장 가설 배제 위해 **실로봇 전원사이클 재현**(emulate 없이 실 Seer 재기동 → zeroing 정상완료=52954 미발생 확인) 예정. 정상완료 시 "emulate 기동 전환 트랜지언트"로 확정, 재발 시 실 zeroDI 점검. ⚠안전: Seer 전원복구=조향 물리 재호밍 동반(field-record §5-4), 가동범위 주변 클리어 후 수행.
- **파일**: (분석) `~/docking_reliability/seermon_endur.log`, `~/docking_reliability/endur_out.log`, `T-Robot_seer_gui/references/seer/robokit-api/appendix/002-alarm-code.md:183`; (재현도구) `~/Project/CAN-Relay/docking_field_kit/seer_powercycle_repro.py`(신규 작성·검증)
- **상태**: 진단 완료 · **재현검증 미실시(다음 세션 재개 필요)**. 내구는 76사이클 완주 PASS(모터급감 0, `endur_out.log` 13:00:12 종료요약). 전원사이클 재현 모니터 2회 기동(13:01·14:52, 각 10분 창)했으나 **양 창 모두 실 전원 OFF→ON 미수행**으로 zeroDI 하드웨어 가설 확정/배제 못함. **재개 절차**: (안전-조향 재호밍 물리이동 주변 클리어) → `python3 ~/Project/CAN-Relay/docking_field_kit/seer_powercycle_repro.py 192.168.44.82 600` 실행 후 Seer 전원 OFF→수초→ON → 판정(zeroing 완료=배제 / 52954 재발=하드웨어).

---

## 2026-07-24

### [Fix] amap-2 현장 CAN 버스 단절오류 다발 — Seer 끝 종단저항(120Ω) 누락

- **문제**: 실 로봇 Foil_A082에서 CAN1(모터) 버스에러 다발(2026-07-23 23:13~24 01:05, 1h52m). Seer 알람 54022(Ack 250·Bit Recessive 183·Bit Dominant 104·Stuff 7 = 544회), 52111 모터 응답타임아웃(4개 동시 302회), 52106 odo lost 408회, 54301 재캘리 347회. 로봇 정지 중 발생, 수 초 내 자동복구 반복. Seer는 "check CAN router"만 지목, 원인 특정 못함. 판다측 모니터도 트래픽만 봐서 못 잡음.
- **원인**: **CAN 버스 종단이 모터(Tongyi) 끝 120Ω 하나뿐 = under-termination.** Seer 끝(DB9 2·7번=CAN_L/H) 종단 **없음**(실측 51.6kΩ 개방). 개방단 신호반사 → Bit/Ack/Stuff 에러. 판다는 온보드 종단이 없음(CAN0 pin4·5 / CAN2 pin23·24 실측 개방) — 문서 `Tools/docking_field_kit/PINMAP.md:50`의 "CAN2 온보드 120Ω 내장"은 오기였음(초기 혼선 원인).
- **해결**: **Seer 끝(DB9 2–7번)에 120Ω 종단저항 1개 추가** → 전체 60Ω(양단 120Ω) 정상화. PINMAP.md 종단 문구를 실측대로 정정(판다 종단 없음·Seer끝 120 필수·도킹시 스위칭종단 필요 명시).
- **파일**: `Tools/docking_field_kit/PINMAP.md`(정정), (하드웨어) Seer DB9 종단 120Ω 추가
- **상태**: 완료(판다측 검증) — 종단 60Ω 확인 후 라이브 트래픽 12s(33,278프레임·2,773fps)에서 판다 CAN 에러 전부 0(can_rx/send/fwd_errs Δ0, faults 0). **잔여 확증**: Seer 자체 로그 지속 무에러(수시간~밤샘 관찰) + per-bus 에러카운터(can_health) 위한 펌웨어 보강 예정.

---

## 2026-07-04

### [Fix] python 훅 전체가 한국어 Windows(cp949) 콘솔에서 UnicodeEncodeError 로 조용히 실패

- **문제**: `.claude/settings.json` 에 등록된 python reminder 훅들이 실제 런타임에서 출력 없이 실패 — 게이트 컨텍스트(user_instruction·debt·git_workflow 등)가 세션에 주입되지 않음. kuks_claude_agent_setup 업데이트(git_workflow v1.4.0) 설치 스모크 테스트 중 발견.
- **원인**: Windows 에서 stdout 이 파이프일 때 python 기본 인코딩이 cp949 — 훅 출력의 em-dash(U+2014) 등 cp949 비수록 문자가 `UnicodeEncodeError` 유발. 예: `docs/claude_guideline/git_workflow/hooks/git_workflow-reminder.py:128` 의 `print(DIRECTIVE ...)` (`[GIT-WORKFLOW SOP — 강제 게이트]` 헤더 18번째 문자). 구버전 훅에도 동일 문자 존재 → 신버전 회귀가 아닌 기존 잠재 버그. 검증: 기본 환경에서 user_instruction(exit=1)·debt(exit=1)·git_workflow(crash) 재현.
- **해결**: `.claude/settings.json` 최상위에 `"env": {"PYTHONUTF8": "1"}` 추가 (4줄 추가). 훅 파일은 저장소 원본과 동일하게 유지(diff 0) — 프로젝트 환경 레벨에서 UTF-8 모드 일괄 적용. 세션 재시작 후 발효.
- **파일**: `.claude/settings.json`
- **상태**: 완료 — 등록 훅 10종 전부 `PYTHONUTF8=1` 환경에서 exit=0 확인 (reminder 8종 + git_workflow track·stage-gate). 업스트림(kuks_claude_agent_setup) 훅에 `sys.stdout.reconfigure(encoding="utf-8")` 추가 또는 install.sh 의 settings env 등록 권고.
