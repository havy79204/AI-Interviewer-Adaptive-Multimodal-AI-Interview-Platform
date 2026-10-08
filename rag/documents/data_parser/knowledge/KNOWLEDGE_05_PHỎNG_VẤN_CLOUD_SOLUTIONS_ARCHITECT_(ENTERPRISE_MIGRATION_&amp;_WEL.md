## [TÀI LIỆU 05] PHỎNG VẤN CLOUD SOLUTIONS ARCHITECT (ENTERPRISE MIGRATION &amp; WELL-ARCHITECTED)

1. Định vị chức danh &amp; Ngành nghề cốt lõi
- Vị trí: Senior / Principal Cloud Solutions Architect.
- Cấp bậc: Senior / Lead Consultant / Enterprise Architect.
- Domain tiêu biểu: Chuyển đổi số doanh nghiệp lớn (Enterprise Digital Transformation), Ngân hàng &amp; Tài chính, Bán lẻ đa kênh, Chính phủ số.
- Mục tiêu then chốt trong buổi phỏng vấn: Thẩm định khả năng nhìn bao quát bức tranh toàn cảnh (Big Picture), năng lực chuyển đổi các yêu cầu kinh doanh mơ hồ thành
6. kiến trúc kỹ thuật chuẩn mực (High-Level &amp; Low-Level Design), tư duy bảo vệ giải pháp trước C-Level và kỹ năng quản trị rủi ro di chuyển hạ tầng.
2. Hệ sinh thái vai trò &amp; Hội đồng phỏng vấn
- Người phỏng vấn chính: Chief Technology Officer (CTO), Head of Enterprise Architecture, VP of Technology.
- Giao diện làm việc thực tế: Làm việc với ban lãnh đạo doanh nghiệp (CFO để bàn về chi phí, CISO để thẩm định bảo mật), dẫn dắt các Tech Lead và DevOps Lead hiện thực hóa bản vẽ kiến trúc.
3. Công nghệ xu hướng &amp; Khái niệm bắt buộc
- Cloud Architecture Frameworks: AWS Well-Architected Tool (6 trụ cột), Azure Architecture Center, Cloud Adoption Framework (CAF).
- Chiến lược Di chuyển Đám mây: The 7 Rs of Cloud Migration (Rehost, Replatform, Refactor, Repurchase, Relocate, Retain, Retire).
- Mạng &amp; Bảo mật Doanh nghiệp: Hybrid Cloud (Direct Connect / ExpressRoute), Transit Gateway, Hub-and-Spoke topology, Zero Trust Architecture.
- Khả năng phục hồi (Resilience): Multi-region Active-Active, RPO / RTO modeling, Chaos Engineering (AWS Fault Injection Simulator).
4. Kịch bản phỏng vấn kỹ thuật &amp; Tình huống "bắt bài"
- Bài toán thiết kế hệ thống lớn (System Design Challenge): "Một tập đoàn bán lẻ truyền thống có 500 siêu thị đang vận hành toàn bộ phần mềm ERP và POS trên một trung tâm dữ liệu On-premise đã cũ. Họ muốn di chuyển toàn bộ lên Cloud trong vòng 9 tháng với yêu cầu: Thời gian ngừng hệ thống để chuyển đổi (Cutover downtime) tối đa là 2 giờ vào đêm Chủ Nhật. Bạn sẽ thiết kế lộ trình di chuyển này như thế nào?"
- Kỳ vọng:
18. ■ Phân tích và phân loại hệ thống theo 7 Rs: Ứng dụng POS cần di chuyển trước hay sau? Cơ sở dữ liệu đồng bộ ra sao?
19. ■ Giải pháp dữ liệu: Dùng AWS Database Migration Service (DMS) kết hợp Change Data Capture (CDC) để đồng bộ dữ liệu liên tục từ On-premise lên Cloud trước hàng tháng trời mà không làm gián đoạn bán hàng.
20. ■ Kế hoạch Cutover: Chạy song song (Parallel Run) trong 2 tuần, thiết lập đường truyền chuyên dụng (Direct Connect); chuẩn bị kịch bản Rollback chi tiết nếu việc cutover vượt quá 2 giờ.
- Tình huống bảo vệ quan điểm trước Hội đồng (C-Level Debate): "CFO nói rằng: 'Chi phí vận hành Cloud của chúng ta đang cao hơn 20% so với việc mua đứt dàn máy chủ đặt ở văn phòng. Tôi muốn hủy dự án Cloud để quay lại dùng On-premise'. Là một Architect, bạn sẽ phân tích và phản biện luận điểm này như thế nào?"
- Kỳ vọng: Đưa ra khái niệm Tổng chi phí sở hữu (TCO - Total Cost of Ownership): Nhắc đến chi phí ẩn của On-premise (tiền điện làm mát 24/7, đội ngũ bảo trì phần cứng, khấu hao linh kiện, chi phí rủi ro khi hỏng hóc phần cứng mất hàng tuần chờ mua linh kiện thay thế). Đồng thời đưa ra kế hoạch FinOps hành động
23. ngay: Áp dụng Savings Plans, Rightsizing hạ tầng để giảm 25% hóa đơn Cloud trong 30 ngày.
5. Sự cố phòng phỏng vấn &amp; Cách làm chủ không gian
- Môi trường Online:
- Sự cố: Bị ngắt lời liên tục hoặc người phỏng vấn đặt câu hỏi xoay quanh nhiều khía cạnh kỹ thuật lan man làm chệch hướng giải pháp chính.
- Xử lý: Sử dụng kỹ thuật "Framing": "Trước khi đi sâu vào chi tiết cấu hình mạng của từng Subnet, em xin phép tóm tắt 3 trụ cột kiến trúc cốt lõi mà em đang giải quyết: (1) Tính toàn vẹn dữ liệu; (2) Thời gian Cutover 2 giờ; và (3) Khả năng Rollback. Em sẽ đi qua trụ cột thứ nhất trong 2 phút, sau đó chúng ta cùng thảo luận sâu nhé."
- Môi trường Onsite:
- Tư thế đứng và tương tác với Bảng trắng: Không bao giờ để bảng bị bẩn hoặc chằng chịt các mũi tên rối rắm. Xóa sạch những phần nháp không còn dùng đến; dùng bút màu khác biệt (xanh cho luồng chính, đỏ cho điểm rủi ro/firewall, đen cho ghi chú thông số) để hội đồng dễ dàng theo dõi bản vẽ kiến trúc.