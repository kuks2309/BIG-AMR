uint16_t fan_tach_counter = 0U;
uint16_t fan_rpm = 0U;

void fan_set_power(uint8_t percentage){
  pwm_set(TIM3, 3, percentage);
}

void fan_tick(void){

    fan_rpm = fan_tach_counter * 15U;
    fan_tach_counter = 0U;
}
