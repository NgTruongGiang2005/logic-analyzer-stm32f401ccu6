#!/usr/bin/env python3
"""
verify_step1_freerun.py
Script kiểm thử thông luồng Bước 1 (Free-Run Base) cho STM32 Logic Analyzer.

Kiểm tra:
  1. CMD_PING (5B) -> RSP_PONG (7B)
  2. CMD_START Free-Run (5B) -> DATA_FRAME (32.776B)
     - Header: Sync 0x5A 0xA5, Status 0x01 (FREE_RUN), Count 32768
     - Payload: 32768 Bytes dữ liệu mẫu GPIOA (PA0..PA7)
     - Footer: 1 Byte Checksum XOR khớp 100%
"""

import sys
import time
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
BAUD = 115200

print(f"=== ĐANG MỞ CỔNG {PORT} ===")
try:
    ser = serial.Serial(PORT, BAUD, timeout=2.0)
except Exception as e:
    print(f"LỖI: Không thể mở cổng {PORT}: {e}")
    print("Gợi ý: Chạy lệnh sau để cấp quyền truy cập cổng:")
    print(f"  sudo chmod 666 {PORT}")
    sys.exit(1)

# Xả sạch bộ đệm serial
ser.reset_input_buffer()
ser.reset_output_buffer()
time.sleep(0.1)

# --- TEST 1: CMD_PING ---
print("\n--- TEST 1: KIỂM TRA PING (CMD_PING) ---")
# 0xA5, 0x03 (PING), 0x00, 0x00, CHECKSUM = A5 ^ 03 ^ 00 ^ 00 = A6
ping_cmd = bytes([0xA5, 0x03, 0x00, 0x00, 0xA6])
ser.write(ping_cmd)
ser.flush()

resp = ser.read(7)
if len(resp) == 7:
    print(f"-> Nhận phản hồi ({len(resp)} Bytes): {[hex(b) for b in resp]}")
    if resp[0] == 0x5A and resp[1] == 0xA5 and resp[2] == 0x04:
        version = f"{resp[3]}.{resp[4]}.{resp[5]}"
        print(f"-> [PASS] PING THÀNH CÔNG! Firmware Version: v{version}")
    else:
        print("-> [FAIL] Phản hồi không đúng định dạng PONG!")
        ser.close()
        sys.exit(1)
else:
    print(f"-> [FAIL] Không nhận đủ 7 bytes (chỉ nhận {len(resp)} bytes).")
    ser.close()
    sys.exit(1)

# --- TEST 2: CMD_START FREE-RUN ---
print("\n--- TEST 2: KIỂM TRA FREE-RUN CAPTURE (1 MHz) ---")
# 0xA5, 0x01 (START), 0x03 (RATE 1MHz), 0x00 (FREE-RUN), CHECKSUM = A5 ^ 01 ^ 03 ^ 00 = A7
start_cmd = bytes([0xA5, 0x01, 0x03, 0x00, 0xA7])
ser.write(start_cmd)
ser.flush()

print("-> Đã gửi CMD_START, đang đợi nhận 32.776 Bytes...")
start_time = time.time()
data = bytearray()
while len(data) < 32776:
    chunk = ser.read(min(4096, 32776 - len(data)))
    if not chunk:
        if time.time() - start_time > 3.0:
            print(f"-> [TIMEOUT] Hết thời gian chờ, mới nhận {len(data)} / 32776 Bytes.")
            break
        continue
    data.extend(chunk)

elapsed = time.time() - start_time
print(f"-> Đã nhận tổng cộng {len(data)} Bytes trong {elapsed:.3f} s.")

if len(data) == 32776:
    # 1. Header (7B)
    header = data[:7]
    sync = (header[0], header[1])
    status = header[2]
    trig_offset = header[3] | (header[4] << 8)
    sample_count = header[5] | (header[6] << 8)

    print(f"-> Header (7B): Sync={hex(sync[0])},{hex(sync[1])} Status={hex(status)} Offset={trig_offset} Count={sample_count}")

    # 2. Payload (32768B)
    payload = data[7:7+32768]
    # 3. Footer (1B)
    footer = data[32775]

    # Tính toán Checksum XOR
    computed_xor = 0
    for b in payload:
        computed_xor ^= b

    print(f"-> Footer Checksum: Nhận={hex(footer)}, Tính toán={hex(computed_xor)}")

    if sync == (0x5A, 0xA5) and status == 0x01 and sample_count == 32768 and computed_xor == footer:
        print("-> [PASS] FREE-RUN CAPTURE THÀNH CÔNG 100%!")
        print(f"-> Xem trước 16 mẫu đầu tiên (PA0..PA7): {[hex(b) for b in payload[:16]]}")
    else:
        print("-> [FAIL] Dữ liệu gói tin không hợp lệ hoặc sai checksum!")
        ser.close()
        sys.exit(1)
else:
    print(f"-> [FAIL] Nhận thiếu dữ liệu: {len(data)} / 32776 Bytes.")
    ser.close()
    sys.exit(1)

ser.close()
print("\n==============================================")
print("  [SUCCESS] BƯỚC 1: FREE-RUN BASE ĐẠT YÊU CẦU!")
print("==============================================")
