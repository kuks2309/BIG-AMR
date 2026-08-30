#define RCC_BDCR_MASK_LSE (RCC_BDCR_RTCEN | RCC_BDCR_RTCSEL | RCC_BDCR_LSEDRV | RCC_BDCR_LSEBYP | RCC_BDCR_LSEON)
#define RCC_BDCR_MASK_LSI (RCC_BDCR_RTCEN | RCC_BDCR_RTCSEL)

void enable_bdomain_protection(void) {
  register_clear_bits(&(PWR->CR1), PWR_CR1_DBP);
}

void disable_bdomain_protection(void) {
  register_set_bits(&(PWR->CR1), PWR_CR1_DBP);
}

void rtc_wakeup_init(void) {
  EXTI->IMR1  |=  EXTI_IMR1_IM19;
  EXTI->RTSR1 |=  EXTI_RTSR1_TR19;
  EXTI->FTSR1 &=  ~EXTI_FTSR1_TR19;

  NVIC_DisableIRQ(RTC_WKUP_IRQn);

  disable_bdomain_protection();
  RTC->WPR = 0xCA;
  RTC->WPR = 0x53;

  RTC->CR &= ~RTC_CR_WUTE;
  while((RTC->ISR & RTC_ISR_WUTWF) == 0){}

  RTC->CR &= ~RTC_CR_WUTIE;
  RTC->ISR &= ~RTC_ISR_WUTF;

  RTC->WUTR = DEEPSLEEP_WAKEUP_DELAY;

  RTC->CR |= RTC_CR_WUTE | RTC_CR_WUTIE | RTC_CR_WUCKSEL_2;

  RTC->WPR = 0x00;
  enable_bdomain_protection();

  NVIC_EnableIRQ(RTC_WKUP_IRQn);
}
