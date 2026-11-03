BÀI TẬP LỚN

Hệ thống nhúng và thiết kế giao tiếp nhúng – 2026.1

1. Đề tài

1.  Thiết kế và xây dựng thiết bị logic analyzer đơn giản.

2.  Thiết kế và xây dựng thiết bị logic analyzer hiệu năng cao.

2. Giải thích

Logic analyzer (LA) là thiết bị chuyên dụng dùng để thu thập, ghi lại và hiển thị đồng thời
nhiều tín hiệu số trong hệ thống điện tử, giúp quan sát trạng thái logic theo thời gian với độ
phân giải cao. Ở các ứng dụng cơ bản, nó được dùng để phân tích mức logic (0/1), kiểm tra
quan hệ timing giữa các tín hiệu và giải mã các giao thức truyền thông như SPI, I2C, UART
nhằm xác định lỗi truyền dữ liệu hoặc sai lệch đồng bộ. Tuy nhiên, trong các hệ thống hiệu
năng cao (VD ứng dụng có FPGA), vai trò của logic analyzer trở nên quan trọng hơn nhiều,
khi nó giúp theo dõi hoạt động song song phức tạp của hàng trăm đến hàng nghìn tín hiệu nội
bộ  và  ngoại  vi.  Kỹ  sư  có  thể  sử  dụng  LA  (bao  gồm  cả  dạng  external  và  embedded  như
Integrated Logic Analyzer – ILA trong FPGA) để quan sát luồng dữ liệu, pipeline xử lý, trạng
thái FSM và các vấn đề timing ở mức hệ thống. Nhờ đó, thiết bị này hỗ trợ mạnh mẽ trong
việc debug các thiết kế tốc độ cao, tối ưu hiệu năng và đảm bảo tính đúng đắn của các thuật
toán phần cứng phức tạp, góp phần rút ngắn đáng kể chu kỳ phát triển sản phẩm.

Bài tập lớn này yêu cầu các nhóm sinh viên  tự xây dựng một LA  ở mức độ “proof of

concept” để cùng lúc đạt được nhiều mục đích gồm:

  Hiểu thêm về LA, một thiết bị đo lường quan trọng trong lĩnh vực điện tử nhưng ít

được biết đến hơn so với oscilloscope hay multimeter.

  Củng cố khả năng thực chiến về lập trình nhúng, phải làm chủ được I/O, ngắt, timer,

quản lý bộ nhớ, truyền dữ liệu, v.v.

  Phát triển khả năng tích hợp hệ thống do phải phối hợp nhiều loại ngoại vi trong chip

và kết nối với App trên máy tính hay màn hình hiển thị.

  Phát triển các năng lực khác: thiết kế và mô phỏng mạch bảo vệ đầu vào, thiết kế và

thực hành các kịch bản test, v.v.

Hai topic của bài tập hướng tới hai công việc đòi hỏi quy mô và nền tảng phần cứng rất

khác nhau. Cụ thể:

  Topic 1: thiết kế và xây dựng một thiết bị logic analyzer có phần cứng đơn giản, gọn
nhẹ, giá rẻ  số lượng kênh không cần nhiều, tốc độ không cần cao. Về cơ bản, topic
này có độ khó trung bình, tập trung vào nguyên lý cơ bản của đo tín hiệu số và giao
tiếp vi điều khiển. Nền tảng phần cứng nên dùng các MCU phổ biến như STM32 hoặc
Arduino, kết hợp bộ đệm logic (VD: 74HC245/74HC125/…) và/hoặc các mạch điện
phù hợp  để bảo vệ đầu vào. Hướng thực hiện: lấy mẫu  GPIO  theo timer (sampling
đều), lưu buffer trong RAM rồi truyền qua UART/USB lên PC; phần mềm PC hiển thị
waveform đơn giản và có thể decode cơ bản (UART/I2C). Trọng tâm là hiểu sampling

rate, aliasing và cách đồng bộ dữ liệu. Ở một cấu hình đơn giản nhất, việc hiển thị có
thể được thực hiện tại chỗ bởi một màn hình LCD đồ họa có kích thước tối thiểu như
quy định trong Mục 3.

  Topic 2: thiết kế và xây dựng một thiết bị logic analyzer có phần cứng phức tạp hơn,
hiệu năng cao hơn trong Topic 1  số lượng kênh lớn (e.g., 8-24), tốc độ cao, phần
mềm đa chức năng (tính nhiều thông số xung, phân tích giao thức, …). Topic này có
độ khó cao, phù hợp nhóm sinh viên thích các yêu cầu có tính thách thức và có nền
tảng về lập trình FPGA vì liên quan đến xử lý song song, timing chính xác và thiết kế
hệ thống. Nền tảng phần cứng nên dùng FPGA như Xilinx Artix-7 hoặc Intel Cyclone
V để đạt tốc độ lấy mẫu cao (tens–hundreds MHz) và nhiều kênh (8–24+). Có thể kết
hợp FIFO + SDRAM/DDR để lưu dữ liệu lớn, giao tiếp PC qua USB tốc độ cao (FTDI
FT2232H hoặc Cypress FX2). Hướng thực hiện: thiết kế module capture song song,
trigger (edge/pattern), bộ đệm dữ liệu và pipeline xử lý; phần mềm PC cần mạnh hơn
(GUI + decode nhiều protocol như SPI/I2C/UART/CAN). Có thể tích hợp thêm ILA
nội bộ FPGA để debug chính hệ thống.

3. Yêu cầu và định hướng

  Topic 1: số kênh tối thiểu là 2, tốc độ lấy mẫu tối thiểu là 1 kHz, hiển thị tín hiệu logic
theo thời gian trên màn hình LCD hoặc LED có độ phân giải tối thiểu là 128×64 pixel
hoặc trên màn hình PC.

  Topic 2: số kênh tối thiểu là 8, tốc độ tối thiểu là 25 MHz, hiển thị dạng sóng trên màn

hình có độ phân giải tối thiểu là HD hoặc trên màn hình máy tính PC.

  Với cả hai topic:

o  Cần luận giải kỹ về độ chính xác của quan hệ timing giữa các tín hiệu (kênh).

o  Khuyến khích xây dựng chức năng giải mã các giao thức truyền thông thông

dụng như SPI, I2C, UART, v.v.

o  Không yêu cầu phải hiển thị real-time. Nếu việc truyền thông dữ liệu tốc độ cao
theo thời gian thực là khó khăn, có thể xử lý offline bằng cách: capture các xung
(trong một khoảng thời gian) và lưu dữ liệu vào buffer rồi xử lý và hiển thị sau.

o  Nên tham khảo tính năng của các loại LA (đơn giản + phức tạp) để xây dựng
các “giá trị gia tăng” phù hợp với năng lực cho sản phẩm của nhóm mình.

o  Phải có mạch bảo vệ đầu vào cho LA với khả năng bảo vệ tối thiểu là 12 V đối
với điện áp một chiều cấp vào liên tục và 200 V đối với một xung xuông đơn lẻ
có độ rộng đến 1 ms.

o  Phải mô phỏng để chứng minh mạch bảo vệ đầu vào không làm xung vuông bị
méo đến mức không thể nhận diện được, từ tần số thấp nhất đến tần số cao nhất.

o  Sau khi thiết kế, các nhóm cần mô tả rõ phạm vi và điều kiện bảo vệ đã được
chứng minh bằng mô phỏng. VD: các input đo mức logic TTL nhưng có thể
chịu điện áp từ −50 V đến +50 V cấp liên tục và có thể chịu đến ±500 V với
từng xung đơn lẻ có độ rộng nhỏ hơn 2 ms.

  Tổ chức thực hiện:

o  Nhóm 3-4 thành viên, tự phân công công việc.

o  Báo cáo tiến độ: bắt đầu từ 11/11, lần lượt các nhóm, mỗi nhóm cử đại diện

trình bày slide trong khoảng 3-5 phút về kết quả hiện tại.

o  Báo cáo cuối kỳ: buổi riêng, thời gian và địa điểm sẽ thống nhất sau.

  Kết quả thực hiện của các nhóm sẽ được review chéo bởi nhóm khác để tăng tính cạnh

tranh và hỗ trợ việc đánh giá.

4. Nộp kết quả và bảo vệ

  Cuối kỳ, các nhóm nộp báo cáo tổng hợp dưới dạng file Word (có template kèm theo)

trên MS Teams. File báo cáo:

o  Trình bày vai trò và chức năng của LA, khảo sát thông số và tính năng của các
LA thông dụng, xác định mục tiêu thiết kế; phân tích các lý thuyết, giải pháp,
công nghệ liên quan; thiết kế hệ thống (cứng/mềm); thiết kế các kịch bản thử
nghiệm, phân tích kết quả, đánh giá, thảo luận và kết luận.

o  Tên file đặt theo thành viên đại diện + thông số chính. VD: “Đào Việt Hùng –

16 kênh 50 MHz”.

  Buổi bảo vệ:

o  Các nhóm in và nộp quyển báo cáo đã hoàn chỉnh (không đóng bìa bóng kính).

o  Trình bày slide ngắn gọn mô tả quá trình thực hiện, kết quả thu được được, và
demo hoặc chiếu video demo quay sẵn (mỗi video dài không quá 3 phút).

o  Từng thành viên trả lời câu hỏi về phần công việc mà mình phụ trách.

  Đánh giá điểm:

o  20% báo cáo tiến độ

o  30% kết quả thực tế đạt được + demo hay video demo

o  30% báo cáo tổng hợp của nhóm

o  20% vấn đáp

o  Thưởng đến 1 điểm cho mỗi thành viên nhóm có video (dài không quá 3 phút)
để giới thiệu dự án + quá trình thực hiện + demo sản phẩm với kịch bản cuốn
hút, nội dung logic, và xử lý hậu kỳ chuyên nghiệp :)

Nếu có câu hỏi liên quan đến đề tài, yêu cầu công việc, vấn đề nảy sinh … cần tháo gỡ, các
nhóm trao đổi với thầy để sớm giải quyết./.

