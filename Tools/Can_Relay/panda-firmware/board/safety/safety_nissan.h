
const uint32_t NISSAN_RT_INTERVAL = 250000;

const struct lookup_t NISSAN_LOOKUP_ANGLE_RATE_UP = {
  {2., 7., 17.},
  {5., .8, .15}};

const struct lookup_t NISSAN_LOOKUP_ANGLE_RATE_DOWN = {
  {2., 7., 17.},
  {5., 3.5, .5}};

const int NISSAN_DEG_TO_CAN = 100;

const CanMsg NISSAN_TX_MSGS[] = {
  {0x169, 0, 8},
  {0x2b1, 0, 8},
  {0x4cc, 0, 8},
  {0x20b, 2, 6},
  {0x20b, 1, 6},
  {0x280, 2, 8}
};

AddrCheckStruct nissan_addr_checks[] = {
  {.msg = {{0x2, 0, 5, .expected_timestep = 10000U},
           {0x2, 1, 5, .expected_timestep = 10000U}, { 0 }}},
  {.msg = {{0x285, 0, 8, .expected_timestep = 20000U},
           {0x285, 1, 8, .expected_timestep = 20000U}, { 0 }}},
  {.msg = {{0x30f, 2, 3, .expected_timestep = 100000U},
           {0x30f, 1, 3, .expected_timestep = 100000U}, { 0 }}},
  {.msg = {{0x15c, 0, 8, .expected_timestep = 20000U},
           {0x15c, 1, 8, .expected_timestep = 20000U},
           {0x239, 0, 8, .expected_timestep = 20000U}}},
  {.msg = {{0x454, 0, 8, .expected_timestep = 100000U},
           {0x454, 1, 8, .expected_timestep = 100000U},
           {0x1cc, 0, 4, .expected_timestep = 10000U}}},
};
#define NISSAN_ADDR_CHECK_LEN (sizeof(nissan_addr_checks) / sizeof(nissan_addr_checks[0]))
addr_checks nissan_rx_checks = {nissan_addr_checks, NISSAN_ADDR_CHECK_LEN};

bool nissan_alt_eps = false;

static int nissan_rx_hook(CANPacket_t *to_push) {

  bool valid = addr_safety_check(to_push, &nissan_rx_checks, NULL, NULL, NULL);

  if (valid) {
    int bus = GET_BUS(to_push);
    int addr = GET_ADDR(to_push);

    if (((bus == 0) && (!nissan_alt_eps)) || ((bus == 1) && (nissan_alt_eps))) {
      if (addr == 0x2) {

        int angle_meas_new = (GET_BYTES_04(to_push) & 0xFFFFU);

        angle_meas_new = to_signed(angle_meas_new, 16) * 10;

        update_sample(&angle_meas, angle_meas_new);
      }

      if (addr == 0x285) {

        vehicle_speed = ((GET_BYTE(to_push, 2) << 8) | (GET_BYTE(to_push, 3))) * 0.005 / 3.6;
        vehicle_moving = vehicle_speed > 0.;
      }

      if ((addr == 0x15c) || (addr == 0x239)) {
        if (addr == 0x15c){
          gas_pressed = ((GET_BYTE(to_push, 5) << 2) | ((GET_BYTE(to_push, 6) >> 6) & 0x3U)) > 3U;
        } else {
          gas_pressed = GET_BYTE(to_push, 0) > 3U;
        }
      }
    }

    if ((addr == 0x454) || (addr == 0x239)) {
      if (addr == 0x454){
        brake_pressed = (GET_BYTE(to_push, 2) & 0x80U) != 0U;
      } else {
        brake_pressed = ((GET_BYTE(to_push, 4) >> 5) & 1U) != 0U;
      }
    }

    if ((addr == 0x30f) && (((bus == 2) && (!nissan_alt_eps)) || ((bus == 1) && (nissan_alt_eps)))) {
      bool cruise_engaged = (GET_BYTE(to_push, 0) >> 3) & 1U;

      if (cruise_engaged && !cruise_engaged_prev) {
        controls_allowed = 1;
      }
      if (!cruise_engaged) {
        controls_allowed = 0;
      }
      cruise_engaged_prev = cruise_engaged;
    }

    generic_rx_checks((addr == 0x169) && (bus == 0));
  }
  return valid;
}

static int nissan_tx_hook(CANPacket_t *to_send, bool longitudinal_allowed) {
  UNUSED(longitudinal_allowed);

  int tx = 1;
  int addr = GET_ADDR(to_send);
  bool violation = 0;

  if (!msg_allowed(to_send, NISSAN_TX_MSGS, sizeof(NISSAN_TX_MSGS) / sizeof(NISSAN_TX_MSGS[0]))) {
    tx = 0;
  }

  if (addr == 0x169) {
    int desired_angle = ((GET_BYTE(to_send, 0) << 10) | (GET_BYTE(to_send, 1) << 2) | ((GET_BYTE(to_send, 2) >> 6) & 0x3U));
    bool lka_active = (GET_BYTE(to_send, 6) >> 4) & 1U;

    desired_angle =  desired_angle - 131000;

    if (controls_allowed && lka_active) {

      float delta_angle_float;
      delta_angle_float = (interpolate(NISSAN_LOOKUP_ANGLE_RATE_UP, vehicle_speed) * NISSAN_DEG_TO_CAN) + 1.;
      int delta_angle_up = (int)(delta_angle_float);
      delta_angle_float =  (interpolate(NISSAN_LOOKUP_ANGLE_RATE_DOWN, vehicle_speed) * NISSAN_DEG_TO_CAN) + 1.;
      int delta_angle_down = (int)(delta_angle_float);
      int highest_desired_angle = desired_angle_last + ((desired_angle_last > 0) ? delta_angle_up : delta_angle_down);
      int lowest_desired_angle = desired_angle_last - ((desired_angle_last >= 0) ? delta_angle_down : delta_angle_up);

      violation |= max_limit_check(desired_angle, highest_desired_angle, lowest_desired_angle);
    }
    desired_angle_last = desired_angle;

    if ((!controls_allowed) &&
          ((desired_angle < (angle_meas.min - 1)) ||
          (desired_angle > (angle_meas.max + 1)))) {
      violation = 1;
    }

    if (!controls_allowed && lka_active) {
      violation = 1;
    }
  }

  if (addr == 0x20b) {

    violation |= ((GET_BYTE(to_send, 1) & 0x3dU) > 0U);
  }

  if (violation) {
    tx = 0;
  }

  return tx;
}

static int nissan_fwd_hook(int bus_num, CANPacket_t *to_fwd) {
  int bus_fwd = -1;
  int addr = GET_ADDR(to_fwd);

  if (bus_num == 0) {
    int block_msg = (addr == 0x280);
    if (!block_msg) {
      bus_fwd = 2;
    }
  }

  if (bus_num == 2) {

    int block_msg = ((addr == 0x169) || (addr == 0x2b1) || (addr == 0x4cc));
    if (!block_msg) {
      bus_fwd = 0;
    }
  }

  return bus_fwd;
}

static const addr_checks* nissan_init(uint16_t param) {
  nissan_alt_eps = param ? 1 : 0;
  return &nissan_rx_checks;
}

const safety_hooks nissan_hooks = {
  .init = nissan_init,
  .rx = nissan_rx_hook,
  .tx = nissan_tx_hook,
  .tx_lin = nooutput_tx_lin_hook,
  .fwd = nissan_fwd_hook,
};
