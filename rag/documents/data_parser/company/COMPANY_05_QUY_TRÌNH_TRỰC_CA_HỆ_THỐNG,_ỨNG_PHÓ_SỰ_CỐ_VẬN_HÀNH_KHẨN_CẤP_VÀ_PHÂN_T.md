## [DOC 05] QUY TRÌNH TRỰC CA HỆ THỐNG, ỨNG PHÓ SỰ CỐ VẬN HÀNH KHẨN CẤP VÀ PHÂN TÍCH NGUYÊN NHÂN GỐC RỄ (ON-CALL, INCIDENT MANAGEMENT &amp; POST-MORTEM POLICY)

- Mã hiệu văn bản: POL-OPS-005/2026/NEXUS
- Phiên bản: 4.2
- Ngày ban hành: 01/01/2026
- Phạm vi hiệu lực: Áp dụng bắt buộc cho toàn bộ nhân sự thuộc Khối Kỹ thuật (Site Reliability Engineering, DevOps, Cloud Infrastructure, Backend Services, Security Operations, Database Administration) tham gia vận hành các hệ thống môi trường Production của Nexus Tech Group.
- Cơ quan thẩm quyền ban hành: Ban Chỉ đạo Kỹ thuật (Engineering Steering Committee) phối hợp cùng Khối Vận hành Dịch vụ Đám mây.

## MỤC I: NGUYÊN TẮC QUẢN TRỊ TRỰC CA VÀ TRÁCH NHIỆM ON-CALL

## Điều 1: Triết lý Vận hành và Tính Bền vững của Đội ngũ Kỹ sư

1. Nexus Tech Group cam kết duy trì tính sẵn sàng của hệ thống ở cấp độ 99.99% (Four Nines Availability), tương ứng với thời gian ngừng hoạt động ngoài kế hoạch (Unplanned Downtime) không vượt quá 4.38 phút mỗi tháng.
2. Việc trực ca vận hành (On-call) là trách nhiệm tập thể của các kỹ sư trực tiếp xây dựng và triển khai dịch vụ (You build it, you run it). Tuy nhiên, công ty kiên quyết phản đối văn hóa vắt kiệt sức lao động: Trực ca phải được đền bù thỏa đáng về mặt tài chính, có cơ chế luân phiên minh bạch và bảo đảm sức khỏe thể chất, tinh thần cho kỹ sư.
3. Kỹ sư đang trong ca trực On-call được quyền ưu tiên xử lý sự cố và tạm hoãn các đầu việc phát triển tính năng mới trong Sprint nếu hệ thống phát sinh cảnh báo bất thường.

## Điều 2: Cơ chế Phân bổ Ca trực và Tiêu chuẩn Sẵn sàng (On-call Readiness) 1. Chu kỳ và luân phiên ca trực:

- Ca trực chuẩn được thiết lập theo chu kỳ 07 ngày liên tục, bắt đầu từ 09:00 sáng Thứ Ba tuần này và kết thúc vào 09:00 sáng Thứ Ba tuần kế tiếp. Việc chuyển giao ca trực vào sáng giữa tuần nhằm bảo đảm có đầy đủ lực lượng hỗ trợ tại văn phòng, tránh bàn giao ca vào cuối tuần hoặc ngày nghỉ Lễ.
- Lịch trực On-call được công bố trước tối thiểu 30 ngày trên hệ thống PagerDuty/Opsgenie. Kỹ sư chỉ được phép trực tối đa 01 ca trong vòng 03 tuần liên tiếp, nghiêm cấm bố trí một kỹ sư trực 02 ca liên tiếp trừ trường hợp khẩn cấp bất khả kháng có sự phê duyệt của Head of Engineering.
2. Quy chuẩn sẵn sàng đối với Kỹ sư Trực ca Chính (Primary On-call):
- Trong suốt thời gian của ca trực (bao gồm cả ban đêm, ngày nghỉ cuối tuần và ngày Lễ), Kỹ sư Trực ca Chính bắt buộc phải luôn mang theo bên mình điện thoại có cài đặt ứng dụng PagerDuty được cấu hình chế độ âm thanh khẩn cấp (Critical Alerts bypass Do Not Disturb).
- Luôn ở trong khu vực có kết nối mạng di động 4G/5G ổn định và mang theo máy tính xách tay công ty có cấu hình sẵn kết nối VPN, khóa bảo mật vật lý (YubiKey).
- Khoảng cách di chuyển từ vị trí cá nhân đến địa điểm có kết nối Internet băng thông rộng và môi trường làm việc an toàn không được vượt quá 15 phút.
- Tuyệt đối không sử dụng đồ uống có cồn, chất kích thích hoặc tham gia các hoạt động thể thao mạo hiểm có thể làm suy giảm khả năng tập trung và tốc độ phản xạ trong suốt thời gian trực ca.
3. Kỹ sư Trực ca Dự phòng (Secondary On-call):
- Đóng vai trò là tuyến hỗ trợ kế cận khi Kỹ sư Trực ca Chính không xác nhận cảnh báo (Acknowledge) trong vòng 05 phút, hoặc khi sự cố phát triển thành thảm họa đòi hỏi sự phối hợp của nhiều chuyên môn cùng lúc. Kỹ sư Dự phòng phải duy trì mức độ sẵn sàng phản hồi trong vòng tối đa 15 phút.

## Điều 3: Chế độ Đãi ngộ Tài chính và Nghỉ bù Trực ca (On-call Compensation)

1. Phụ cấp trách nhiệm giữ máy trực ca cố định:
- Trực ca tuần thông thường (ngoài giờ hành chính từ Thứ Hai đến Chủ Nhật): Chi trả cố định 3.500.000 VNĐ / tuần trực.
- Trực ca tuần rơi vào các dịp Lễ, Tết theo quy định nhà nước: Chi trả cố định 8.000.000 VNĐ / tuần trực.
2. Thù lao can thiệp sự cố thực tế ngoài giờ hành chính (Incident Intervention Pay):
- Nếu phát sinh sự cố đòi hỏi kỹ sư phải mở máy tính can thiệp kỹ thuật trong khoảng thời gian từ 22:00 đêm hôm trước đến 06:00 sáng hôm sau, kỹ sư được hưởng thêm thù lao làm thêm giờ (Overtime):
6. ■ Ngày thường: Tính bằng 200% mức lương giờ cơ bản cho thời gian can thiệp thực tế.
7. ■ Ngày nghỉ cuối tuần: Tính bằng 270% mức lương giờ cơ bản.
8. ■ Ngày nghỉ Lễ, Tết: Tính bằng 390% mức lương giờ cơ bản.
9. ■ Quy tắc làm tròn: Thời gian can thiệp thực tế được làm tròn tối thiểu là 01 giờ cho mỗi lần mở máy xử lý, kể cả khi sự cố được khắc phục xong trong 15 phút.
3. Chính sách Nghỉ bù Hồi phục Thể lực (Rest &amp; Recovery Leave):
- Trường hợp kỹ sư phải thức đêm xử lý sự cố nghiêm trọng (SEV-1 hoặc SEV-2) với tổng thời gian can thiệp vượt quá 02 giờ liên tục trong khoảng từ 00:00 đến 06:00 sáng:
12. ■ Kỹ sư được quyền lùi giờ bắt đầu làm việc của ngày hôm sau sang buổi chiều (bắt đầu từ 13:30) hoặc nghỉ trọn vẹn cả ngày hôm sau hưởng nguyên lương (tùy thuộc vào quyết định của Engineering Manager) để hồi phục sức khỏe.
13. ■ Toàn bộ các cuộc họp dự kiến có mặt kỹ sư trong buổi sáng hôm đó phải được hủy bỏ hoặc chuyển giao cho người khác chủ trì.

## MỤC II: PHÂN CẤP SỰ CỐ VÀ QUY TRÌNH KÍCH HOẠT PHẢN ỨNG KHẨN CẤP

Điều 4: Ma trận Định nghĩa Cấp độ Nghiêm trọng của Sự cố (Incident Severity Levels) Mọi trục trặc kỹ thuật ảnh hưởng đến hệ sinh thái Nexus phải được phân loại ngay lập tức theo 04 cấp độ nghiêm ngặt:

1. Sự cố Cấp độ 1 (SEV-1: Critical / Catastrophic Incident):
- Định nghĩa: Hệ thống lõi ngừng hoạt động hoàn toàn; sập cổng thanh toán trực tuyến hoặc sập cơ sở dữ liệu giao dịch chính; rò rỉ dữ liệu nhạy cảm ra bên ngoài; tỷ lệ giao dịch lỗi của toàn hệ sinh thái vượt quá 15%; hoặc có trên 25% lượng người dùng tích cực đồng thời (CCU) bị ảnh hưởng nghiêm trọng.
- Thời gian chấp nhận cảnh báo (MTTA - Mean Time to Acknowledge): Dưới 03 phút (24/7/365).
- Thời gian bắt đầu can thiệp kỹ thuật (MTTI - Mean Time to Investigate): Dưới 07 phút.
- Thành phần tham gia bắt buộc: Kỹ sư Trực ca Chính, SRE Lead, Tech Lead của dịch vụ liên quan, Incident Commander, và thông báo tức thời tới CTO / Head of Engineering.
2. Sự cố Cấp độ 2 (SEV-2: Major Incident):
- Định nghĩa: Một dịch vụ quan trọng bị tê liệt nhưng hệ thống lõi vẫn duy trì được luồng nghiệp vụ cơ bản (ví dụ: Tính năng tìm kiếm sản phẩm bị lỗi, hệ thống gợi ý ngừng hoạt động, nhưng giỏ hàng và thanh toán vẫn chạy bình thường); hoặc tỷ lệ giao dịch lỗi dao động từ 5% đến 15%; hoặc hiệu năng hệ thống suy giảm nghiêm trọng (độ trễ P99 Latency tăng vọt trên 5 giây).
- Thời gian chấp nhận cảnh báo (MTTA): Dưới 10 phút.
- Thời gian bắt đầu can thiệp: Dưới 15 phút.
- Thành phần tham gia: Kỹ sư Trực ca Chính và Tech Lead phụ trách module bị ảnh hưởng.
3. Sự cố Cấp độ 3 (SEV-3: Moderate Incident):
- Định nghĩa: Lỗi chức năng cục bộ không ảnh hưởng trực tiếp đến doanh thu; các tính năng phụ trợ gặp trục trặc (ví dụ: Lỗi cập nhật ảnh đại diện người dùng, thông báo đẩy marketing bị trễ); người dùng vẫn có thể hoàn thành luồng công việc thông qua thao tác thay thế.
- Thời hạn xử lý: Phản hồi và bắt đầu xử lý trong vòng 02 giờ làm việc trong khung giờ hành chính; không đánh thức kỹ sư vào ban đêm.
4. Sự cố Cấp độ 4 (SEV-4: Minor / Low Impact Incident):
- Định nghĩa: Lỗi hiển thị giao diện nhỏ (UI glitch), sai lệch định dạng text, tài liệu nội bộ bị lỗi liên kết, hoặc các cảnh báo tài nguyên đĩa cứng chạm ngưỡng 75% trên môi trường Staging/Dev.
- Thời hạn xử lý: Ghi nhận thành ticket trên Jira Backlog và xử lý trong các Sprint thường kỳ tiếp theo.

## Điều 5: Cơ chế Vận hành Phòng Tác chiến Khẩn cấp (Incident War Room Protocol)

1. Thiết lập quyền Chỉ huy Sự cố (Incident Commander - IC):
- Ngay khi sự cố SEV-1 hoặc SEV-2 được xác lập, Kỹ sư Trực ca Chính hoặc một Senior SRE được chỉ định sẽ lập tức đảm nhận vai trò Chỉ huy Sự cố (Incident Commander).
- Quyền lực của IC là tối cao trong suốt thời gian diễn ra sự cố: IC có toàn quyền ra quyết định cô lập mạng, rollback mã nguồn, ngắt kết nối với các đối tác thứ ba, hoặc kích hoạt chế độ bảo trì toàn hệ thống mà không cần chờ đợi phê duyệt từ ban giám đốc kinh doanh.
2. Kênh tác chiến chuyên biệt:
- Tự động khởi tạo một kênh Slack khẩn cấp theo cú pháp chuẩn: #incident-[NămThángNgày]-[TênDịchVụBịLỗi] (Ví dụ: #incident-20261005-payment-gateway).
- Tự động mở một đường link Google Meet hoặc Zoom War Room cố định, yêu cầu toàn bộ các kỹ sư liên quan phải tham gia thoại trực tiếp và bật chia sẻ màn hình theo dõi log.
3. Phân định vai trò tác chiến:
- Incident Commander (IC): Điều phối chung, nắm giữ bức tranh toàn cảnh, không trực tiếp gõ lệnh debug để tránh bị phân tâm chi tiết.
- Technical Lead / Scribe (Kỹ sư Ghi chép): Chịu trách nhiệm ghi lại chi tiết từng mốc thời gian (Timeline log): Ai đã làm gì, gõ lệnh gì vào lúc nào, kết quả ra sao.
- Communications Lead (Đầu mối Truyền thông): Soạn thảo thông báo tình trạng hệ thống gửi cho bộ phận Chăm sóc Khách hàng (CS), Ban Lãnh đạo và cập nhật trang trạng thái công khai (Status Page) theo định kỳ mỗi 20 phút / lần.

## MỤC III: NGUYÊN TẮC HỌP HẬU SỰ CỐ VÀ QUẢN TRỊ NGUYÊN NHÂN GỐC RỄ (POST-MORTEM POLICY)

## Điều 6: Tinh thần Văn hóa Hậu sự cố Không Đổ lỗi (Blameless Post-Mortem Culture)

1. Nexus Tech Group tuyệt đối nghiêm cấm việc tìm kiếm cá nhân để quy tội, chỉ trích hoặc áp dụng các hình thức phạt tài chính, kỷ luật lao động đối với nhân viên vô ý gây ra lỗi vận hành trong quá trình thao tác hệ thống.
2. Mọi sự cố kỹ thuật đều được nhìn nhận là thất bại mang tính cấu trúc của cả hệ thống:
- Nếu một kỹ sư vô tình gõ lệnh làm xóa dữ liệu, lỗi thuộc về hệ sinh thái đã không có cơ chế chặn lệnh nguy hiểm, thiếu môi trường sandbox an toàn, hoặc tài liệu hướng dẫn vận hành không rõ ràng.
- Mục tiêu duy nhất của phiên họp Post-Mortem là học hỏi từ thất bại, củng cố rào chắn kỹ thuật để sai sót tương tự không bao giờ có thể tái diễn trong tương lai.
3. Hành vi duy nhất bị xử lý kỷ luật là: Cố tình che giấu sự cố, nói dối về các thao tác mình đã thực hiện, hoặc cố tình chỉnh sửa file log kiểm toán nhằm thoái thác trách nhiệm minh bạch thông tin.

## Điều 7: Quy chuẩn Hồ sơ Phân tích Nguyên nhân Gốc rễ (RCA Report Standards)

1. Thời hạn ban hành: Trong vòng tối đa 48 giờ làm việc sau khi sự cố SEV-1 hoặc SEV-2 được khắc phục hoàn toàn, Incident Commander bắt buộc phải hoàn thành bản dự thảo Báo cáo Phân tích Nguyên nhân Gốc rễ (Root Cause Analysis - RCA Report) và gửi thư mời họp Post-Mortem toàn thể các bên liên quan.
2. Cấu trúc bắt buộc của một bản Báo cáo RCA:
- Bản tóm tắt dành cho Lãnh đạo (Executive Summary): Mô tả ngắn gọn sự cố trong 03 câu: Chuyện gì đã xảy ra? Tác động kinh doanh ra sao? Hệ thống đã được khôi phục như thế nào?
- Chỉ số Định lượng Thiệt hại (Impact Metrics): Thời gian ngừng dịch vụ chính xác (tính bằng phút); số lượng người dùng bị ảnh hưởng; số lượng giao dịch bị thất bại; ước tính thiệt hại doanh thu trực tiếp.
- Biên niên sử Sự kiện Chi tiết (Detailed Chronological Timeline): Ghi nhận chính xác từng mốc thời gian theo chuẩn UTC+7, từ thời điểm mầm mống lỗi được đưa vào hệ thống (thời điểm commit/deploy code), thời điểm hệ thống bắt đầu suy giảm hiệu năng, thời điểm cảnh báo PagerDuty kích hoạt, cho đến từng bước can thiệp sửa đổi và thời điểm dịch vụ xanh trở lại.
- Phương pháp luận "5 Câu hỏi Tại sao" (5 Whys Root Cause Analysis): Lần theo chuỗi nhân quả sâu nhất để chạm tới lỗ hổng quy trình hoặc kiến trúc, không dừng lại ở nguyên nhân bề mặt.
- Danh mục Hành động Phòng ngừa (Action Items &amp; Preventative Measures): Phải bao gồm tối thiểu 03 đầu việc cụ thể. Mỗi đầu việc bắt buộc phải có: Mã ticket Jira, người chịu trách nhiệm duy nhất (Single Owner), và thời hạn hoàn thành cam kết (Hard Deadline không quá 30 ngày).