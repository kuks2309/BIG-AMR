#define GMLAN_TICKS_PER_SECOND 33300
#define GMLAN_TICKS_PER_TIMEOUT_TICKLE 500
#define GMLAN_HIGH 0
#define GMLAN_LOW 1

#define DISABLED -1
#define BITBANG 0
#define GPIO_SWITCH 1

#define MAX_BITS_CAN_PACKET (200)

int gmlan_alt_mode = DISABLED;

int do_bitstuff(char *out, char *in, int in_len) {
  int last_bit = -1;
  int bit_cnt = 0;
  int j = 0;
  for (int i = 0; i < in_len; i++) {
    char bit = in[i];
    out[j] = bit;
    j++;

    if (bit == last_bit) {
      bit_cnt++;
      if (bit_cnt == 5) {

        last_bit = !bit;
        out[j] = last_bit;
        j++;
        bit_cnt = 1;
      }
    } else {

      last_bit = bit;
      bit_cnt = 1;
    }
  }
  return j;
}

int append_crc(char *in, int in_len) {
  unsigned int crc = 0;
  for (int i = 0; i < in_len; i++) {
    crc <<= 1;
    if (((unsigned int)(in[i]) ^ ((crc >> 15) & 1U)) != 0U) {
      crc = crc ^ 0x4599U;
    }
    crc &= 0x7fffU;
  }
  int in_len_copy = in_len;
  for (int i = 14; i >= 0; i--) {
    in[in_len_copy] = (crc >> (unsigned int)(i)) & 1U;
    in_len_copy++;
  }
  return in_len_copy;
}

int append_bits(char *in, int in_len, char *app, int app_len) {
  int in_len_copy = in_len;
  for (int i = 0; i < app_len; i++) {
    in[in_len_copy] = app[i];
    in_len_copy++;
  }
  return in_len_copy;
}

int append_int(char *in, int in_len, int val, int val_len) {
  int in_len_copy = in_len;
  for (int i = val_len - 1; i >= 0; i--) {
    in[in_len_copy] = ((unsigned int)(val) & (1U << (unsigned int)(i))) != 0U;
    in_len_copy++;
  }
  return in_len_copy;
}

int get_bit_message(char *out, CANPacket_t *to_bang) {
  char pkt[MAX_BITS_CAN_PACKET];
  char footer[] = {
    1,
    1,
    1,
    1,1,1,1,1,1,1,
    1,1,1,
  };

  int len = 0;

  int dlc_len = GET_LEN(to_bang);
  len = append_int(pkt, len, 0, 1);

  if (to_bang->extended != 0U) {

    len = append_int(pkt, len, GET_ADDR(to_bang) >> 18, 11);
    len = append_int(pkt, len, 3, 2);
    len = append_int(pkt, len, (GET_ADDR(to_bang)) & ((1U << 18) - 1U), 18);
    len = append_int(pkt, len, 0, 3);
  } else {

    len = append_int(pkt, len, GET_ADDR(to_bang), 11);
    len = append_int(pkt, len, 0, 3);
  }

  len = append_int(pkt, len, dlc_len, 4);

  for (int i = 0; i < dlc_len; i++) {
    len = append_int(pkt, len, to_bang->data[i], 8);
  }

  len = append_crc(pkt, len);

  len = do_bitstuff(out, pkt, len);

  len = append_bits(out, len, footer, sizeof(footer));
  return len;
}

void TIM12_IRQ_Handler(void);

void setup_timer(void) {

  REGISTER_INTERRUPT(TIM8_BRK_TIM12_IRQn, TIM12_IRQ_Handler, 40000U, FAULT_INTERRUPT_RATE_GMLAN)

  register_set(&(TIM12->PSC), (48-1), 0xFFFFU);
  register_set(&(TIM12->CR1), TIM_CR1_CEN, 0x3FU);
  register_set(&(TIM12->ARR), (30-1), 0xFFFFU);

  NVIC_EnableIRQ(TIM8_BRK_TIM12_IRQn);

  register_set(&(TIM12->DIER), TIM_DIER_UIE, 0x5F5FU);
  TIM12->SR = 0;
}

int gmlan_timeout_counter = GMLAN_TICKS_PER_TIMEOUT_TICKLE;
int can_timeout_counter = GMLAN_TICKS_PER_SECOND;

int inverted_bit_to_send = GMLAN_HIGH;
int gmlan_switch_below_timeout = -1;
int gmlan_switch_timeout_enable = 0;

void gmlan_switch_init(int timeout_enable) {
  gmlan_switch_timeout_enable = timeout_enable;
  gmlan_alt_mode = GPIO_SWITCH;
  gmlan_switch_below_timeout = 1;
  set_gpio_mode(GPIOB, 13, MODE_OUTPUT);

  setup_timer();

  inverted_bit_to_send = GMLAN_LOW;
}

void set_gmlan_digital_output(int to_set) {
  inverted_bit_to_send = to_set;

}

void reset_gmlan_switch_timeout(void) {
  can_timeout_counter = GMLAN_TICKS_PER_SECOND;
  gmlan_switch_below_timeout = 1;
  gmlan_alt_mode = GPIO_SWITCH;
}

void set_bitbanged_gmlan(int val) {
  if (val != 0) {
    register_set_bits(&(GPIOB->ODR), (1U << 13));
  } else {
    register_clear_bits(&(GPIOB->ODR), (1U << 13));
  }
}

char pkt_stuffed[MAX_BITS_CAN_PACKET];
int gmlan_sending = -1;
int gmlan_sendmax = -1;
bool gmlan_send_ok = true;

int gmlan_silent_count = 0;
int gmlan_fail_count = 0;
#define REQUIRED_SILENT_TIME 10
#define MAX_FAIL_COUNT 10

void TIM12_IRQ_Handler(void) {
  if (gmlan_alt_mode == BITBANG) {
    if ((TIM12->SR & TIM_SR_UIF) && (gmlan_sendmax != -1)) {
      int read = get_gpio_input(GPIOB, 12);
      if (gmlan_silent_count < REQUIRED_SILENT_TIME) {
        if (read == 0) {
          gmlan_silent_count = 0;
        } else {
          gmlan_silent_count++;
        }
      } else {
        bool retry = 0;

        if ((gmlan_sending > 0) &&
           ((read == 0) && (pkt_stuffed[gmlan_sending-1] == 1)) &&
           (gmlan_sending != (gmlan_sendmax - 11))) {
          puts("GMLAN ERR: bus driven at ");
          puth(gmlan_sending);
          puts("\n");
          retry = 1;
        } else if ((read == 1) && (gmlan_sending == (gmlan_sendmax - 11))) {
          puts("GMLAN ERR: didn't recv ACK\n");
          retry = 1;
        } else {

        }
        if (retry) {

          set_bitbanged_gmlan(1);
          gmlan_silent_count = 0;
          gmlan_sending = 0;
          gmlan_fail_count++;
          if (gmlan_fail_count == MAX_FAIL_COUNT) {
            puts("GMLAN ERR: giving up send\n");
            gmlan_send_ok = false;
          }
        } else {
          set_bitbanged_gmlan(pkt_stuffed[gmlan_sending]);
          gmlan_sending++;
        }
      }
      if ((gmlan_sending == gmlan_sendmax) || (gmlan_fail_count == MAX_FAIL_COUNT)) {
        set_bitbanged_gmlan(1);
        set_gpio_mode(GPIOB, 13, MODE_INPUT);
        register_clear_bits(&(TIM12->DIER), TIM_DIER_UIE);
        register_set(&(TIM12->CR1), 0U, 0x3FU);
        gmlan_sendmax = -1;
      }
    }
  } else if (gmlan_alt_mode == GPIO_SWITCH) {
    if ((TIM12->SR & TIM_SR_UIF) && (gmlan_switch_below_timeout != -1)) {
      if ((can_timeout_counter == 0) && gmlan_switch_timeout_enable) {

        set_gpio_output(GPIOB, 13, GMLAN_LOW);
        gmlan_switch_below_timeout = -1;
        gmlan_timeout_counter = GMLAN_TICKS_PER_TIMEOUT_TICKLE;
        gmlan_alt_mode = DISABLED;
      }
      else {
        can_timeout_counter--;
        if (gmlan_timeout_counter == 0) {

          gmlan_timeout_counter = GMLAN_TICKS_PER_TIMEOUT_TICKLE;
          set_gpio_output(GPIOB, 13, GMLAN_LOW);
        }
        else {
          set_gpio_output(GPIOB, 13, inverted_bit_to_send);
          gmlan_timeout_counter--;
        }
      }
    }
  } else {

  }
  TIM12->SR = 0;
}

bool bitbang_gmlan(CANPacket_t *to_bang) {
  gmlan_send_ok = true;
  gmlan_alt_mode = BITBANG;

  if (gmlan_sendmax == -1) {
    int len = get_bit_message(pkt_stuffed, to_bang);
    gmlan_fail_count = 0;
    gmlan_silent_count = 0;
    gmlan_sending = 0;
    gmlan_sendmax = len;

    set_bitbanged_gmlan(1);
    set_gpio_mode(GPIOB, 13, MODE_OUTPUT);

    setup_timer();
  }
  return gmlan_send_ok;
}
