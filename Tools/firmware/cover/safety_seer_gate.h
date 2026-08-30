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

static void seer_cache_reply(int addr, CANPacket_t *req) {
  uint8_t node = (uint8_t)(addr - 0x600);
  uint16_t index = (uint16_t)(req->data[1] | ((uint16_t)req->data[2] << 8));
  uint8_t sub = req->data[3];
  for (int i = 0; i < SEER_CACHE_N; i++) {
    if ((seer_cache[i].valid != 0U) && (seer_cache[i].node == node) &&
        (seer_cache[i].index == index) && (seer_cache[i].sub == sub)) {
      seer_send_bus0((uint32_t)(0x580 + node), seer_cache[i].data, 8U);
      break;
    }
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

  if (bus_num == 0) {  // Seer -> 모터
    if (cover && (addr >= 0x601) && (addr <= 0x604) && (to_fwd->rtr == 0U)) {
      // 커버 중: 모터 회복 대기 없이 캐시로 Seer에 즉답
      uint8_t cmd = to_fwd->data[0];
      if (cmd == 0x40U) {
        seer_cache_reply(addr, to_fwd);   // 읽기 → 캐시 응답
      } else {
        seer_fake_ack(addr, to_fwd);      // 쓰기 → 가짜 ack
      }
      bus_fwd = -1;  // 회복중 모터로 전달 안 함
    } else if (cover && (addr >= 0x701) && (addr <= 0x704) && (to_fwd->rtr != 0U)) {
      uint8_t gn = (uint8_t)(addr - 0x700);
      if (seer_guard_valid[gn] != 0U) {
        seer_send_bus0((uint32_t)(0x700 + gn), seer_guard_data[gn], seer_guard_len[gn]);
      }
      bus_fwd = -1;
    } else if (pc_authority && (addr >= 0x601) && (addr <= 0x604) && (to_fwd->rtr == 0U)) {
      uint8_t cmd = to_fwd->data[0];
      if ((cmd == 0x23U) || (cmd == 0x27U) || (cmd == 0x2BU) || (cmd == 0x2FU)) {
        seer_fake_ack(addr, to_fwd);   // Seer 쓰기 drop + 가짜 ack
        bus_fwd = -1;
      } else {
        bus_fwd = 2;   // 읽기 등 통과
      }
    } else {
      bus_fwd = 2;     // 평시/읽기/guard 통과
    }
  } else if (bus_num == 2) {  // 모터 -> Seer
    if ((addr >= 0x600) && (addr <= 0x604)) {
      bus_fwd = -1;  // PC 명령 에코 차단
    } else {
      bus_fwd = 0;   // 응답(0x580)·guard 응답(0x700) 통과
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
