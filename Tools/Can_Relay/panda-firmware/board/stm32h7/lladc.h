
#define ADCCHAN_VOLTAGE 2

void adc_init(void) {
  ADC1->CR &= ~(ADC_CR_DEEPPWD);
  ADC1->CR |= ADC_CR_ADVREGEN;
  while(!(ADC1->ISR & ADC_ISR_LDORDY));

  ADC1->CR &= ~(ADC_CR_ADCALDIF);
  ADC1->CR |= ADC_CR_ADCALLIN;
  ADC1->CR |= ADC_CR_ADCAL;
  while((ADC1->CR & ADC_CR_ADCAL) != 0);

  ADC1->ISR |= ADC_ISR_ADRDY;
  ADC1->CR |= ADC_CR_ADEN;
  while(!(ADC1->ISR & ADC_ISR_ADRDY));
}

uint32_t adc_get(unsigned int channel) {

  ADC1->SQR1 &= ~(ADC_SQR1_L);
  ADC1->SQR1 = (channel << 6U);

  ADC1->SMPR1 = (0x7U << (channel * 3U) );
  ADC1->PCSEL_RES0 = (0x1U << channel);

  ADC1->CR |= ADC_CR_ADSTART;
  while (!(ADC1->ISR & ADC_ISR_EOC));

  uint16_t res = ADC1->DR;

  while (!(ADC1->ISR & ADC_ISR_EOS));
  ADC1->ISR |= ADC_ISR_EOS;

  return res;
}

uint32_t adc_get_voltage(void) {

  return (adc_get(ADCCHAN_VOLTAGE) * 5539U) / 10000U;
}
