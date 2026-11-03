#!/usr/bin/env python3
"""
mock_serial.py
Giả lập thiết bị Logic Analyzer STM32F401 qua cổng Virtual Serial (pty trên Linux).
Giúp TV3 kiểm thử toàn bộ PyQt GUI và bộ giải mã UART mà không cần phần cứng thật.

Cách dùng:
  1. Chạy: python3 software/tests/mock_serial.py
  2. Script sẽ in ra đường dẫn cổng ảo: e.g. /dev/pts/X
  3. Cấu hình GUI kết nối tới cổng /dev/pts/X đó.
"""

import os
import pty
import time
import struct

def run_mock_server():
    master, slave = pty.openpty()
    s_name = os.ttyname(slave)
    print("==================================================")
    print("MOCK SERIAL STM32 LOGIC ANALYZER ĐANG CHẠY")
    print(f"-> Cổng COM ảo cho GUI kết nối: {s_name}")
    print("==================================================")

    # Đọc sẵn file dữ liệu mẫu 32.776 bytes
    sample_file = os.path.join(os.path.dirname(__file__), "sample_data_1mhz.bin")
    if not os.path.exists(sample_file):
        print(f"Lỗi: Không tìm thấy {sample_file}. Hãy chạy generate_test_data.py trước!")
        return

    with open(sample_file, "rb") as f:
        sample_packet = f.read()

    rx_buf = bytearray()

    try:
        while True:
            data = os.read(master, 128)
            if not data:
                continue
            rx_buf.extend(data)

            # Quét tìm khung lệnh 5 bytes bắt đầu bằng 0xA5
            while len(rx_buf) >= 5:
                if rx_buf[0] != 0xA5:
                    rx_buf.pop(0)
                    continue

                cmd_frame = rx_buf[:5]
                # Kiểm tra Checksum: B0 ^ B1 ^ B2 ^ B3
                expected_csum = cmd_frame[0] ^ cmd_frame[1] ^ cmd_frame[2] ^ cmd_frame[3]
                if cmd_frame[4] != expected_csum:
                    print(f"[MOCK] Lỗi Checksum: nhận {cmd_frame[4]:#x}, tính {expected_csum:#x}")
                    # Gửi NAK ERR_CHECKSUM (7 bytes)
                    nak = bytes([0x5A, 0xA5, 0xE0, cmd_frame[1], cmd_frame[2], cmd_frame[3],
                                 0x5A ^ 0xA5 ^ 0xE0 ^ cmd_frame[1] ^ cmd_frame[2] ^ cmd_frame[3]])
                    os.write(master, nak)
                    rx_buf.pop(0)
                    continue

                # Nhận lệnh hợp lệ:
                cmd_id = cmd_frame[1]
                rate_idx = cmd_frame[2]
                trig_cfg = cmd_frame[3]
                rx_buf = rx_buf[5:]

                if cmd_id == 0x03:  # PING
                    print("[MOCK] Nhận CMD_PING -> Phản hồi RSP_PONG (v1.0.0)")
                    pong = bytes([0x5A, 0xA5, 0x04, 0x01, 0x00, 0x00, 0xFA])
                    os.write(master, pong)

                elif cmd_id == 0x02:  # ABORT
                    print("[MOCK] Nhận CMD_ABORT -> Phản hồi RSP_ABORTED")
                    abort_ack = bytes([0x5A, 0xA5, 0x05, 0x00, 0x00, 0x00, 0xFA])
                    os.write(master, abort_ack)

                elif cmd_id == 0x01:  # START
                    print(f"[MOCK] Nhận CMD_START: Rate={rate_idx}, TrigCfg={trig_cfg:#x}")
                    print("[MOCK] Bắt đầu truyền gói dữ liệu mẫu 32.776 Bytes theo từng block 512B...")
                    # Giả lập thời gian nạp bộ đệm
                    time.sleep(0.05)
                    # Gửi dữ liệu theo từng block 512B
                    chunk_size = 512
                    for offset in range(0, len(sample_packet), chunk_size):
                        chunk = sample_packet[offset:offset+chunk_size]
                        os.write(master, chunk)
                        time.sleep(0.001)  # Giả lập trễ nhẹ USB
                    print("[MOCK] Đã truyền xong toàn bộ 32.776 Bytes!")
                else:
                    print(f"[MOCK] Lệnh không nhận diện: {cmd_id:#x}")

    except KeyboardInterrupt:
        print("\n[MOCK] Dừng Mock Serial.")
    finally:
        os.close(master)
        os.close(slave)

if __name__ == "__main__":
    run_mock_server()
