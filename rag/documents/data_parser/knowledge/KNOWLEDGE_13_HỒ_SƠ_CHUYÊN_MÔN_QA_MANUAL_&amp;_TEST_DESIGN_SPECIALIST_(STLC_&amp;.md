## [TÀI LIỆU 13] HỒ SƠ CHUYÊN MÔN: QA MANUAL &amp; TEST DESIGN SPECIALIST (STLC &amp; RISK-BASED TESTING)

## 1. Phạm vi vai trò &amp; Hệ quy chiếu ngành

- Vị trí cốt lõi: Software Quality Assurance Engineer (Manual &amp; Test Design / Functional QA).
- Domain ứng dụng: Core Banking &amp; FinTech (luồng chuyển tiền, đối soát), HealthTech (hồ sơ bệnh án điện tử, bảo mật HIPAA), E-Commerce Checkout &amp; Logistics.
- Mục tiêu then chốt của vị trí: Đóng vai trò là tuyến phòng thủ chất lượng đầu tiên; bảo đảm độ bao phủ yêu cầu (Requirements Traceability); phát hiện lỗi ở giai đoạn sớm nhất (Shift-Left Testing) nhằm giảm thiểu chi phí sửa lỗi (Cost of Quality); thiết kế kịch bản thử nghiệm góc cạnh (Edge cases) mà người phát triển thường bỏ quên.

## 2. Hệ sinh thái cộng tác &amp; Giao diện luồng công việc

- Thượng nguồn: Nhận tài liệu PRD, User Stories và tiêu chí nghiệm thu (Acceptance Criteria - AC) từ Product Owner / Business Analyst; tham gia các buổi Grooming/Refinement để chất vấn các điểm mâu thuẫn hoặc thiếu logic trong luồng nghiệp vụ.
- Hạ nguồn: Làm việc trực tiếp với Software Developer (tái hiện lỗi, xác nhận môi trường, giải thích Root Cause); bàn giao các bộ test cases hồi quy cốt lõi (Regression Suite) cho Automation QA để tự động hóa.
- Giao tiếp ngang: Phối hợp với UI/UX Designer để đối chiếu giao diện chuẩn pixel, luồng vi tương tác (micro-interactions) và tính khả dụng (Usability Testing) trên các thiết bị thực tế.
3. Ngăn xếp công nghệ xu hướng &amp; Khái niệm cốt lõi
- Kỹ thuật thiết kế kiểm thử (Test Design Techniques): Equivalence Partitioning (Phân vùng tương đương), Boundary Value Analysis (Phân tích giá trị biên 2-value/3-value), State Transition Testing (Kiểm thử chuyển trạng thái), Decision Table Testing (Bảng quyết định), Pairwise/Orthogonal Array Testing.
- Công cụ quản lý vòng đời kiểm thử: Jira, TestRail, Xray, Zephyr Scale, Confluence.
- Kiểm thử API &amp; Dữ liệu: Postman (Collections, Variables, Tests script với Chai assertions), Charles Proxy / Fiddler (bắt và can thiệp gói tin HTTP/HTTPS, giả lập mạng yếu/mất kết nối đột ngột), SQL cơ bản (truy vấn verify dữ liệu tầng DB).
- Kiểm thử đa thiết bị: BrowserStack, Sauce Labs, Xcode Simulator, Android Studio Emulators.
4. Bài toán kỹ thuật thực chiến &amp; Điểm nghẽn vận hành
- Hiện tượng "Cháy giáo án" kiểm thử hồi quy (Regression Test Bottleneck):
- Vấn đề: Khi ứng dụng phình to sau 2 năm phát triển, bộ test case hồi quy lên tới hơn 1,500 ca. Mỗi đợt release cuối sprint, đội QA mất 3 ngày manual test nhưng vẫn bị trễ hạn hoặc bỏ sót lỗi ở các module phụ.
- Bản chất: Thiếu chiến lược phân loại rủi ro; xem tất cả test cases có độ ưu tiên ngang nhau dẫn đến lãng phí nguồn lực.
- Giải pháp: Áp dụng Risk-Based Testing (RBT): Đánh giá từng tính năng theo ma trận ma lực tác động (Impact) và khả năng xảy ra lỗi (Likelihood). Chia bộ hồi quy thành 3 tầng: P0 - Smoke/Sanity (chạy 100% trước khi release, ~50 cases luồng sống còn); P1 - Critical Business Flow (~200 cases); P2/P3 - Edge cases/Giao diện phụ (chạy luân phiên hoặc tự động hóa dần).
- Lỗi phụ thuộc trạng thái dữ liệu (State-dependent Bugs) &amp; Dữ liệu rác trên Staging:
- Vấn đề: Tester không thể tái hiện được lỗi người dùng gặp phải trên Production vì môi trường Staging có dữ liệu không đồng nhất, bị ghi đè liên tục bởi các tester khác.
- Giải pháp: Chuẩn hóa quy trình chuẩn bị dữ liệu kiểm thử (Test Data Management - TDM): Thiết lập các bộ kịch bản API tự động tạo dữ liệu mới (Seeding Data) trước mỗi lượt test; quy định cơ chế cô lập dữ liệu người dùng test bằng tiền tố định danh riêng.
5. Tương tác chuyên môn &amp; Phản biện kỹ thuật
- Xử lý tình huống "Lỗi này là tính năng, không phải bug" (Bug vs. Feature Dispute):
- Tình huống: Lập trình viên từ chối sửa lỗi (đóng ticket với trạng thái Won't Fix hoặc By Design) khi người dùng nhập số tiền có ký tự thập phân khiến hệ thống làm tròn xuống gây thất thoát tiền lẻ.
- Luận điểm xử lý: Không tranh cãi cảm tính. QA trích dẫn trực tiếp điều khoản nghiệp vụ tài chính, tính toán mức thất thoát lũy kế nếu có 100,000 giao dịch/ngày; gắn kèm log dữ liệu, video bằng chứng hành vi người dùng và kéo Product Owner vào cuộc họp 10 phút để chốt quyết định cuối cùng dựa trên rủi ro kinh doanh.
6. Môi trường tác nghiệp &amp; Công cụ thực tế
- Thiết bị tác nghiệp: Bàn làm việc luôn có ít nhất 2-3 thiết bị thật (1 iPhone đời mới, 1 iPhone đời cũ màn hình nhỏ, 1 thiết bị Android chip yếu/hệ điều hành tùy biến như Xiaomi/Oppo).
- Màn hình theo dõi: Một màn hình mở tài liệu đặc tả và giao diện web cần test; một màn hình bật Network Tab của trình duyệt cùng phần mềm bắt gói tin Charles Proxy để soi mã phản hồi (Response Status, Payload JSON) theo thời gian thực.