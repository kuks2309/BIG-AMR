const int VOLKSWAGEN_MQB_MAX_STEER = 300;
const int VOLKSWAGEN_MQB_MAX_RT_DELTA = 75;
const uint32_t VOLKSWAGEN_MQB_RT_INTERVAL = 250000;
const int VOLKSWAGEN_MQB_MAX_RATE_UP = 4;
const int VOLKSWAGEN_MQB_MAX_RATE_DOWN = 10;
const int VOLKSWAGEN_MQB_DRIVER_TORQUE_ALLOWANCE = 80;
const int VOLKSWAGEN_MQB_DRIVER_TORQUE_FACTOR = 3;

#define MSG_ESP_19      0x0B2
#define MSG_LH_EPS_03   0x09F
#define MSG_ESP_05      0x106
#define MSG_TSK_06      0x120
#define MSG_MOTOR_20    0x121
#define MSG_HCA_01      0x126
#define MSG_GRA_ACC_01  0x12B
#define MSG_LDW_02      0x397

const CanMsg VOLKSWAGEN_MQB_TX_MSGS[] = {{MSG_HCA_01, 0, 8}, {MSG_GRA_ACC_01, 0, 8}, {MSG_GRA_ACC_01, 2, 8}, {MSG_LDW_02, 0, 8}};
#define VOLKSWAGEN_MQB_TX_MSGS_LEN (sizeof(VOLKSWAGEN_MQB_TX_MSGS) / sizeof(VOLKSWAGEN_MQB_TX_MSGS[0]))

AddrCheckStruct volkswagen_mqb_addr_checks[] = {
  {.msg = {{MSG_ESP_19, 0, 8, .check_checksum = false, .max_counter = 0U,  .expected_timestep = 10000U}, { 0 }, { 0 }}},
  {.msg = {{MSG_LH_EPS_03, 0, 8, .check_checksum = true,  .max_counter = 15U, .expected_timestep = 10000U}, { 0 }, { 0 }}},
  {.msg = {{MSG_ESP_05, 0, 8, .check_checksum = true,  .max_counter = 15U, .expected_timestep = 20000U}, { 0 }, { 0 }}},
  {.msg = {{MSG_TSK_06, 0, 8, .check_checksum = true,  .max_counter = 15U, .expected_timestep = 20000U}, { 0 }, { 0 }}},
  {.msg = {{MSG_MOTOR_20, 0, 8, .check_checksum = true,  .max_counter = 15U, .expected_timestep = 20000U}, { 0 }, { 0 }}},
};
#define VOLKSWAGEN_MQB_ADDR_CHECKS_LEN (sizeof(volkswagen_mqb_addr_checks) / sizeof(volkswagen_mqb_addr_checks[0]))
addr_checks volkswagen_mqb_rx_checks = {volkswagen_mqb_addr_checks, VOLKSWAGEN_MQB_ADDR_CHECKS_LEN};

uint8_t volkswagen_crc8_lut_8h2f[256];

static uint32_t volkswagen_mqb_get_checksum(CANPacket_t *to_push) {
  return (uint8_t)GET_BYTE(to_push, 0);
}

static uint8_t volkswagen_mqb_get_counter(CANPacket_t *to_push) {

  return (uint8_t)GET_BYTE(to_push, 1) & 0xFU;
}

static uint32_t volkswagen_mqb_compute_crc(CANPacket_t *to_push) {
  int addr = GET_ADDR(to_push);
  int len = GET_LEN(to_push);

  uint8_t crc = 0xFFU;
  for (int i = 1; i < len; i++) {
    crc ^= (uint8_t)GET_BYTE(to_push, i);
    crc = volkswagen_crc8_lut_8h2f[crc];
  }

  uint8_t counter = volkswagen_mqb_get_counter(to_push);
  switch(addr) {
    case MSG_LH_EPS_03:
      crc ^= (uint8_t[]){0xF5,0xF5,0xF5,0xF5,0xF5,0xF5,0xF5,0xF5,0xF5,0xF5,0xF5,0xF5,0xF5,0xF5,0xF5,0xF5}[counter];
      break;
    case MSG_ESP_05:
      crc ^= (uint8_t[]){0x07,0x07,0x07,0x07,0x07,0x07,0x07,0x07,0x07,0x07,0x07,0x07,0x07,0x07,0x07,0x07}[counter];
      break;
    case MSG_TSK_06:
      crc ^= (uint8_t[]){0xC4,0xE2,0x4F,0xE4,0xF8,0x2F,0x56,0x81,0x9F,0xE5,0x83,0x44,0x05,0x3F,0x97,0xDF}[counter];
      break;
    case MSG_MOTOR_20:
      crc ^= (uint8_t[]){0xE9,0x65,0xAE,0x6B,0x7B,0x35,0xE5,0x5F,0x4E,0xC7,0x86,0xA2,0xBB,0xDD,0xEB,0xB4}[counter];
      break;
    default:
      break;
  }
  crc = volkswagen_crc8_lut_8h2f[crc];

  return (uint8_t)(crc ^ 0xFFU);
}

static const addr_checks* volkswagen_mqb_init(uint16_t param) {
  UNUSED(param);

  gen_crc_lookup_table_8(0x2F, volkswagen_crc8_lut_8h2f);
  return &volkswagen_mqb_rx_checks;
}

static int volkswagen_mqb_rx_hook(CANPacket_t *to_push) {

  bool valid = addr_safety_check(to_push, &volkswagen_mqb_rx_checks,
                                 volkswagen_mqb_get_checksum, volkswagen_mqb_compute_crc, volkswagen_mqb_get_counter);

  if (valid && (GET_BUS(to_push) == 0U)) {
    int addr = GET_ADDR(to_push);

    if (addr == MSG_ESP_19) {
      int wheel_speed_fl = GET_BYTE(to_push, 4) | (GET_BYTE(to_push, 5) << 8);
      int wheel_speed_fr = GET_BYTE(to_push, 6) | (GET_BYTE(to_push, 7) << 8);

      vehicle_moving = (wheel_speed_fl + wheel_speed_fr) > 288;
    }

    if (addr == MSG_LH_EPS_03) {
      int torque_driver_new = GET_BYTE(to_push, 5) | ((GET_BYTE(to_push, 6) & 0x1FU) << 8);
      int sign = (GET_BYTE(to_push, 6) & 0x80U) >> 7;
      if (sign == 1) {
        torque_driver_new *= -1;
      }
      update_sample(&torque_driver, torque_driver_new);
    }

    if (addr == MSG_TSK_06) {
      int acc_status = (GET_BYTE(to_push, 3) & 0x7U);
      int cruise_engaged = ((acc_status == 3) || (acc_status == 4) || (acc_status == 5)) ? 1 : 0;
      if (cruise_engaged && !cruise_engaged_prev) {
        controls_allowed = 1;
      }
      if (!cruise_engaged) {
        controls_allowed = 0;
      }
      cruise_engaged_prev = cruise_engaged;
    }

    if (addr == MSG_MOTOR_20) {
      gas_pressed = ((GET_BYTES_04(to_push) >> 12) & 0xFFU) != 0U;
    }

    if (addr == MSG_ESP_05) {
      brake_pressed = (GET_BYTE(to_push, 3) & 0x4U) >> 2;
    }

    generic_rx_checks((addr == MSG_HCA_01));
  }
  return valid;
}

static int volkswagen_mqb_tx_hook(CANPacket_t *to_send, bool longitudinal_allowed) {
  UNUSED(longitudinal_allowed);

  int addr = GET_ADDR(to_send);
  int tx = 1;

  if (!msg_allowed(to_send, VOLKSWAGEN_MQB_TX_MSGS, VOLKSWAGEN_MQB_TX_MSGS_LEN)) {
    tx = 0;
  }

  if (addr == MSG_HCA_01) {
    int desired_torque = GET_BYTE(to_send, 2) | ((GET_BYTE(to_send, 3) & 0x3FU) << 8);
    int sign = (GET_BYTE(to_send, 3) & 0x80U) >> 7;
    if (sign == 1) {
      desired_torque *= -1;
    }

    bool violation = false;
    uint32_t ts = microsecond_timer_get();

    if (controls_allowed) {

      violation |= max_limit_check(desired_torque, VOLKSWAGEN_MQB_MAX_STEER, -VOLKSWAGEN_MQB_MAX_STEER);

      violation |= driver_limit_check(desired_torque, desired_torque_last, &torque_driver,
        VOLKSWAGEN_MQB_MAX_STEER, VOLKSWAGEN_MQB_MAX_RATE_UP, VOLKSWAGEN_MQB_MAX_RATE_DOWN,
        VOLKSWAGEN_MQB_DRIVER_TORQUE_ALLOWANCE, VOLKSWAGEN_MQB_DRIVER_TORQUE_FACTOR);
      desired_torque_last = desired_torque;

      violation |= rt_rate_limit_check(desired_torque, rt_torque_last, VOLKSWAGEN_MQB_MAX_RT_DELTA);

      uint32_t ts_elapsed = get_ts_elapsed(ts, ts_last);
      if (ts_elapsed > VOLKSWAGEN_MQB_RT_INTERVAL) {
        rt_torque_last = desired_torque;
        ts_last = ts;
      }
    }

    if (!controls_allowed && (desired_torque != 0)) {
      violation = true;
    }

    if (violation || !controls_allowed) {
      desired_torque_last = 0;
      rt_torque_last = 0;
      ts_last = ts;
    }

    if (violation) {
      tx = 0;
    }
  }

  if ((addr == MSG_GRA_ACC_01) && !controls_allowed) {

    if ((GET_BYTE(to_send, 2) & 0x9U) != 0U) {
      tx = 0;
    }
  }

  return tx;
}

static int volkswagen_mqb_fwd_hook(int bus_num, CANPacket_t *to_fwd) {
  int addr = GET_ADDR(to_fwd);
  int bus_fwd = -1;

  switch (bus_num) {
    case 0:

      bus_fwd = 2;
      break;
    case 2:
      if ((addr == MSG_HCA_01) || (addr == MSG_LDW_02)) {

        bus_fwd = -1;
      } else {

        bus_fwd = 0;
      }
      break;
    default:

      bus_fwd = -1;
      break;
  }

  return bus_fwd;
}

const safety_hooks volkswagen_mqb_hooks = {
  .init = volkswagen_mqb_init,
  .rx = volkswagen_mqb_rx_hook,
  .tx = volkswagen_mqb_tx_hook,
  .tx_lin = nooutput_tx_lin_hook,
  .fwd = volkswagen_mqb_fwd_hook,
};
