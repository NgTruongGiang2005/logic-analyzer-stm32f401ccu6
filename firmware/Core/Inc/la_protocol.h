/**
  ******************************************************************************
  * @file    la_protocol.h
  * @brief   Xử lý khung truyền nhị phân và mã hóa gói tin USB-CDC.
  *          Thành viên phụ trách: TV1 (Firmware STM32).
  ******************************************************************************
  */

#ifndef INC_LA_PROTOCOL_H_
#define INC_LA_PROTOCOL_H_

#include <stdint.h>
#include <stdbool.h>

/* Mã Status phản hồi Data Frame */
#define LA_STATUS_TRIGGER_OK   (0x00U)
#define LA_STATUS_FREERUN_OK   (0x01U)
#define LA_STATUS_TIMEOUT      (0x02U)

/* Mã RSP_CODE phản hồi Control Frame (7 Bytes) */
#define LA_RSP_PONG            (0x04U)
#define LA_RSP_ABORTED         (0x05U)
#define LA_ERR_CHECKSUM        (0xE0U)
#define LA_ERR_INVALID_RATE    (0xE1U)
#define LA_ERR_INVALID_TRIG    (0xE2U)
#define LA_ERR_BUSY            (0xE3U)

/* Nhận và xử lý dòng byte từ USB CDC (gọi trong CDC_Receive_FS) */
void la_protocol_process_rx_bytes(const uint8_t *data, uint32_t len);

/* Gửi khung phản hồi điều khiển 7 Bytes (PONG, ABORT ACK, NAK) */
void la_protocol_send_control_frame(uint8_t rsp_code, uint8_t d1, uint8_t d2, uint8_t d3);

/* Gửi khung phản hồi dữ liệu 32.776 Bytes */
void la_protocol_send_data_frame(uint8_t status, uint16_t trig_offset, const uint8_t *payload, uint16_t count);

#endif /* INC_LA_PROTOCOL_H_ */
