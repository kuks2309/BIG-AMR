# ADR 2026-07-28 — 전환 커버(`cover`) 타이머 랩어라운드 수정

## 상태

**Accepted — 2026-07-28 실기 플래시 완료.** 서명 md5 `d341d5d8e2a2c96a`, 실기=빌드 일치.
장기 재현(40분 방치)은 미수행 — 아래 §검증 참조.

## 맥락

`seer_gate_fwd_hook()` 의 커버 만료 판정이 **32비트 타이머 랩을 견디지 못한다.**

```c
uint32_t seer_cover_until_us = 0U;                                        // 마감시각(절대)
bool cover = ((int32_t)(seer_cover_until_us - microsecond_timer_get()) > 0);
```

`(int32_t)(deadline − now) > 0` 는 정상적인 wrap-safe 관용구지만, **전제조건은 `|deadline − now| < 2³¹`** 이다. 여기서는 마감시각이 `0xe8` 때 한 번 설정된 뒤 **재무장되지 않으므로** 그 전제가 반드시 깨진다.

### 타이머 사실 (1차 확인)

| 항목 | 값 | 근거 |
|---|---|---|
| `MICROSECOND_TIMER` | TIM2 (STM32F413 의 **32비트** 타이머) | `board/stm32fx/stm32fx_config.h` |
| 분주 | `PSC = APB1_FREQ − 1 = 47`, APB1 타이머클럭 48 MHz → **1 µs/tick** | `board/drivers/timers.h` |
| `ARR` | **쓰는 코드 0건** → 리셋값 `0xFFFFFFFF` | grep 전수 |
| 랩 주기 | 2³² µs = **4,294.97 s = 71.58 분** | 위에서 유도 |

### 결함의 크기 (시뮬레이션, C 의미론 재현)

`0xe8` 을 t0 에 1회 보내고 재무장하지 않은 채 한 랩 주기를 스캔:

| | 오판 구간 |
|---|---|
| 구 로직 | **4,295초 중 2,147초** — 정확히 절반. t0+35.80분부터 **35.79분간** `cover=true` |
| `0xe8` 미송신(`until=0`) | 부팅 후 35.8분부터 동일하게 거짓 참 |

`emulate = cover || pc_authority` 이므로 **`pc_authority=false`(투명 중계여야 할 구간)에서도** Seer→모터 SDO 쓰기가 전량 drop + 가짜 ack 되고 모터 실응답이 Seer 로 suppress 된다. Seer 는 명령이 성공했다고 믿지만 모터는 받은 적이 없다.

### 결정적 정황

upstream·벤더 safety 모드는 **전 11곳이 예외 없이** `get_ts_elapsed(now, last)`(`board/utils.h`)를 쓰고 매 수신마다 `last` 를 재무장한다. 랩 안전 관용구를 벗어난 곳은 자작 코드 이 한 줄뿐이었다.

## 결정

**마감시각(절대) 대신 시작시각 + armed 플래그(경과시간 비교)** 로 전환한다.

```c
uint32_t seer_cover_start_us = 0U;
bool seer_cover_armed = false;

/* 0xe8 (usb_comms.h) */
seer_cover_start_us = microsecond_timer_get();
seer_cover_armed = true;

/* seer_gate_fwd_hook() */
bool cover = false;
if (seer_cover_armed) {
  if (get_ts_elapsed(microsecond_timer_get(), seer_cover_start_us) < SEER_COVER_US) {
    cover = true;
  } else {
    seer_cover_armed = false;     /* 1회성 해제 — 재무장 전까지 다시 서지 않는다 */
  }
}
```

**핵심은 두 가지다.**

1. `get_ts_elapsed()` 는 무부호 뺄셈이라 랩을 그대로 통과한다. 경과시간이 2³² µs 를 넘지만 않으면 정확하고, 커버는 300 ms 라 여유가 4 자릿수 크다.
2. `armed` 가 만료 시 스스로 내려가므로 **한 번 만료한 커버는 재무장 전까지 절대 되살아나지 않는다.** 구 로직의 실패는 "만료가 상태로 남지 않은 것"이 근본 원인이었다.

`SEER_COVER_US`(300 ms) 값 자체는 변경하지 않았다.

## 검증

시뮬레이션은 `utils.h` 의 `get_ts_elapsed` 를 그대로 옮겨 C 의미론을 재현했다.

| 시나리오 | 결과 |
|---|---|
| A. `0xe8` 1회 후 한 랩 주기(71.6분) 스캔 | 구 로직 오판 **2,147초** → 신 로직 **0초** |
| B. `0xe8` 미송신 (`armed=false`) | `cover=true` **0회** (기대 0) |
| C. 타이머 랩 경계를 가로지르는 `0xe8` (`start = 2³²−100 ms`) | dt=0·50 ms·299.999 ms → true / 300 ms·400 ms → false — **랩 경계 정상 통과** |

- [x] 빌드 통과(`-Werror`), 30,204 B / 한도 49,152 B
- [x] 시뮬레이션 3종
- [x] 실기 플래시 + 서명 md5 대조 (`d341d5d8e2a2c96a`)
- [ ] **실기 장기 재현**: 판다를 40분 이상 무조작 방치 후 `pc_authority=false` 상태에서 bus0 에 판다 발신 `0x580+N` 프레임이 나타나지 않는지 스니핑 — 구 펌웨어라면 35.8분 지점부터 나타났어야 한다

## Rollback Plan

| 항목 | 내용 |
|---|---|
| 직전 실기 이미지 | `Tools/Can_Relay/fw_backups/panda.bin.signed.clamp_and_0xec_removed_2026-07-28_5caa5cff` (30,188 B, 서명 `5caa5cff5173e690`) |
| 오늘 변경 전 이미지 | `…/panda.bin.signed.device_2026-07-28_b31d6789` (30,268 B) — 속도 클램프·`0xec` 제거·본 수정 **전부 없는** 상태 |
| 되돌리는 법 | `flash_panda.py <대상 이미지>` 후 `0xd3`+`0xd4` 서명 md5 복귀 확인 |
| 되돌림 판단 기준 | 도킹 engage 직후 300 ms 커버가 동작하지 않아 Seer 52111/52106 이 재발하는 경우 |
| 부분 롤백 | 불가(펌웨어 단위) |
| 체인 전체 | `Tools/Can_Relay/fw_backups/README-2026-07-28.md` |

## 영향 범위

- **펌웨어**: `board/safety/safety_seer_gate.h`(전역 2개 교체 + 판정 6줄), `board/usb_comms.h`(`0xe8` 2줄). 잔존 `seer_cover_until_us` 참조 0건.
- **호스트**: 없음. `0xe8` 의 외부 규약(wValue 로 릴레이 전환)은 그대로다.
- **거동 변화**: 정상 운용(300 ms 이내)에서는 **차이 없다.** 달라지는 것은 마지막 `0xe8` 로부터 35.8분 이후 구간뿐이며, 그 구간이 바로 결함이었다.

## 참조

- 리뷰 결함 C1: `docs/code_review/can_relay_firmware/2026-07-28.md` §Critical (함수 #11 `seer_gate_fwd_hook`)
- 판정 충돌 기록: 같은 문서 §평가 머리말 — A6·A8 이 "관용구가 옳으므로 무결함"으로 판정한 것을 기각한 근거
