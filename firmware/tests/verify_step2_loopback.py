#!/usr/bin/env python3
"""
verify_step2_loopback.py
Script kiểm thử Loopback Self-Test (Bước 2):
Phát chuỗi UART "TEST_LA_2026\\r\\n" trên PA9 (USART1 TX, 115200 bps, 8-N-1)
và thu nhận trên Kênh 0 (PA0) ở tần số lấy mẫu 1 MHz.

Yêu cầu phần cứng: Cắm dây jumper nối chân PA9 sang PA0.
"""

import sys
import time
import serial

SERIAL_PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
BAUDRATE = 115200
TIMEOUT = 4.0

def test_loopback():
    print(f"=== ĐANG MỞ CỔNG {SERIAL_PORT} ===")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT)
    except Exception as e:
        print(f"LỖI: Không thể mở cổng {SERIAL_PORT}: {e}")
        print("Gợi ý: Cấp quyền cổng: sudo chmod 666 " + SERIAL_PORT)
        sys.exit(1)

    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(0.05)

    # 1. PING test
    print("\n--- TEST 1: KIỂM TRA PING (CMD_PING) ---")
    # Header: 0xA5, CMD: 0x03 (PING), Rate: 0x00, Trig: 0x00, Checksum: 0xA6
    ping_cmd = bytes([0xA5, 0x03, 0x00, 0x00, 0xA6])
    ser.write(ping_cmd)
    ser.flush()

    resp = ser.read(7)
    if len(resp) != 7 or resp[0] != 0x5A or resp[1] != 0xA5 or resp[2] != 0x04:
        print(f"[FAIL] Phản hồi PING không hợp lệ: {[hex(b) for b in resp]}")
        ser.close()
        sys.exit(1)
    print(f"-> [PASS] PING THÀNH CÔNG! Firmware Version: v{resp[3]}.{resp[4]}.{resp[5]}")

    # 2. START Capture (1 MHz, Free-run)
    print("\n--- TEST 2: THU THẬP TÍN HIỆU LOOPBACK (1 MHz) ---")
    # Header: 0xA5, CMD: 0x01 (START), Rate: 0x03 (1 MHz), Trig: 0x00 (Free-run), Checksum: 0xA7
    start_cmd = bytes([0xA5, 0x01, 0x03, 0x00, 0xA7])
    ser.write(start_cmd)
    ser.flush()

    t_start = time.time()
    raw_data = bytearray()
    expected_len = 32776

    while len(raw_data) < expected_len:
        chunk = ser.read(expected_len - len(raw_data))
        if not chunk:
            break
        raw_data.extend(chunk)

    elapsed = time.time() - t_start
    print(f"-> Đã nhận tổng cộng {len(raw_data)} Bytes trong {elapsed:.3f} s.")

    if len(raw_data) != expected_len:
        print(f"[FAIL] Nhận thiếu dữ liệu: {len(raw_data)} / {expected_len} Bytes.")
        if len(raw_data) == 7:
            print(f"-> Gói 7B nhận được (có thể là NAK/Control): {[hex(b) for b in raw_data]}")
        ser.close()
        sys.exit(1)

    # Header check
    magic = raw_data[0:2]
    status = raw_data[2]
    trig_offset = int.from_bytes(raw_data[3:5], byteorder="little")
    sample_count = int.from_bytes(raw_data[5:7], byteorder="little")
    samples = raw_data[7:32775]
    checksum_rx = raw_data[32775]

    checksum_calc = 0
    for b in samples:
        checksum_calc ^= b

    if magic != b"\x5A\xA5" or checksum_rx != checksum_calc:
        print(f"[FAIL] Dữ liệu lỗi: magic={magic.hex()}, checksum_rx={checksum_rx:#x}, checksum_calc={checksum_calc:#x}")
        ser.close()
        sys.exit(1)

    print(f"-> Header (7B): Status={status:#x}, Offset={trig_offset}, Count={sample_count}")
    print(f"-> Checksum XOR: 0x{checksum_rx:02X} (Khớp 100%)")

    # 3. UART Software Demodulator on PA0 (CH0)
    print("\n--- TEST 3: GIẢI MÃ UART TRÊN KÊNH 0 (PA0) TẠI 115200 BAUD ---")
    # Ch0 is bit 0 of each sample
    ch0 = [(b & 0x01) for b in samples]
    
    # Check if there is toggle activity on PA0
    transitions = sum(1 for i in range(len(ch0) - 1) if ch0[i] != ch0[i+1])
    print(f"-> Số lần chuyển mức logic (Transitions) trên PA0: {transitions}")
    if transitions < 10:
        print("[CẢNH BÁO] Chưa thấy tín hiệu dao động trên chân PA0!")
        print("-> Bạn đã cắm dây nối (jumper wire) từ chân PA9 sang PA0 chưa?")
        ser.close()
        sys.exit(1)

    # Decode UART 115200 baud at 1 MHz sample rate
    # Bit period = 1000000 / 115200 = 8.68055 samples
    samples_per_bit = 1000000.0 / 115200.0
    decoded_chars = []
    
    idx = 0
    while idx < len(ch0) - 150:
        # Look for Falling Edge (Start Bit from IDLE high=1 to 0)
        if ch0[idx] == 1 and ch0[idx+1] == 0:
            start_edge = idx + 1
            # Sample middle of Start Bit
            start_mid = int(start_edge + samples_per_bit * 0.5)
            if start_mid < len(ch0) and ch0[start_mid] == 0:
                # Valid start bit, read 8 data bits (LSB first)
                byte_val = 0
                valid_byte = True
                for bit_num in range(8):
                    sample_pos = int(start_edge + samples_per_bit * (1.5 + bit_num))
                    if sample_pos >= len(ch0):
                        valid_byte = False
                        break
                    bit_val = ch0[sample_pos]
                    byte_val |= (bit_val << bit_num)
                
                # Check Stop Bit (should be 1)
                stop_pos = int(start_edge + samples_per_bit * 9.5)
                if valid_byte and stop_pos < len(ch0) and ch0[stop_pos] == 1:
                    char_ascii = chr(byte_val) if (32 <= byte_val <= 126 or byte_val in (10, 13)) else '?'
                    decoded_chars.append(char_ascii)
                    # Nhảy tới vị trí giữa Stop Bit (bit thứ 9), sau đó để bộ dò cạnh tự bắt Falling Edge tiếp theo
                    idx = int(start_edge + samples_per_bit * 9.0)
                    continue
        idx += 1

    decoded_str = "".join(decoded_chars)
    print(f"-> Chuỗi ký tự giải mã được trên PA0:\n   {repr(decoded_str)}")

    if "TEST_LA_2026" in decoded_str:
        print("\n==============================================")
        print("  [SUCCESS] LOOPBACK SELF-TEST ĐÃ THÀNH CÔNG!")
        print("  Chuỗi 'TEST_LA_2026' đã được phát từ PA9 và")
        print("  thu nhận chính xác 100% qua PA0 ở 115200 bps!")
        print("==============================================")
    else:
        print("\n[CHÚ Ý] Đã bắt được dữ liệu nhưng chưa thấy chuỗi 'TEST_LA_2026'.")
        print("Kiểm tra lại kết nối dây jumper PA9 -> PA0.")
        ser.close()
        sys.exit(1)

    ser.close()

if __name__ == "__main__":
    test_loopback()
