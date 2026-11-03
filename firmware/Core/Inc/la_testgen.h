/**
  ******************************************************************************
  * @file    la_testgen.h
  * @brief   Kênh phát tín hiệu mẫu tự kiểm tra trên chân PA9 (USART1_TX).
  *          Thành viên phụ trách: TV1 (Firmware STM32).
  ******************************************************************************
  */

#ifndef INC_LA_TESTGEN_H_
#define INC_LA_TESTGEN_H_

#include <stdint.h>

/* Khởi tạo bộ phát UART test trên chân PA9 (115.200 bps) */
void la_testgen_init(void);

/* Vòng lặp phát chuỗi TEST_LA_2026 định kỳ (gọi trong while(1)) */
void la_testgen_process(void);

#endif /* INC_LA_TESTGEN_H_ */
