# CAN Relay intercept 릴레이 미작동 근본 원인·해결 (open-drain → push-pull) — 2026-09-04

> debt-129(제어권 반환 시 재호밍)의 **릴레이 축** 근본 원인과 해결. 실측 검증.
> `board/main.c` 는 **git 미추적**이라(과거 add 안 됨) 여기에 변경을 보존한다 — 재적용 근거.

## 근본 원인 (실측 확정)

**릴레이(K1)가 engage 때 안 끊긴 진짜 이유 = `board/boards/black.h` 초기화가 릴레이 구동핀
PC10/PC11 을 open-drain 으로 설정** (`black.h:143-144` `set_gpio_output_type(GPIOC,10/11, OUTPUT_TYPE_OPEN_DRAIN)`).

- open-drain 은 LOW 로만 당기고 **HIGH 를 못 낸다**.
- 이 자작 보드 릴레이는 **active-high** (도면 `CAN RELAY R02.pdf`): `PC10 → R31(1K) → Q31(2N2222 NPN) 베이스`,
  `R33(10K) 베이스 풀다운`, `Q31 콜렉터 → K1 코일 → 5V`, `D3 플라이백`. 즉 **PC10 HIGH → Q31 ON → 릴레이 ON → K1 개방 → Seer↔모터 물리 절체**.
- 따라서 open-drain 이면 PC10 이 R33 풀다운에 눌려 **항상 LOW = 릴레이 영영 안 뜸.** (실측: 토글 펌웨어에서 PC10 핀 무변동)
- **하드웨어 결함이 아니라 펌웨어 설정 문제.** 보드 정상. (제조사 반품 불필요)

> comma 원본 `set_intercept_relay(true)` 는 핀을 `!intercept`=**LOW** 로 몰아 이 active-high 보드에선 릴레이 OFF — 극성도 반대.
> 통신핀 겹침 없음: black 에서 PC10 은 릴레이 전용(USART3 AF 는 white 만 설정), CAN 은 PB8/9·PA8/15·PB5/6.

## 해결

### 1) `board/main.c` — 릴레이 push-pull active-high 제어 (미추적 파일, 아래 코드로 재적용)

`set_safety_mode()` 의 case 에서 릴레이핀을 **push-pull 로** 두고 구동:

```c
case SAFETY_SEER_GATE:                       // engage = 릴레이 ON = 물리 절체(intercept)
  set_gpio_mode(GPIOC, 10, MODE_OUTPUT);
  set_gpio_output_type(GPIOC, 10, OUTPUT_TYPE_PUSH_PULL);
  set_gpio_output(GPIOC, 10, true);
  heartbeat_counter = 0U; ...

case SAFETY_SILENT:                          // release/idle = 릴레이 OFF = passthrough(fail-safe)
  set_gpio_mode(GPIOC, 10, MODE_OUTPUT);
  set_gpio_output_type(GPIOC, 10, OUTPUT_TYPE_PUSH_PULL);
  set_gpio_output(GPIOC, 10, false);
  set_intercept_relay(false); ...
```

(진단용 main-loop 토글 테스트 펌웨어: `for(cnt){ set_gpio_mode/output_type push_pull; set_gpio_output(GPIOC,10,cnt&1); }` — 릴레이 물리작동 소리/파형 확인용. 정본 아님.)

### 2) `board/safety/safety_seer_gate.h` — emulate (추적 파일, 커밋됨)

릴레이 절체로 모터가 격리되면 Seer 는 emulate 만 본다. Seer 재init/재호밍을 막으려면:
- **pos_act(0x6064) = Seer 가 명령한 목표(0x607A)** 로 되돌림 → following error 0 → Seer "완벽 홀드" 인식.
  (`seer_fake_ack` 에서 0x607A 캡처 → `seer_last_target[]`, `seer_cache_reply` 에서 조향 pos 를 그 값으로 서브)
- **freeze 시 목표=frozen pos 초기화** (engage 시작 창 정합).
- statusword 2슬롯 heartbeat replay + node-guarding 토글 생성(debt-127).

## 실측 결과 (4e002c)

| 단계 | release 재호밍 |
|---|---|
| open-drain(릴레이 안뜸) + 무송신 | 100% (0/4) |
| **push-pull 절체 + emulate pos=target + freeze init** | **~25% (3/4)** |

- engage 중 모터가 bus0 에서 **0.5초 후 완전 격리**(src0=0) 실측 — 릴레이 절체 성공.
- engage CAN 오류 40건 → 2건.
- 잔여 ~25% 는 간헐(미세 타이밍/레이스 추정). 클린 보드(51003b) 검증 권장.

## 상태
- 릴레이 미작동 **근본(open-drain) 해결** — push-pull 로 물리 절체 성립.
- 재호밍 100%→25% — 완전 0 은 잔여 타이밍 과제.
