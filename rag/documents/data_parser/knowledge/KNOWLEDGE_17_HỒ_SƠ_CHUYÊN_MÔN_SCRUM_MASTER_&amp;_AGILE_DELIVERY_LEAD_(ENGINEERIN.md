## [TÀI LIỆU 17] HỒ SƠ CHUYÊN MÔN: SCRUM MASTER &amp; AGILE DELIVERY LEAD (ENGINEERING VELOCITY &amp; TEAM EMPOWERMENT)

1. Phạm vi vai trò &amp; Hệ quy chiếu ngành
- Vị trí cốt lõi: Scrum Master / Agile Delivery Lead / Technical Project Manager.
- Domain ứng dụng: Các tổ chức công nghệ phát triển sản phẩm phần mềm theo mô hình Agile, Squads, Spotify Model hoặc Scaled Agile Framework (SAFe).
- Mục tiêu then chốt của vị trí: Không phải là "người chấm công" hay "người điều phối lịch họp", mà là một Lãnh đạo phục vụ (Servant Leader); tháo gỡ triệt để các rào cản cản trở tiến độ của đội ngũ kỹ thuật; tối ưu hóa tốc độ phân phối giá trị (Engineering Velocity); xây dựng văn hóa minh bạch, tự chủ và cải tiến liên tục (Kaizen).
2. Hệ sinh thái cộng tác &amp; Giao diện luồng công việc
- Thượng nguồn: Làm việc cùng Product Owner để duy trì một Product Backlog lành mạnh, được tinh gọn và làm rõ tiêu chuẩn sẵn sàng (Definition of Ready - DoR).
- Hạ nguồn: Bảo vệ đội ngũ kỹ sư (Developers, QA, DevOps) khỏi sự can thiệp làm gián đoạn từ các bên ngoài trong suốt Sprint; theo dõi tiến độ hoàn thành dựa trên Định nghĩa Hoàn thành (Definition of Done - DoD).
- Giao tiếp ngang: Phối hợp cùng các Scrum Masters khác để quản lý các điểm nghẽn phụ thuộc chéo (Cross-team Dependencies) trong các buổi Scrum of Scrums.
3. Ngăn xếp công nghệ xu hướng &amp; Phương pháp luận
- Phương pháp luận: Scrum, Kanban (WIP Limits, Cumulative Flow Diagram), SAFe (PI Planning), Lean Software Development.
- Chỉ số Kỹ thuật &amp; Tốc độ phát triển hiện đại (DORA Metrics): Deployment Frequency, Lead Time for Changes, Change Failure Rate, Time to Restore Service (MTTR).
- Công cụ quản trị quy trình: Jira Software (Cấu hình JQL, Automation Rules, Advanced Roadmaps), Linear, Miro (Retrospective Boards), Confluence.
- Khái niệm kỹ thuật hỗ trợ: Hiểu rõ Tech Debt, CI/CD pipelines, Test Automation pyramid để có tiếng nói chung với các kỹ sư.
4. Bài toán kỹ thuật thực chiến &amp; Điểm nghẽn vận hành
- Hiện tượng Sprint biến thành "Mini-Waterfall":
- Vấn đề: Đội ngũ chạy Sprint 2 tuần nhưng 8 ngày đầu các lập trình viên chỉ viết code, đến ngày thứ 9 mới dồn toàn bộ tính năng sang cho QA test. Kết quả là QA bị quá tải, phát hiện hàng loạt lỗi vào ngày cuối cùng và Sprint luôn thất bại.
- Bản chất: Thiếu tư duy chia nhỏ công việc (User Story Slicing) và thói quen làm việc theo silo chức năng.
- Giải pháp: Hướng dẫn đội ngũ kỹ thuật chia nhỏ User Story theo lát cắt dọc (Vertical Slicing: mỗi story nhỏ bao gồm cả UI, Logic và Test có thể hoàn thành trong 2-3 ngày); áp dụng quy tắc WIP Limits (Giới hạn công việc đang xử lý) trên bảng Kanban: Mỗi kỹ sư không được nhận task mới nếu task cũ chưa hoàn tất kiểm thử; thúc đẩy văn hóa Pair Testing và Tester tham gia viết test cases ngay từ ngày đầu tiên của Sprint.
- Họp Cải tiến Sprint (Sprint Retrospective) trở nên hình thức và độc hại:
- Vấn đề: Buổi Retro biến thành nơi đổ lỗi cho nhau (Blame game) giữa Dev và QA, hoặc mọi người im lặng cho qua chuyện và các vấn đề cũ tiếp tục tái diễn ở Sprint sau.
- Giải pháp: Thay đổi cấu trúc buổi họp bằng các kỹ thuật tạo môi trường an toàn tâm lý (Psychological Safety): Dùng kỹ thuật Prime Directive ("Dù kết quả thế nào, chúng ta hiểu rằng mọi người đều đã nỗ lực hết sức với những thông tin họ có tại thời điểm đó"); sử dụng bảng tương tác ẩn danh (Miro/EasyRetro); áp dụng phương pháp "5 Whys" để tìm nguyên nhân gốc rễ của quy trình thay vì nhắm vào cá nhân; chỉ chọn ra tối đa 2 hành động cải tiến có thể đo lường được (Action Items) để theo dõi gắt gao trong Sprint tiếp theo.
5. Tương tác chuyên môn &amp; Phản biện kỹ thuật
- Bảo vệ Đội ngũ trước yêu cầu "Chèn thêm task gấp" của Lãnh đạo:
- Tình huống: Giám đốc Kinh doanh bước vào phòng họp ở giữa Sprint và yêu cầu đội kỹ sư phải lập tức bỏ dở công việc để làm ngay một tính năng mới cho một khách hàng VIP vừa ký hợp đồng.
- Bản lĩnh của Scrum Master: Lịch sự nhưng kiên quyết đứng ra làm tấm khiên chắn: "Mục tiêu Sprint (Sprint Goal) đã được toàn đội cam kết và đang trong quá trình thực thi tối đa năng suất. Nếu chúng ta chèn thêm tính năng này ngay bây giờ, các cam kết chất lượng của Sprint sẽ bị vỡ. Tôi sẽ cùng anh và Product Owner ngồi lại ngay trong chiều nay để đánh giá độ ưu tiên của tính năng này. Nếu nó thực sự khẩn cấp hơn toàn bộ mục tiêu hiện tại, Product Owner có thẩm

quyền hủy Sprint hiện tại để tái lập kế hoạch Sprint mới, hoặc chúng ta sẽ đưa nó vào vị trí số 1 của Backlog cho Sprint kế tiếp bắt đầu vào thứ Hai tới."

## 6. Môi trường tác nghiệp &amp; Công cụ thực tế

- Không gian tương tác: Khu vực bảng tin vật lý với các thẻ màu sắc (Post-it notes) trong không gian mở của văn phòng, các phòng họp yên tĩnh trang bị màn hình lớn cảm ứng phục vụ các buổi tương tác nhóm từ xa.
- Bộ công cụ trực quan: Biểu đồ Burndown Chart, biểu đồ thông lượng (Throughput) và biểu đồ phân phối thời gian chu kỳ (Cycle Time Scatterplot) dùng để phản ánh sức khỏe vận hành thực tế của đội ngũ mà không dựa trên phỏng đoán cảm tính.