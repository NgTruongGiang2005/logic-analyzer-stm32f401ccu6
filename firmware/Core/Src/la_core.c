/**
  ******************************************************************************
  * @file    la_core.c
  * @brief   Triển khai bộ điều khiển lõi Logic Analyzer.
  *          Thành viên phụ trách: TV1 (Firmware STM32).
  ******************************************************************************
  */

#include "la_core.h"
#include "la_protocol.h"

#if __has_include("main.h")
#include "main.h"
#endif

#if defined(HAL_TIM_MODULE_ENABLED) || defined(TIM1)
#if __has_include("tim.h")
#include "tim.h"
#endif
#if __has_include("dma.h")
#include "dma.h"
#endif
extern TIM_HandleTypeDef htim1;
extern TIM_HandleTypeDef htim2;
extern DMA_HandleTypeDef hdma_tim1_up;
#endif

/* Bộ đệm vòng 32 KB nằm trong SRAM STM32F401CCU6 (64 KB tổng, căn lề 4 byte) */
uint8_t la_capture_buffer[LA_BUFFER_SIZE] __attribute__((aligned(4)));

/* Biến trạng thái máy trạng thái */
static volatile la_state_t g_la_state = LA_STATE_IDLE;
static volatile uint8_t  g_current_rate_idx = 0;
static volatile uint8_t  g_current_trig_cfg = 0;
static volatile uint16_t g_captured_write_pos = 0;
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
    g_captured_write_pos = 0;

#if defined(TIM1)
    /* Cấu hình chu kỳ đếm Post-trigger cho TIM2 (đếm đúng 26.214 mẫu) */
    TIM2->ARR = LA_POST_TRIGGER_SAMPLES - 1; /* 26213 */

    /* Bật cờ ngắt Update cho TIM2 */
    __HAL_TIM_ENABLE_IT(&htim2, TIM_IT_UPDATE);

    /* Xóa sạch cờ ngắt DMA2 Stream 5 */
    DMA2->HIFCR = DMA_HIFCR_CTCIF5 | DMA_HIFCR_CHTIF5 | DMA_HIFCR_CTEIF5 |
                  DMA_HIFCR_CDMEIF5 | DMA_HIFCR_CFEIF5;
#endif
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
    g_timeout_counter_ms = 0;
    g_timeout_limit_ms = 2000;

    g_la_state = LA_STATE_ARMED;

#if defined(TIM1)
    /* 1. Dừng an toàn các Timer và DMA nếu đang chạy */
    TIM1->CR1 &= ~TIM_CR1_CEN;
    TIM2->CR1 &= ~TIM_CR1_CEN;
    DMA2_Stream5->CR &= ~DMA_SxCR_EN;

    /* 2. Cấu hình tần số lấy mẫu trên TIM1 */
    TIM1->ARR = TIM1_ARR_TABLE[rate_idx];
    TIM1->CNT = 0;

    /* 3. Cấu hình đếm 26.214 mẫu trên TIM2 One-Pulse */
    TIM2->ARR = LA_POST_TRIGGER_SAMPLES - 1; /* 26213 */
    TIM2->CNT = 0;

    /* 4. Xóa cờ ngắt cũ trên DMA2 Stream 5 */
    DMA2->HIFCR = DMA_HIFCR_CTCIF5 | DMA_HIFCR_CHTIF5 | DMA_HIFCR_CTEIF5 |
                  DMA_HIFCR_CDMEIF5 | DMA_HIFCR_CFEIF5;

    /* 5. Khởi động DMA2 Stream 5 đọc trực tiếp từ GPIOA->IDR vào buffer 32KB vòng */
    HAL_DMA_Start_IT(&hdma_tim1_up, (uint32_t)&(GPIOA->IDR), (uint32_t)la_capture_buffer, LA_BUFFER_SIZE);

    /* 6. Cho phép TIM1 phát yêu cầu DMA Update */
    __HAL_TIM_ENABLE_DMA(&htim1, TIM_DMA_UPDATE);

    /* 7. Chuyển FSM sang PRE_SAMPLING và kích hoạt TIM1 lấy mẫu */
    g_la_state = LA_STATE_PRE_SAMPLING;
    __HAL_TIM_ENABLE(&htim1);
#else
    g_la_state = LA_STATE_PRE_SAMPLING;
#endif

    return true;
}

void la_core_abort(void)
{
#if defined(TIM1)
    /* Dừng khẩn cấp TIM1, TIM2, DMA2 */
    TIM1->CR1 &= ~TIM_CR1_CEN;
    TIM2->CR1 &= ~TIM_CR1_CEN;
    DMA2_Stream5->CR &= ~DMA_SxCR_EN;

    DMA2->HIFCR = DMA_HIFCR_CTCIF5 | DMA_HIFCR_CHTIF5 | DMA_HIFCR_CTEIF5 |
                  DMA_HIFCR_CDMEIF5 | DMA_HIFCR_CFEIF5;
#endif
    g_la_state = LA_STATE_IDLE;
}

void la_core_on_dma_ht_isr(void)
{
    /* Gọi khi nạp được 50% = 16.384 mẫu >= 20% Pre-trigger (6.554 mẫu) */
    if (g_la_state == LA_STATE_PRE_SAMPLING) {
        uint8_t mode = g_current_trig_cfg & 0x0F;
        if (mode == 0x00) {
            /* Free-run: Không chờ EXTI, kích hoạt ngay TIM2 One-Pulse */
            g_la_state = LA_STATE_POST_SAMPLING;
#if defined(TIM2)
            TIM2->CNT = 0;
            TIM2->CR1 |= TIM_CR1_CEN;
#endif
        } else {
            /* Kích hoạt ngắt EXTI trên chân chỉ định (Bước 3) */
            g_la_state = LA_STATE_WAIT_TRIGGER;
        }
    }
}

void la_core_on_exti_trigger_isr(void)
{
    if (g_la_state == LA_STATE_WAIT_TRIGGER) {
        /* Bật TIM2 đếm 26.214 xung Post-trigger */
#if defined(TIM2)
        TIM2->CNT = 0;
        TIM2->CR1 |= TIM_CR1_CEN;
#endif
        g_la_state = LA_STATE_POST_SAMPLING;
    }
}

void la_core_on_tim2_period_elapsed_isr(void)
{
    if (g_la_state == LA_STATE_POST_SAMPLING) {
#if defined(TIM1)
        /* Dừng TIM1 ngay lập tức */
        TIM1->CR1 &= ~TIM_CR1_CEN;

        /* Dừng DMA2 Stream 5 */
        DMA2_Stream5->CR &= ~DMA_SxCR_EN;

        /* Lưu vị trí con trỏ ghi DMA hiện tại (vị trí mẫu cũ nhất t0) */
        uint16_t ndtr = (uint16_t)(DMA2_Stream5->NDTR);
        g_captured_write_pos = (LA_BUFFER_SIZE - ndtr) % LA_BUFFER_SIZE;
#else
        g_captured_write_pos = 0;
#endif
        g_la_state = LA_STATE_TRANSFERRING;
    }
}

void la_core_process(void)
{
    if (g_la_state == LA_STATE_TRANSFERRING) {
        uint8_t status = ((g_current_trig_cfg & 0x0F) == 0x00) ? LA_STATUS_FREERUN_OK : LA_STATUS_TRIGGER_OK;

        /* Thực hiện đóng gói 32.776 Bytes xoay vòng từ g_captured_write_pos và truyền qua USB-CDC phân đoạn 512B */
        la_protocol_send_data_frame(status, LA_TRIG_OFFSET_DEFAULT, la_capture_buffer, g_captured_write_pos);

        g_la_state = LA_STATE_IDLE;
    }
}
