# 새 세션 시작 프롬프트 (복붙용)

> 새 Claude Code 세션을 열고 아래 블록을 그대로 붙여넣으면 이어서 진행됩니다.
> (프로젝트 루트 `d:\kkw2\2026\Project\CATL-Ford\CAN-Relay` 에서 열 것.)

---

## ⛔ [2026-07-27 정정] 이 프롬프트를 **그대로 붙여넣지 말 것** ⛔

이 프롬프트는 **2026-07-23 기준**(본문 :11 "현재 상태(2026-07-23 저녁 확정)")이며, 그 이후 실차에서
아래 항목들이 **반증·보류**됐다. 배경을 모르는 새 세션이 이 블록을 그대로 받으면 곧장 실차
intercept·실모터 구동으로 유도된다.

| 프롬프트 항목 | 2026-07-27 판정 | 근거 |
| --- | --- | --- |
| 1) `monitor 30` | 유효(무개입 리슨) | field-record `:30` H0 ✅ |
| **2) `gate 30`** | ⛔ **보류** — intercept 전환이 Seer 리셋 유발(2026-07-25 인시던트) | `docs/can_relay/field-record-orin-nx-2026-07-25.md:31`, `:68-71` |
| **3) `gatecheck 30`** | ⛔ **보류** — 실차에서 Seer write 가 모터측으로 **누출**(차단 실패) | 같은 문서 `:33` |
| **4) `docking_drive.py` 실도킹** | ⛔ **보류** — 원인 규명 전까지 보류, 실 구동 전 사용자 확인 필수 | 같은 문서 `:56`, `:54`(실차 비안전) |
| 본문 "정상 position-hold" 단정 | ⚠ **미판정 모순** (아래 참조) | `docs/verified_facts/2026-07-27.md` §B-1 |
| 킷 경로 `~/Project/T-Robotics/...` | ❌ 현 장비에 없음 | `ls -d ~/Project/T-Robotics` → 없음 / 실제 경로 field-record `:11`, 정본 `Big-AMR/Tools/docking_field_kit/` |
| 펌웨어 `DEV-26524538` | 구버전 — 현행 빌드는 250 kbps 부팅 기본값+heartbeat fail-open 포함 | `Tools/Can_Relay/panda-firmware/board/obj/version`, ADR `2026-07-27-panda-boot-bitrate-and-failsafe.md` D1·D2 |

중대성: field-record `:49` — **Seer 는 리셋되면 복구 시 항상 재호밍 = 조향 물리 이동 동반(안전 직결).**

원문은 이력 보존을 위해 아래에 그대로 남긴다.

---

```
CATL-Ford CAN 릴레이 도킹 프로젝트를 이어서 진행합니다.

현재 상태(2026-07-23 저녁 확정):
- amap-2(현장)에 판다 #2(우리 펌웨어 DEV-26524538: RTR+릴레이분리+SEER_GATE)를 seer↔panda↔모터로 배선 완료, 실통신 활성 확인함.
  [2026-07-27 정정] DEV-26524538 은 구버전이다. 현행 빌드(Tools/Can_Relay/panda-firmware/board/obj/version 참조)에만 부팅 기본 250 kbps(board/drivers/can_common.h:174-176)와 heartbeat fail-open(board/main.c:257-258)이 들어있다(ADR 2026-07-27-panda-boot-bitrate-and-failsafe.md D1·D2). 킷 동봉 panda.bin.signed(2026-07-23)로 재플래시하지 말 것.
- Seer가 정차 중 steer(node3·4)에 target_position(0x607A=7871815/7840086)을 지속 지령함(관측). 작동이상 HOMING 모드 진입 0(검출기로 확인).
  [2026-07-27 정정] 이 목표값이 곧 "현재 위치(home)" 인지는 **미판정 모순**이다 — 따라서 "= 정상 position-hold" 로 단정하지 말 것.
  근거: docs/verified_facts/2026-07-27.md §B-1 (판다 read node3 ≈ -1,517 · node4 ≈ +1,161 counts vs Seer 1040 encoder -7,871,810/-7,840,091, 바퀴 육안 0° — 조향 노드에서만 7.87M counts(=137°) 어긋남, 어느 쪽인지 미판정),
  docs/ros2_driver/2026-07-09-design-inputs.md:56,81 (부팅 시 0x6064≈0 이 정상, 홈 상수는 절대 목표 steerOffset 137.3°, 매 기동 시 스윙 필요),
  verified_facts 사용 규칙 2 (§B 항목은 확정으로 인용하지 않는다),
  src/Actuators/motor_control/config/tongyi_amr.yaml:91 ("⚠ debt-007 판정 전까지 무비판 신뢰 금지").
  판정에 필요한 측정: intercept off 상태에서 판다로 조향 0x6064 를 다회 read + 동시각 Seer 1040 encoder 대조.
- amap-1에서 24h 신뢰성 테스트 연속 진행중(Run1·Run2 각 100%, 0실패). 러너 ~/run_reliability_loop.sh 가 24h마다 자동 반복.

먼저 Tools/docking_field_kit/HANDOFF-amap2.md 를 읽고, tailscale로 amap-2(ssh amap@amap-2) 접속해 판다 연결과 실통신을 재확인해줘.

오늘 할 일(현장, attended):
1) amap2_monitor.py monitor 30  — 실 통신 건전성 + Seer 지령 관측 재확인
2) [보류 2026-07-25] amap2_monitor.py gate 30      — intercept 전환이 실차 Seer 리셋 유발(field-record :31,:68-71). 실행 금지.
3) [보류 2026-07-25] amap2_monitor.py gatecheck 30 — 실차에서 Seer write 가 모터측으로 누출됨 = 차단 실패(field-record :33). 실행 금지.
4) [보류 2026-07-25] docking_drive.py 실도킹(take→enable→f 30→도킹→stop→release) — 원인 규명·사용자 승인 전까지 보류(field-record :56, :54). 실행 금지.
   ⇒ 2)~4) 를 진행하려면 먼저 전환 무중단화(커널 can-gw 수준) 확보 + 사용자 승인이 필요하다.

킷: amap-2 ~/Project/T-Robotics/T-Driver-Analysis/tools/docking_field_kit/ (본 저장소 Tools/docking_field_kit/ 와 동기).
   [2026-07-27 정정] 이 경로는 현 로봇 PC(Ford-CATL-orin-nx)에 없다. 실제 사본 = ~/Project/Ford-CATL-AMR/T-Driver-Analysis/tools/docking_field_kit/ · ~/Project/CAN-Relay/docking_field_kit/ (field-record-orin-nx-2026-07-25.md:11). 정본 = 저장소 Big-AMR/Tools/docking_field_kit/.
클론 핀맵 주의: CAN2_H=pin23(pin22 死핀). git 협업 모드 solo.
각 단계 실행·판정 결과를 보고하고, 실모터 구동(4번) 전에는 나에게 확인받고 진행해.
```

---

## 참고 — 이 프롬프트가 가리키는 핵심 파일
- `Tools/docking_field_kit/HANDOFF-amap2.md` — 상태·발견·절차 인수인계
- `Tools/docking_field_kit/amap2_monitor.py` — monitor/gate/gatecheck/seq
- `Tools/docking_field_kit/docking_drive.py` — 실 도킹 드라이버
- `Tools/docking_field_kit/PINMAP.md` · `RUNBOOK.md`
- `docs/can_relay/reliability-24h-results.md` — 24h 결과
