#include "usb_protocol.h"
#include "health.h"

extern int _app_start[0xc000]; // Only first 3 sectors of size 0x4000 are used

// Prototypes
void set_safety_mode(uint16_t mode, uint16_t param);

#ifdef STM32H7
  #include "stm32h7/llflash.h"
#else
  #include "stm32fx/llflash.h"
#endif

// ── 보드 이름 (런타임 USB 기록, 플래시 섹터 4 = 0x08010000, 앱 재플래시에도 보존) ─────────
// 레코드: [magic 'CRNM'][name 32B, NUL 패딩]. 0xee 로 RAM 스테이징(2바이트씩) → 0xef 로 커밋(섹터 erase+program).
#define BOARD_NAME_ADDR   0x08010000U
#define BOARD_NAME_SECTOR 4U
#define BOARD_NAME_MAGIC  0x4D4E5243U   // 'C','R','N','M' little-endian
#define BOARD_NAME_LEN    32U
#define BOARD_NAME_COMMIT_KEY 0x5AA5U
uint8_t board_name_stage[BOARD_NAME_LEN] = {0};

static uint8_t board_name_read(uint8_t *out) {   // out: 32B, 반환 = 이름 길이(0 = 미기록)
  const uint32_t *rec = (const uint32_t *)BOARD_NAME_ADDR;
  uint8_t n = 0U;
  for (uint8_t i = 0U; i < BOARD_NAME_LEN; i++) { out[i] = 0U; }
  if (rec[0] != BOARD_NAME_MAGIC) { return 0U; }
  const uint8_t *nm = (const uint8_t *)(BOARD_NAME_ADDR + 4U);
  while ((n < (BOARD_NAME_LEN - 1U)) && (nm[n] != 0U) && (nm[n] != 0xFFU)) { out[n] = nm[n]; n++; }
  return n;
}

static bool board_name_commit(void) {
#ifndef STM32F4
  return false;   // 섹터 배치가 F413 기준 — 다른 MCU 빌드는 기록 기능 없음
#else
  // SILENT idle 에서만 — 섹터 erase 동안 코어가 정지해 CAN 수신을 놓치므로 intercept 중엔 금지
  if ((current_safety_mode != SAFETY_SILENT) || seer_handover_active() || pc_authority) { return false; }
  uint32_t words[1U + (BOARD_NAME_LEN / 4U)];
  words[0] = BOARD_NAME_MAGIC;
  for (uint8_t i = 0U; i < (BOARD_NAME_LEN / 4U); i++) {
    words[1U + i] = (uint32_t)board_name_stage[4U * i] | ((uint32_t)board_name_stage[(4U * i) + 1U] << 8) |
                    ((uint32_t)board_name_stage[(4U * i) + 2U] << 16) | ((uint32_t)board_name_stage[(4U * i) + 3U] << 24);
  }
  disable_interrupts();
  if (flash_is_locked()) { flash_unlock(); }
  bool ok = flash_erase_sector(BOARD_NAME_SECTOR, true);
  if (ok) {
    for (uint8_t i = 0U; i < (1U + (BOARD_NAME_LEN / 4U)); i++) {
      flash_write_word((void *)(BOARD_NAME_ADDR + (4U * i)), words[i]);
    }
  }
  FLASH->CR |= FLASH_CR_LOCK;
  enable_interrupts();
  if (ok) {
    const uint32_t *rec = (const uint32_t *)BOARD_NAME_ADDR;
    for (uint8_t i = 0U; i < (1U + (BOARD_NAME_LEN / 4U)); i++) { if (rec[i] != words[i]) { ok = false; } }
  }
  return ok;
#endif
}
bool is_car_safety_mode(uint16_t mode);

int get_health_pkt(void *dat) {
  COMPILE_TIME_ASSERT(sizeof(struct health_t) <= USBPACKET_MAX_SIZE);
  struct health_t * health = (struct health_t*)dat;

  health->uptime_pkt = uptime_cnt;
  health->voltage_pkt = adc_get_voltage();
  health->current_pkt = current_board->read_current();

  //Use the GPIO pin to determine ignition or use a CAN based logic
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

// CAN-Relay: per-bus CAN 에러 상태(bxCAN ESR). bus 0~2 → can_num_lookup → cans[n]->ESR.
int get_can_health_pkt(void *dat, uint8_t bus) {
  COMPILE_TIME_ASSERT(sizeof(struct can_health_t) <= USBPACKET_MAX_SIZE);
  struct can_health_t * can_health = (struct can_health_t*)dat;
  uint32_t esr = 0U;

  if (bus < 3U) {
    uint8_t can_num = bus_config[bus].can_num_lookup;
    if (can_num < 3U) {
#ifndef STM32H7
      // bxCAN(F4): ESR 레지스터에 TEC/REC/LEC/BOFF 존재
      CAN_TypeDef *CAN = CANIF_FROM_CAN_NUM(can_num);
      esr = CAN->ESR;
#else
      // FDCAN(H7)은 본 프로젝트 미사용 → 0 반환 (필요 시 PSR/ECR로 구현)
      UNUSED(can_num);
#endif
    }
  }

  can_health->esr_reg = esr;
  can_health->error_warning      = (uint8_t)(esr & 0x1U);
  can_health->error_passive      = (uint8_t)((esr >> 1) & 0x1U);
  can_health->bus_off            = (uint8_t)((esr >> 2) & 0x1U);
  can_health->last_error_code    = (uint8_t)((esr >> 4) & 0x7U);
  can_health->receive_error_cnt  = (uint8_t)((esr >> 16) & 0xFFU);
  can_health->transmit_error_cnt = (uint8_t)((esr >> 24) & 0xFFU);
  return sizeof(*can_health);
}

int get_rtc_pkt(void *dat) {
  timestamp_t t = rtc_get_time();
  (void)memcpy(dat, &t, sizeof(t));
  return sizeof(t);
}



// send on serial, first byte to select the ring
void usb_cb_ep2_out(void *usbdata, int len) {
  uint8_t *usbdata8 = (uint8_t *)usbdata;
  uart_ring *ur = get_ring_by_number(usbdata8[0]);
  if ((len != 0) && (ur != NULL)) {
    if ((usbdata8[0] < 2U) || safety_tx_lin_hook(usbdata8[0] - 2U, &usbdata8[1], len - 1)) {
      for (int i = 1; i < len; i++) {
        while (!putc(ur, usbdata8[i])) {
          // wait
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
    // **** 0xa0: get rtc time
    case 0xa0:
      resp_len = get_rtc_pkt(resp);
      break;
    // **** 0xa1: set rtc year
    case 0xa1:
      t = rtc_get_time();
      t.year = setup->b.wValue.w;
      rtc_set_time(t);
      break;
    // **** 0xa2: set rtc month
    case 0xa2:
      t = rtc_get_time();
      t.month = setup->b.wValue.w;
      rtc_set_time(t);
      break;
    // **** 0xa3: set rtc day
    case 0xa3:
      t = rtc_get_time();
      t.day = setup->b.wValue.w;
      rtc_set_time(t);
      break;
    // **** 0xa4: set rtc weekday
    case 0xa4:
      t = rtc_get_time();
      t.weekday = setup->b.wValue.w;
      rtc_set_time(t);
      break;
    // **** 0xa5: set rtc hour
    case 0xa5:
      t = rtc_get_time();
      t.hour = setup->b.wValue.w;
      rtc_set_time(t);
      break;
    // **** 0xa6: set rtc minute
    case 0xa6:
      t = rtc_get_time();
      t.minute = setup->b.wValue.w;
      rtc_set_time(t);
      break;
    // **** 0xa7: set rtc second
    case 0xa7:
      t = rtc_get_time();
      t.second = setup->b.wValue.w;
      rtc_set_time(t);
      break;
    // **** 0xb0: set IR power
    case 0xb0:
      current_board->set_ir_power(setup->b.wValue.w);
      break;
    // **** 0xb1: set fan power
    case 0xb1:
      current_board->set_fan_power(setup->b.wValue.w);
      break;
    // **** 0xb2: get fan rpm
    case 0xb2:
      resp[0] = (fan_rpm & 0x00FFU);
      resp[1] = ((fan_rpm & 0xFF00U) >> 8U);
      resp_len = 2;
      break;
    // **** 0xb3: set phone power
    case 0xb3:
      current_board->set_phone_power(setup->b.wValue.w > 0U);
      break;
    // **** 0xc0: get CAN debug info
    case 0xc0:
      puts("can tx: "); puth(can_tx_cnt);
      puts(" txd: "); puth(can_txd_cnt);
      puts(" rx: "); puth(can_rx_cnt);
      puts(" err: "); puth(can_err_cnt);
      puts("\n");
      break;
    // **** 0xc1: get hardware type
    case 0xc1:
      resp[0] = hw_type;
      resp_len = 1;
      break;
    // **** 0xd0: fetch serial number
    case 0xd0:
      // addresses are OTP
      if (setup->b.wValue.w == 1U) {
        (void)memcpy(resp, (uint8_t *)DEVICE_SERIAL_NUMBER_ADDRESS, 0x10);
        resp_len = 0x10;
      } else {
        get_provision_chunk(resp);
        resp_len = PROVISION_CHUNK_LEN;
      }
      break;
    // **** 0xd1: enter bootloader mode
    case 0xd1:
      // this allows reflashing of the bootstub
      switch (setup->b.wValue.w) {
        case 0:
          // only allow bootloader entry on debug builds
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
    // **** 0xd2: get health packet
    case 0xd2:
      resp_len = get_health_pkt(resp);
      break;
    // **** 0xc3: get per-bus CAN health (bxCAN ESR: TEC/REC/LEC/BOFF)
    case 0xc3:
      resp_len = get_can_health_pkt(resp, (uint8_t)(setup->b.wValue.w));
      break;
    // **** 0xd3: get first 64 bytes of signature
    case 0xd3:
      {
        resp_len = 64;
        char * code = (char*)_app_start;
        int code_len = _app_start[0];
        (void)memcpy(resp, &code[code_len], resp_len);
      }
      break;
    // **** 0xd4: get second 64 bytes of signature
    case 0xd4:
      {
        resp_len = 64;
        char * code = (char*)_app_start;
        int code_len = _app_start[0];
        (void)memcpy(resp, &code[code_len + 64], resp_len);
      }
      break;
    // **** 0xd6: get version
    case 0xd6:
      COMPILE_TIME_ASSERT(sizeof(gitversion) <= USBPACKET_MAX_SIZE);
      (void)memcpy(resp, gitversion, sizeof(gitversion));
      resp_len = sizeof(gitversion) - 1U;
      {
        // 보드 이름이 기록돼 있으면 "#<name>" 을 덧붙인다 (총 64B 이내)
        uint8_t nm[BOARD_NAME_LEN];
        uint8_t nl = board_name_read(nm);
        if ((nl > 0U) && ((resp_len + 1U + nl) <= USBPACKET_MAX_SIZE)) {
          resp[resp_len] = (uint8_t)'#'; resp_len += 1U;
          (void)memcpy(&resp[resp_len], nm, nl); resp_len += nl;
        }
      }
      break;
    // **** 0xd8: reset ST
    case 0xd8:
      NVIC_SystemReset();
      break;
    // **** 0xd9: set ESP power
    case 0xd9:
      if (setup->b.wValue.w == 1U) {
        current_board->set_gps_mode(GPS_ENABLED);
      } else if (setup->b.wValue.w == 2U) {
        current_board->set_gps_mode(GPS_BOOTMODE);
      } else {
        current_board->set_gps_mode(GPS_DISABLED);
      }
      break;
    // **** 0xda: reset ESP, with optional boot mode
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
    // **** 0xdb: set GMLAN (white/grey) or OBD CAN (black) multiplexing mode
    case 0xdb:
      if(current_board->has_obd){
        if (setup->b.wValue.w == 1U) {
          // Enable OBD CAN
          current_board->set_can_mode(CAN_MODE_OBD_CAN2);
        } else {
          // Disable OBD CAN
          current_board->set_can_mode(CAN_MODE_NORMAL);
        }
      } else {
        if (setup->b.wValue.w == 1U) {
          // GMLAN ON
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

    // **** 0xdc: set safety mode
    case 0xdc:
      if (setup->b.wValue.w == SAFETY_SILENT) {
        if (seer_handover_active()) {
          // 복원 중의 SILENT 요청은 보류했다가 시퀀서 완료 시 적용한다
          seer_ho_pending_silent = true;
        } else if (pc_authority) {
          // 0xe8/0xe9 없이 SILENT 만 온 반환(예: 호스트 롤백 일부 실패) — 그래도 복원 뒤 해제한다
          seer_handover_request(SEER_HO_SRC_HOST);
          seer_ho_pending_silent = true;
        } else {
          set_safety_mode(setup->b.wValue.w, (uint16_t)setup->b.wIndex.w);
        }
      } else {
        // 라이브 모드 요청(재engage 시작) — 보류된 SILENT 는 더 이상 유효하지 않다
        if (seer_handover_active()) { seer_ho_pending_silent = false; }
        set_safety_mode(setup->b.wValue.w, (uint16_t)setup->b.wIndex.w);
      }
      break;
    // **** 0xdd: get healthpacket and CANPacket versions
    case 0xdd:
      resp[0] = HEALTH_PACKET_VERSION;
      resp[1] = CAN_PACKET_VERSION;
      resp_len = 2;
      break;
    // **** 0xde: set can bitrate
    case 0xde:
      if (setup->b.wValue.w < BUS_CNT) {
        // TODO: add sanity check, ideally check if value is correct(from array of correct values)
        bus_config[setup->b.wValue.w].can_speed = setup->b.wIndex.w;
        bool ret = can_init(CAN_NUM_FROM_BUS_NUM(setup->b.wValue.w));
        UNUSED(ret);
      }
      break;
    // **** 0xdf: set alternative experience
    case 0xdf:
      // you can only set this if you are in a non car safety mode
      if (!is_car_safety_mode(current_safety_mode)) {
        alternative_experience = setup->b.wValue.w;
      }
      break;
    // **** 0xe0: uart read
    case 0xe0:
      ur = get_ring_by_number(setup->b.wValue.w);
      if (!ur) {
        break;
      }

      // TODO: Remove this again and fix boardd code to hande the message bursts instead of single chars
      if (ur == &uart_ring_gps) {
        dma_pointer_handler(ur, DMA2_Stream5->NDTR);
      }

      // read
      while ((resp_len < MIN(setup->b.wLength.w, USBPACKET_MAX_SIZE)) &&
                         getc(ur, (char*)&resp[resp_len])) {
        ++resp_len;
      }
      break;
    // **** 0xe1: uart set baud rate
    case 0xe1:
      ur = get_ring_by_number(setup->b.wValue.w);
      if (!ur) {
        break;
      }
      uart_set_baud(ur->uart, setup->b.wIndex.w);
      break;
    // **** 0xe2: uart set parity
    case 0xe2:
      ur = get_ring_by_number(setup->b.wValue.w);
      if (!ur) {
        break;
      }
      switch (setup->b.wIndex.w) {
        case 0:
          // disable parity, 8-bit
          ur->uart->CR1 &= ~(USART_CR1_PCE | USART_CR1_M);
          break;
        case 1:
          // even parity, 9-bit
          ur->uart->CR1 &= ~USART_CR1_PS;
          ur->uart->CR1 |= USART_CR1_PCE | USART_CR1_M;
          break;
        case 2:
          // odd parity, 9-bit
          ur->uart->CR1 |= USART_CR1_PS;
          ur->uart->CR1 |= USART_CR1_PCE | USART_CR1_M;
          break;
        default:
          break;
      }
      break;
    // **** 0xe4: uart set baud rate extended
    case 0xe4:
      ur = get_ring_by_number(setup->b.wValue.w);
      if (!ur) {
        break;
      }
      uart_set_baud(ur->uart, (int)setup->b.wIndex.w*300);
      break;
    // **** 0xe5: set CAN loopback (for testing)
    case 0xe5:
      can_loopback = (setup->b.wValue.w > 0U);
      can_init_all();
      break;
    // **** 0xe6: set USB power
    case 0xe6:
      current_board->set_usb_power_mode(setup->b.wValue.w);
      break;
    // **** 0xe7: set power save state
    case 0xe7:
      set_power_save_state(setup->b.wValue.w);
      break;
    case 0xe8:
      // wValue=0(반환)이고 PC 주도 중이면 핸드오버 시퀀서가 복원 뒤 권한을 내리고 cover 를 건다.
      if (setup->b.wValue.w != 0U) {
        set_intercept_relay(true);
        seer_cover_start_us = microsecond_timer_get();
        seer_cover_armed = true;
      } else if (pc_authority) {
        seer_handover_request(SEER_HO_SRC_HOST);
      } else {
        set_intercept_relay(false);
        seer_cover_start_us = microsecond_timer_get();
        seer_cover_armed = true;
      }
      break;
    case 0xe9:
      if (setup->b.wValue.w != 0U) {
        if (seer_handover_active()) {
          // 복원 진행 중의 재engage: 복원을 끝까지 수행한 뒤 권한을 유지한 채 넘긴다(보류 SILENT 폐기)
          seer_ho_reengage = true;
          seer_ho_pending_silent = false;
        } else {
          pc_authority = true;
        }
      } else if (pc_authority) {
        seer_handover_request(SEER_HO_SRC_HOST);   // 복원 뒤 시퀀서가 pc_authority 를 내린다
      } else {
        pc_authority = false;
      }
      break;
    // **** 0xec: 핸드오버 복원 시퀀서 상태 조회 (CAN-Relay)
    //   resp[0]=state(0 IDLE·1 RESTORE·2 SETTLE) resp[1]=source(1 host·2 failsafe)
    //   resp[2]=result(0 none·1 reached·2 timeout·3 no-target) resp[3]=pending_silent
    //   resp[4]=ticks(8 Hz) resp[5]=pc_authority
    case 0xec:
      resp[0] = seer_ho_state; resp[1] = seer_ho_source; resp[2] = seer_ho_result;
      resp[3] = seer_ho_pending_silent ? 1U : 0U; resp[4] = seer_ho_ticks; resp[5] = pc_authority ? 1U : 0U;
      resp_len = 6;
      break;
    // **** 0xed: 보드 이름 읽기 (CAN-Relay) — 32B, 미기록이면 길이 0
    case 0xed:
      resp_len = board_name_read(resp);
      break;
    // **** 0xee: 보드 이름 스테이징 — wValue=바이트 인덱스(0..30, 짝수), wIndex=2바이트(lo=idx, hi=idx+1)
    case 0xee:
      if ((setup->b.wValue.w + 1U) < BOARD_NAME_LEN) {
        board_name_stage[setup->b.wValue.w] = (uint8_t)(setup->b.wIndex.w & 0xFFU);
        board_name_stage[setup->b.wValue.w + 1U] = (uint8_t)((setup->b.wIndex.w >> 8) & 0xFFU);
      }
      break;
    // **** 0xef: 보드 이름 커밋 (wValue=0x5AA5) — SILENT idle 에서만. resp[0]=1 성공/0 거부·실패
    case 0xef:
      resp[0] = ((setup->b.wValue.w == BOARD_NAME_COMMIT_KEY) && board_name_commit()) ? 1U : 0U;
      resp_len = 1;
      break;
    // **** 0xea: 조향 호밍 개시/중단 (CAN-Relay)
    //   wValue: 1=개시, 0=중단   wIndex: 호밍속도(0.1 r/min), 0 이면 기본값 2500
    //   resp[0]: 1=수락, 0=거부(pc_authority 아님 / safety_mode 불일치 / 이미 진행중)
    //   개시 전제: 0xe9=1(PC 주도) + safety_mode 30. 구동축(node1·2)은 대상이 아니다.
    case 0xea:
      resp[0] = seer_homing_cmd((setup->b.wValue.w != 0U), setup->b.wIndex.w) ? 1U : 0U;
      resp_len = 1;
      break;
    // **** 0xeb: 조향 호밍 상태 조회 (CAN-Relay)
    //   resp[0]: 상태 (0=IDLE 1=ENABLE 2=SET_SPEED 3=START 4=WAIT(원점탐색) 5=DONE(0° 복귀완료)
    //                  6=ERR_TIMEOUT 7=ERR_ABORT 8=RESTORE 9=GOZERO 10=ERR_GOZERO 11=GOZERO_W)
    //   resp[1]: 원점 확정 마스크 (bit0=node3, bit1=node4)
    //   resp[2]: 진행중(bit15=0) 관측 마스크 — 개시 전 잔류값 오인 방지용
    //   resp[3..4]: 현 단계 경과 초 (little-endian)
    //   resp[5]: node3 의 0x6000 하위바이트, resp[6]: node4 의 0x6000 하위바이트 (0xFF=미판독)
    //            → 리밋 스위치 해제 여부는 **호스트가 이 값으로 판단**한다. 0x6000 비트 매핑이
    //              아직 1차 source 로 확정되지 않아 펌웨어는 이 값으로 분기하지 않는다.
    //   resp[7]: 조향 0° 도달 마스크
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
    // **** 0xf0: k-line/l-line wake-up pulse for KWP2000 fast initialization
    case 0xf0:
      if(current_board->has_lin) {
        bool k = (setup->b.wValue.w == 0U) || (setup->b.wValue.w == 2U);
        bool l = (setup->b.wValue.w == 1U) || (setup->b.wValue.w == 2U);
        if (bitbang_wakeup(k, l)) {
          resp_len = -1; // do not clear NAK yet (wait for bit banging to finish)
        }
      }
      break;
    // **** 0xf1: Clear CAN ring buffer.
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
    // **** 0xf2: Clear UART ring buffer.
    case 0xf2:
      {
        uart_ring * rb = get_ring_by_number(setup->b.wValue.w);
        if (rb != NULL) {
          puts("Clearing UART queue.\n");
          clear_uart_buff(rb);
        }
        break;
      }
    // **** 0xf3: Heartbeat. Resets heartbeat counter.
    case 0xf3:
      {
        heartbeat_counter = 0U;
        heartbeat_lost = false;
        heartbeat_disabled = false;
        heartbeat_engaged = (setup->b.wValue.w == 1U);
        break;
      }
    // **** 0xf4: k-line/l-line 5 baud initialization
    case 0xf4:
      if(current_board->has_lin) {
        bool k = (setup->b.wValue.w == 0U) || (setup->b.wValue.w == 2U);
        bool l = (setup->b.wValue.w == 1U) || (setup->b.wValue.w == 2U);
        uint8_t five_baud_addr = (setup->b.wIndex.w & 0xFFU);
        if (bitbang_five_baud_addr(k, l, five_baud_addr)) {
          resp_len = -1; // do not clear NAK yet (wait for bit banging to finish)
        }
      }
      break;
    // **** 0xf5: set clock source mode
    case 0xf5:
      current_board->set_clock_source_mode(setup->b.wValue.w);
      break;
    // **** 0xf6: set siren enabled
    case 0xf6:
      siren_enabled = (setup->b.wValue.w != 0U);
      break;
    // **** 0xf7: set green led enabled
    case 0xf7:
      green_led_enabled = (setup->b.wValue.w != 0U);
      break;
#ifdef ALLOW_DEBUG
    // **** 0xf8: disable heartbeat checks
    case 0xf8:
      heartbeat_disabled = true;
      break;
#endif
    // **** 0xde: set CAN FD data bitrate
    case 0xf9:
      if (setup->b.wValue.w < CAN_CNT) {
        // TODO: add sanity check, ideally check if value is correct (from array of correct values)
        bus_config[setup->b.wValue.w].can_data_speed = setup->b.wIndex.w;
        bus_config[setup->b.wValue.w].canfd_enabled = (setup->b.wIndex.w >= bus_config[setup->b.wValue.w].can_speed);
        bus_config[setup->b.wValue.w].brs_enabled = (setup->b.wIndex.w > bus_config[setup->b.wValue.w].can_speed);
        bool ret = can_init(CAN_NUM_FROM_BUS_NUM(setup->b.wValue.w));
        UNUSED(ret);
      }
      break;
    // **** 0xfa: check if CAN FD and BRS are enabled
    case 0xfa:
      if (setup->b.wValue.w < CAN_CNT) {
        resp[0] =  bus_config[setup->b.wValue.w].canfd_enabled;
        resp[1] = bus_config[setup->b.wValue.w].brs_enabled;
        resp_len = 2;
      }
      break;
    // **** 0xfb: enter deep sleep(stop) mode
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
