
#include "config.h"

#include "drivers/pwm.h"
#include "drivers/usb.h"
#include "drivers/gmlan_alt.h"
#include "drivers/kline_init.h"

#include "early_init.h"
#include "provision.h"

#include "power_saving.h"
#include "safety.h"

#include "drivers/can_common.h"

#ifdef STM32H7
  #include "drivers/fdcan.h"
#else
  #include "drivers/bxcan.h"
#endif

#include "obj/gitversion.h"

#include "usb_comms.h"

bool check_started(void) {
  return current_board->check_ignition() || ignition_can;
}

void debug_ring_callback(uart_ring *ring) {
  char rcv;
  while (getc(ring, &rcv)) {
    (void)putc(ring, rcv);

    #ifdef ALLOW_DEBUG

      if (rcv == 'z') {
        enter_bootloader_mode = ENTER_BOOTLOADER_MAGIC;
        NVIC_SystemReset();
      }
    #endif

    if (rcv == 'x') {
      NVIC_SystemReset();
    }

    if (rcv == 'C') {
      puts("switching USB to CDP mode\n");
      current_board->set_usb_power_mode(USB_POWER_CDP);
    }
    if (rcv == 'c') {
      puts("switching USB to client mode\n");
      current_board->set_usb_power_mode(USB_POWER_CLIENT);
    }
    if (rcv == 'D') {
      puts("switching USB to DCP mode\n");
      current_board->set_usb_power_mode(USB_POWER_DCP);
    }
  }
}

void set_safety_mode(uint16_t mode, uint16_t param) {
  uint16_t mode_copy = mode;
  int err = set_safety_hooks(mode_copy, param);
  if (err == -1) {
    puts("Error: safety set mode failed. Falling back to SILENT\n");
    mode_copy = SAFETY_SILENT;
    err = set_safety_hooks(mode_copy, 0U);
    if (err == -1) {
      puts("Error: Failed setting SILENT mode. Hanging\n");
      while (true) {

      }
    }
  }
  blocked_msg_cnt = 0;

  switch (mode_copy) {
    case SAFETY_SILENT:
      // debt-129: 릴레이 OFF(push-pull LOW) = K1 닫힘 = Seer↔모터 직결 passthrough
      set_gpio_mode(GPIOC, 10, MODE_OUTPUT);
      set_gpio_output_type(GPIOC, 10, OUTPUT_TYPE_PUSH_PULL);
      set_gpio_output(GPIOC, 10, false);
      set_intercept_relay(false);
      if (current_board->has_obd) {
        current_board->set_can_mode(CAN_MODE_NORMAL);
      }
      can_silent = ALL_CAN_SILENT;
      break;
    case SAFETY_NOOUTPUT:
      set_intercept_relay(false);
      if (current_board->has_obd) {
        current_board->set_can_mode(CAN_MODE_NORMAL);
      }
      can_silent = ALL_CAN_LIVE;
      break;
    case SAFETY_ELM327:
      set_intercept_relay(false);
      heartbeat_counter = 0U;
      heartbeat_lost = false;
      if (current_board->has_obd) {
        if (param == 0U) {
          current_board->set_can_mode(CAN_MODE_OBD_CAN2);
        } else {
          current_board->set_can_mode(CAN_MODE_NORMAL);
        }
      }
      can_silent = ALL_CAN_LIVE;
      break;
    case SAFETY_ALLOUTPUT:
      set_intercept_relay(true);
      heartbeat_counter = 0U;
      heartbeat_lost = false;
      if (current_board->has_obd) {
        current_board->set_can_mode(CAN_MODE_NORMAL);
      }
      can_silent = ALL_CAN_LIVE;
      break;
    case SAFETY_SEER_GATE:
      // debt-129: 릴레이 K1 을 active-high push-pull 로 구동해 Seer↔모터 물리 절체(intercept). PC10 open-drain→push-pull.
      set_gpio_mode(GPIOC, 10, MODE_OUTPUT);
      set_gpio_output_type(GPIOC, 10, OUTPUT_TYPE_PUSH_PULL);
      set_gpio_output(GPIOC, 10, true);
      heartbeat_counter = 0U;
      heartbeat_lost = false;
      if (current_board->has_obd) {
        current_board->set_can_mode(CAN_MODE_NORMAL);
      }
      can_silent = ALL_CAN_LIVE;
      break;
    default:
      set_intercept_relay(true);
      heartbeat_counter = 0U;
      heartbeat_lost = false;
      if (current_board->has_obd) {
        current_board->set_can_mode(CAN_MODE_NORMAL);
      }
      can_silent = ALL_CAN_LIVE;
      break;
  }
  can_init_all();
}

bool is_car_safety_mode(uint16_t mode) {
  return (mode != SAFETY_SILENT) &&
         (mode != SAFETY_NOOUTPUT) &&
         (mode != SAFETY_ELM327);
}

// cppcheck-suppress unusedFunction ; used in headers not included in cppcheck
void __initialize_hardware_early(void) {
  early_initialization();
}

void __attribute__ ((noinline)) enable_fpu(void) {

  SCB->CPACR |= ((3UL << (10U * 2U)) | (3UL << (11U * 2U)));
}

#define HEARTBEAT_IGNITION_CNT_ON 5U
#define HEARTBEAT_IGNITION_CNT_OFF 2U

uint8_t loop_counter = 0U;
void tick_handler(void) {
  if (TICK_TIMER->SR != 0) {

    current_board->set_siren((loop_counter & 1U) && (siren_enabled || (siren_countdown > 0U)));

    seer_homing_tick();
    seer_handover_tick();

    if (loop_counter == 0U) {
      can_live = pending_can_live;

      current_board->usb_power_mode_tick(uptime_cnt);

      if ((uptime_cnt & 0xFU) == 0U) {
        pending_can_live = 0;
      }
      #ifdef DEBUG
        puts("** blink ");
        puts("rx:"); puth4(can_rx_q.r_ptr); puts("-"); puth4(can_rx_q.w_ptr); puts("  ");
        puts("tx1:"); puth4(can_tx1_q.r_ptr); puts("-"); puth4(can_tx1_q.w_ptr); puts("  ");
        puts("tx2:"); puth4(can_tx2_q.r_ptr); puts("-"); puth4(can_tx2_q.w_ptr); puts("  ");
        puts("tx3:"); puth4(can_tx3_q.r_ptr); puts("-"); puth4(can_tx3_q.w_ptr); puts("\n");
      #endif

      fan_tick();

      current_board->set_led(LED_GREEN, controls_allowed | green_led_enabled);

      current_board->set_led(LED_BLUE, (uptime_cnt & 1U) && (power_save_status == POWER_SAVE_STATUS_ENABLED));

      if (heartbeat_counter < __UINT32_MAX__) {
        heartbeat_counter += 1U;
      }

      if (siren_countdown > 0U) {
        siren_countdown -= 1U;
      }

      if (controls_allowed) {
        controls_allowed_countdown = 30U;
      } else if (controls_allowed_countdown > 0U) {
        controls_allowed_countdown -= 1U;
      } else {

      }

      if (controls_allowed && !heartbeat_engaged) {
        heartbeat_engaged_mismatches += 1U;
        if (heartbeat_engaged_mismatches >= 3U) {
          controls_allowed = 0U;
        }
      } else {
        heartbeat_engaged_mismatches = 0U;
      }

      if (!heartbeat_disabled) {

        if (heartbeat_counter >= (check_started() ? HEARTBEAT_IGNITION_CNT_ON : HEARTBEAT_IGNITION_CNT_OFF)) {
          puts("device hasn't sent a heartbeat for 0x");
          puth(heartbeat_counter);
          puts(" seconds. Safety is set to SILENT mode.\n");

          if (controls_allowed_countdown > 0U) {
            siren_countdown = 5U;
            controls_allowed_countdown = 0U;
          }

          if (is_car_safety_mode(current_safety_mode)) {
            heartbeat_lost = true;
          }

          if ((current_safety_mode == SAFETY_SEER_GATE) && pc_authority) {
            // 구동 0 + 조향을 Seer 목표로 복원한 뒤 시퀀서가 SILENT·래치까지 처리한다
            seer_handover_request(SEER_HO_SRC_FAILSAFE);
          } else if (seer_handover_active()) {
            // 복원 진행 중(최대 8.5 s) — power-save 가 트랜시버를 끄므로 완료를 기다린다
          } else {
            if (current_safety_mode != SAFETY_SILENT) {
              set_safety_mode(SAFETY_SILENT, 0U);
            }

            set_intercept_relay(false);
            pc_authority = false;

            if (power_save_status != POWER_SAVE_STATUS_ENABLED) {
              set_power_save_state(POWER_SAVE_STATUS_ENABLED);
            }
          }

          current_board->set_ir_power(0U);

          if(usb_enumerated){
            current_board->set_fan_power(50U);
          } else {
            current_board->set_fan_power(0U);
          }
        }

        if (check_started() && ((usb_power_mode != USB_POWER_CDP) || !usb_enumerated)) {
          current_board->set_usb_power_mode(USB_POWER_CDP);
        }
      }

      check_registers();

      if (ignition_can_cnt > 2U) {
        ignition_can = false;
      }

      uptime_cnt += 1U;
      safety_mode_cnt += 1U;
      ignition_can_cnt += 1U;

      safety_tick(current_rx_checks);
    }

    loop_counter++;
    loop_counter %= 8U;
  }
  TICK_TIMER->SR = 0;
}

void EXTI_IRQ_Handler(void) {
  if (check_exti_irq()) {
    exti_irq_clear();
    clock_init();

    current_board->set_usb_power_mode(USB_POWER_CDP);
    set_power_save_state(POWER_SAVE_STATUS_DISABLED);
    deepsleep_requested = false;
    heartbeat_counter = 0U;
    usb_soft_disconnect(false);

    NVIC_EnableIRQ(TICK_TIMER_IRQ);
  }
}

uint8_t rtc_counter = 0;
void RTC_WKUP_IRQ_Handler(void) {
  exti_irq_clear();
  clock_init();

  rtc_counter++;
  if ((rtc_counter % 2U) == 0U) {
    current_board->set_led(LED_BLUE, false);
  } else {
    current_board->set_led(LED_BLUE, true);
  }

  if (rtc_counter == __UINT8_MAX__) {
    rtc_counter = 1U;
  }
}

int main(void) {

  init_interrupts(true);

  disable_interrupts();

  clock_init();
  peripherals_init();
  detect_external_debug_serial();
  detect_board_type();
  adc_init();

  puts("\n\n\n************************ MAIN START ************************\n");

  if(hw_type == HW_TYPE_UNKNOWN){
    puts("Unsupported board type\n");
    while (1) {   }
  }

  puts("Config:\n");
  puts("  Board type: "); puts(current_board->board_type); puts("\n");
  puts(has_external_debug_serial ? "  Real serial\n" : "  USB serial\n");

  current_board->init();

  enable_fpu();

  if (has_external_debug_serial) {

    uart_init(&uart_ring_debug, 115200);
  }

  if (current_board->has_gps) {
    uart_init(&uart_ring_gps, 9600);
  } else {

    uart_init(&uart_ring_gps, 115200);
  }

  if(current_board->has_lin){

    uart_init(&uart_ring_lin1, 10400);
    UART5->CR2 |= USART_CR2_LINEN;
    uart_init(&uart_ring_lin2, 10400);
    USART3->CR2 |= USART_CR2_LINEN;
  }

  microsecond_timer_init();

  set_safety_mode(SAFETY_SILENT, 0U);

  current_board->enable_can_transceivers(true);

  REGISTER_INTERRUPT(TICK_TIMER_IRQ, tick_handler, 10U, FAULT_INTERRUPT_RATE_TICK)
  tick_timer_init();

#ifdef DEBUG
  puts("DEBUG ENABLED\n");
#endif

  usb_init();

  puts("**** INTERRUPTS ON ****\n");
  enable_interrupts();

  can_silent = ALL_CAN_LIVE;
  can_init_all();

  uint64_t cnt = 0;

  for (cnt=0;;cnt++) {
    current_board->enable_can_transceivers(true);

    if (power_save_status == POWER_SAVE_STATUS_DISABLED) {
      #ifdef DEBUG_FAULTS
      if(fault_status == FAULT_STATUS_NONE){
      #endif
        uint32_t div_mode = ((usb_power_mode == USB_POWER_DCP) ? 4U : 1U);

        for(uint32_t fade = 0U; fade < MAX_LED_FADE; fade += div_mode){
          current_board->set_led(LED_RED, true);
          delay(fade >> 4);
          current_board->set_led(LED_RED, false);
          delay((MAX_LED_FADE - fade) >> 4);
        }

        for(uint32_t fade = MAX_LED_FADE; fade > 0U; fade -= div_mode){
          current_board->set_led(LED_RED, true);
          delay(fade >> 4);
          current_board->set_led(LED_RED, false);
          delay((MAX_LED_FADE - fade) >> 4);
        }

      #ifdef DEBUG_FAULTS
      } else {
          current_board->set_led(LED_RED, 1);
          delay(512000U);
          current_board->set_led(LED_RED, 0);
          delay(512000U);
        }
      #endif
    } else {
      if (deepsleep_requested && !usb_enumerated && !check_started()) {
        usb_soft_disconnect(true);
        current_board->set_fan_power(0U);
        current_board->set_usb_power_mode(USB_POWER_CLIENT);
        NVIC_DisableIRQ(TICK_TIMER_IRQ);
        delay(512000U);

        exti_irq_init();

        REGISTER_INTERRUPT(RTC_WKUP_IRQn, RTC_WKUP_IRQ_Handler, 10U, FAULT_INTERRUPT_RATE_EXTI)
        rtc_wakeup_init();

        SCB->SCR |= SCB_SCR_SLEEPDEEP_Msk;
      }
      __WFI();
      SCB->SCR &= ~SCB_SCR_SLEEPDEEP_Msk;
    }
  }

  return 0;
}
