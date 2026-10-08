## [DOC 02] CHÍNH SÁCH BẢO MẬT THÔNG TIN, AN TOÀN HẠ TẦNG VÀ QUẢN TRỊ TÀI NGUYÊN SỐ

- Mã hiệu tài liệu: POL-SEC-002/2026/NEXUS
- Phiên bản: 5.0 (Chuẩn hóa theo khung ISO/IEC 27001:2022 và SOC 2 Type II)
- Ngày có hiệu lực: 01/01/2026
- Phạm vi áp dụng: Toàn bộ nhân viên chính thức, nhân viên thử việc, thực tập sinh, nhà thầu phụ (Contractors) và đối tác kỹ thuật có quyền truy cập vào tài nguyên công nghệ của Nexus Tech Group.
- Đơn vị chủ trì: Ban An toàn Thông tin &amp; Vận hành Hạ tầng (Information Security &amp; SRE Division).

## PHẦN I: PHÂN LOẠI DỮ LIỆU VÀ QUẢN TRỊ TRUY CẬP (ACCESS CONTROL)

Điều 1: Bảng Phân cấp Dữ liệu Toàn tập đoàn (Data Classification Matrix)

Mọi thông tin, dữ liệu được khởi tạo, xử lý hoặc lưu trữ trên hệ thống của Nexus bắt buộc phải được định danh và gắn nhãn theo một trong 04 cấp độ bảo mật sau:

Plaintext ┌──────────────┬──────────────────────────────────────────── ────────────┬─────────────────────────────────────────┐ │ CẤP ĐỘ DỮ LIỆU│ DANH MỤC THÔNG TIN ĐIỂN HÌNH │ NGUYÊN TẮC KIỂM SOÁT BẮT BUỘC │ ├──────────────┼──────────────────────────────────────────── ────────────┼─────────────────────────────────────────┤ │ CẤP 1: │ - Thông cáo báo chí, bài đăng tuyển dụng, tài liệu │ - Được phép chia sẻ công khai không │ │ PUBLIC │ Marketing đã duyệt, tài liệu Open Source SDKs. │ cần bảo vệ mật khẩu. │ ├──────────────┼──────────────────────────────────────────── ────────────┼─────────────────────────────────────────┤

│ CẤP 2: │ - Sơ đồ tổ chức, quy trình nội bộ, tài liệu hướng dẫn │ - Yêu cầu xác thực tài khoản công ty │ │ INTERNAL │ công việc, biên bản họp chung của các phòng ban. │ (SSO); cấm chia sẻ cho bên ngoài. │ ├──────────────┼──────────────────────────────────────────── ────────────┼─────────────────────────────────────────┤ │ CẤP 3: │ - Toàn bộ mã nguồn ứng dụng (Source code); │ - Phân quyền theo nguyên tắc Need-to- │ │ CONFIDENTIAL │ - Báo cáo tài chính nội bộ, bảng lương chi tiết; │ Know; mã hóa trên đường truyền (TLS) │ │ │ - Dữ liệu định danh cá nhân nhân viên (PII); │ và tại chỗ (AES-256); cấm tải về │ │ │ - Bản thiết kế kiến trúc hệ thống, API specs nội bộ. │ thiết bị cá nhân. │ ├──────────────┼────────────────────────────────────────────

────────────┼─────────────────────────────────────────┤

│ CẤP 4: │ - Khóa mã hóa (Private Encryption Keys, SSL/TLS certs);│ - Cô lập tuyệt đối; chỉ truy cập qua │ │ RESTRICTED │ - Khóa truy cập hạ tầng (AWS/GCP Root Credentials); │ Bastion Host/Jumphost có MFA vật lý; │ │ (TUYỆT MẬT) │ - Dữ liệu thẻ thanh toán, mật khẩu mã hóa của users; │ bắt buộc có phê duyệt 2 cấp (Dual │ │ │ - Bản sao lưu (Snapshots/Dumps) cơ sở dữ liệu Prod. │ Approval); ghi log kiểm toán vĩnh viễn│ └──────────────┴──────────────────────────────────────────── ────────────┴─────────────────────────────────────────┘

Điều 2: Nguyên tắc Quản trị Định danh và Phân quyền Truy cập (IAM Policy)

1. Nguyên tắc Đặc quyền Tối thiểu (Principle of Least Privilege - PoLP):
- Mọi tài khoản người dùng, máy chủ dịch vụ (Service Accounts) chỉ được cấp phát quyền hạn vừa đủ ở mức tối thiểu để hoàn thành nhiệm vụ được giao.
- Nghiêm cấm cấp quyền Administrator/Root vĩnh viễn cho bất kỳ cá nhân nào trên môi trường Production.
2. Quy tắc Phân tách Môi trường Tuyệt đối (Environment Segregation):
- Môi trường Phát triển (Development), Kiểm thử (Staging) và Vận hành thực tế (Production) phải được cô lập hoàn toàn về mặt vật lý hoặc phân vùng mạng ảo (VPC/Subnets độc lập).
- Dữ liệu từ môi trường Production tuyệt đối không được phép sao chép nguyên trạng về môi trường Staging/Dev để phục vụ việc debug. Mọi dữ liệu kiểm thử bắt buộc phải trải qua quá trình làm sạch, ẩn danh hóa (Data Anonymization/Masking) hoặc sinh ngẫu nhiên (Synthetic Data).
3. Quản trị Truy cập Tạm thời (Just-In-Time Access):
- Khi kỹ sư cần quyền truy cập khẩn cấp vào máy chủ Production để xử lý sự cố (Break-glass access), yêu cầu phải được khởi tạo qua hệ thống vé (Jira Service

Desk), có phê duyệt bằng văn bản số từ Technical Lead hoặc Incident Commander, và quyền truy cập sẽ tự động bị thu hồi sau tối đa 04 giờ làm việc.

## PHẦN II: TIÊU CHUẨN THIẾT BỊ VÀ AN TOÀN TRẠM ĐẦU CUỐI (ENDPOINT SECURITY)

Điều 3: Quy chế Quản trị Máy tính Doanh nghiệp cấp phát (Corporate Laptops)

1. Thiết lập Cấu hình Bắt buộc (Mandatory Baseline Configuration):
- Mọi máy tính xách tay do Nexus cấp phát (MacBook / ThinkPad) bắt buộc phải cài đặt phần mềm Quản lý Thiết bị Di động tập trung (MDM - Jamf Pro hoặc Microsoft Intune) trước khi bàn giao cho nhân viên.
- Tính năng mã hóa toàn bộ ổ đĩa cứng bắt buộc phải được kích hoạt vĩnh viễn: Sử dụng FileVault 2 (đối với macOS) hoặc BitLocker với mã hóa AES-XTS 256-bit (đối với Windows). Khóa khôi phục (Recovery Key) được lưu trữ tập trung trên hệ thống quản trị của Ban InfoSec.
- Tính năng tự động khóa màn hình (Screen Auto-Lock) bắt buộc thiết lập sau tối đa 05 phút không có thao tác bàn phím/chuột. Mật khẩu mở khóa phải có độ dài tối thiểu 12 ký tự hoặc xác thực sinh trắc học (Touch ID/Windows Hello).
2. Phần mềm Phòng thủ Điểm cuối (EDR - Endpoint Detection &amp; Response):
- Toàn bộ máy tính phải duy trì hoạt động liên tục 24/7 của tác nhân EDR (CrowdStrike Falcon). Nghiêm cấm mọi hành vi vô hiệu hóa, gỡ bỏ hoặc can thiệp vào tiến trình của EDR. Mọi hành vi tắt EDR sẽ tự động kích hoạt cảnh báo Cấp độ Đỏ về Trung tâm Giám sát SOC.
3. Danh mục Phần mềm Cấm cài đặt:
- Phần mềm không có bản quyền hợp pháp, các công cụ bẻ khóa (Cracks, Keygens, Patchers).
- Các ứng dụng chia sẻ tệp ngang hàng qua giao thức BitTorrent hoặc mạng ẩn danh (Tor Browser).
- Các công cụ đào tiền kỹ thuật số (Cryptocurrency Miners) hoặc các ứng dụng giám sát mạng cá nhân không phục vụ công việc chuyên môn được giao.

Điều 4: Quy định về Thiết bị Lưu trữ Ngoại vi và Thiết bị Cá nhân (BYOD)

1. Chặn cổng giao tiếp dữ liệu ngoại vi (USB/External Storage Blocking):
- Tất cả các cổng USB và kết nối Thunderbolt trên máy tính công ty bị khóa chức năng truyền tải dữ liệu (Data Transfer Disabled) mặc định thông qua chính sách MDM, chỉ giữ lại tính năng sạc điện và kết nối thiết bị ngoại vi chuẩn (Bàn phím, Chuột, Màn hình hiển thị).
- Trường hợp kỹ sư phần cứng hoặc kỹ sư nhúng (Embedded Engineers) có nhu cầu sử dụng USB để nạp firmware hoặc giao tiếp mạch nạp, phải nộp đơn xin phê duyệt ngoại lệ (Security Exception Request) kèm theo thông tin Serial Number của thiết bị USB đã được quét mã độc.
2. Quy định đối với Thiết bị Di động Cá nhân (BYOD Policy):
- Nhân viên sử dụng điện thoại thông minh cá nhân để nhận email công ty hoặc trao đổi qua Slack bắt buộc phải cài đặt ứng dụng bảo mật phân vùng doanh nghiệp.
- Thiết bị cá nhân bắt buộc phải thiết lập mã khóa màn hình tối thiểu 6 chữ số, không bị bẻ khóa hệ điều hành (No Jailbreak trên iOS, No Root trên Android).
- Khi nhân sự nghỉ việc hoặc mất điện thoại, Ban InfoSec có toàn quyền thực hiện lệnh Xóa dữ liệu doanh nghiệp từ xa (Enterprise Remote Wipe) trên ứng dụng mà không can thiệp vào dữ liệu cá nhân của nhân sự.

## PHẦN III: AN TOÀN TRONG CHU TRÌNH PHÁT TRIỂN PHẦN MỀM (DEVSECOPS POLICY)

Điều 5: Kiểm soát Mã nguồn và Quy tắc Đẩy dữ liệu (Source Code &amp; Push Restrictions)

1. Cấm tuyệt đối đưa Bí mật hệ thống vào Kho lưu trữ (No Hardcoded Secrets):
- Nghiêm cấm đưa bất kỳ thông tin nào sau đây vào mã nguồn, tệp cấu hình, Dockerfile hoặc tệp tài liệu Markdown:
3. ■ Khóa bí mật API (API Keys), Token truy cập dịch vụ (Bearer Tokens, Access Tokens).
4. ■ Mật khẩu cơ sở dữ liệu, tên tài khoản quản trị viên.
5. ■ Khóa ký chứng chỉ số cá nhân hoặc chứng chỉ hệ thống (Private Certificates, SSH Keys).
- Toàn bộ các giá trị nhạy cảm trên bắt buộc phải được quản lý tập trung trên HashiCorp Vault hoặc AWS Secrets Manager, và chỉ được nạp động vào ứng dụng lúc khởi chạy dưới dạng Biến Môi trường (Environment Variables).
2. Cơ chế Quét Tự động tại Pipeline (Automated Security Gates):
- Mọi kho lưu trữ (Repository) trên GitLab/GitHub của Nexus bắt buộc phải tích hợp các công cụ quét tự động trong quy trình CI/CD:
9. ■ Pre-commit Hooks (TruffleHog / Git-secrets): Tự động phát hiện và chặn lệnh git push nếu phát hiện có định dạng chuỗi giống khóa bí mật.
10. ■ SAST (Static Application Security Testing - SonarQube): Quét phân tích mã tĩnh; tự động đánh rớt (Fail pipeline) nếu xuất hiện lỗ hổng bảo mật mức độ nghiêm trọng (Blocker/Critical Security Vulnerabilities).
11. ■ SCA (Software Composition Analysis - Snyk/Trivy): Quét toàn bộ các thư viện bên thứ ba (Dependencies) trong file cấu hình (package.json, pom.xml, go.mod, requirements.txt); tự động chặn việc đóng gói image nếu các thư viện có điểm CVSS mà chưa có bản vá. ≥ 7. 0
12. ■ Container Scanning: Toàn bộ Docker Images trước khi đẩy lên Production Registry phải vượt qua bài kiểm tra quét lỗ hổng lớp hệ điều hành nền tảng (Base OS Layer).

Điều 6: Đảm bảo An toàn Hệ thống và Trách nhiệm Ứng phó Lỗ hổng

1. Quy trình Quản lý và Vá Lỗ hổng Bảo mật (Vulnerability Management SLA):
- Khi Ban InfoSec hoặc các công cụ quét phát hiện lỗ hổng bảo mật trên hệ thống Production, các Tech Leads chịu trách nhiệm quản lý dịch vụ đó phải tuân thủ nghiêm ngặt thời hạn khắc phục:
3. ■ Lỗ hổng Cấp độ Khẩn cấp (Critical - CVSS 9.0 - 10.0): Phải hoàn tất bản vá hoặc áp dụng giải pháp giảm thiểu (Mitigation) trong vòng 24 giờ.
4. ■ Lỗ hổng Cấp độ Cao (High - CVSS 7.0 - 8.9): Phải hoàn tất vá lỗi và triển khai trong vòng 07 ngày làm việc.
5. ■ Lỗ hổng Cấp độ Trung bình (Medium - CVSS 4.0 - 6.9): Đưa vào kế hoạch xử lý trong Sprint tiếp theo (tối đa 30 ngày).
2. Chính sách Thử nghiệm Xâm nhập (Pentest) và Rà quét Định kỳ:
- Toàn bộ hệ thống core tiếp nhận lưu lượng người dùng bên ngoài bắt buộc phải trải qua hoạt động kiểm thử xâm nhập độc lập (Black-box &amp; Grey-box Pentest) tối thiểu 02 lần / năm do đơn vị an ninh mạng uy tín bên ngoài thực hiện.
- Mọi tính năng thanh toán hoặc xác thực mới trước khi ra mắt công chúng (Go-Live) bắt buộc phải có chứng nhận ký duyệt an toàn thông tin (Security Sign-off) từ Trưởng ban InfoSec.

## PHẦN IV: ĐIỀU KHOẢN THI HÀNH VÀ CHẾ TÀI XỬ LÝ VI PHẠM

Điều 7: Khung Chế tài Xử phạt Vi phạm Quy chế An toàn Thông tin

Mọi hành vi vi phạm Quy chế này sẽ bị xử lý kỷ luật lao động nghiêm khắc theo quy định của pháp luật và Nội quy lao động của Nexus Tech Group:

1. Vi phạm Mức độ 1 (Khiển trách bằng văn bản &amp; Cắt thưởng thi đua quý):
- Để lộ mật khẩu máy tính cá nhân, không khóa màn hình khi rời vị trí làm việc.
- Tự ý cài đặt các phần mềm tiện ích ngoài danh mục được phê duyệt nhưng chưa gây ra hậu quả lây nhiễm mã độc.
- Để sót lọt việc xử lý lỗ hổng bảo mật mức độ Medium quá hạn quy định mà không có văn bản giải trình hợp lý.
2. Vi phạm Mức độ 2 (Cách chức, Chuyển công tác làm công việc khác có mức lương thấp hơn trong thời hạn 06 tháng):
- Tắt phần mềm giám sát an ninh (EDR) hoặc phần mềm quản lý thiết bị (MDM) trên máy tính công ty cấp.
- Vô ý làm rò rỉ mã nguồn dự án nội bộ (không chứa dữ liệu khách hàng) lên các nền tảng công cộng cá nhân (Personal GitHub, Pastebin).
- Chia sẻ tài khoản truy cập hệ thống của mình cho nhân sự khác hoặc cho người ngoài công ty sử dụng.
3. Vi phạm Mức độ 3 (Sa thải ngay lập tức &amp; Khởi kiện yêu cầu bồi thường thiệt hại):
- Đánh cắp, cố ý phát tán mã nguồn cốt lõi, bí mật công nghệ hoặc dữ liệu cá nhân của khách hàng ra bên ngoài.
- Chèn cửa sau (Backdoor), mã độc, hoặc cố tình phá hoại tính toàn vẹn của cơ sở dữ liệu công ty.
- Thực hiện các hành vi tấn công mạng trái phép nhắm vào chính hạ tầng của công ty hoặc sử dụng hạ tầng của công ty để tấn công bên thứ ba.
- Tùy thuộc vào mức độ thiệt hại thực tế, công ty bảo lưu toàn quyền chuyển toàn bộ hồ sơ chứng cứ số sang Cơ quan Cảnh sát Điều tra để truy cứu trách nhiệm hình sự theo Điều 289 Bộ luật Hình sự (Tội xâm nhập trái phép vào mạng máy tính, mạng viễn thông hoặc phương tiện điện tử của người khác).