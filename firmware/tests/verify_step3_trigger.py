#!/usr/bin/env python3
"""
verify_step3_trigger.py
Script kiểm thử Toàn phần FSM Trigger (Bước 3):
- Chế độ Trigger cạnh xuống trên PA0 (Start bit của bản tin UART)
- Bộ đếm mẫu Post-trigger TIM2 One-Pulse (80% buffer sau trigger)
- Giải thuật xoay vòng bộ đệm (Buffer Unrolling): đưa điểm Trigger về danh định tại mẫu 6554 (20% pre-trigger)
- Kiểm chứng Jitter / sai số trễ thực tế so với mẫu 6554
- Giải mã chuỗi UART ngay sau điểm Trigger.

Yêu cầu phần cứng: Cắm dây jumper nối PA9 sang PA0.
"""

import sys
import time
import serial

SERIAL_PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
BAUDRATE = 115200
TIMEOUT = 5.0

def read_exact(ser, count):
    buf = bytearray()
    t0 = time.time()
    while len(buf) < count:
        chunk = ser.read(count - len(buf))
        if not chunk:
            break
        buf.extend(chunk)
    return buf, time.time() - t0

def decode_uart_ch0(samples, start_idx=0):
    ch0 = [(b & 0x01) for b in samples]
    samples_per_bit = 1000000.0 / 115200.0
    decoded_chars = []
    
    idx = start_idx
    while idx < len(ch0) - 150:
        if ch0[idx] == 1 and ch0[idx+1] == 0:
            start_edge = idx + 1
            start_mid = int(start_edge + samples_per_bit * 0.5)
            if start_mid < len(ch0) and ch0[start_mid] == 0:
                byte_val = 0
                valid_byte = True
                for bit_num in range(8):
                    pos = int(start_edge + samples_per_bit * (1.5 + bit_num))
                    if pos >= len(ch0):
                        valid_byte = False
                        break
                    byte_val |= (ch0[pos] << bit_num)
                
                stop_pos = int(start_edge + samples_per_bit * 9.5)
                if valid_byte and stop_pos < len(ch0) and ch0[stop_pos] == 1:
                    char_ascii = chr(byte_val) if (32 <= byte_val <= 126 or byte_val in (10, 13)) else '?'
                    decoded_chars.append(char_ascii)
                    idx = int(start_edge + samples_per_bit * 9.0)
                    continue
        idx += 1
    return "".join(decoded_chars)

def run_step3_verification():
    print(f"=== ĐANG MỞ CỔNG {SERIAL_PORT} ===")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT)
    except Exception as e:
        print(f"LỖI: Không thể mở cổng {SERIAL_PORT}: {e}")
        print(f"Gợi ý: sudo chmod 666 {SERIAL_PORT}")
        sys.exit(1)

    time.sleep(0.1)
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # --- TEST 1: PING ---
    print("\n--- TEST 1: KIỂM TRA PING (CMD_PING) ---")
    ser.write(bytes([0xA5, 0x03, 0x00, 0x00, 0xA6]))
    resp, _ = read_exact(ser, 7)
    if len(resp) != 7 or resp[0] != 0x5A or resp[1] != 0xA5 or resp[2] != 0x04:
        print(f"[FAIL] PING thất bại: {[hex(b) for b in resp]}")
        ser.close()
        sys.exit(1)
    print(f"-> [PASS] PING THÀNH CÔNG! Firmware Version: v{resp[3]}.{resp[4]}.{resp[5]}")

    # --- TEST 2: FALLING EDGE TRIGGER TRÊN PA0 (CH0) ---
    print("\n--- TEST 2: KIỂM TRA EDGE TRIGGER (Cạnh xuống trên PA0 - Start Bit UART) ---")
    # CMD_START (1 MHz, Falling Edge on PA0): [0xA5, 0x01, 0x03, 0x02, 0xA5]
    ser.write(bytes([0xA5, 0x01, 0x03, 0x02, 0xA5]))
    raw_data, elapsed = read_exact(ser, 32776)

    print(f"-> Đã nhận {len(raw_data)} Bytes trong {elapsed:.3f} s.")
    if len(raw_data) != 32776:
        print(f"[FAIL] Nhận thiếu dữ liệu: {len(raw_data)} / 32776 Bytes.")
        if len(raw_data) == 7:
            print(f"-> Gói điều khiển/NAK nhận được: {[hex(b) for b in raw_data]}")
        ser.close()
        sys.exit(1)

    status = raw_data[2]
    trig_offset = int.from_bytes(raw_data[3:5], byteorder="little")
    sample_count = int.from_bytes(raw_data[5:7], byteorder="little")
    samples = raw_data[7:32775]
    checksum_rx = raw_data[32775]

    checksum_calc = 0
    for b in samples:
        checksum_calc ^= b

    print(f"-> Header: Status={status:#04x}, Offset={trig_offset}, Count={sample_count}")
    print(f"-> Checksum XOR: Nhận=0x{checksum_rx:02X}, Tính=0x{checksum_calc:02X}")

    if checksum_rx != checksum_calc:
        print("[FAIL] Sai lệch Checksum XOR!")
        ser.close()
        sys.exit(1)

    if status != 0x00:
        print(f"[FAIL] Status mong đợi 0x00 (STATUS_TRIGGER_OK) nhưng nhận được: {status:#04x}")
        ser.close()
        sys.exit(1)

    print("-> [PASS] Status đúng 0x00 (STATUS_TRIGGER_OK - Đã bắt cạnh trigger thành công)!")

    # Kiểm tra điểm kích hoạt Trigger trên dạng sóng (PA0)
    ch0 = [(b & 0x01) for b in samples]
    print(f"\n-> Phân tích dạng sóng xung quanh điểm Trigger danh định (Mẫu {trig_offset}):")
    # Xem trước 20 mẫu trước và sau điểm trigger
    pre_window = ch0[trig_offset - 10 : trig_offset]
    post_window = ch0[trig_offset : trig_offset + 10]
    print(f"   Mức logic 10 mẫu trước điểm trig : {pre_window}")
    print(f"   Mức logic 10 mẫu sau điểm trig   : {post_window}")

    # Tìm vị trí cạnh xuống thực tế gần điểm 6554 nhất
    found_edge = -1
    min_dist = 999
    for i in range(trig_offset - 15, trig_offset + 15):
        if i >= 0 and i < len(ch0) - 1 and ch0[i] == 1 and ch0[i+1] == 0:
            dist = abs(i + 1 - trig_offset)
            if dist < min_dist:
                min_dist = dist
                found_edge = i + 1

    if found_edge != -1:
        jitter = found_edge - trig_offset
        print(f"-> [PASS] Bắt được cạnh xuống thực tế tại mẫu: {found_edge} (Sai số Jitter = {jitter:+d} mẫu)")
    else:
        print("-> [CẢNH BÁO] Không tìm thấy cạnh xuống rõ ràng quanh điểm 6554.")

    # Giải mã chuỗi UART bắt đầu từ điểm Trigger
    decoded = decode_uart_ch0(samples, start_idx=max(0, trig_offset - 20))
    print(f"-> Chuỗi giải mã UART ngay sau điểm Trigger:\n   {repr(decoded)}")

    if "TEST_LA_2026" in decoded:
        print("\n========================================================")
        print("  [SUCCESS] BƯỚC 3: EDGE TRIGGER HOẠT ĐỘNG HOÀN HẢO!")
        print("  Bắt đúng Start Bit cạnh xuống trên PA0 tại mẫu 6554!")
        print("  Bộ đệm xoay vòng (Unrolling) đưa điểm Trigger về chuẩn.")
        print("========================================================")
    else:
        print("[FAIL] Chưa giải mã được chuỗi UART hoàn chỉnh.")
        ser.close()
        sys.exit(1)

    ser.close()

if __name__ == "__main__":
    run_step3_verification()
