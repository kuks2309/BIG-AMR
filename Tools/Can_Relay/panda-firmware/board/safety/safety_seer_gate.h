bool pc_authority = false;
// 안전 off 후 재engage 차단 래치 — 0xe9 주도권 재취득 시 해제.
bool relay_off_latched = false;

#define SEER_COVER_US 300000U
uint32_t seer_cover_start_us = 0U;
bool seer_cover_armed = false;

#define SEER_CACHE_N 24
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
uint8_t seer_guard_tgl[5] = {0};   // pc_authority 시 판다가 진행시키는 node guarding 토글(bit7)

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
  for (int i = 0; i < SEER_CACHE_N; i++) {
    seer_frozen[i] = seer_cache[i];
  }
  // node guarding 토글 위상을 모터 마지막값에서 이어받아 전환 순간 위상 점프를 막는다.
  for (int gn = 1; gn <= 4; gn++) {
    seer_guard_tgl[gn] = (uint8_t)(seer_guard_data[gn][0] & 0x80U);
  }
  seer_frozen_valid = 1U;
}

static bool seer_is_motion_obj(uint16_t index) {
  return (index == 0x6064U) || (index == 0x606CU) ||
         (index == 0x6078U) || (index == 0x6041U);
}

static void seer_cache_reply(int addr, CANPacket_t *req) {
  uint8_t node = (uint8_t)(addr - 0x600);
  uint16_t index = (uint16_t)(req->data[1] | ((uint16_t)req->data[2] << 8));
  uint8_t sub = req->data[3];
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

// node guarding 응답을 Seer(bus0)로 보낸다. pc_authority 면 판다가 토글(bit7)을 스스로
// 진행시켜 「살아있는 모터」를 emulate 하고, 그 외(cover 전환)면 캡처값 그대로 replay 한다.
static void seer_guard_reply(uint8_t gn) {
  if (seer_guard_valid[gn] == 0U) { return; }
  if (pc_authority) {
    seer_guard_tgl[gn] ^= 0x80U;
    uint8_t g[8];
    for (int i = 0; i < 8; i++) { g[i] = seer_guard_data[gn][i]; }
    g[0] = (uint8_t)((seer_guard_data[gn][0] & 0x7FU) | seer_guard_tgl[gn]);
    seer_send_bus0((uint32_t)(0x700 + gn), g, seer_guard_len[gn]);
  } else {
    seer_send_bus0((uint32_t)(0x700 + gn), seer_guard_data[gn], seer_guard_len[gn]);
  }
}

// 판다가 Seer 의 bus0 폴에 「가짜 모터」로 응답한다(모터로 전달할지는 fwd_hook 이 별도 결정).
static void seer_gate_emulate_bus0(int addr, CANPacket_t *req) {
  if ((addr >= 0x601) && (addr <= 0x604) && (req->rtr == 0U)) {
    if (req->data[0] == 0x40U) {
      seer_cache_reply(addr, req);
    } else {
      seer_fake_ack(addr, req);
    }
  } else if ((addr >= 0x701) && (addr <= 0x704) && (req->rtr != 0U)) {
    seer_guard_reply((uint8_t)(addr - 0x700));
  } else {
  }
}

static const addr_checks* seer_gate_init(uint16_t param) {
  UNUSED(param);
  controls_allowed = true;
  return &default_rx_checks;
}

static int seer_gate_tx_hook(CANPacket_t *to_send, bool longitudinal_allowed) {
  UNUSED(to_send);
  UNUSED(longitudinal_allowed);
  return true;
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

  static bool prev_pc_auth = false;
  if ((pc_authority) && (!prev_pc_auth)) {
    seer_freeze_snapshot();
  } else if ((!pc_authority) && (prev_pc_auth)) {
    seer_frozen_valid = 0U;
  } else {
  }
  prev_pc_auth = pc_authority;

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
  }

  bool cover = false;
  if (seer_cover_armed) {
    if (get_ts_elapsed(microsecond_timer_get(), seer_cover_start_us) < SEER_COVER_US) {
      cover = true;
    } else {
      seer_cover_armed = false;
    }
  }
  bool emulate = cover || pc_authority;

  // pc_authority(제어권 획득) 시 bus0↔bus2 포워딩을 끊어 Seer↔모터를 완전 분리한다
  // (Seer 대리응답은 유지). passthrough·전환커버(pc_authority=false)는 종전대로 브리지.
  if (bus_num == 0) {
    if (emulate) {
      seer_gate_emulate_bus0(addr, to_fwd);   // 판다가 가짜 모터로 Seer 에 응답
    }
    // 전달 결정: 완전분리(pc_authority)면 bus2 로 안 보냄. Seer 쓰기는 emulate 중 항상 drop(모터 보호).
    bool seer_write = emulate && (addr >= 0x601) && (addr <= 0x604) &&
                      (to_fwd->rtr == 0U) && (to_fwd->data[0] != 0x40U);
    bus_fwd = (seer_write || pc_authority) ? -1 : 2;
  } else if (bus_num == 2) {
    if ((addr >= 0x600) && (addr <= 0x604)) {
      bus_fwd = -1;
    } else if (emulate && (((addr >= 0x581) && (addr <= 0x584)) ||
                           ((addr >= 0x701) && (addr <= 0x704)))) {
      bus_fwd = -1;
    } else {
      bus_fwd = pc_authority ? -1 : 0;
    }
  } else {
    bus_fwd = -1;
  }
  return bus_fwd;
}

extern uint16_t current_safety_mode;
#define SEER_HOME_REQ_SAFETY_MODE 30U

#define SEER_HOME_NODE_LO   3U
#define SEER_HOME_NODE_HI   4U
#define SEER_HOME_NODE_CNT  2U
#define SEER_HOME_SPEED_DEF 2500U
#define SEER_HOME_SPEED_MIN 100U
#define SEER_HOME_SPEED_MAX 3000U
#define SEER_HOME_TIMEOUT_S 120U
#define SEER_HOME_POLL_DIV  2U

// ⚠ 이름에 ZERO 가 붙어 있으나 **이 값들은 조향 0° 가 아니다.** 이 파일 어디에도 0° 는 없다.
//   · 조향 0° 정본 = [7871815, 7840086]
//     (`src/Comm/CAN/can_relay/config/machine/foil_a082.yaml` `steer_home_counts`)
//   · 아래 두 상수는 **호밍 후 축이 자연히 멈추는 자리**(정착값)다. 0° 에서
//     node3 +10,205 counts = +0.178° · node4 +18,976 counts = +0.331° 떨어져 있다(57,344 counts/°).
//     호밍 10회 실측 정착값 7,882,021 / 7,859,065 근방에 재현성 있게 정착한다
//     (σ≈3 c, 최대 편차 6 c. **상수 적정성 자체는 실측 밖 — debt-016 소관**).
//   ⇒ 따라서 `SEER_HOME_GOZERO` 는 "0° 로 간다"가 아니라 "이 두 상수로 간다"이며,
//     이동 거리가 사실상 0 이라 **움직이지 않는 것을 「복귀했다」고 읽어 온 것**이다.
//     「호밍하면 조향이 0° 로 돌아온다」는 상수 이름에서 온 서술이지 동작에서 온 것이 아니다.
//   ⇒ 0° 로 보내려면 **호스트가 별도로 지령**해야 한다(can_relay `steer_to_zero()`).
//   ※ 이름 변경은 재플래시를 요구하고 상태 라벨(`test_link.py`)이 값에 묶여 있어
//     **값·이름은 그대로 두고 라벨만 정정**한다(라벨 정정 이력: 위 리뷰 #221·222).
#define SEER_HOME_ZERO_N3   7882020
#define SEER_HOME_ZERO_N4   7859062
#define SEER_HOME_PROF_VEL  30000U
#define SEER_HOME_PROF_ACC  250U
#define SEER_HOME_PROF_DEC  250U
// ⚠ 도달 판정 허용오차 = 57,344 counts = **정확히 1.000°**.
//   위 정착값과 0° 의 편차(0.178° / 0.331°)보다 5.6배 / 3.0배 크다 ⇒ 이 펌웨어는
//   **「0° 가 아니다」를 원리적으로 검출할 수 없다.** 항상 도달로 판정해 DONE 으로 넘어간다.
#define SEER_HOME_ZERO_TOL  57344
#define SEER_HOME_ZERO_TMO_S 30U
// 「이미 홈」 판정 대기(초). 이 시간 안에 bit15 하강이 없고 위치가 목표 허용오차 이내면
// 드라이브가 무동작 즉시 완료한 것으로 본다. 드라이브 기동 지연을 흡수할 만큼 넉넉해야 한다.
#define SEER_HOME_ATHOME_S   3U
#define SEER_HOME_CW_ENABLE 0x86U
#define SEER_HOME_CW_SETPOINT 0x3FU

#define SEER_HOME_IDLE      0U
#define SEER_HOME_ENABLE    1U
#define SEER_HOME_SET_SPEED 2U
#define SEER_HOME_START     3U
#define SEER_HOME_WAIT      4U
#define SEER_HOME_DONE      5U
#define SEER_HOME_ERR_TIMEOUT 6U
#define SEER_HOME_ERR_ABORT   7U
#define SEER_HOME_RESTORE   8U
#define SEER_HOME_GOZERO    9U
#define SEER_HOME_GOZERO_W  11U
#define SEER_HOME_ERR_GOZERO 10U

uint8_t seer_home_state = SEER_HOME_IDLE;
uint16_t seer_home_speed = SEER_HOME_SPEED_DEF;
uint16_t seer_home_elapsed_s = 0U;
uint8_t seer_home_tick_cnt = 0U;
uint8_t seer_home_poll_cnt = 0U;
uint8_t seer_home_seen_active = 0U;
uint8_t seer_home_done_mask = 0U;
uint8_t seer_home_reached_mask = 0U;
// 「이미 홈이라 무동작 즉시 완료」로 판정된 노드 비트마스크. 2026-08-03 실기 확정 대응.
uint8_t seer_home_athome_mask = 0U;

// ⚠ 이름이 zero_target 이지만 **0° 목표가 아니다** — 호밍 후 정착값을 돌려준다(위 :212-217 참조).
static int32_t seer_home_zero_target(uint8_t node) {
  return (node == SEER_HOME_NODE_LO) ? (int32_t)SEER_HOME_ZERO_N3 : (int32_t)SEER_HOME_ZERO_N4;
}

static void seer_send_bus2(uint32_t sndaddr, const uint8_t *d) {
  CANPacket_t p;
  p.rtr = 0U; p.returned = 0U; p.rejected = 0U; p.extended = 0U;
  p.bus = 2U;
  p.addr = sndaddr;
  p.data_len_code = 8U;
  for (int i = 0; i < 8; i++) { p.data[i] = d[i]; }
  can_send(&p, 2U, true);
}

static void seer_home_sdo_write(uint8_t node, uint16_t index, uint8_t sub,
                                uint32_t value, uint8_t size) {
  uint8_t d[8];
  uint8_t cmd;
  if (size == 1U) { cmd = 0x2FU; } else if (size == 2U) { cmd = 0x2BU; } else { cmd = 0x23U; }
  d[0] = cmd;
  d[1] = (uint8_t)(index & 0xFFU);
  d[2] = (uint8_t)((index >> 8) & 0xFFU);
  d[3] = sub;
  d[4] = (uint8_t)(value & 0xFFU);
  d[5] = (uint8_t)((value >> 8) & 0xFFU);
  d[6] = (uint8_t)((value >> 16) & 0xFFU);
  d[7] = (uint8_t)((value >> 24) & 0xFFU);
  seer_send_bus2((uint32_t)(0x600U + node), d);
}

static void seer_home_sdo_read(uint8_t node, uint16_t index, uint8_t sub) {
  uint8_t d[8];
  d[0] = 0x40U;
  d[1] = (uint8_t)(index & 0xFFU);
  d[2] = (uint8_t)((index >> 8) & 0xFFU);
  d[3] = sub;
  d[4] = 0U; d[5] = 0U; d[6] = 0U; d[7] = 0U;
  seer_send_bus2((uint32_t)(0x600U + node), d);
}

static bool seer_home_cached_sub(uint8_t node, uint16_t index, uint8_t sub, uint32_t *out) {
  for (int i = 0; i < SEER_CACHE_N; i++) {
    if ((seer_cache[i].valid != 0U) && (seer_cache[i].node == node) &&
        (seer_cache[i].index == index) && (seer_cache[i].sub == sub)) {
      *out = (uint32_t)seer_cache[i].data[4] |
             ((uint32_t)seer_cache[i].data[5] << 8) |
             ((uint32_t)seer_cache[i].data[6] << 16) |
             ((uint32_t)seer_cache[i].data[7] << 24);
      return true;
    }
  }
  return false;
}

static bool seer_home_cached(uint8_t node, uint16_t index, uint32_t *out) {
  return seer_home_cached_sub(node, index, 0U, out);
}

static uint8_t seer_home_digital_in(uint8_t node) {
  uint32_t v = 0U;
  return seer_home_cached_sub(node, 0x6000U, 0x01U, &v) ? (uint8_t)(v & 0xFFU) : 0xFFU;
}

static void seer_home_cancel_frames(void) {
  for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
    seer_home_sdo_write(n, 0x60FBU, 0x04U, 0U, 1U);
  }
}

static void seer_home_stage_reset(void) {
  seer_home_elapsed_s = 0U;
  seer_home_tick_cnt = 0U;
  seer_home_poll_cnt = 0U;
}

static bool seer_home_is_terminal(uint8_t st) {
  return (st == SEER_HOME_IDLE) || (st == SEER_HOME_DONE) ||
         (st == SEER_HOME_ERR_TIMEOUT) || (st == SEER_HOME_ERR_ABORT) ||
         (st == SEER_HOME_ERR_GOZERO);
}

bool seer_homing_cmd(bool start, uint16_t speed) {
  if (!start) {
    if (!seer_home_is_terminal(seer_home_state)) {
      seer_home_cancel_frames();
      seer_home_state = SEER_HOME_ERR_ABORT;
    } else {
      seer_home_state = SEER_HOME_IDLE;
    }
    return true;
  }
  if (!pc_authority) { return false; }
  if (current_safety_mode != SEER_HOME_REQ_SAFETY_MODE) { return false; }
  if (!seer_home_is_terminal(seer_home_state)) { return false; }
  if ((speed != 0U) && ((speed < SEER_HOME_SPEED_MIN) || (speed > SEER_HOME_SPEED_MAX))) {
    return false;
  }
  seer_home_speed = (speed == 0U) ? SEER_HOME_SPEED_DEF : speed;
  seer_home_stage_reset();
  seer_home_seen_active = 0U;
  seer_home_done_mask = 0U;
  seer_home_reached_mask = 0U;
  seer_home_athome_mask = 0U;
  seer_home_state = SEER_HOME_ENABLE;
  return true;
}

void seer_homing_tick(void) {
  if (seer_home_is_terminal(seer_home_state)) { return; }

  if ((!pc_authority) || (current_safety_mode != SEER_HOME_REQ_SAFETY_MODE)) {
    seer_home_cancel_frames();
    seer_home_state = SEER_HOME_ERR_ABORT;
    return;
  }

  switch (seer_home_state) {
    case SEER_HOME_ENABLE:
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        seer_home_sdo_write(n, 0x6040U, 0U, (uint32_t)SEER_HOME_CW_ENABLE, 2U);
      }
      seer_home_state = SEER_HOME_SET_SPEED;
      break;

    case SEER_HOME_SET_SPEED:
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        seer_home_sdo_write(n, 0x6099U, 0U, (uint32_t)seer_home_speed, 4U);
      }
      seer_home_state = SEER_HOME_START;
      break;

    case SEER_HOME_START:
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        seer_home_sdo_write(n, 0x60FBU, 0x04U, 1U, 1U);
      }
      seer_home_stage_reset();
      seer_home_state = SEER_HOME_WAIT;
      break;

    case SEER_HOME_WAIT:
      seer_home_poll_cnt++;
      if (seer_home_poll_cnt >= SEER_HOME_POLL_DIV) {
        seer_home_poll_cnt = 0U;
        for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
          seer_home_sdo_read(n, 0x6041U, 0U);
          seer_home_sdo_read(n, 0x6000U, 0x01U);
          seer_home_sdo_read(n, 0x6064U, 0U);   // 「이미 홈」 판정용
        }
      }
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        uint32_t sw = 0U;
        uint8_t bit = (uint8_t)(1U << (n - SEER_HOME_NODE_LO));
        if (seer_home_cached(n, 0x6041U, &sw)) {
          if ((sw & 0x8000U) == 0U) {
            seer_home_seen_active |= bit;
          } else if ((seer_home_seen_active & bit) != 0U) {
            seer_home_done_mask |= bit;
          } else {
          }
        }
      }
      // ── 「이미 홈」 처리 (2026-08-03 실기 확정) ─────────────────────────
      // Handbook V7.0 §4.6: "When the motor is already in the resetting position, the
      // resetting is triggered again, and the driver directly outputs the resetting end
      // signal." ⇒ 축이 이미 홈이면 드라이브가 **움직이지 않고 즉시 완료**하므로
      // 0x6041 bit15 가 1→0 으로 떨어지지 않는다. 위 에지 검출기만으로는 완료를 영영
      // 인정하지 못하고 120 s 타임아웃한다 — 2026-08-03 09:58 실기가 그렇게 실패했고,
      // 같은 날 14:46 축을 10° 떼어놓자 정상 완료(37.0 s)해 원인이 확정됐다.
      //   근거: docs/homing/2026-08-03-can-relay-homing-assets.md §15·§16 · debt-035
      //
      // ⚠ 단순 타임아웃으로 완료 처리하면 **드라이브가 RstStart 를 무시한 경우까지**
      //   완료로 오인해 GOZERO 로 축을 움직인다. 그래서 **위치를 확인한 경우에만** 인정한다:
      //     ① 개시 후 SEER_HOME_ATHOME_S 경과 (드라이브 기동 지연 흡수)
      //     ② 그 노드에서 bit15 하강을 **한 번도 못 봤다**(seen_active 비트 0)
      //     ③ 현재 bit15 = 1
      //     ④ 0x6064 가 GOZERO 목표의 SEER_HOME_ZERO_TOL 이내
      //   ④가 핵심이다 — 위치가 목표 밖이면 「이미 홈」이 아니므로 인정하지 않고
      //   기존대로 타임아웃까지 기다린다(안전 측 실패).
      if (seer_home_elapsed_s >= SEER_HOME_ATHOME_S) {
        for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
          uint8_t abit = (uint8_t)(1U << (n - SEER_HOME_NODE_LO));
          if (((seer_home_seen_active & abit) == 0U) &&
              ((seer_home_done_mask & abit) == 0U)) {
            uint32_t sw2 = 0U;
            uint32_t raw = 0U;
            if (seer_home_cached(n, 0x6041U, &sw2) && ((sw2 & 0x8000U) != 0U) &&
                seer_home_cached(n, 0x6064U, &raw)) {
              int32_t aerr = (int32_t)raw - seer_home_zero_target(n);
              if (aerr < 0) { aerr = -aerr; }
              if (aerr < (int32_t)SEER_HOME_ZERO_TOL) {
                seer_home_athome_mask |= abit;
              }
            }
          }
        }
      }

      if (seer_home_done_mask == ((1U << SEER_HOME_NODE_CNT) - 1U)) {
        seer_home_stage_reset();
        seer_home_state = SEER_HOME_RESTORE;
      } else if ((uint8_t)(seer_home_done_mask | seer_home_athome_mask) ==
                 ((1U << SEER_HOME_NODE_CNT) - 1U)) {
        // 전 노드가 「실제 호밍 완료」이거나 「이미 홈」이다.
        if (seer_home_done_mask == 0U) {
          // 아무 축도 움직이지 않았다 — 이미 전부 홈이므로 GOZERO 이동도 불필요하다.
          seer_home_reached_mask = seer_home_athome_mask;
          seer_home_state = SEER_HOME_DONE;
        } else {
          // 일부만 움직였다 — 두 축을 같은 목표로 맞추기 위해 기존 복귀 경로를 탄다.
          seer_home_stage_reset();
          seer_home_state = SEER_HOME_RESTORE;
        }
      } else {
        seer_home_tick_cnt++;
        if (seer_home_tick_cnt >= 8U) {
          seer_home_tick_cnt = 0U;
          seer_home_elapsed_s++;
          if (seer_home_elapsed_s >= SEER_HOME_TIMEOUT_S) {
            seer_home_cancel_frames();
            seer_home_state = SEER_HOME_ERR_TIMEOUT;
          }
        }
      }
      break;

    case SEER_HOME_RESTORE:
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        seer_home_sdo_write(n, 0x6060U, 0U, 1U, 1U);
        seer_home_sdo_write(n, 0x6081U, 0U, (uint32_t)SEER_HOME_PROF_VEL, 4U);
        seer_home_sdo_write(n, 0x6083U, 0U, (uint32_t)SEER_HOME_PROF_ACC, 4U);
        seer_home_sdo_write(n, 0x6084U, 0U, (uint32_t)SEER_HOME_PROF_DEC, 4U);
      }
      seer_home_state = SEER_HOME_GOZERO;
      break;

    // ⚠ 이름과 달리 0° 로 보내지 않는다 — SEER_HOME_ZERO_N3/N4(정착값)로 보낸다(:212-217).
    //   호밍 직후 축은 이미 그 근방이라 이동 거리가 사실상 0 이다.
    case SEER_HOME_GOZERO:
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        seer_home_sdo_write(n, 0x607AU, 0U, (uint32_t)seer_home_zero_target(n), 4U);
        seer_home_sdo_write(n, 0x6040U, 0U, (uint32_t)SEER_HOME_CW_SETPOINT, 2U);
      }
      seer_home_stage_reset();
      seer_home_state = SEER_HOME_GOZERO_W;
      break;

    case SEER_HOME_GOZERO_W:
      seer_home_poll_cnt++;
      if (seer_home_poll_cnt >= SEER_HOME_POLL_DIV) {
        seer_home_poll_cnt = 0U;
        for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
          seer_home_sdo_read(n, 0x6064U, 0U);
          seer_home_sdo_read(n, 0x6000U, 0x01U);
        }
      }
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        uint32_t raw = 0U;
        uint8_t bit = (uint8_t)(1U << (n - SEER_HOME_NODE_LO));
        if (seer_home_cached(n, 0x6064U, &raw)) {
          int32_t err = (int32_t)raw - seer_home_zero_target(n);
          if (err < 0) { err = -err; }
          if (err < (int32_t)SEER_HOME_ZERO_TOL) {
            seer_home_reached_mask |= bit;
          } else {
          }
        }
      }
      if (seer_home_reached_mask == ((1U << SEER_HOME_NODE_CNT) - 1U)) {
        seer_home_state = SEER_HOME_DONE;
      } else {
        seer_home_tick_cnt++;
        if (seer_home_tick_cnt >= 8U) {
          seer_home_tick_cnt = 0U;
          seer_home_elapsed_s++;
          if (seer_home_elapsed_s >= SEER_HOME_ZERO_TMO_S) {
            seer_home_state = SEER_HOME_ERR_GOZERO;
          }
        }
      }
      break;

    default:
      seer_home_state = SEER_HOME_ERR_ABORT;
      break;
  }
}

// 구동륜(node1,2)을 목표속도 0(0x60FF)으로 세운다 — PV 프로파일 감속.
#define SEER_DRIVE_NODE_LO 1U
#define SEER_DRIVE_NODE_HI 2U
void seer_stop_drives(void) {
  // 단발 SDO 유실 대비 각 노드 3회 발행.
  for (uint8_t rep = 0U; rep < 3U; rep++) {
    for (uint8_t n = SEER_DRIVE_NODE_LO; n <= SEER_DRIVE_NODE_HI; n++) {
      seer_home_sdo_write(n, 0x60FFU, 0U, 0U, 4U);
    }
  }
}

const safety_hooks seer_gate_hooks = {
  .init = seer_gate_init,
  .rx = default_rx_hook,
  .tx = seer_gate_tx_hook,
  .tx_lin = seer_gate_tx_lin_hook,
  .fwd = seer_gate_fwd_hook,
};
