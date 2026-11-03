/**
  ******************************************************************************
  * @file    la_core.c
  * @brief   Triển khai bộ điều khiển lõi Logic Analyzer.
  *          Thành viên phụ trách: TV1 (Firmware STM32).
  ******************************************************************************
  */

#include "la_core.h"
#include "la_protocol.h"

/* Bộ đệm vòng 32 KB nằm trong SRAM STM32F401CCU6 (64 KB tổng) */
uint8_t la_capture_buffer[LA_BUFFER_SIZE];

/* Biến trạng thái máy trạng thái */
static volatile la_state_t g_la_state = LA_STATE_IDLE;
static volatile uint8_t  g_current_rate_idx = 0;
static volatile uint8_t  g_current_trig_cfg = 0;
static volatile uint32_t g_timeout_counter_ms = 0;
static volatile uint32_t g_timeout_limit_ms = 2000;

/* Bảng nạp ARR cho TIM1 (PSC = 0, SYSCLK = 84 MHz) */
const uint16_t TIM1_ARR_TABLE[9] = {
    13,    /* Mức 0: 6 MHz */
    27,    /* Mức 1: 3 MHz */
    41,    /* Mức 2: 2 MHz */
    83,    /* Mức 3: 1 MHz */
    167,   /* Mức 4: 500 kHz */
    419,   /* Mức 5: 200 kHz */
    839,   /* Mức 6: 100 kHz */
    1679,  /* Mức 7: 50 kHz */
    8399   /* Mức 8: 10 kHz */
};

void la_core_init(void)
{
    g_la_state = LA_STATE_IDLE;
    /* Khởi tạo cấu hình ban đầu cho GPIO, Timer, DMA nếu cần */
}

la_state_t la_core_get_state(void)
{
    return g_la_state;
}

bool la_core_start_capture(uint8_t rate_idx, uint8_t trig_cfg)
{
    if (g_la_state != LA_STATE_IDLE) {
        return false; /* Đang bận */
    }

    if (rate_idx > 8) {
        return false; /* RATE_IDX không hợp lệ */
    }

    g_current_rate_idx = rate_idx;
    g_current_trig_cfg = trig_cfg;

    /* Tính toán thời gian timeout: (16384 / fs) + 2000ms */
    /* fs từ bảng tần số */
    g_timeout_counter_ms = 0;
    g_timeout_limit_ms = 2000; /* Mặc định cho tần số cao, TV1 mở rộng thêm cho 10kHz */

    g_la_state = LA_STATE_ARMED;

    /* TODO: Kích hoạt DMA2_Stream5 Channel 6 đọc GPIOA->IDR vào la_capture_buffer */
    /* TODO: Kích hoạt TIM1 */

    g_la_state = LA_STATE_PRE_SAMPLING;
    return true;
}

void la_core_abort(void)
{
    /* Dừng khẩn cấp TIM1, TIM2, DMA2 */
    g_la_state = LA_STATE_IDLE;
}

void la_core_on_dma_ht_isr(void)
{
    /* Gọi khi nạp được 50% = 16.384 mẫu >= 20% Pre-trigger */
    if (g_la_state == LA_STATE_PRE_SAMPLING) {
        uint8_t mode = g_current_trig_cfg & 0x0F;
        if (mode == 0x00) {
            /* Free-run: Không chờ EXTI, kích hoạt ngay TIM2 One-Pulse */
            g_la_state = LA_STATE_POST_SAMPLING;
            /* TODO: Bật TIM2 One-Pulse */
        } else {
            /* Kích hoạt ngắt EXTI trên chân chỉ định */
            g_la_state = LA_STATE_WAIT_TRIGGER;
            /* TODO: Unmask EXTI */
        }
    }
}

void la_core_on_exti_trigger_isr(void)
{
    if (g_la_state == LA_STATE_WAIT_TRIGGER) {
        /* Bật TIM2 đếm 26.214 xung Post-trigger */
        /* TODO: TIM2->CR1 |= TIM_CR1_CEN */
        g_la_state = LA_STATE_POST_SAMPLING;
    }
}

void la_core_on_tim2_period_elapsed_isr(void)
{
    if (g_la_state == LA_STATE_POST_SAMPLING) {
        /* Dừng TIM1 và DMA ngay lập tức */
        /* TODO: TIM1->CR1 &= ~TIM_CR1_CEN */
        g_la_state = LA_STATE_TRANSFERRING;
    }
}

void la_core_process(void)
{
    if (g_la_state == LA_STATE_TRANSFERRING) {
        /* Thực hiện đóng gói 32.776 Bytes và truyền qua USB-CDC phân đoạn 512B */
        la_protocol_send_data_frame(0x00, LA_TRIG_OFFSET_DEFAULT, la_capture_buffer, LA_BUFFER_SIZE);
        g_la_state = LA_STATE_IDLE;
    }
}
