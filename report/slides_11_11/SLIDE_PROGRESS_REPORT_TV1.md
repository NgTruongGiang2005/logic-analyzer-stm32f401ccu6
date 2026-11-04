# KỊCH BẢN & DÀN Ý SLIDE BÁO CÁO TIẾN ĐỘ (MỐC 11/11)
**Phân hệ:** Firmware STM32 (TV1 - Nguyễn Văn Hội - MSSV: 20233419)  
**Đề tài:** Logic Analyzer 8 kênh 6 MHz – STM32F401CCU6 (Topic 1)  
**Thời lượng báo cáo:** 3 – 5 phút (Chuẩn 4 slides, ~450 từ lời thoại)  
**Hình thức:** Slide thuyết trình (Proof of work bằng kết quả chạy HIL Test thực tế)  

---

## I. TỔNG QUAN YÊU CẦU & NHẬT KÝ QUYẾT ĐỊNH (DECISION LOG)

### 1. Tóm tắt Ràng buộc & Phạm vi (Understanding Summary)
* **Thời lượng ngặt nghèo:** 3 – 5 phút (trung bình 50 giây / slide).
* **Định hướng nội dung:** Tập trung sâu vào phân hệ **Firmware (TV1)** do đã nạp và kiểm chứng thành công 100% trên kit thật; phần cứng TV2 và phần mềm TV3 sẽ được tổng hợp ở giai đoạn cuối kỳ.
* **Bằng chứng kỹ thuật (Proof of Work):** Ảnh chụp kết quả chạy kiểm thử tự động HIL (`firmware/tests/verify_step*.py`) kết hợp sơ đồ khối kiến trúc FSM/Timer để thuyết phục thầy và các nhóm phản biện.

### 2. Nhật ký Quyết định Thiết kế (Decision Log)
| Mã Quyết định | Vấn đề Thiết kế | Phương án Lựa chọn | Phương án Thay thế | Lý do Lựa chọn |
| :---: | :--- | :--- | :--- | :--- |
| **DEC-01** | Phạm vi nội dung | Trọng tâm Firmware TV1 | Báo cáo cả 3 thành viên | Firmware đã hoàn thành vượt tiến độ 4 bước; đảm bảo tính sâu sắc trong 3–5 phút. |
| **DEC-02** | Hình thức minh chứng | Ảnh Terminal HIL Test + Sơ đồ khối | Video demo hoặc live code | Thầy yêu cầu slide ngắn; ảnh terminal test hiển thị số liệu khách quan, cô đọng nhất. |
| **DEC-03** | Khung thời lượng | 4 Slides (~50s/slide) | 3 slides hoặc 5 slides | Cân bằng hoàn hảo giữa chiều sâu kỹ thuật và kiểm soát thời gian không bị lố 5 phút. |
| **DEC-04** | Cấu trúc câu chuyện | Engineering Proof & Vertical Slice | Problem-Solver Narrative | Logic kỹ sư kinh điển: Mục tiêu $\rightarrow$ Kiến trúc $\rightarrow$ Số liệu đo thật $\rightarrow$ Kế hoạch. |

---

## II. CHI TIẾT NỘI DUNG & LỜI THOẠI 4 SLIDE (SPEAKER NOTES)

```
Thời gian biểu dự kiến:
- Slide 1: 0:00 - 0:50 (50s)
- Slide 2: 0:50 - 1:45 (55s)
- Slide 3: 1:45 - 2:40 (55s)
- Slide 4: 2:40 - 3:30 (50s)
Tổng thời gian: ~3 phút 30 giây (để dư 1 phút 30 giây trả lời câu hỏi phản biện).
```

---

### SLIDE 1: THIẾT KẾ PHẦN CỨNG & BỘ THU THẬP TÍN HIỆU 8 KÊNH 6 MHz

#### Bố cục hiển thị Slide (Visual Layout):
* **Tiêu đề:** THIẾT KẾ PHẦN CỨNG & BỘ THU THẬP TÍN HIỆU 8 KÊNH 6 MHz
* **Cột trái — Thông số kỹ thuật cốt lõi:**
  * **Số kênh đo:** 8 kênh đồng bộ trên Port A (`PA0 – PA7`).
  * **Tần số lấy mẫu ($f_s$):** 9 mức từ $10\text{ kHz}$ đến $6\text{ MHz}$ (sai số chu kỳ $0\%$).
  * **Bộ đệm dữ liệu:** Mảng tĩnh `32.768 Bytes` (chiếm đúng $50\%$ trong 64 KB SRAM của chip STM32F401CCU6).
* **Cột phải — Cấu hình Clock Tree & Luồng DMA phần cứng:**
  * Thạch anh ngoài $\text{HSE} = 25\text{ MHz} \xrightarrow{\text{PLL}} \text{SYSCLK} = 84\text{ MHz}$ & $\text{USB} = 48\text{ MHz}$.
  * `TIM1_UP` kích hoạt `DMA2_Stream5 Channel 6` đọc trực tiếp thanh ghi `GPIOA->IDR`.
  * **Độ lệch kênh (Skew):** Bằng $\mathbf{0\text{ ns}}$ tại thời điểm chốt mẫu do DMA đọc song song 8 bit qua bus AHB1 trong cùng 1 chu kỳ xung nhịp. Giải phóng $100\%$ CPU khi capture.

#### Lời thoại thuyết trình (Speaker Notes — ~50 giây, 105 từ):
> *"Kính thưa thầy và các bạn, em xin đại diện nhóm báo cáo tiến độ phân hệ Firmware cho thiết bị Logic Analyzer 8 kênh 6 MHz trên kit STM32F401 Black Pill.*  
> *Để triệt tiêu hoàn toàn sai số chu kỳ lấy mẫu, firmware thiết lập xung nhịp hệ thống cố định 84 MHz từ thạch anh ngoài, kết hợp bộ chia USB 48 MHz.*  
> *Về luồng thu thập dữ liệu, 8 kênh đo PA0 đến PA7 được đọc đồng bộ bằng Timer 1 kích hoạt DMA2 Stream 5 chốt trực tiếp từ thanh ghi `GPIOA->IDR` vào mảng đệm 32 KB trong SRAM. Nhờ việc đọc đồng thời trên bus AHB1, độ lệch pha giữa 8 kênh tại thời điểm lấy mẫu bằng 0 ns, đồng thời giải phóng hoàn toàn CPU khi đang capture."*

---

### SLIDE 2: KIẾN TRÚC MÁY TRẠNG THÁI (FSM) & ĐỒNG BỘ TRIGGER THỜI GIAN THỰC

#### Bố cục hiển thị Slide (Visual Layout):
* **Tiêu đề:** KIẾN TRÚC MÁY TRẠNG THÁI (FSM) & ĐỒNG BỘ TRIGGER THỜI GIAN THỰC
* **Sơ đồ khối FSM trung tâm:**
  ```text
  [IDLE] ───> [ARMED] ───> [PRE_SAMPLING] ──(Cờ HTIF5)──> [WAIT_TRIGGER] ──(EXTI0..7)──> [POST_SAMPLING] ──(TIM2_IRQ)──> [TRANSFERRING] ───> [IDLE]
  ```
* **3 Điểm sáng kỹ thuật then chốt:**
  1. **Chống rỗng Pre-trigger bằng cờ DMA Half-Transfer:** Khóa ngắt EXTI ban đầu, chỉ mở ngắt khi cờ `HTIF5` bật (đảm bảo đã ghi đủ $\ge 20\%$ lịch sử tín hiệu trước khi bắt sự kiện).
  2. **Bộ đếm Post-trigger Cascade (TIM1 $\rightarrow$ TIM2):** TIM2 cấu hình Slave One-Pulse Mode nhận xung `ITR0` từ TIM1. Đếm chính xác tuyệt đối $26.214\text{ mẫu}$ ($80\%$ bộ đệm) bằng phần cứng rồi tự ngắt dừng TIM1 (giải phóng hoàn toàn CPU).
  3. **Giải thuật xoay vòng (Buffer Unrolling):** Xoay vòng bộ đệm tròn từ vị trí con trỏ `write_pos = 32768 - NDTR`, chuẩn hóa điểm Trigger danh định luôn nằm tại mẫu thứ $\mathbf{6.554}$ ($t_{6554}$).

#### Lời thoại thuyết trình (Speaker Notes — ~55 giây, 115 từ):
> *"Tiếp theo là kiến trúc FSM và cơ chế Trigger thời gian thực. Để giải quyết triệt để nguy cơ mất dữ liệu pre-trigger, firmware khóa ngắt EXTI trong giai đoạn Pre-sampling và chỉ mở ngắt khi cờ DMA Half-Transfer bật, đảm bảo chắc chắn có ít nhất 20% dữ liệu lịch sử.*  
> *Khi phát hiện cạnh tín hiệu, ngắt EXTI ưu tiên mức cao nhất lập tức kích hoạt Timer 2 One-Pulse. Timer 2 nhận xung nội bộ từ Timer 1 qua đường liên kết ITR0, đếm chính xác tuyệt đối 26.214 mẫu sau trigger hoàn toàn bằng phần cứng rồi ngắt dừng Timer 1.*  
> *Trước khi truyền qua USB, firmware thực hiện giải thuật xoay vòng Buffer Unrolling từ con trỏ DMA, định vị điểm trigger chuẩn xác tại mẫu thứ 6.554 cho phần mềm máy tính phân tích."*

---

### SLIDE 3: KẾT QUẢ ĐO KIỂM THỰC NGHIỆM TRÊN PHẦN CỨNG (HIL TEST)

#### Bố cục hiển thị Slide (Visual Layout):
* **Tiêu đề:** KẾT QUẢ ĐO KIỂM THỰC NGHIỆM TRÊN PHẦN CỨNG (HARDWARE-IN-THE-LOOP)
* **Khung hiển thị kết quả 4 bài test tự động (Kèm ảnh chụp màn hình Terminal):**
  * **Test 1 — Free-Run (1 MHz):** Đọc và truyền trọn vẹn $32.776\text{ Bytes}$ qua USB-CDC, Header chuẩn Little-Endian, Checksum XOR khớp $100\%$.
  * **Test 2 — Loopback Self-Test:** PA9 phát UART 115.200 bps $\rightarrow$ Kênh PA0 thu thập và giải mã phần mềm chuẩn xác chuỗi `'TEST_LA_2026\r\n'` (0 bit error).
  * **Test 3 — Edge Trigger & Jitter:** Bắt cạnh xuống Start bit UART tại mẫu 6.553. **Sai số Jitter thực tế chỉ $\mathbf{-1\text{ mẫu}}$** so với mốc danh định 6.554.
  * **Test 4 — Kiểm thử biên & Độ bền (8/8 PASS):** Phản hồi NAK chuẩn (`0xE0 – 0xE2`), ngắt khẩn cấp ABORT (`0x05`), và cơ chế Dynamic Timeout ($2.092\text{ s}$) tự dừng an toàn.
* **Hộp điểm nhấn (Key Takeaway):** Sai số Jitter $-1$ mẫu chứng minh thời gian đáp ứng ngắt NVIC Cortex-M4 ($12-14$ clock) và liên kết Timer cascade hoạt động với độ chính xác cao.

#### Lời thoại thuyết trình (Speaker Notes — ~55 giây, 125 từ):
> *"Để chứng minh firmware hoạt động tin cậy trên kit thật mà không cần máy phát sóng ngoài, em đã xây dựng bộ kiểm thử tự động Hardware-in-the-Loop gồm 4 kịch bản chạy trực tiếp qua cổng COM.*  
> *Kết quả đo đạc thực nghiệm ghi nhận:*  
> *Thứ nhất, tính năng Loopback tự phát UART 115.200 bps từ chân PA9 sang PA0 hoạt động hoàn hảo, giải mã chính xác 100% chuỗi ký tự mà không bị lệch bit.*  
> *Thứ hai, ở bài test Edge Trigger, firmware bắt đúng Start bit cạnh xuống tại mẫu 6.553. Sai số Jitter thực tế chỉ âm 1 mẫu so với danh định 6.554, chứng minh trễ ngắt NVIC và độ trễ dừng Timer hoàn toàn nằm trong tầm kiểm soát.*  
> *Thứ ba, toàn bộ 8 bài test biên bao gồm NAK, ngắt khẩn cấp Abort và Timeout đều vượt qua 100%, đảm bảo hệ thống không bao giờ bị treo."*

---

### SLIDE 4: TỔNG KẾT TIẾN ĐỘ FIRMWARE & KẾ HOẠCH TÍCH HỢP HỆ THỐNG

#### Bố cục hiển thị Slide (Visual Layout):
* **Tiêu đề:** TỔNG KẾT TIẾN ĐỘ FIRMWARE & KẾ HOẠCH TÍCH HỢP HỆ THỐNG
* **Cột trái — Bảng tiến độ phân hệ Firmware (TV1 đạt $100\%$):**
  * **Bước 1 (Free-Run):** TIM1 + DMA2_Stream5 32KB + USB-CDC. *(Đã kiểm chứng)*
  * **Bước 2 (Loopback):** Tự phát & giải mã UART 115.200 bps PA9 $\rightarrow$ PA0. *(Đã kiểm chứng)*
  * **Bước 3 (FSM Trigger):** EXTI Priority 0 + TIM2 Post-counter + Buffer Unrolling. *(Đã kiểm chứng)*
  * **Bước 4 (Edge Cases):** Timeout SysTick, NAK, Abort, USB Watchdog. *(Đã kiểm chứng)*
  * *(Đã chốt hạ nhánh Git sạch vào `main` và đẩy lên GitHub).*
* **Cột phải — Kế hoạch giai đoạn 2 (Tích hợp hoàn thiện đồ án):**
  * **Bàn giao cho TV3 (Phần mềm PC):** Sử dụng hợp đồng `spec/protocol.md` để kết nối GUI PyQt, hiển thị đồ thị 8 kênh và kích hoạt bộ giải mã UART/SPI/I2C.
  * **Phối hợp cùng TV2 (Phần cứng):** Ghép nối mạch bảo vệ đầu vào 8 kênh và IC đệm 74LVC245 sau khi TV2 hoàn thiện mô phỏng LTspice và thi công mạch.
  * **Nhiệm vụ nâng cao của TV1:** Đo đạc trễ ngắt thực tế bằng chân debug PB1 trên máy hiện sóng và cấu hình xung 500 kHz minh họa hiện tượng Aliasing (Định lý Nyquist).

#### Lời thoại thuyết trình (Speaker Notes — ~50 giây, 115 từ):
> *"Tổng kết lại, tính đến thời điểm báo cáo tiến độ 11/11, phân hệ Firmware do em phụ trách đã hoàn thành 100% cả 4 bước phát triển và được chốt hạ vào nhánh main trên Git. Firmware đã sẵn sàng cung cấp nguồn dữ liệu nhị phân chuẩn xác cho toàn hệ thống.*  
> *Trong giai đoạn tiếp theo hướng tới báo cáo cuối kỳ, nhóm sẽ tập trung vào các mục tiêu tích hợp:*  
> *Thứ nhất, TV3 sẽ kết nối giao diện PyQt với cổng USB để hiển thị dạng sóng 8 kênh và hoàn thiện bộ giải mã giao thức.*  
> *Thứ hai, ghép nối mạch bảo vệ đầu vào và đệm bus do TV2 thiết kế sau khi kiểm chứng mô phỏng.*  
> *Và thứ ba, đo kiểm trễ ngắt trên máy hiện sóng để hoàn thiện báo cáo.*  
> *Em xin chân thành cảm ơn thầy và các bạn đã chú ý lắng nghe, em rất mong nhận được câu hỏi góp ý từ thầy và các nhóm!"*

---

## III. MẸO TRẢ LỜI CÂU HỎI VẤN ĐÁP / PHẢN BIỆN (Q&A TIPS)

1. **Thầy hỏi: "Tại sao nhóm chọn tần số SYSCLK là 84 MHz mà không dùng 96 MHz?"**
   * *Trả lời:* "Dạ thưa thầy, thạch anh ngoài trên kit WeAct V3.0 là 25 MHz. Với bộ chia PLL của dòng STM32F401, cấu hình SYSCLK = 84 MHz (M=25, N=336, P=4) cho phép bộ chia USB PLL (Q=7) tạo ra chính xác $48.0\text{ MHz}$ cho USB OTG FS mà không có sai số. Đồng thời, 84 MHz chia chẵn ra các tần số lấy mẫu 6 MHz, 3 MHz, 2 MHz, 1 MHz... với sai số chu kỳ bằng 0."
2. **Thầy hỏi: "Làm thế nào để đảm bảo không bị mất mẫu dữ liệu trước khi có trigger (Pre-trigger)?"**
   * *Trả lời:* "Dạ thưa thầy, nhóm giải quyết bằng cách: Trong trạng thái Pre-sampling, firmware khóa hoàn toàn ngắt EXTI. Firmware chỉ unmask EXTI khi cờ DMA Half-Transfer bật, nghĩa là DMA đã ghi tròn ít nhất $16.384\text{ mẫu}$ ($\ge 20\%$ pre-trigger yêu cầu). Sau đó kết hợp giải thuật Buffer Unrolling xoay vòng mảng tròn để đưa điểm trigger về đúng vị trí danh định $t_{6554}$."
3. **Nhóm khác hỏi: "Tại sao không dùng ngắt CPU đếm số mẫu sau trigger mà phải dùng Timer 2?"**
   * *Trả lời:* "Ở tần số 6 MHz, mỗi mẫu chỉ cách nhau $166.7\text{ ns}$ (tương đương 14 chu kỳ clock). Nếu CPU phải vào ngắt đếm từng mẫu thì CPU sẽ bị quá tải $100\%$ và gây mất mẫu. Việc dùng Timer 2 ở chế độ Slave nhận xung ITR0 từ Timer 1 giúp việc đếm 26.214 mẫu được thực hiện hoàn toàn bằng phần cứng mà không tốn một chu kỳ CPU nào."
