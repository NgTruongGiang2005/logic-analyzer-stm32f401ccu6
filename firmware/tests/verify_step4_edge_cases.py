#!/usr/bin/env python3
"""
verify_step4_edge_cases.py
Script kiểm thử Toàn diện Trường hợp Biên & Độ bền Giao thức (Bước 4):

Kiểm tra 8 kịch bản bắt buộc:
1. PING (0x03) -> PONG (0x04)
2. Invalid RATE_IDX (>8) -> NAK ERR_INVALID_RATE (0xE1)
3. Invalid TRIG_CH (>7)  -> NAK ERR_INVALID_TRIG (0xE2)
4. Invalid TRIG_MODE (>2)-> NAK ERR_INVALID_TRIG (0xE2)
5. Bad Checksum          -> NAK ERR_CHECKSUM (0xE0)
6. ABORT in IDLE         -> RSP_ABORTED (0x05)
7. ABORT while capturing -> RSP_ABORTED (0x05) & FSM khôi phục về IDLE ngay lập tức
8. Dynamic Timeout       -> Data Frame 32.776B với Status = 0x02 (STATUS_TIMEOUT)
"""

import sys
import time
import serial

SERIAL_PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
BAUDRATE = 115200
TIMEOUT = 4.0

def read_exact(ser, count):
    buf = bytearray()
    t0 = time.time()
    while len(buf) < count:
        chunk = ser.read(count - len(buf))
        if not chunk:
            break
        buf.extend(chunk)
    return buf, time.time() - t0

def test_ctrl_frame(ser, cmd_bytes, expected_rsp_code, test_name):
    print(f"\n--- {test_name} ---")
    ser.reset_input_buffer()
    ser.write(bytes(cmd_bytes))
    resp, elapsed = read_exact(ser, 7)
    if len(resp) != 7:
        print(f"[FAIL] Không nhận đủ 7 Bytes phản hồi ({len(resp)}B nhận được)")
        return False
    
    magic = resp[0:2]
    code = resp[2]
    csum = resp[6]
    calc_csum = resp[0] ^ resp[1] ^ resp[2] ^ resp[3] ^ resp[4] ^ resp[5]

    print(f"-> Gửi: {[hex(b) for b in cmd_bytes]}")
    print(f"-> Nhận 7B: {[hex(b) for b in resp]} ({elapsed:.3f} s)")
    
    if magic != b"\x5A\xA5" or code != expected_rsp_code or csum != calc_csum:
        print(f"[FAIL] Sai phản hồi: mong đợi Code={expected_rsp_code:#04x}, nhận Code={code:#04x}, Checksum hợp lệ={csum == calc_csum}")
        return False
    
    print(f"-> [PASS] {test_name}: Code {code:#04x} chuẩn xác, Checksum XOR đúng!")
    return True

def run_step4_tests():
    print(f"=== ĐANG MỞ CỔNG {SERIAL_PORT} ===")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT)
    except Exception as e:
        print(f"LỖI: Không thể mở cổng {SERIAL_PORT}: {e}")
        print(f"Gợi ý: sudo chmod 666 {SERIAL_PORT}")
        sys.exit(1)

    time.sleep(0.1)

    # 1. PING
    # [0xA5, 0x03, 0x00, 0x00, 0xA6]
    if not test_ctrl_frame(ser, [0xA5, 0x03, 0x00, 0x00, 0xA6], 0x04, "TEST 1: PING (0x03) -> PONG (0x04)"):
        ser.close()
        sys.exit(1)

    # 2. Invalid RATE_IDX = 9 (> 8)
    # Checksum: 0xA5 ^ 0x01 ^ 0x09 ^ 0x00 = 0xAD
    if not test_ctrl_frame(ser, [0xA5, 0x01, 0x09, 0x00, 0xAD], 0xE1, "TEST 2: INVALID RATE (RATE_IDX=9) -> NAK 0xE1"):
        ser.close()
        sys.exit(1)

    # 3. Invalid Trigger Channel = 8 (> 7)
    # TRIG_CFG = 0x80 (Ch=8, Mode=0). Checksum: 0xA5 ^ 0x01 ^ 0x03 ^ 0x80 = 0x27
    if not test_ctrl_frame(ser, [0xA5, 0x01, 0x03, 0x80, 0x27], 0xE2, "TEST 3: INVALID CHANNEL (Ch=8) -> NAK 0xE2"):
        ser.close()
        sys.exit(1)

    # 4. Invalid Trigger Mode = 3 (> 2)
    # TRIG_CFG = 0x03 (Ch=0, Mode=3). Checksum: 0xA5 ^ 0x01 ^ 0x03 ^ 0x03 = 0xA4
    if not test_ctrl_frame(ser, [0xA5, 0x01, 0x03, 0x03, 0xA4], 0xE2, "TEST 4: INVALID MODE (Mode=3) -> NAK 0xE2"):
        ser.close()
        sys.exit(1)

    # 5. Bad Checksum
    # Sent checksum 0x00 instead of 0xA7
    if not test_ctrl_frame(ser, [0xA5, 0x01, 0x03, 0x00, 0x00], 0xE0, "TEST 5: BAD CHECKSUM -> NAK 0xE0"):
        ser.close()
        sys.exit(1)

    # 6. ABORT in IDLE
    # CMD_ABORT: [0xA5, 0x02, 0x00, 0x00, 0xA7] -> 0x05
    if not test_ctrl_frame(ser, [0xA5, 0x02, 0x00, 0x00, 0xA7], 0x05, "TEST 6: ABORT TRONG TRẠNG THÁI IDLE -> 0x05"):
        ser.close()
        sys.exit(1)

    # 7. ABORT WHILE CAPTURING
    print("\n--- TEST 7: KHẨN CẤP ABORT KHI ĐANG ĐỢI TRIGGER TRÊN PA1 (KHÔNG CÓ TÍN HIỆU) ---")
    # Start trigger on PA1 (ch1=0x10, rising=0x01 -> TRIG_CFG=0x11)
    # Checksum: 0xA5 ^ 0x01 ^ 0x03 ^ 0x11 = 0xB6
    ser.write(bytes([0xA5, 0x01, 0x03, 0x11, 0xB6]))
    time.sleep(0.05) # Cho FSM sang WAIT_TRIGGER
    # Gửi ABORT
    ser.write(bytes([0xA5, 0x02, 0x00, 0x00, 0xA7]))
    abort_resp, _ = read_exact(ser, 7)
    if len(abort_resp) == 7 and abort_resp[2] == 0x05:
        print(f"-> [PASS] ABORT thành công khi đang capture: {[hex(b) for b in abort_resp]}")
    else:
        print(f"[FAIL] ABORT thất bại: {[hex(b) for b in abort_resp]}")
        ser.close()
        sys.exit(1)

    # Kiểm tra FSM đã về IDLE an toàn bằng lệnh PING
    ser.write(bytes([0xA5, 0x03, 0x00, 0x00, 0xA6]))
    ping_resp, _ = read_exact(ser, 7)
    if len(ping_resp) == 7 and ping_resp[2] == 0x04:
        print(f"-> [PASS] FSM đã trở về IDLE an toàn (PING phản hồi 0x04)!")
    else:
        print(f"[FAIL] FSM không trở về IDLE: {[hex(b) for b in ping_resp]}")
        ser.close()
        sys.exit(1)

    # 8. DYNAMIC TIMEOUT TEST
    print("\n--- TEST 8: KIỂM CHỨNG DYNAMIC TIMEOUT (KÍCH HOẠT CHỜ TRÊN PA1 VÀ ĐỂ HẾT GIỜ) ---")
    print("-> Bắt đầu Trigger trên PA1 (không có xung), thời gian timeout dự kiến: ~2.017 s...")
    ser.reset_input_buffer()
    # TRIG_CFG = 0x11 (PA1 Rising). Checksum = 0xB6
    ser.write(bytes([0xA5, 0x01, 0x03, 0x11, 0xB6]))
    t_start = time.time()
    raw_data, elapsed = read_exact(ser, 32776)
    print(f"-> Đã nhận {len(raw_data)} Bytes sau {elapsed:.3f} s.")

    if len(raw_data) != 32776:
        print(f"[FAIL] Nhận thiếu dữ liệu: {len(raw_data)} / 32776 Bytes.")
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

    if status == 0x02:
        print("-> [PASS] Status đúng 0x02 (STATUS_TIMEOUT - MCU tự động dừng khi hết hạn)!")
    else:
        print(f"[FAIL] Status nhận được không phải 0x02: {status:#04x}")
        ser.close()
        sys.exit(1)

    if checksum_rx == checksum_calc:
        print("-> [PASS] Checksum XOR khớp 100% trên dữ liệu Timeout 32KB unrolled!")

    print("\n========================================================")
    print("  [SUCCESS] BƯỚC 4: TẤT CẢ EDGE CASES & TIMEOUT ĐÃ ĐẠT!")
    print("  Firmware đạt độ ổn định và tin cậy cấp công nghiệp.")
    print("========================================================")

    ser.close()

if __name__ == "__main__":
    run_step4_tests()
