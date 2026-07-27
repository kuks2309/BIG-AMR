// *** Seer 게이트 safety 모드 (도킹 릴레이) + 전환 커버 (debt-002) ***
// bus0 = Seer, bus2 = 모터. pc_authority 시 Seer SDO 쓰기(0x601~604, 0x23/27/2B/2F) drop +
// 가짜 ack(0x580+N: 60 idxlo idxhi sub 0..) 합성, 읽기(0x40)·guard(RTR)·응답은 통과.
// 전환 커버(debt-002): 0xe8 engage 후 SEER_COVER_US 동안, 릴레이 스위치로 CAN2(모터)가 회복(~150ms)
//   하는 사이 판다가 캐시된 모터 응답으로 Seer read/guard/write에 대신 답해 Motor timeout(52111)/
//   odo lost(52106) 방지. Seer(CAN0)는 항상 판다 bus0에 연결, 정차 중이라 캐시값이 곧 정확값.
//   근거: docs/can_relay/field-record-orin-nx-2026-07-25.md §13, debt-002, PCAN make_seer_gate_hook 이식.
bool pc_authority = false;  // 0xe9 AUTH_SET: false=Seer 투명중계, true=PC 주도(게이트 ON)

#define SEER_COVER_US 300000U           // 전환 커버 지속(μs) = 300ms (engage/disengage 공통 고정)
uint32_t seer_cover_until_us = 0U;      // usb_comms.h 0xe8 시 설정(engage·disengage 모두)

#define SEER_CACHE_N 24                 // Seer 읽기객체 5*4node=20 + 여유
typedef struct {
  uint8_t valid;
  uint8_t node;
  uint16_t index;
  uint8_t sub;
  uint8_t data[8];
} seer_resp_cache_t;
seer_resp_cache_t seer_cache[SEER_CACHE_N];
uint8_t seer_guard_data[5][8];
uint8_t seer_guard_len[5] = {0};
uint8_t seer_guard_valid[5] = {0};

// *** 정지값 고정(freeze) — PC 구동을 Seer 에게 숨김 ***
// pc_authority(도킹/구동) engage 시점의 캐시(정차 상태)를 스냅샷으로 잡고, 구동 중 Seer 폴에
// 이 스냅샷을 고정 응답한다. → PC 가 모터를 실제 구동해 실위치(0x6064)·statusword 가 변해도
// Seer 는 engage 시점 "정지" 상태만 읽음 → 추종오차 0 → motor following warning(55602) 예방.
// release 시 해제하여 실시간 캐시로 복귀(Seer 직결 정상). 근거: docs/claude-mistake/2026-07-26-001.
seer_resp_cache_t seer_frozen[SEER_CACHE_N];
uint8_t seer_frozen_valid = 0U;

static void seer_send_bus0(uint32_t sndaddr, const uint8_t *d, uint8_t len) {
  CANPacket_t p;
  p.rtr = 0U; p.returned = 0U; p.rejected = 0U; p.extended = 0U;
  p.bus = 0U;
  p.addr = sndaddr;
  p.data_len_code = len;
  for (int i = 0; i < 8; i++) { p.data[i] = (i < (int)len) ? d[i] : 0U; }
  can_send(&p, 0U, true);
}

static void seer_cache_store_resp(CANPacket_t *r) {
  uint8_t cmd = r->data[0];
  if ((cmd != 0x43U) && (cmd != 0x47U) && (cmd != 0x4BU) && (cmd != 0x4FU)) { return; }
  uint8_t node = (uint8_t)(GET_ADDR(r) - 0x580);
  uint16_t index = (uint16_t)(r->data[1] | ((uint16_t)r->data[2] << 8));
  uint8_t sub = r->data[3];
  int match = -1;
  int free_slot = -1;
  for (int i = 0; i < SEER_CACHE_N; i++) {
    if (seer_cache[i].valid != 0U) {
      if ((seer_cache[i].node == node) && (seer_cache[i].index == index) && (seer_cache[i].sub == sub)) {
        match = i;
        break;
      }
    } else if (free_slot < 0) {
      free_slot = i;
    } else {
      // occupied slot with no match yet
    }
  }
  int slot = (match >= 0) ? match : free_slot;
  if (slot >= 0) {
    seer_cache[slot].valid = 1U;
    seer_cache[slot].node = node;
    seer_cache[slot].index = index;
    seer_cache[slot].sub = sub;
    for (int i = 0; i < 8; i++) { seer_cache[slot].data[i] = r->data[i]; }
  }
}

static void seer_freeze_snapshot(void) {
  // engage 시점의 캐시(정차값) 전량을 frozen 으로 복사. 이후 구동 중엔 이 값만 Seer 에 응답.
  for (int i = 0; i < SEER_CACHE_N; i++) {
    seer_frozen[i] = seer_cache[i];
  }
  seer_frozen_valid = 1U;
}

// 모션 노출 객체 — 이것만 정지 스냅샷으로 치환한다.
// 근거: 2026-07-27 Seer SDO 폴 12초 실측(bus0 0x601~604, cmd 0x40 인덱스 집계).
//   0x6064 위치        노드당 2718~2920회  → freeze 필수
//   0x6041 statusword  node3/4 300여·node1/2 66회 → freeze 필수 (구동 중 상태비트가 변함)
//   0x6078 전류        66회                → freeze 필수
//   0x606C 실속도      0회(Seer 미폴)      → 현재 죽은 분기지만 모션 노출 객체이므로 유지
//   0x603F error·0x6000 digital in 은 폴되나 모션 아님 → **freeze 금지**(실 고장은 Seer 가 봐야 함)
// ⚠ 정정 이력: 종전 소스에 0x6041 이 빠져 있었다. 그대로 두면 PC 구동 중 Seer 가 실제
//   statusword 변화를 보게 된다. 운영 기록(메모리 biguamr-motor-node4-sign-crab)의
//   {0x6064, 0x6078, 0x6041} 이 옳았고 실측으로 확정했다.
//   ADR: docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md
static bool seer_is_motion_obj(uint16_t index) {
  return (index == 0x6064U) || (index == 0x606CU) ||
         (index == 0x6078U) || (index == 0x6041U);
}

static void seer_cache_reply(int addr, CANPacket_t *req) {
  uint8_t node = (uint8_t)(addr - 0x600);
  uint16_t index = (uint16_t)(req->data[1] | ((uint16_t)req->data[2] << 8));
  uint8_t sub = req->data[3];
  // 수술적 freeze: 기본은 항상 실시간 캐시(Seer 응답 누락 0 → 타임아웃 회귀 불가).
  // pc_authority 중 '모션객체'만 engage 스냅샷(정지값)으로 치환 → 위치/속도만 정지로 보임.
  seer_resp_cache_t *chosen = NULL;
  for (int i = 0; i < SEER_CACHE_N; i++) {
    if ((seer_cache[i].valid != 0U) && (seer_cache[i].node == node) &&
        (seer_cache[i].index == index) && (seer_cache[i].sub == sub)) {
      chosen = &seer_cache[i];
      break;
    }
  }
  if ((pc_authority) && (seer_frozen_valid != 0U) && seer_is_motion_obj(index)) {
    for (int i = 0; i < SEER_CACHE_N; i++) {
      if ((seer_frozen[i].valid != 0U) && (seer_frozen[i].node == node) &&
          (seer_frozen[i].index == index) && (seer_frozen[i].sub == sub)) {
        chosen = &seer_frozen[i];
        break;
      }
    }
  }
  if (chosen != NULL) {
    seer_send_bus0((uint32_t)(0x580 + node), chosen->data, 8U);
  }
}

static void seer_fake_ack(int addr, CANPacket_t *req) {
  uint8_t d[8];
  d[0] = 0x60U;
  d[1] = req->data[1];
  d[2] = req->data[2];
  d[3] = req->data[3];
  d[4] = 0U; d[5] = 0U; d[6] = 0U; d[7] = 0U;
  seer_send_bus0((uint32_t)(0x580 + (addr - 0x600)), d, 8U);
}

static const addr_checks* seer_gate_init(uint16_t param) {
  UNUSED(param);
  controls_allowed = true;
  return &default_rx_checks;
}

static int seer_gate_tx_hook(CANPacket_t *to_send, bool longitudinal_allowed) {
  UNUSED(to_send);
  UNUSED(longitudinal_allowed);
  return true;  // PC 원발 CAN_TX 허용
}

static int seer_gate_tx_lin_hook(int lin_num, uint8_t *data, int len) {
  UNUSED(lin_num);
  UNUSED(data);
  UNUSED(len);
  return false;
}

static int seer_gate_fwd_hook(int bus_num, CANPacket_t *to_fwd) {
  int addr = GET_ADDR(to_fwd);
  int bus_fwd = -1;

  // pc_authority engage/release 에지 처리: engage 시 현 캐시(정차값)를 freeze,
  // release 시 해제(실시간 캐시 복귀). 한 번의 짧은 스냅샷 복사만 수행(ISR 부담 최소).
  static bool prev_pc_auth = false;
  if ((pc_authority) && (!prev_pc_auth)) {
    seer_freeze_snapshot();
  } else if ((!pc_authority) && (prev_pc_auth)) {
    seer_frozen_valid = 0U;
  } else {
    // 에지 없음
  }
  prev_pc_auth = pc_authority;

  // 캐시 갱신: 모터 응답(0x581~584)·guard 응답(0x701~704, rtr=0)을 어느 버스에서 보이든 최신 저장
  if ((addr >= 0x581) && (addr <= 0x584) && (to_fwd->rtr == 0U)) {
    seer_cache_store_resp(to_fwd);
  } else if ((addr >= 0x701) && (addr <= 0x704) && (to_fwd->rtr == 0U)) {
    uint8_t gn = (uint8_t)(addr - 0x700);
    uint8_t glen = (uint8_t)GET_LEN(to_fwd);
    if (glen > 8U) { glen = 8U; }
    for (int i = 0; i < 8; i++) { seer_guard_data[gn][i] = (i < (int)glen) ? to_fwd->data[i] : 0U; }
    seer_guard_len[gn] = glen;
    seer_guard_valid[gn] = 1U;
  } else {
    // no cache update
  }

  bool cover = ((int32_t)(seer_cover_until_us - microsecond_timer_get()) > 0);
  // 모범답안(모터 에뮬레이션) 지속: 전환 커버창(300ms) OR PC주도(도킹) 내내.
  // → 릴레이 작동 중 Seer 폴 전량을 캐시 모범답안으로 응답(Seer는 모터 상태·전환과 무관하게 만족).
  //   읽기/guard는 모터로도 forward해 모터를 계속 폴(살려둠)+캐시 신선도 유지. 쓰기는 가짜ack(PC/hold가 구동).
  //   모터 실응답은 캐시만 갱신하고 Seer로는 suppress(Seer는 캐시로 받음). auth=Seer(노드이동)은 투명 유지.
  bool emulate = cover || pc_authority;

  if (bus_num == 0) {  // Seer -> 모터
    if (emulate && (addr >= 0x601) && (addr <= 0x604) && (to_fwd->rtr == 0U)) {
      uint8_t cmd = to_fwd->data[0];
      if (cmd == 0x40U) {
        seer_cache_reply(addr, to_fwd);   // 읽기 → 캐시 모범답안 즉답
        bus_fwd = 2;                      // + 모터로도 폴 forward(모터 폴 유지·캐시 갱신)
      } else {
        seer_fake_ack(addr, to_fwd);      // 쓰기 → 가짜 ack
        bus_fwd = -1;                     // 모터로 안 보냄
      }
    } else if (emulate && (addr >= 0x701) && (addr <= 0x704) && (to_fwd->rtr != 0U)) {
      uint8_t gn = (uint8_t)(addr - 0x700);
      if (seer_guard_valid[gn] != 0U) {
        seer_send_bus0((uint32_t)(0x700 + gn), seer_guard_data[gn], seer_guard_len[gn]);
      }
      bus_fwd = 2;   // guard RTR도 모터로 forward(모터 guard 유지)
    } else {
      bus_fwd = 2;   // 투명(auth=Seer 노드이동, non-emulate)
    }
  } else if (bus_num == 2) {  // 모터 -> Seer
    if ((addr >= 0x600) && (addr <= 0x604)) {
      bus_fwd = -1;  // PC 명령 에코 차단
    } else if (emulate && (((addr >= 0x581) && (addr <= 0x584)) ||
                           ((addr >= 0x701) && (addr <= 0x704)))) {
      bus_fwd = -1;  // emulate 중: Seer는 캐시 모범답안으로 받음 → 실응답 suppress(캐시는 위서 갱신됨)
    } else {
      bus_fwd = 0;   // 투명: 모터 응답(0x580)·guard 응답(0x700) → Seer
    }
  } else {
    bus_fwd = -1;
  }
  return bus_fwd;
}

const safety_hooks seer_gate_hooks = {
  .init = seer_gate_init,
  .rx = default_rx_hook,
  .tx = seer_gate_tx_hook,
  .tx_lin = seer_gate_tx_lin_hook,
  .fwd = seer_gate_fwd_hook,
};
