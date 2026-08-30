
void uart_tx_ring(uart_ring *q){
  ENTER_CRITICAL();

  if (q->w_ptr_tx != q->r_ptr_tx) {

    if ((q->uart->SR & USART_SR_TXE) != 0) {
      q->uart->DR = q->elems_tx[q->r_ptr_tx];
      q->r_ptr_tx = (q->r_ptr_tx + 1U) % q->tx_fifo_size;
    }

    if(q->r_ptr_tx != q->w_ptr_tx){
      q->uart->CR1 |= USART_CR1_TXEIE;
    } else {
      q->uart->CR1 &= ~USART_CR1_TXEIE;
    }
  }
  EXIT_CRITICAL();
}

void uart_rx_ring(uart_ring *q){

  if (q->dma_rx == false) {
    ENTER_CRITICAL();

    uint8_t c = q->uart->DR;

    uint16_t next_w_ptr = (q->w_ptr_rx + 1U) % q->rx_fifo_size;

    if (next_w_ptr != q->r_ptr_rx) {
      q->elems_rx[q->w_ptr_rx] = c;
      q->w_ptr_rx = next_w_ptr;
      if (q->callback != NULL) {
        q->callback(q);
      }
    }

    EXIT_CRITICAL();
  }
}

void uart_send_break(uart_ring *u) {
  while ((u->uart->CR1 & USART_CR1_SBK) != 0);
  u->uart->CR1 |= USART_CR1_SBK;
}

uint32_t prev_w_index = 0;
void dma_pointer_handler(uart_ring *q, uint32_t dma_ndtr) {
  ENTER_CRITICAL();
  uint32_t w_index = (q->rx_fifo_size - dma_ndtr);

  if (w_index != prev_w_index){

    if (
      ((prev_w_index < q->r_ptr_rx) && (q->r_ptr_rx <= w_index)) ||
      ((w_index < prev_w_index) && ((q->r_ptr_rx <= w_index) || (prev_w_index < q->r_ptr_rx)))
    ){

      q->r_ptr_rx = (w_index + 1U) % q->rx_fifo_size;
    }

    q->w_ptr_rx = w_index;
  }

  prev_w_index = w_index;
  EXIT_CRITICAL();
}

#define UART_READ_DR(uart) volatile uint8_t t = (uart)->DR; UNUSED(t);

void uart_interrupt_handler(uart_ring *q) {
  ENTER_CRITICAL();

  uint32_t status = q->uart->SR;

  if((status & USART_SR_RXNE) != 0U){
    uart_rx_ring(q);
  }

  uint32_t err = (status & USART_SR_ORE) | (status & USART_SR_NE) | (status & USART_SR_FE) | (status & USART_SR_PE);
  if(err != 0U){
    #ifdef DEBUG_UART
      puts("Encountered UART error: "); puth(err); puts("\n");
    #endif
    UART_READ_DR(q->uart)
  }

  uart_tx_ring(q);

  if(q->dma_rx && (status & USART_SR_IDLE)){

    UART_READ_DR(q->uart)

    if(q == &uart_ring_gps){
      dma_pointer_handler(&uart_ring_gps, DMA2_Stream5->NDTR);
    } else {
      #ifdef DEBUG_UART
        puts("No IDLE dma_pointer_handler implemented for this UART.");
      #endif
    }
  }

  EXIT_CRITICAL();
}

void USART1_IRQ_Handler(void) { uart_interrupt_handler(&uart_ring_gps); }
void USART2_IRQ_Handler(void) { uart_interrupt_handler(&uart_ring_debug); }
void USART3_IRQ_Handler(void) { uart_interrupt_handler(&uart_ring_lin2); }
void UART5_IRQ_Handler(void) { uart_interrupt_handler(&uart_ring_lin1); }

void DMA2_Stream5_IRQ_Handler(void) {
  ENTER_CRITICAL();

  if((DMA2->HISR & DMA_HISR_TEIF5) || (DMA2->HISR & DMA_HISR_DMEIF5) || (DMA2->HISR & DMA_HISR_FEIF5)){
    #ifdef DEBUG_UART
      puts("Encountered UART DMA error. Clearing and restarting DMA...\n");
    #endif

    DMA2->HIFCR = DMA_HIFCR_CTEIF5 | DMA_HIFCR_CDMEIF5 | DMA_HIFCR_CFEIF5;

    DMA2_Stream5->CR |= DMA_SxCR_EN;
  }

  dma_pointer_handler(&uart_ring_gps, DMA2_Stream5->NDTR);
  DMA2->HIFCR = DMA_HIFCR_CTCIF5 | DMA_HIFCR_CHTIF5;

  EXIT_CRITICAL();
}

void dma_rx_init(uart_ring *q) {

  if(q == &uart_ring_gps){

    DMA2_Stream5->FCR &= ~DMA_SxFCR_DMDIS;

    DMA2_Stream5->PAR = (uint32_t)&(USART1->DR);
    DMA2_Stream5->M0AR = (uint32_t)q->elems_rx;
    DMA2_Stream5->NDTR = q->rx_fifo_size;

    DMA2_Stream5->CR = DMA_SxCR_CHSEL_2 | DMA_SxCR_MINC | DMA_SxCR_CIRC | DMA_SxCR_HTIE | DMA_SxCR_TCIE | DMA_SxCR_TEIE | DMA_SxCR_DMEIE | DMA_SxCR_EN;

    q->uart->CR3 |= USART_CR3_DMAR;

    q->uart->CR1 |= USART_CR1_IDLEIE;

    NVIC_EnableIRQ(DMA2_Stream5_IRQn);
  } else {
    puts("Tried to initialize RX DMA for an unsupported UART\n");
  }
}

#define __DIV(_PCLK_, _BAUD_)                    (((_PCLK_) * 25U) / (4U * (_BAUD_)))
#define __DIVMANT(_PCLK_, _BAUD_)                (__DIV((_PCLK_), (_BAUD_)) / 100U)
#define __DIVFRAQ(_PCLK_, _BAUD_)                ((((__DIV((_PCLK_), (_BAUD_)) - (__DIVMANT((_PCLK_), (_BAUD_)) * 100U)) * 16U) + 50U) / 100U)
#define __USART_BRR(_PCLK_, _BAUD_)              ((__DIVMANT((_PCLK_), (_BAUD_)) << 4) | (__DIVFRAQ((_PCLK_), (_BAUD_)) & 0x0FU))

void uart_set_baud(USART_TypeDef *u, unsigned int baud) {
  if (u == USART1) {

    u->BRR = __USART_BRR(48000000U, baud);
  } else {
    u->BRR = __USART_BRR(24000000U, baud);
  }
}

void uart_init(uart_ring *q, int baud) {

  if(q->uart == USART1){
    REGISTER_INTERRUPT(USART1_IRQn, USART1_IRQ_Handler, 150000U, FAULT_INTERRUPT_RATE_UART_1)
  } else if (q->uart == USART2){
    REGISTER_INTERRUPT(USART2_IRQn, USART2_IRQ_Handler, 150000U, FAULT_INTERRUPT_RATE_UART_2)
  } else if (q->uart == USART3){
    REGISTER_INTERRUPT(USART3_IRQn, USART3_IRQ_Handler, 150000U, FAULT_INTERRUPT_RATE_UART_3)
  } else if (q->uart == UART5){
    REGISTER_INTERRUPT(UART5_IRQn, UART5_IRQ_Handler, 150000U, FAULT_INTERRUPT_RATE_UART_5)
  } else {

  }
  if(q->dma_rx){
    REGISTER_INTERRUPT(DMA2_Stream5_IRQn, DMA2_Stream5_IRQ_Handler, 100U, FAULT_INTERRUPT_RATE_UART_DMA)
  }

  uart_set_baud(q->uart, baud);
  q->uart->CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
  if ((q->uart == USART2) || (q->uart == USART3) || (q->uart == UART5)) {
    q->uart->CR1 |= USART_CR1_RXNEIE;
  }

  if(q->uart == USART1){
    NVIC_EnableIRQ(USART1_IRQn);
  } else if (q->uart == USART2){
    NVIC_EnableIRQ(USART2_IRQn);
  } else if (q->uart == USART3){
    NVIC_EnableIRQ(USART3_IRQn);
  } else if (q->uart == UART5){
    NVIC_EnableIRQ(UART5_IRQn);
  } else {

  }

  if(q->dma_rx){
    dma_rx_init(q);
  }
}
