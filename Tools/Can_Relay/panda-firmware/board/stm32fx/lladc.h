
#define ADCCHAN_ACCEL0 10
#define ADCCHAN_ACCEL1 11
#define ADCCHAN_VOLTAGE 12
#define ADCCHAN_CURRENT 13

void register_set(volatile uint32_t *addr, uint32_t val, uint32_t mask);

void adc_init(void) {
  register_set(&(ADC->CCR), ADC_CCR_TSVREFE | ADC_CCR_VBATE, 0xC30000U);
  register_set(&(ADC1->CR2), ADC_CR2_ADON, 0xFF7F0F03U);
  register_set(&(ADC1->SMPR1), ADC_SMPR1_SMP12 | ADC_SMPR1_SMP13, 0x7FFFFFFU);
}

uint32_t adc_get(unsigned int channel) {

  register_set(&(ADC1->JSQR), (channel << 15U), 0x3FFFFFU);

  ADC1->SR &= ~(ADC_SR_JEOC);
  ADC1->CR2 |= ADC_CR2_JSWSTART;
  while (!(ADC1->SR & ADC_SR_JEOC));

  return ADC1->JDR1;
}

uint32_t adc_get_voltage(void) {

  return (adc_get(ADCCHAN_VOLTAGE) * 8862U) / 1000U;
}
