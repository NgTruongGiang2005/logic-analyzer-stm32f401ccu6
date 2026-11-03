/**
  ******************************************************************************
  * @file    la_testgen.c
  * @brief   Triển khai kênh phát tín hiệu mẫu tự kiểm tra trên chân PA9.
  *          Thành viên phụ trách: TV1 (Firmware STM32).
  ******************************************************************************
  */

#include "la_testgen.h"
#include <string.h>

static const char *TEST_MESSAGE = "TEST_LA_2026\r\n";
static uint32_t g_last_tx_tick = 0;

/* Giả lập lấy tick hệ thống từ HAL_GetTick hoặc biến đếm SysTick */
extern uint32_t HAL_GetTick(void);

void la_testgen_init(void)
{
    /* Cấu hình USART1 trên PA9 (Baudrate 115200, 8-N-1) */
    /* Khi tạo project bằng CubeMX, cấu hình USART1_TX trên PA9 */
    g_last_tx_tick = 0;
}

void la_testgen_process(void)
{
    uint32_t now = HAL_GetTick();
    /* Phát chuỗi test định kỳ mỗi 50 ms */
    if (now - g_last_tx_tick >= 50) {
        g_last_tx_tick = now;
        /* TODO: Gọi hàm truyền USART1 (ví dụ HAL_UART_Transmit_IT hoặc LL_USART) */
        /* HAL_UART_Transmit(&huart1, (uint8_t*)TEST_MESSAGE, strlen(TEST_MESSAGE), 10); */
    }
}
