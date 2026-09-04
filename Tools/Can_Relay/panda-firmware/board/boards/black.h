
void black_enable_can_transceiver(uint8_t transceiver, bool enabled) {
  switch (transceiver){
    case 1U:
      set_gpio_output(GPIOC, 1, !enabled);
      break;
    case 2U:
      set_gpio_output(GPIOC, 13, !enabled);
      break;
    case 3U:
      set_gpio_output(GPIOA, 0, !enabled);
      break;
    case 4U:
      set_gpio_output(GPIOB, 10, !enabled);
      break;
    default:
      puts("Invalid CAN transceiver ("); puth(transceiver); puts("): enabling failed\n");
      break;
  }
}

void black_enable_can_transceivers(bool enabled) {
  for(uint8_t i=1U; i<=4U; i++){

    if((car_harness_status == HARNESS_STATUS_FLIPPED) ? (i == 3U) : (i == 1U)){
      black_enable_can_transceiver(i, true);
    } else {
      black_enable_can_transceiver(i, enabled);
    }
  }
}

void black_set_led(uint8_t color, bool enabled) {
  switch (color){
    case LED_RED:
      set_gpio_output(GPIOC, 9, !enabled);
      break;
     case LED_GREEN:
      set_gpio_output(GPIOC, 7, !enabled);
      break;
    case LED_BLUE:
      set_gpio_output(GPIOC, 6, !enabled);
      break;
    default:
      break;
  }
}

void black_set_gps_load_switch(bool enabled) {
  set_gpio_output(GPIOC, 12, enabled);
}

void black_set_usb_load_switch(bool enabled) {
  set_gpio_output(GPIOB, 1, !enabled);
}

void black_set_usb_power_mode(uint8_t mode) {
  bool valid = false;
  switch (mode) {
    case USB_POWER_CLIENT:
      black_set_usb_load_switch(false);
      valid = true;
      break;
    case USB_POWER_CDP:
      black_set_usb_load_switch(true);
      valid = true;
      break;
    default:
      puts("Invalid USB power mode\n");
      break;
  }
  if (valid) {
    usb_power_mode = mode;
  }
}

void black_set_gps_mode(uint8_t mode) {
  switch (mode) {
    case GPS_DISABLED:

      set_gpio_output(GPIOC, 12, 0);
      set_gpio_output(GPIOC, 5, 0);
      break;
    case GPS_ENABLED:

      set_gpio_output(GPIOC, 12, 1);
      set_gpio_output(GPIOC, 5, 1);
      break;
    case GPS_BOOTMODE:
      set_gpio_output(GPIOC, 12, 1);
      set_gpio_output(GPIOC, 5, 0);
      break;
    default:
      puts("Invalid GPS mode\n");
      break;
  }
}

void black_set_can_mode(uint8_t mode){
  switch (mode) {
    case CAN_MODE_NORMAL:
    case CAN_MODE_OBD_CAN2:
      if ((bool)(mode == CAN_MODE_NORMAL) != (bool)(car_harness_status == HARNESS_STATUS_FLIPPED)) {

        set_gpio_mode(GPIOB, 12, MODE_INPUT);
        set_gpio_mode(GPIOB, 13, MODE_INPUT);

        set_gpio_alternate(GPIOB, 5, GPIO_AF9_CAN2);
        set_gpio_alternate(GPIOB, 6, GPIO_AF9_CAN2);
      } else {

        set_gpio_mode(GPIOB, 5, MODE_INPUT);
        set_gpio_mode(GPIOB, 6, MODE_INPUT);

        set_gpio_alternate(GPIOB, 12, GPIO_AF9_CAN2);
        set_gpio_alternate(GPIOB, 13, GPIO_AF9_CAN2);
      }
      break;
    default:
      puts("Tried to set unsupported CAN mode: "); puth(mode); puts("\n");
      break;
  }
}

bool black_check_ignition(void){

  return harness_check_ignition();
}

void black_init(void) {
  common_init_gpio();

  set_gpio_alternate(GPIOA, 8, GPIO_AF11_CAN3);
  set_gpio_alternate(GPIOA, 15, GPIO_AF11_CAN3);

  set_gpio_mode(GPIOC, 0, MODE_ANALOG);
  set_gpio_mode(GPIOC, 3, MODE_ANALOG);

  current_board->set_gps_mode(GPS_ENABLED);

  set_gpio_mode(GPIOC, 10, MODE_OUTPUT);
  set_gpio_mode(GPIOC, 11, MODE_OUTPUT);
  set_gpio_output_type(GPIOC, 10, OUTPUT_TYPE_OPEN_DRAIN);
  set_gpio_output_type(GPIOC, 11, OUTPUT_TYPE_OPEN_DRAIN);
  set_gpio_output(GPIOC, 10, 1);
  set_gpio_output(GPIOC, 11, 1);

  black_set_gps_load_switch(true);

  black_set_usb_load_switch(true);

  black_set_usb_power_mode(USB_POWER_CDP);

  // debt-130: 이 보드(CAN RELAY R01/R02)에는 comma 하네스가 없다. SBU 핀(PC0=CAN3_EN, PC3=미연결)의
  // ADC 방향 판정은 부팅마다 흔들리며, FLIPPED 로 판정되면 can_flip_buses(0,2) 와
  // set_intercept_relay()(PC10 반전)가 릴레이·버스 제어를 깨뜨린다. 판정을 생략하고 NC 로 고정한다.
  // 릴레이(PC10)는 set_safety_mode() 의 push-pull 구동만이 제어한다.
  car_harness_status = HARNESS_STATUS_NC;

  rtc_init();

  black_enable_can_transceivers(true);

  black_set_led(LED_RED, false);
  black_set_led(LED_GREEN, false);
  black_set_led(LED_BLUE, false);

  black_set_can_mode(CAN_MODE_NORMAL);
}

const harness_configuration black_harness_config = {
  .has_harness = false,
  .GPIO_SBU1 = GPIOC,
  .GPIO_SBU2 = GPIOC,
  .GPIO_relay_SBU1 = GPIOC,
  .GPIO_relay_SBU2 = GPIOC,
  .pin_SBU1 = 0,
  .pin_SBU2 = 3,
  .pin_relay_SBU1 = 10,
  .pin_relay_SBU2 = 11,
  .adc_channel_SBU1 = 10,
  .adc_channel_SBU2 = 13
};

const board board_black = {
  .board_type = "Black",
  .harness_config = &black_harness_config,
  .has_gps = true,
  .has_hw_gmlan = false,
  .has_obd = true,
  .has_lin = false,
  .has_rtc_battery = false,
  .init = black_init,
  .enable_can_transceiver = black_enable_can_transceiver,
  .enable_can_transceivers = black_enable_can_transceivers,
  .set_led = black_set_led,
  .set_usb_power_mode = black_set_usb_power_mode,
  .set_gps_mode = black_set_gps_mode,
  .set_can_mode = black_set_can_mode,
  .usb_power_mode_tick = unused_usb_power_mode_tick,
  .check_ignition = black_check_ignition,
  .read_current = unused_read_current,
  .set_fan_power = unused_set_fan_power,
  .set_ir_power = unused_set_ir_power,
  .set_phone_power = unused_set_phone_power,
  .set_clock_source_mode = unused_set_clock_source_mode,
  .set_siren = unused_set_siren
};
