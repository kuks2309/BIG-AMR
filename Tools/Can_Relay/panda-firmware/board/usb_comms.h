#include "usb_protocol.h"
#include "health.h"

extern int _app_start[0xc000];

void set_safety_mode(uint16_t mode, uint16_t param);
bool is_car_safety_mode(uint16_t mode);

int get_health_pkt(void *dat) {
  COMPILE_TIME_ASSERT(sizeof(struct health_t) <= USBPACKET_MAX_SIZE);
  struct health_t * health = (struct health_t*)dat;

  health->uptime_pkt = uptime_cnt;
  health->voltage_pkt = adc_get_voltage();
  health->current_pkt = current_board->read_current();

  health->ignition_line_pkt = (uint8_t)(current_board->check_ignition());
  health->ignition_can_pkt = (uint8_t)(ignition_can);

  health->controls_allowed_pkt = controls_allowed;
  health->gas_interceptor_detected_pkt = gas_interceptor_detected;
  health->can_rx_errs_pkt = can_rx_errs;
  health->can_send_errs_pkt = can_send_errs;
  health->can_fwd_errs_pkt = can_fwd_errs;
  health->gmlan_send_errs_pkt = gmlan_send_errs;
  health->car_harness_status_pkt = car_harness_status;
  health->usb_power_mode_pkt = usb_power_mode;
  health->safety_mode_pkt = (uint8_t)(current_safety_mode);
  health->safety_param_pkt = current_safety_param;
  health->alternative_experience_pkt = alternative_experience;
  health->power_save_enabled_pkt = (uint8_t)(power_save_status == POWER_SAVE_STATUS_ENABLED);
  health->heartbeat_lost_pkt = (uint8_t)(heartbeat_lost);
  health->blocked_msg_cnt_pkt = blocked_msg_cnt;

  health->fault_status_pkt = fault_status;
  health->faults_pkt = faults;

  health->interrupt_load = interrupt_load;

  return sizeof(*health);
}

int get_can_health_pkt(void *dat, uint8_t bus) {
  COMPILE_TIME_ASSERT(sizeof(struct can_health_t) <= USBPACKET_MAX_SIZE);
  struct can_health_t * can_health = (struct can_health_t*)dat;
  uint32_t esr = 0U;

  if (bus < 3U) {
    uint8_t can_num = bus_config[bus].can_num_lookup;
    if (can_num < 3U) {
#ifndef STM32H7

      CAN_TypeDef *CAN = CANIF_FROM_CAN_NUM(can_num);
      esr = CAN->ESR;
#else

      UNUSED(can_num);
#endif
    }
  }

  can_health->esr_reg = esr;
  can_health->error_warning      = (uint8_t)(esr & 0x1U);
  can_health->error_passive      = (uint8_t)((esr >> 1) & 0x1U);
  can_health->bus_off            = (uint8_t)((esr >> 2) & 0x1U);
  can_health->last_error_code    = (uint8_t)((esr >> 4) & 0x7U);
  can_health->transmit_error_cnt = (uint8_t)((esr >> 16) & 0xFFU);
  can_health->receive_error_cnt  = (uint8_t)((esr >> 24) & 0xFFU);
  return sizeof(*can_health);
}

int get_rtc_pkt(void *dat) {
  timestamp_t t = rtc_get_time();
  (void)memcpy(dat, &t, sizeof(t));
  return sizeof(t);
}

void usb_cb_ep2_out(void *usbdata, int len) {
  uint8_t *usbdata8 = (uint8_t *)usbdata;
  uart_ring *ur = get_ring_by_number(usbdata8[0]);
  if ((len != 0) && (ur != NULL)) {
    if ((usbdata8[0] < 2U) || safety_tx_lin_hook(usbdata8[0] - 2U, &usbdata8[1], len - 1)) {
      for (int i = 1; i < len; i++) {
        while (!putc(ur, usbdata8[i])) {

        }
      }
    }
  }
}

void usb_cb_ep3_out_complete(void) {
  if (can_tx_check_min_slots_free(MAX_CAN_MSGS_PER_BULK_TRANSFER)) {
    usb_outep3_resume_if_paused();
  }
}

void usb_cb_enumeration_complete(void) {
  puts("USB enumeration complete\n");
  is_enumerated = 1;
}

int usb_cb_control_msg(USB_Setup_TypeDef *setup, uint8_t *resp) {
  unsigned int resp_len = 0;
  uart_ring *ur = NULL;
  timestamp_t t;
  switch (setup->b.bRequest) {

    case 0xa0:
      resp_len = get_rtc_pkt(resp);
      break;

    case 0xa1:
      t = rtc_get_time();
      t.year = setup->b.wValue.w;
      rtc_set_time(t);
      break;

    case 0xa2:
      t = rtc_get_time();
      t.month = setup->b.wValue.w;
      rtc_set_time(t);
      break;

    case 0xa3:
      t = rtc_get_time();
      t.day = setup->b.wValue.w;
      rtc_set_time(t);
      break;

    case 0xa4:
      t = rtc_get_time();
      t.weekday = setup->b.wValue.w;
      rtc_set_time(t);
      break;

    case 0xa5:
      t = rtc_get_time();
      t.hour = setup->b.wValue.w;
      rtc_set_time(t);
      break;

    case 0xa6:
      t = rtc_get_time();
      t.minute = setup->b.wValue.w;
      rtc_set_time(t);
      break;

    case 0xa7:
      t = rtc_get_time();
      t.second = setup->b.wValue.w;
      rtc_set_time(t);
      break;

    case 0xb0:
      current_board->set_ir_power(setup->b.wValue.w);
      break;

    case 0xb1:
      current_board->set_fan_power(setup->b.wValue.w);
      break;

    case 0xb2:
      resp[0] = (fan_rpm & 0x00FFU);
      resp[1] = ((fan_rpm & 0xFF00U) >> 8U);
      resp_len = 2;
      break;

    case 0xb3:
      current_board->set_phone_power(setup->b.wValue.w > 0U);
      break;

    case 0xc0:
      puts("can tx: "); puth(can_tx_cnt);
      puts(" txd: "); puth(can_txd_cnt);
      puts(" rx: "); puth(can_rx_cnt);
      puts(" err: "); puth(can_err_cnt);
      puts("\n");
      break;

    case 0xc1:
      resp[0] = hw_type;
      resp_len = 1;
      break;

    case 0xd0:

      if (setup->b.wValue.w == 1U) {
        (void)memcpy(resp, (uint8_t *)DEVICE_SERIAL_NUMBER_ADDRESS, 0x10);
        resp_len = 0x10;
      } else {
        get_provision_chunk(resp);
        resp_len = PROVISION_CHUNK_LEN;
      }
      break;

    case 0xd1:

      switch (setup->b.wValue.w) {
        case 0:

          #ifdef ALLOW_DEBUG
            puts("-> entering bootloader\n");
            enter_bootloader_mode = ENTER_BOOTLOADER_MAGIC;
            NVIC_SystemReset();
          #endif
          break;
        case 1:
          puts("-> entering softloader\n");
          enter_bootloader_mode = ENTER_SOFTLOADER_MAGIC;
          NVIC_SystemReset();
          break;
        default:
          puts("Bootloader mode invalid\n");
          break;
      }
      break;

    case 0xd2:
      resp_len = get_health_pkt(resp);
      break;

    case 0xc3:
      resp_len = get_can_health_pkt(resp, (uint8_t)(setup->b.wValue.w));
      break;

    case 0xd3:
      {
        resp_len = 64;
        char * code = (char*)_app_start;
        int code_len = _app_start[0];
        (void)memcpy(resp, &code[code_len], resp_len);
      }
      break;

    case 0xd4:
      {
        resp_len = 64;
        char * code = (char*)_app_start;
        int code_len = _app_start[0];
        (void)memcpy(resp, &code[code_len + 64], resp_len);
      }
      break;

    case 0xd6:
      COMPILE_TIME_ASSERT(sizeof(gitversion) <= USBPACKET_MAX_SIZE);
      (void)memcpy(resp, gitversion, sizeof(gitversion));
      resp_len = sizeof(gitversion) - 1U;
      break;

    case 0xd8:
      NVIC_SystemReset();
      break;

    case 0xd9:
      if (setup->b.wValue.w == 1U) {
        current_board->set_gps_mode(GPS_ENABLED);
      } else if (setup->b.wValue.w == 2U) {
        current_board->set_gps_mode(GPS_BOOTMODE);
      } else {
        current_board->set_gps_mode(GPS_DISABLED);
      }
      break;

    case 0xda:
      current_board->set_gps_mode(GPS_DISABLED);
      delay(1000000);
      if (setup->b.wValue.w == 1U) {
        current_board->set_gps_mode(GPS_BOOTMODE);
      } else {
        current_board->set_gps_mode(GPS_ENABLED);
      }
      delay(1000000);
      current_board->set_gps_mode(GPS_ENABLED);
      break;

    case 0xdb:
      if(current_board->has_obd){
        if (setup->b.wValue.w == 1U) {

          current_board->set_can_mode(CAN_MODE_OBD_CAN2);
        } else {

          current_board->set_can_mode(CAN_MODE_NORMAL);
        }
      } else {
        if (setup->b.wValue.w == 1U) {

          if (setup->b.wIndex.w == 1U) {
            can_set_gmlan(1);
          } else if (setup->b.wIndex.w == 2U) {
            can_set_gmlan(2);
          } else {
            puts("Invalid bus num for GMLAN CAN set\n");
          }
        } else {
          can_set_gmlan(-1);
        }
      }
      break;

    case 0xdc:
      set_safety_mode(setup->b.wValue.w, (uint16_t)setup->b.wIndex.w);
      break;

    case 0xdd:
      resp[0] = HEALTH_PACKET_VERSION;
      resp[1] = CAN_PACKET_VERSION;
      resp_len = 2;
      break;

    case 0xde:
      if (setup->b.wValue.w < BUS_CNT) {

        bus_config[setup->b.wValue.w].can_speed = setup->b.wIndex.w;
        bool ret = can_init(CAN_NUM_FROM_BUS_NUM(setup->b.wValue.w));
        UNUSED(ret);
      }
      break;

    case 0xdf:

      if (!is_car_safety_mode(current_safety_mode)) {
        alternative_experience = setup->b.wValue.w;
      }
      break;

    case 0xe0:
      ur = get_ring_by_number(setup->b.wValue.w);
      if (!ur) {
        break;
      }

      if (ur == &uart_ring_gps) {
        dma_pointer_handler(ur, DMA2_Stream5->NDTR);
      }

      while ((resp_len < MIN(setup->b.wLength.w, USBPACKET_MAX_SIZE)) &&
                         getc(ur, (char*)&resp[resp_len])) {
        ++resp_len;
      }
      break;

    case 0xe1:
      ur = get_ring_by_number(setup->b.wValue.w);
      if (!ur) {
        break;
      }
      uart_set_baud(ur->uart, setup->b.wIndex.w);
      break;

    case 0xe2:
      ur = get_ring_by_number(setup->b.wValue.w);
      if (!ur) {
        break;
      }
      switch (setup->b.wIndex.w) {
        case 0:

          ur->uart->CR1 &= ~(USART_CR1_PCE | USART_CR1_M);
          break;
        case 1:

          ur->uart->CR1 &= ~USART_CR1_PS;
          ur->uart->CR1 |= USART_CR1_PCE | USART_CR1_M;
          break;
        case 2:

          ur->uart->CR1 |= USART_CR1_PS;
          ur->uart->CR1 |= USART_CR1_PCE | USART_CR1_M;
          break;
        default:
          break;
      }
      break;

    case 0xe4:
      ur = get_ring_by_number(setup->b.wValue.w);
      if (!ur) {
        break;
      }
      uart_set_baud(ur->uart, (int)setup->b.wIndex.w*300);
      break;

    case 0xe5:
      can_loopback = (setup->b.wValue.w > 0U);
      can_init_all();
      break;

    case 0xe6:
      current_board->set_usb_power_mode(setup->b.wValue.w);
      break;

    case 0xe7:
      set_power_save_state(setup->b.wValue.w);
      break;
    case 0xe8:
      // 래치 중 engage(≠0) 차단, off(=0)는 항상 허용.
      if ((setup->b.wValue.w != 0U) && relay_off_latched) {
      } else {
        set_intercept_relay(setup->b.wValue.w != 0U);
        seer_cover_start_us = microsecond_timer_get();
        seer_cover_armed = true;
      }
      break;
    case 0xe9:
      pc_authority = (setup->b.wValue.w != 0U);
      if (setup->b.wValue.w != 0U) { relay_off_latched = false; }  // 주도권 재취득 시 래치 해제
      break;

    case 0xea:
      resp[0] = seer_homing_cmd((setup->b.wValue.w != 0U), setup->b.wIndex.w) ? 1U : 0U;
      resp_len = 1;
      break;


    case 0xeb:
      resp[0] = seer_home_state;
      resp[1] = seer_home_done_mask;
      resp[2] = seer_home_seen_active;
      resp[3] = (uint8_t)(seer_home_elapsed_s & 0xFFU);
      resp[4] = (uint8_t)((seer_home_elapsed_s >> 8) & 0xFFU);
      resp[5] = seer_home_digital_in(3U);
      resp[6] = seer_home_digital_in(4U);
      resp[7] = seer_home_reached_mask;
      resp_len = 8;
      break;

    case 0xf0:
      if(current_board->has_lin) {
        bool k = (setup->b.wValue.w == 0U) || (setup->b.wValue.w == 2U);
        bool l = (setup->b.wValue.w == 1U) || (setup->b.wValue.w == 2U);
        if (bitbang_wakeup(k, l)) {
          resp_len = -1;
        }
      }
      break;

    case 0xf1:
      if (setup->b.wValue.w == 0xFFFFU) {
        puts("Clearing CAN Rx queue\n");
        can_clear(&can_rx_q);
      } else if (setup->b.wValue.w < BUS_CNT) {
        puts("Clearing CAN Tx queue\n");
        can_clear(can_queues[setup->b.wValue.w]);
      } else {
        puts("Clearing CAN CAN ring buffer failed: wrong bus number\n");
      }
      break;

    case 0xf2:
      {
        uart_ring * rb = get_ring_by_number(setup->b.wValue.w);
        if (rb != NULL) {
          puts("Clearing UART queue.\n");
          clear_uart_buff(rb);
        }
        break;
      }

    case 0xf3:
      {
        heartbeat_counter = 0U;
        heartbeat_lost = false;
        heartbeat_disabled = false;
        heartbeat_engaged = (setup->b.wValue.w == 1U);
        break;
      }

    case 0xf4:
      if(current_board->has_lin) {
        bool k = (setup->b.wValue.w == 0U) || (setup->b.wValue.w == 2U);
        bool l = (setup->b.wValue.w == 1U) || (setup->b.wValue.w == 2U);
        uint8_t five_baud_addr = (setup->b.wIndex.w & 0xFFU);
        if (bitbang_five_baud_addr(k, l, five_baud_addr)) {
          resp_len = -1;
        }
      }
      break;

    case 0xf5:
      current_board->set_clock_source_mode(setup->b.wValue.w);
      break;

    case 0xf6:
      siren_enabled = (setup->b.wValue.w != 0U);
      break;

    case 0xf7:
      green_led_enabled = (setup->b.wValue.w != 0U);
      break;
#ifdef ALLOW_DEBUG

    case 0xf8:
      heartbeat_disabled = true;
      break;
#endif

    case 0xf9:
      if (setup->b.wValue.w < CAN_CNT) {

        bus_config[setup->b.wValue.w].can_data_speed = setup->b.wIndex.w;
        bus_config[setup->b.wValue.w].canfd_enabled = (setup->b.wIndex.w >= bus_config[setup->b.wValue.w].can_speed);
        bus_config[setup->b.wValue.w].brs_enabled = (setup->b.wIndex.w > bus_config[setup->b.wValue.w].can_speed);
        bool ret = can_init(CAN_NUM_FROM_BUS_NUM(setup->b.wValue.w));
        UNUSED(ret);
      }
      break;

    case 0xfa:
      if (setup->b.wValue.w < CAN_CNT) {
        resp[0] =  bus_config[setup->b.wValue.w].canfd_enabled;
        resp[1] = bus_config[setup->b.wValue.w].brs_enabled;
        resp_len = 2;
      }
      break;

    case 0xfb:
      deepsleep_requested = true;
      break;
    default:
      puts("NO HANDLER ");
      puth(setup->b.bRequest);
      puts("\n");
      break;
  }
  return resp_len;
}
