## [TÀI LIỆU 14] HỒ SƠ CHUYÊN MÔN: AUTOMATION TEST ARCHITECT / SDET (TEST FRAMEWORK &amp; CI/CD PIPELINES)

1. Phạm vi vai trò &amp; Hệ quy chiếu ngành
- Vị trí cốt lõi: Software Development Engineer in Test (SDET) / Middle-Senior Automation QA Engineer.
- Domain ứng dụng: SaaS quy mô toàn cầu, Nền tảng phân phối nội dung trực tuyến, Hệ sinh thái ứng dụng siêu thị/bán lẻ.
- Mục tiêu then chốt của vị trí: Xây dựng, bảo trì và nhân rộng các khung kiểm thử tự động (Automation Frameworks) có độ ổn định cao (High Reliability), thời gian thực thi ngắn và dễ bảo trì; tích hợp sâu kiểm thử vào chu trình CI/CD để chặn đứng mã nguồn lỗi trước khi hợp nhất vào nhánh chính.
2. Hệ sinh thái cộng tác &amp; Giao diện luồng công việc
- Thượng nguồn: Tiếp nhận các kịch bản kiểm thử hồi quy được chuẩn hóa từ Manual QA; phối hợp cùng Backend/Frontend Engineers để yêu cầu gắn định danh kiểm thử chuẩn (Test IDs / data-testid).
- Hạ nguồn: Chuyển giao các pipeline kiểm thử cho DevOps/Platform Team chạy trong chu trình phát hành; cung cấp báo cáo đo lường chất lượng mã nguồn tự động (Test Execution Metrics) cho Engineering Manager.
- Giao tiếp ngang: Phối hợp cùng SRE để thiết lập các bài thử nghiệm tải (Load/Stress Testing) trước các chiến dịch kinh doanh lớn.
3. Ngăn xếp công nghệ xu hướng &amp; Kiến trúc lõi
- Web UI Automation: Playwright (TypeScript/Python - dẫn đầu về tốc độ và khả năng chạy song song), Cypress, Selenium 4 (BiDi protocol).
- Mobile Automation: Appium 2.0, Maestro (công cụ kiểm thử di động thế hệ mới với cú pháp khai báo YAML tốc độ cao).
- API &amp; Contract Testing: RestAssured, Pact.io (Consumer-Driven Contract Testing cho Microservices), Postman/Newman.
- Performance &amp; Reliability: k6 (viết script bằng JavaScript, tiêu tốn ít tài nguyên), Locust, Apache JMeter.
- Hạ tầng thực thi: Docker, Selenium Grid / Moon (Kubernetes-native), Allure Report, GitHub Actions / GitLab CI.

## 4. Bài toán kỹ thuật thực chiến &amp; Điểm nghẽn vận hành

- Vấn nạn "Kiểm thử chập chờn" (Flaky Tests Epidemic):
- Vấn đề: Bộ kiểm thử gồm 500 test cases chạy trên CI/CD, có những lần chạy fail ngẫu nhiên dù mã nguồn không thay đổi. Đội ngũ lập trình viên mất niềm tin vào kết quả test và bấm "Re-run" vô tội vạ.
- Bản chất kỹ thuật: Lạm dụng hàm ngủ cứng (sleep(5000)), bất đồng bộ DOM chưa hoàn tất, rò rỉ trạng thái giữa các ca test (Test State Leakage), hoặc tài nguyên máy chủ CI bị nghẽn CPU/RAM đột ngột.
- Giải pháp: Triệt tiêu hoàn toàn sleep(), chuyển sang cơ chế Auto-waiting và Explicit Polling (chờ sự kiện mạng idle hoặc phần tử đạt trạng thái attached/visible); thực thi cơ chế cô lập dữ liệu (Data Isolation: mỗi test case tự khởi tạo tài khoản và phiên độc lập); gắn cờ tự động cách ly các test case chập chờn (Quarantine Pipeline) để phân tích nguyên nhân mà không chặn luồng release chính.
- Thời gian thực thi pipeline quá lâu (Slow Execution Time):
- Vấn đề: Bộ test tự động mất hơn 2 tiếng để hoàn thành, làm nghẽn toàn bộ quá trình tích hợp liên tục (CI).
- Giải pháp: Tái cấu trúc framework để hỗ trợ Sharding &amp; Parallel Execution (chia bộ test thành nhiều phần chạy đồng thời trên 8-16 worker containers qua Playwright Sharding); thay thế các bước thao tác UI đăng nhập lặp đi lặp lại bằng cách inject trực tiếp Auth Token/Cookies vào Session Storage trước mỗi ca test.

## 5. Tương tác chuyên môn &amp; Phản biện kỹ thuật

- Phản biện về Tháp Kiểm thử (The Testing Pyramid Reality):
- Tình huống: Quản lý dự án yêu cầu đội Automation viết kịch bản End-to-End (E2E) qua giao diện Web cho 100% tất cả các trường hợp kiểm thử để "nhìn thấy app chạy trên màn hình cho yên tâm".
- Luận điểm phản biện: Chứng minh tính thiếu bền vững của mô hình cây kem ngược (Inverted Testing Pyramid / Ice Cream Cone): E2E test qua UI chạy chậm nhất, chi phí bảo trì đắt nhất và dễ flaky nhất khi giao diện thay đổi nhỏ. Đề xuất quy hoạch lại theo Tháp chuẩn: 70% Unit Test (do Developers viết), 20% Integration/API/Contract Test (nhanh, ổn định), và chỉ dành 10% E2E UI cho các luồng kinh doanh sống còn (Happy Paths).

## 6. Môi trường tác nghiệp &amp; Công cụ thực tế

- Hạ tầng làm việc: Môi trường dòng lệnh (CLI), VS Code với extension Playwright Runner, Dashboard Allure hiển thị lịch sử chạy test và video quay lại khoảnh khắc test bị gãy.
- Công cụ giám sát: Bảng theo dõi thời gian thực thi (Pipeline Execution Duration Trends) và tỷ lệ vượt qua lần đầu (Pass Rate on First Run) gắn trực tiếp trên kênh Slack của Engineering Team.