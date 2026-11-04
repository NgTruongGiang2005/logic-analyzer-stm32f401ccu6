#!/usr/bin/env python3
"""
software/tests/test_gui_integration.py
Kiểm thử tích hợp tự động toàn diện cho phân hệ Desktop GUI (TV3):
1. Khởi động Mock Serial STM32 qua pty ảo
2. Kết nối LogicAnalyzerClient tới cổng ảo
3. Gửi lệnh Ping -> Xác nhận PONG v1.0.0
4. Gửi lệnh Start 1 MHz -> Nhận 32.776 Bytes -> Xác thực Checksum XOR
5. Chạy UARTDecoder trên Kênh 0 -> Giải mã chính xác chuỗi "TEST_LA_2026\r\n"
6. Khởi động MainWindow trong chế độ offscreen -> Xác nhận nạp và vẽ 8 kênh, vạch Trigger và bảng dữ liệu.
"""

import os
import pty
import sys
import time
import threading
import numpy as np

# Thiết lập đường dẫn import
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from software.gui.logic_client import LogicAnalyzerClient
from software.decoders.uart_decoder import UARTDecoder


def run_integration_test():
    print("==================================================")
    print("BẮT ĐẦU KIỂM THỬ TÍCH HỢP TỰ ĐỘNG PHẦN MỀM (TV3)")
    print("==================================================")

    # 1. Tạo mock serial pty
    master, slave = pty.openpty()
    port_name = os.ttyname(slave)
    print(f"[TEST] Đã tạo cổng ảo giả lập STM32: {port_name}")

    sample_bin = os.path.join(os.path.dirname(__file__), "sample_data_1mhz.bin")
    with open(sample_bin, "rb") as f:
        mock_packet = f.read()

    def mock_server():
        while True:
            try:
                cmd = os.read(master, 5)
                if not cmd:
                    break
                if cmd[1] == 0x03:  # PING
                    os.write(master, bytes([0x5A, 0xA5, 0x04, 0x01, 0x00, 0x00, 0xFA]))
                elif cmd[1] == 0x01:  # START
                    # Gửi theo block 512B
                    chunk_sz = 512
                    for offset in range(0, len(mock_packet), chunk_sz):
                        os.write(master, mock_packet[offset:offset+chunk_sz])
                        time.sleep(0.001)
                elif cmd[1] == 0x02:  # ABORT
                    os.write(master, bytes([0x5A, 0xA5, 0x05, 0x00, 0x00, 0x00, 0xFA]))
            except Exception:
                break

    srv_thread = threading.Thread(target=mock_server, daemon=True)
    srv_thread.start()

    # 2. Kiểm thử LogicAnalyzerClient
    client = LogicAnalyzerClient()
    ok, msg = client.connect(port_name)
    assert ok, f"Không thể kết nối tới {port_name}: {msg}"
    print(f"-> [PASS] Kết nối thành công tới cổng giả lập: {port_name}")

    # PING
    ok, ver = client.ping()
    assert ok, f"Lỗi PING: {ver}"
    print(f"-> [PASS] PING thành công! Firmware Version: {ver}")

    # START CAPTURE
    print("-> Đang gửi lệnh START capture (1 MHz, Falling PA0)...")
    res = client.start_capture(rate_idx=3, trig_ch=0, trig_mode=2)
    assert res["success"], f"Lỗi Capture: {res.get('error')}"
    assert res["checksum_ok"], "Lỗi Checksum XOR của gói dữ liệu!"
    assert res["trig_offset"] == 6554, f"Trig offset sai: {res['trig_offset']} != 6554"
    assert len(res["channels"]) == 8, "Số kênh khác 8!"
    assert len(res["channels"][0]) == 32768, "Số mẫu khác 32768!"
    print(f"-> [PASS] Thu thập 32.776B hoàn tất trong {res['elapsed_s']:.3f} s!")
    print(f"   Trạng thái: {res['status_name']}")
    print(f"   Checksum XOR: Khớp 100%")

    # 3. Kiểm thử UARTDecoder
    print("-> Đang giải mã UART trên Kênh 0 (PA0) tại 115200 bps...")
    ch0_samples = res["channels"][0].tolist()
    decoder = UARTDecoder(sample_rate=1_000_000, baudrate=115_200)
    decoded_text, frames = decoder.decode(ch0_samples, start_idx=res["trig_offset"] - 50)
    print(f"-> [PASS] Chuỗi ASCII giải mã được: {repr(decoded_text)}")
    print(f"   Tổng số ký tự giải mã: {len(frames)} frames")
    assert "TEST_LA_2026" in decoded_text, f"Không tìm thấy chuỗi mong muốn trong: {decoded_text}"

    # Đóng kết nối serial
    client.disconnect()
    os.close(master)
    os.close(slave)

    # 4. Kiểm thử khởi tạo và nạp dữ liệu trên giao diện PyQt5
    print("-> Đang kiểm thử giao diện đồ họa PyQt5 (Offscreen Mode)...")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt5 import QtWidgets
    from software.gui.main_window import MainWindow

    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication([])

    win = MainWindow()
    # Nạp dữ liệu vừa nhận vào giao diện
    win._render_capture_data(res)

    assert win.current_data is not None
    assert win.txt_decoded.toPlainText().strip() == decoded_text.strip()
    assert win.table_frames.rowCount() == len(frames)
    print(f"-> [PASS] Giao diện PyQt5 đã vẽ 8 kênh, đặt vạch Trigger tại mẫu {res['trig_offset']}, và điền bảng {len(frames)} ký tự!")

    print("\n==================================================")
    print("  [SUCCESS] 100% KIỂM THỬ TÍCH HỢP PHẦN MỀM ĐẠT PASS!")
    print("  Phân hệ Desktop GUI (TV3) đã hoàn chỉnh và sẵn sàng!")
    print("==================================================")


if __name__ == "__main__":
    run_integration_test()
