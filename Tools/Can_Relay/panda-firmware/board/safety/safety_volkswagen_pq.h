const int VOLKSWAGEN_PQ_MAX_STEER = 300;
const int VOLKSWAGEN_PQ_MAX_RT_DELTA = 75;
const uint32_t VOLKSWAGEN_PQ_RT_INTERVAL = 250000;
const int VOLKSWAGEN_PQ_MAX_RATE_UP = 4;
const int VOLKSWAGEN_PQ_MAX_RATE_DOWN = 10;
const int VOLKSWAGEN_PQ_DRIVER_TORQUE_ALLOWANCE = 80;
const int VOLKSWAGEN_PQ_DRIVER_TORQUE_FACTOR = 3;

#define MSG_LENKHILFE_3 0x0D0
#define MSG_HCA_1       0x0D2
#define MSG_MOTOR_2     0x288
#define MSG_MOTOR_3     0x380
#define MSG_GRA_NEU     0x38A
#define MSG_BREMSE_1    0x1A0
#define MSG_LDW_1       0x5BE

const CanMsg VOLKSWAGEN_PQ_TX_MSGS[] = {{MSG_HCA_1, 0, 5}, {MSG_GRA_NEU, 0, 4}, {MSG_GRA_NEU, 2, 4}, {MSG_LDW_1, 0, 8}};
#define VOLKSWAGEN_PQ_TX_MSGS_LEN (sizeof(VOLKSWAGEN_PQ_TX_MSGS) / sizeof(VOLKSWAGEN_PQ_TX_MSGS[0]))

AddrCheckStruct volkswagen_pq_addr_checks[] = {
  {.msg = {{MSG_LENKHILFE_3, 0, 6, .check_checksum = true,  .max_counter = 15U, .expected_timestep = 10000U}, { 0 }, { 0 }}},
  {.msg = {{MSG_MOTOR_2, 0, 8, .check_checksum = false, .max_counter = 0U,  .expected_timestep = 20000U}, { 0 }, { 0 }}},
  {.msg = {{MSG_MOTOR_3, 0, 8, .check_checksum = false, .max_counter = 0U,  .expected_timestep = 10000U}, { 0 }, { 0 }}},
  {.msg = {{MSG_BREMSE_1, 0, 8, .check_checksum = false, .max_counter = 0U,  .expected_timestep = 10000U}, { 0 }, { 0 }}},
};
#define VOLKSWAGEN_PQ_ADDR_CHECKS_LEN (sizeof(volkswagen_pq_addr_checks) / sizeof(volkswagen_pq_addr_checks[0]))
addr_checks volkswagen_pq_rx_checks = {volkswagen_pq_addr_checks, VOLKSWAGEN_PQ_ADDR_CHECKS_LEN};

static uint32_t volkswagen_pq_get_checksum(CANPacket_t *to_push) {
  return (uint8_t)GET_BYTE(to_push, 0);
}

static uint8_t volkswagen_pq_get_counter(CANPacket_t *to_push) {

  return (uint8_t)(GET_BYTE(to_push, 1) & 0xF0U) >> 4;
}

static uint32_t volkswagen_pq_compute_checksum(CANPacket_t *to_push) {
  int len = GET_LEN(to_push);
  uint8_t checksum = 0U;

  for (int i = 1; i < len; i++) {
    checksum ^= (uint8_t)GET_BYTE(to_push, i);
  }

  return checksum;
}

static const addr_checks* volkswagen_pq_init(uint16_t param) {
  UNUSED(param);

  return &volkswagen_pq_rx_checks;
}

static int volkswagen_pq_rx_hook(CANPacket_t *to_push) {

  bool valid = addr_safety_check(to_push, &volkswagen_pq_rx_checks,
                                volkswagen_pq_get_checksum, volkswagen_pq_compute_checksum, volkswagen_pq_get_counter);

  if (valid && (GET_BUS(to_push) == 0U)) {
    int addr = GET_ADDR(to_push);

    if (addr == MSG_BREMSE_1) {
      int speed = ((GET_BYTE(to_push, 2) & 0xFEU) >> 1) | (GET_BYTE(to_push, 3) << 7);

      vehicle_moving = speed > 108;
    }

    if (addr == MSG_LENKHILFE_3) {
      int torque_driver_new = GET_BYTE(to_push, 2) | ((GET_BYTE(to_push, 3) & 0x3U) << 8);
      int sign = (GET_BYTE(to_push, 3) & 0x4U) >> 2;
      if (sign == 1) {
        torque_driver_new *= -1;
      }
      update_sample(&torque_driver, torque_driver_new);
    }

    if (addr == MSG_MOTOR_2) {
      int acc_status = (GET_BYTE(to_push, 2) & 0xC0U) >> 6;
      int cruise_engaged = ((acc_status == 1) || (acc_status == 2)) ? 1 : 0;
      if (cruise_engaged && !cruise_engaged_prev) {
        controls_allowed = 1;
      }
      if (!cruise_engaged) {
        controls_allowed = 0;
      }
      cruise_engaged_prev = cruise_engaged;
    }

    if (addr == MSG_MOTOR_3) {
      gas_pressed = (GET_BYTE(to_push, 2));
    }

    if (addr == MSG_MOTOR_2) {
      brake_pressed = (GET_BYTE(to_push, 2) & 0x1U);
    }

    generic_rx_checks((addr == MSG_HCA_1));
  }
  return valid;
}

static int volkswagen_pq_tx_hook(CANPacket_t *to_send, bool longitudinal_allowed) {
  UNUSED(longitudinal_allowed);

  int addr = GET_ADDR(to_send);
  int tx = 1;

  if (!msg_allowed(to_send, VOLKSWAGEN_PQ_TX_MSGS, VOLKSWAGEN_PQ_TX_MSGS_LEN)) {
    tx = 0;
  }

  if (addr == MSG_HCA_1) {
    int desired_torque = GET_BYTE(to_send, 2) | ((GET_BYTE(to_send, 3) & 0x7FU) << 8);
    desired_torque = desired_torque / 32;
    int sign = (GET_BYTE(to_send, 3) & 0x80U) >> 7;
    if (sign == 1) {
      desired_torque *= -1;
    }

    bool violation = false;
    uint32_t ts = microsecond_timer_get();

    if (controls_allowed) {

      violation |= max_limit_check(desired_torque, VOLKSWAGEN_PQ_MAX_STEER, -VOLKSWAGEN_PQ_MAX_STEER);

      violation |= driver_limit_check(desired_torque, desired_torque_last, &torque_driver,
        VOLKSWAGEN_PQ_MAX_STEER, VOLKSWAGEN_PQ_MAX_RATE_UP, VOLKSWAGEN_PQ_MAX_RATE_DOWN,
        VOLKSWAGEN_PQ_DRIVER_TORQUE_ALLOWANCE, VOLKSWAGEN_PQ_DRIVER_TORQUE_FACTOR);
      desired_torque_last = desired_torque;

      violation |= rt_rate_limit_check(desired_torque, rt_torque_last, VOLKSWAGEN_PQ_MAX_RT_DELTA);

      uint32_t ts_elapsed = get_ts_elapsed(ts, ts_last);
      if (ts_elapsed > VOLKSWAGEN_PQ_RT_INTERVAL) {
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

  if ((addr == MSG_GRA_NEU) && !controls_allowed) {

    if ((GET_BYTE(to_send, 2) & 0x3U) != 0U) {
      tx = 0;
    }
  }

  return tx;
}

static int volkswagen_pq_fwd_hook(int bus_num, CANPacket_t *to_fwd) {
  int addr = GET_ADDR(to_fwd);
  int bus_fwd = -1;

  switch (bus_num) {
    case 0:

      bus_fwd = 2;
      break;
    case 2:
      if ((addr == MSG_HCA_1) || (addr == MSG_LDW_1)) {

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

const safety_hooks volkswagen_pq_hooks = {
  .init = volkswagen_pq_init,
  .rx = volkswagen_pq_rx_hook,
  .tx = volkswagen_pq_tx_hook,
  .tx_lin = nooutput_tx_lin_hook,
  .fwd = volkswagen_pq_fwd_hook,
};
