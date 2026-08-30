
#define CAN_PCLK 80000U
#define BITRATE_PRESCALER 2U
#define CAN_SP_NOMINAL 80U
#define CAN_SP_DATA_2M 80U
#define CAN_SP_DATA_5M 75U
#define CAN_QUANTA(speed, prescaler) (CAN_PCLK / ((speed) / 10U * (prescaler)))
#define CAN_SEG1(tq, sp) (((tq) * (sp) / 100U)- 1U)
#define CAN_SEG2(tq, sp) ((tq) * (100U - (sp)) / 100U)

#define FDCAN_MESSAGE_RAM_SIZE 0x2800UL
#define FDCAN_START_ADDRESS 0x4000AC00UL
#define FDCAN_OFFSET 3412UL
#define FDCAN_OFFSET_W 853UL
#define FDCAN_END_ADDRESS 0x4000D3FCUL

#define FDCAN_RX_FIFO_0_EL_CNT 24UL
#define FDCAN_RX_FIFO_0_HEAD_SIZE 8UL
#define FDCAN_RX_FIFO_0_DATA_SIZE 64UL
#define FDCAN_RX_FIFO_0_EL_SIZE (FDCAN_RX_FIFO_0_HEAD_SIZE + FDCAN_RX_FIFO_0_DATA_SIZE)
#define FDCAN_RX_FIFO_0_EL_W_SIZE (FDCAN_RX_FIFO_0_EL_SIZE / 4UL)
#define FDCAN_RX_FIFO_0_OFFSET 0UL

#define FDCAN_TX_FIFO_EL_CNT 16UL
#define FDCAN_TX_FIFO_HEAD_SIZE 8UL
#define FDCAN_TX_FIFO_DATA_SIZE 64UL
#define FDCAN_TX_FIFO_EL_SIZE (FDCAN_TX_FIFO_HEAD_SIZE + FDCAN_TX_FIFO_DATA_SIZE)
#define FDCAN_TX_FIFO_EL_W_SIZE (FDCAN_TX_FIFO_EL_SIZE / 4UL)
#define FDCAN_TX_FIFO_OFFSET (FDCAN_RX_FIFO_0_OFFSET + (FDCAN_RX_FIFO_0_EL_CNT * FDCAN_RX_FIFO_0_EL_W_SIZE))

#define CAN_NAME_FROM_CANIF(CAN_DEV) (((CAN_DEV)==FDCAN1) ? "FDCAN1" : (((CAN_DEV) == FDCAN2) ? "FDCAN2" : "FDCAN3"))
#define CAN_NUM_FROM_CANIF(CAN_DEV) (((CAN_DEV)==FDCAN1) ? 0UL : (((CAN_DEV) == FDCAN2) ? 1UL : 2UL))

void puts(const char *a);

bool fdcan_request_init(FDCAN_GlobalTypeDef *CANx) {
  bool ret = true;

  CANx->CCCR &= ~(FDCAN_CCCR_CSR);
  while ((CANx->CCCR & FDCAN_CCCR_CSA) == FDCAN_CCCR_CSA);

  uint32_t timeout_counter = 0U;
  CANx->CCCR |= FDCAN_CCCR_INIT;
  while ((CANx->CCCR & FDCAN_CCCR_INIT) == 0) {

    delay(10000);
    timeout_counter++;

    if (timeout_counter >= CAN_INIT_TIMEOUT_MS){
      ret = false;
      break;
    }
  }
  return ret;
}

bool fdcan_exit_init(FDCAN_GlobalTypeDef *CANx) {
  bool ret = true;

  CANx->CCCR &= ~(FDCAN_CCCR_INIT);
  uint32_t timeout_counter = 0U;
  while ((CANx->CCCR & FDCAN_CCCR_INIT) != 0) {

    delay(10000);
    timeout_counter++;

    if (timeout_counter >= CAN_INIT_TIMEOUT_MS) {
      ret = false;
      break;
    }
  }
  return ret;
}

bool llcan_set_speed(FDCAN_GlobalTypeDef *CANx, uint32_t speed, uint32_t data_speed, bool loopback, bool silent) {
  UNUSED(speed);
  bool ret = fdcan_request_init(CANx);

  if (ret) {

    CANx->CCCR |= FDCAN_CCCR_CCE;

    CANx->CCCR &= ~(FDCAN_CCCR_TEST);
    CANx->TEST &= ~(FDCAN_TEST_LBCK);
    CANx->CCCR &= ~(FDCAN_CCCR_MON);
    CANx->CCCR &= ~(FDCAN_CCCR_ASM);

    uint8_t prescaler = BITRATE_PRESCALER;
    if (speed < 2500U) {

      prescaler = BITRATE_PRESCALER * 16U;
    }

    uint16_t tq = CAN_QUANTA(speed, prescaler);
    uint8_t sp = CAN_SP_NOMINAL;
    uint8_t seg1 = CAN_SEG1(tq, sp);
    uint8_t seg2 = CAN_SEG2(tq, sp);
    uint8_t sjw = seg2;

    CANx->NBTP = (((sjw & 0x7FU)-1U)<<FDCAN_NBTP_NSJW_Pos) | (((seg1 & 0xFFU)-1U)<<FDCAN_NBTP_NTSEG1_Pos) | (((seg2 & 0x7FU)-1U)<<FDCAN_NBTP_NTSEG2_Pos) | (((prescaler & 0x1FFU)-1U)<<FDCAN_NBTP_NBRP_Pos);

    if (data_speed == 50000U) {
      sp = CAN_SP_DATA_5M;
    } else {
      sp = CAN_SP_DATA_2M;
    }
    tq = CAN_QUANTA(data_speed, prescaler);
    seg1 = CAN_SEG1(tq, sp);
    seg2 = CAN_SEG2(tq, sp);
    sjw = seg2;

    CANx->DBTP = (((sjw & 0xFU)-1U)<<FDCAN_DBTP_DSJW_Pos) | (((seg1 & 0x1FU)-1U)<<FDCAN_DBTP_DTSEG1_Pos) | (((seg2 & 0xFU)-1U)<<FDCAN_DBTP_DTSEG2_Pos) | (((prescaler & 0x1FU)-1U)<<FDCAN_DBTP_DBRP_Pos);

    if (loopback) {
      CANx->CCCR |= FDCAN_CCCR_TEST;
      CANx->TEST |= FDCAN_TEST_LBCK;
      CANx->CCCR |= FDCAN_CCCR_MON;
    }

    if (silent) {
      CANx->CCCR |= FDCAN_CCCR_MON;
    }
    ret = fdcan_exit_init(CANx);
    if (!ret) {
      puts(CAN_NAME_FROM_CANIF(CANx)); puts(" set_speed timed out! (2)\n");
    }
  } else {
    puts(CAN_NAME_FROM_CANIF(CANx)); puts(" set_speed timed out! (1)\n");
  }
  return ret;
}

bool llcan_init(FDCAN_GlobalTypeDef *CANx) {
  uint32_t can_number = CAN_NUM_FROM_CANIF(CANx);
  bool ret = fdcan_request_init(CANx);

  if (ret) {

    CANx->CCCR |= FDCAN_CCCR_CCE;

    CANx->CCCR &= ~(FDCAN_CCCR_DAR);

    CANx->CCCR |= FDCAN_CCCR_TXP;

    CANx->CCCR |= FDCAN_CCCR_PXHD;

    CANx->CCCR |= (FDCAN_CCCR_FDOE | FDCAN_CCCR_BRSE);

    CANx->TXBC &= ~(FDCAN_TXBC_TFQM);

    CANx->TXESC |= 0x7U << FDCAN_TXESC_TBDS_Pos;

    CANx->RXESC |= 0x7U << FDCAN_RXESC_F0DS_Pos;

    CANx->XIDFC &= ~(FDCAN_XIDFC_LSE);
    CANx->SIDFC &= ~(FDCAN_SIDFC_LSS);
    CANx->GFC &= ~(FDCAN_GFC_RRFE);
    CANx->GFC &= ~(FDCAN_GFC_RRFS);
    CANx->GFC &= ~(FDCAN_GFC_ANFE);
    CANx->GFC &= ~(FDCAN_GFC_ANFS);

    uint32_t RxFIFO0SA = FDCAN_START_ADDRESS + (can_number * FDCAN_OFFSET);
    uint32_t TxFIFOSA = RxFIFO0SA + (FDCAN_RX_FIFO_0_EL_CNT * FDCAN_RX_FIFO_0_EL_SIZE);

    CANx->RXF0C |= (FDCAN_RX_FIFO_0_OFFSET + (can_number * FDCAN_OFFSET_W)) << FDCAN_RXF0C_F0SA_Pos;
    CANx->RXF0C |= FDCAN_RX_FIFO_0_EL_CNT << FDCAN_RXF0C_F0S_Pos;

    CANx->RXF0C |= FDCAN_RXF0C_F0OM;

    CANx->TXBC |= (FDCAN_TX_FIFO_OFFSET + (can_number * FDCAN_OFFSET_W)) << FDCAN_TXBC_TBSA_Pos;
    CANx->TXBC |= FDCAN_TX_FIFO_EL_CNT << FDCAN_TXBC_TFQS_Pos;

    uint32_t EndAddress = TxFIFOSA + (FDCAN_TX_FIFO_EL_CNT * FDCAN_TX_FIFO_EL_SIZE);
    for (uint32_t RAMcounter = RxFIFO0SA; RAMcounter < EndAddress; RAMcounter += 4U) {
        *(uint32_t *)(RAMcounter) = 0x00000000;
    }

    CANx->ILE = (FDCAN_ILE_EINT0 | FDCAN_ILE_EINT1);

    CANx->IE &= 0x0U;

    CANx->IE |= FDCAN_IE_RF0NE;

    CANx->ILS |= FDCAN_ILS_TFEL;
    CANx->IE |= FDCAN_IE_TFEE;

    ret = fdcan_exit_init(CANx);
    if(!ret) {
      puts(CAN_NAME_FROM_CANIF(CANx)); puts(" llcan_init timed out (2)!\n");
    }

    if (CANx == FDCAN1) {
      NVIC_EnableIRQ(FDCAN1_IT0_IRQn);
      NVIC_EnableIRQ(FDCAN1_IT1_IRQn);
    } else if (CANx == FDCAN2) {
      NVIC_EnableIRQ(FDCAN2_IT0_IRQn);
      NVIC_EnableIRQ(FDCAN2_IT1_IRQn);
    } else if (CANx == FDCAN3) {
      NVIC_EnableIRQ(FDCAN3_IT0_IRQn);
      NVIC_EnableIRQ(FDCAN3_IT1_IRQn);
    } else {
      puts("Invalid CAN: initialization failed\n");
    }

  } else {
    puts(CAN_NAME_FROM_CANIF(CANx)); puts(" llcan_init timed out (1)!\n");
  }
  return ret;
}

void llcan_clear_send(FDCAN_GlobalTypeDef *CANx) {

  UNUSED(CANx);
}
