## [TÀI LIỆU 24] KỸ THUẬT PHỎNG VẤN ONSITE: LÀM CHỦ WHITEBOARD, TÂM LÝ VÀ TRANH LUẬN KỸ THUẬT

1. Bối cảnh không gian &amp; Động lực phòng phỏng vấn Onsite
- Buổi phỏng vấn trực tiếp tại văn phòng (Onsite Interview) là nơi bộc lộ rõ nhất bản lĩnh thực tế, tác phong làm việc nhóm và khả năng chịu áp lực của ứng viên.
- Bầu không khí phòng họp, sự hiện diện vật lý của Hội đồng phỏng vấn, chiếc bảng trắng và các vật dụng xung quanh tạo ra một trường tương tác tâm lý đa chiều.
- Mục tiêu của tài liệu: Hướng dẫn cách điều phối không gian phỏng vấn Onsite chuẩn mực cho cả người phỏng vấn và ứng viên, biến một buổi "hỏi cung căng thẳng" thành một phiên "cộng tác kỹ thuật thực chất" (Collaborative Engineering Session).
2. Quản trị Không gian &amp; Vật dụng phòng họp (Physical &amp; Environmental Dynamics)
- Chiếc Bảng trắng (The Whiteboard Anchor):
- Quy tắc bố cục bảng chuẩn: Không gian bảng phản ánh trật tự tư duy của bộ não. Cần hướng dẫn ứng viên chia bảng thành các khu vực logic trước khi bắt đầu:
- Plaintext

┌──────────────────┬─────────────────────────────────┬──────

────────────┐

│ 1. YÊU CẦU &amp; │ 2. BẢN VẼ KIẾN TRÚC CHÍNH │ 3. RỦI RO &amp; │ │ RÀNG BUỘC │ (Component &amp; Data Flow) │ TỐI ƯU HÓA │ │ - DAU / QPS │ │ - Single Point │ │ - Latency SLA │ [Load Balancer] ➔ [API Gateway] │ of Failure │ │ - Storage/5Yrs │ │ │ - Caching Layer │ │ - Constraints │ [Microservices] ➔ [Database] │ - Bottlenecks │

└──────────────────┴─────────────────────────────────┴──────

────────────┘

○

○

- Xử lý sự cố vật lý: Bút dạ hết mực, bảng bẩn không xóa được. Người phỏng vấn cần chủ động chuẩn bị sẵn 3 màu bút mới (Đen, Xanh, Đỏ) và khăn lau sạch trước khi ứng viên bước vào phòng. Nếu bút hỏng, đây cũng là bài kiểm tra phản xạ: Ứng viên chủ động nhờ đổi bút hay lúng túng cố viết bằng cây bút mờ?
- Cốc nước trên bàn &amp; Nhịp thở điều hòa:
- Khi gặp một câu hỏi hóc búa làm tim đập nhanh hoặc não bộ bị đơ (Blank out), hãy cầm cốc nước lên, uống một ngụm chậm rãi. Hành động này mang lại 4-5 giây quý giá để cơ thể lấy lại bình tĩnh, hạ nhịp tim và sắp xếp lại các suy nghĩ trước khi mở lời.
- Giao tiếp thị giác và Góc đứng cơ thể:
- Tuyệt đối tránh tư thế đứng quay lưng 100% vào người phỏng vấn để cắm cúi vẽ lên bảng quá 2 phút mà không nói gì.
- Góc đứng lý tưởng là 45 độ so với mặt bảng: Một mắt nhìn bản vẽ, một mắt hướng về phía Hội đồng phỏng vấn, liên tục tương tác: "Em đang vẽ khối này để làm nhiệm vụ X, anh/chị có thấy luồng này hợp lý với bài toán chưa ạ?".
3. Kiểm soát Tranh luận Kỹ thuật (Handling Technical Debates &amp; Disagreements)
- Kịch bản xung đột quan điểm:
- Người phỏng vấn cố tình phản bác một giải pháp của ứng viên: "Tôi thấy dùng MongoDB ở đây là hoàn toàn sai lầm, tại sao không dùng PostgreSQL?".
- Phản xạ của ứng viên kém: Hoặc là sợ sệt lập tức từ bỏ quan điểm của mình ("Dạ vâng thế em đổi sang Postgres ạ"), hoặc là hiếu chiến tranh cãi tay đôi để bảo vệ cái tôi ("Mongo tốt hơn chứ, ai dùng Postgres cho việc này nữa").
- Phản xạ của ứng viên xuất sắc (Tư duy Trưởng thành): Tách bạch giữa Sự thật

kỹ thuật (Facts) và Sự đánh đổi (Trade-offs): "Em đề xuất MongoDB ở đây vì cấu trúc dữ liệu của các sự kiện log này hoàn toàn không cố định và chúng ta cần tốc độ ghi cực nhanh mà không cần quan hệ ràng buộc ACID phức tạp. Tuy nhiên, nếu nghiệp vụ của công ty ưu tiên tính toàn vẹn giao dịch và đội ngũ hiện tại đã quá thành thạo tối ưu Postgres, thì việc chọn PostgreSQL kết hợp JSONB cũng là một sự đánh đổi hoàn toàn hợp lý. Chúng ta hãy cùng xem xét yếu tố nào quan trọng hơn đối với hệ thống này ạ."

- Nguyên tắc "Strong Opinions, Weakly Held":
- Đánh giá cao những ứng viên có quan điểm kỹ thuật vững vàng dựa trên dữ liệu, nhưng sẵn sàng thay đổi phương án khi được cung cấp thêm các dữ kiện ràng buộc mới một cách cởi mở, không tự ái.