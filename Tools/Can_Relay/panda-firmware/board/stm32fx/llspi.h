
void spi_init(void);
int spi_cb_rx(uint8_t *data, int len, uint8_t *data_out);

#define SPI_BUF_SIZE 256
uint8_t spi_buf[SPI_BUF_SIZE];
int spi_buf_count = 0;
int spi_total_count = 0;

void spi_tx_dma(void *addr, int len) {

  register_clear_bits(&(SPI1->CR2), SPI_CR2_TXDMAEN);
  register_clear_bits(&(DMA2_Stream3->CR), DMA_SxCR_EN);

  register_set(&(DMA2_Stream3->M0AR), (uint32_t)addr, 0xFFFFFFFFU);
  DMA2_Stream3->NDTR = len;
  register_set(&(DMA2_Stream3->PAR), (uint32_t)&(SPI1->DR), 0xFFFFFFFFU);

  register_set(&(DMA2_Stream3->CR), (DMA_SxCR_CHSEL_1 | DMA_SxCR_CHSEL_0 | DMA_SxCR_MINC | DMA_SxCR_DIR_0 | DMA_SxCR_EN), 0x1E077EFEU);
  delay(0);
  register_set_bits(&(DMA2_Stream3->CR), DMA_SxCR_TCIE);

  register_set_bits(&(SPI1->CR2), SPI_CR2_TXDMAEN);

  set_gpio_output(GPIOB, 0, 0);
}

void spi_rx_dma(void *addr, int len) {

  register_clear_bits(&(SPI1->CR2), SPI_CR2_RXDMAEN);
  register_clear_bits(&(DMA2_Stream2->CR), DMA_SxCR_EN);

  volatile uint8_t dat = SPI1->DR;
  (void)dat;

  register_set(&(DMA2_Stream2->M0AR), (uint32_t)addr, 0xFFFFFFFFU);
  DMA2_Stream2->NDTR = len;
  register_set(&(DMA2_Stream2->PAR), (uint32_t)&(SPI1->DR), 0xFFFFFFFFU);

  register_set(&(DMA2_Stream2->CR), (DMA_SxCR_CHSEL_1 | DMA_SxCR_CHSEL_0 | DMA_SxCR_MINC | DMA_SxCR_EN), 0x1E077EFEU);
  delay(0);
  register_set_bits(&(DMA2_Stream2->CR), DMA_SxCR_TCIE);

  register_set_bits(&(SPI1->CR2), SPI_CR2_RXDMAEN);
}

uint8_t spi_tx_buf[0x44];

void DMA2_Stream2_IRQ_Handler(void) {
  int *resp_len = (int*)spi_tx_buf;
  (void)memset(spi_tx_buf, 0xaa, 0x44);
  *resp_len = spi_cb_rx(spi_buf, 0x14, spi_tx_buf+4);
  #ifdef DEBUG_SPI
    puts("SPI write: ");
    puth(*resp_len);
    puts("\n");
  #endif
  spi_tx_dma(spi_tx_buf, *resp_len + 4);

  DMA2->LIFCR = DMA_LIFCR_CTCIF2;
}

void DMA2_Stream3_IRQ_Handler(void) {
  #ifdef DEBUG_SPI
    puts("SPI handshake\n");
  #endif

  set_gpio_mode(GPIOB, 0, MODE_INPUT);
  set_gpio_pullup(GPIOB, 0, PULL_UP);

  DMA2->LIFCR = DMA_LIFCR_CTCIF3;
}

void EXTI4_IRQ_Handler(void) {
  volatile unsigned int pr = EXTI->PR & (1U << 4);
  #ifdef DEBUG_SPI
    puts("exti4\n");
  #endif

  if ((pr & (1U << 4)) != 0U) {
    spi_total_count = 0;
    spi_rx_dma(spi_buf, 0x14);
  }
  EXTI->PR = pr;
}

void spi_init(void) {

  REGISTER_INTERRUPT(DMA2_Stream2_IRQn, DMA2_Stream2_IRQ_Handler, 50000U, FAULT_INTERRUPT_RATE_SPI_DMA)
  REGISTER_INTERRUPT(DMA2_Stream3_IRQn, DMA2_Stream3_IRQ_Handler, 50000U, FAULT_INTERRUPT_RATE_SPI_DMA)
  REGISTER_INTERRUPT(EXTI4_IRQn, EXTI4_IRQ_Handler, 50000U, FAULT_INTERRUPT_RATE_SPI_CS)

  register_set(&(SPI1->CR1), SPI_CR1_SPE, 0xFFFFU);

  register_set(&(SPI1->CR2), SPI_CR2_RXNEIE, 0xF7U);

  NVIC_EnableIRQ(DMA2_Stream2_IRQn);
  NVIC_EnableIRQ(DMA2_Stream3_IRQn);

  set_gpio_mode(GPIOB, 0, MODE_INPUT);
  set_gpio_pullup(GPIOB, 0, PULL_UP);

  register_set(&(SYSCFG->EXTICR[2]), SYSCFG_EXTICR2_EXTI4_PA, 0xFFFFU);
  register_set_bits(&(EXTI->IMR), (1U << 4));
  register_set_bits(&(EXTI->FTSR), (1U << 4));
  NVIC_EnableIRQ(EXTI4_IRQn);
}
