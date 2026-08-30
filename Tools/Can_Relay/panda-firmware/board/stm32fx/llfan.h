
void EXTI2_IRQ_Handler(void) {
    volatile unsigned int pr = EXTI->PR & (1U << 2);
    if ((pr & (1U << 2)) != 0U) {
        fan_tach_counter++;
    }
    EXTI->PR = (1U << 2);
}

void fan_init(void){

    REGISTER_INTERRUPT(EXTI2_IRQn, EXTI2_IRQ_Handler, 700U, FAULT_INTERRUPT_RATE_TACH)

    pwm_init(TIM3, 3);

    register_set(&(SYSCFG->EXTICR[0]), SYSCFG_EXTICR1_EXTI2_PD, 0xF00U);
    register_set_bits(&(EXTI->IMR), (1U << 2));
    register_set_bits(&(EXTI->RTSR), (1U << 2));
    register_set_bits(&(EXTI->FTSR), (1U << 2));
    NVIC_EnableIRQ(EXTI2_IRQn);
}
