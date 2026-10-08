## [TÀI LIỆU 15] HỒ SƠ CHUYÊN MÔN: SOC ANALYST &amp; THREAT HUNTER (SECURITY OPERATIONS &amp; INCIDENT RESPONSE)

1. Phạm vi vai trò &amp; Hệ quy chiếu ngành
- Vị trí cốt lõi: Security Operations Center (SOC) Analyst (Tier 2/3) / Threat Hunter.
- Domain ứng dụng: Hạ tầng trọng yếu quốc gia, Ngân hàng &amp; Định chế tài chính, Sàn thương mại điện tử, Doanh nghiệp công nghệ xử lý dữ liệu lớn.
- Mục tiêu then chốt của vị trí: Liên tục giám sát bề mặt tấn công; phát hiện, phân tích và ngăn chặn các cuộc tấn công mạng trước khi kẻ xâm nhập đạt được mục tiêu đánh cắp dữ liệu hoặc phá hoại hệ thống; giảm thiểu tối đa hai chỉ số vàng: Thời gian phát hiện trung bình (MTTD) và Thời gian ứng phó trung bình (MTTR).
2. Hệ sinh thái cộng tác &amp; Giao diện luồng công việc
- Thượng nguồn: Tiếp nhận các luồng telemetry, nhật ký sự kiện (Logs) từ toàn bộ máy chủ, thiết bị mạng, tường lửa và trạm đầu cuối (Endpoints).
- Hạ nguồn: Chỉ đạo đội System Admin và Network Engineers thực hiện cô lập mạng, thu hồi tài khoản bị thỏa hiệp; báo cáo sự cố vi phạm an toàn thông tin lên CISO và Ban Pháp chế/Quan hệ khách hàng nếu có rò rỉ dữ liệu cá nhân.
- Giao tiếp ngang: Phối hợp cùng Red Team (Penetration Testers) để rà soát các điểm mù phòng thủ sau các đợt tập trận mô phỏng (Purple Teaming).
3. Ngăn xếp công nghệ xu hướng &amp; Kiến trúc lõi
- SIEM &amp; Phân tích Log: Splunk (SPL), Microsoft Sentinel (KQL), Elastic Security, Wazuh.
- EDR/XDR &amp; Endpoint Detection: CrowdStrike Falcon, SentinelOne, Microsoft Defender for Endpoint.
- Khung chuẩn &amp; Tình báo nguy cơ (Threat Intel): MITRE ATT&amp;CK Framework, Cyber Kill Chain, MISP, AlienVault OTX, VirusTotal Enterprise.
- Điều tra dấu vết &amp; Phân tích mạng: Wireshark, Zeek (Network Security Monitoring), Volatility (Phân tích bộ nhớ RAM), KAPE (Thu thập chứng cứ số).
- SOAR (Security Orchestration, Automation and Response): Cortex XSOAR, Tines, Shuffle.

## 4. Bài toán kỹ thuật thực chiến &amp; Điểm nghẽn vận hành

- Hội chứng "Bội thực cảnh báo" (Alert Fatigue) &amp; Tỷ lệ báo động giả cao:
- Vấn đề: Trung tâm SOC nhận hơn 10,000 cảnh báo mỗi ngày. Các chuyên viên phân tích bị quá tải, dẫn đến việc bỏ qua một cảnh báo leo thang đặc quyền thực sự của tin tặc núp bóng trong hàng nghìn cảnh báo quét cổng thông thường.
- Bản chất: Quy tắc tương quan (Correlation Rules) viết quá lỏng lẻo, thiếu ngữ cảnh và không có cơ chế loại trừ hành vi hợp lệ của nhân viên quản trị.
- Giải pháp: Tinh chỉnh quy tắc phát hiện dựa trên ma trận rủi ro; tích hợp SOAR để tự động hóa khâu làm giàu dữ liệu ban đầu (Tự động tra cứu IP trên VirusTotal, kiểm tra vai trò người dùng trong Active Directory); nếu là cảnh báo rác đã biết, SOAR tự động đóng ticket, chỉ chuyển lên con người những cảnh báo đã được xác thực có độ nguy hiểm cao.
- Kỹ thuật tấn công "Sống dựa vào tài nguyên có sẵn" (Living off the Land - LotL):
- Vấn đề: Kẻ tấn công không tải mã độc hay file lạ về máy (Fileless Malware) mà dùng chính các công cụ quản trị hợp pháp của Windows (PowerShell, WMI, Certutil, Bitsadmin) để tải và thực thi payload trong bộ nhớ RAM, vượt mặt hoàn toàn các phần mềm Antivirus truyền thống.
- Giải pháp: Thiết lập chính sách ghi nhận sự kiện chi tiết (Bật Sysmon Event ID 1 - Process Creation, Event ID 3 - Network Connection, PowerShell Script Block Logging Event ID 4104); áp dụng các quy tắc phát hiện chuỗi đối số dòng lệnh bất thường (như PowerShell với tham số -enc, -w hidden, -nop) thay vì chỉ quét mã băm (Hash) của file.

## 5. Tương tác chuyên môn &amp; Phản biện kỹ thuật

- Xử lý khủng hoảng: Cô lập máy chủ vận hành kinh doanh (Containment Dilemma):
- Tình huống: Bạn phát hiện một máy chủ ứng dụng đang phát tán tín hiệu kết nối về máy chủ điều khiển của tin tặc (C2 Server). Tuy nhiên, máy chủ này đang xử lý các giao dịch trị giá hàng trăm nghìn USD mỗi giờ. Giám đốc Vận hành (COO) yêu cầu không được ngắt mạng để tránh mất doanh thu.
- Luận điểm xử lý: Bản lĩnh của một kỹ sư phòng thủ: Không ngắt kết nối vật lý gây sập toàn bộ dịch vụ ngay lập tức, mà áp dụng kỹ thuật EDR Network Containment: Cách ly máy chủ khỏi mạng nội bộ để chặn việc lây lan ngang (Lateral Movement), nhưng chỉ giữ lại duy nhất luồng kết nối quản trị an toàn của đội SOC để trích xuất bộ nhớ (Memory Dump) và phân tích luồng tiến trình độc hại; đồng thời chuyển hướng tải kinh doanh sang một cụm máy chủ dự phòng sạch khác.

## 6. Môi trường tác nghiệp &amp; Công cụ thực tế

- Không gian làm việc: Phòng tác chiến SOC chuyên biệt (War Room), hệ thống màn hình giám sát thời gian thực hiển thị bản đồ tấn công toàn cầu, lưu lượng băng thông bất thường và bảng phân loại mức độ nghiêm trọng của sự cố.
- Vật dụng bảo mật: Thiết bị xác thực vật lý đa yếu tố (YubiKey), máy tính chuyên dụng được cô lập mạng (Air-gapped laptop) phục vụ việc mở và phân tích các tệp tin nghi ngờ chứa mã độc.