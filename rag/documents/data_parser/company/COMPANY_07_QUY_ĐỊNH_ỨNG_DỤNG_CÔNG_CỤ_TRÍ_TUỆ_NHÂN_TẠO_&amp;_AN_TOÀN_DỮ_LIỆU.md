## [DOC 07] QUY ĐỊNH ỨNG DỤNG CÔNG CỤ TRÍ TUỆ NHÂN TẠO &amp; AN TOÀN DỮ LIỆU

- Mã hiệu: POL-IT-007/2026/NEXUS | Hiệu lực: Toàn tập đoàn | Cơ quan ban hành: Ban Công nghệ (CTO Office) &amp; Ban Pháp chế

## Điều 1: Danh mục công cụ AI được phép sử dụng

1. Nhân sự chỉ được phép sử dụng các công cụ Generative AI (LLMs, Coding Assistants) thuộc danh mục tài khoản doanh nghiệp do công ty cấp phép và chi trả (GitHub Copilot Enterprise, ChatGPT Enterprise, Claude for Business).
2. Nghiêm cấm sử dụng tài khoản cá nhân miễn phí của bất kỳ công cụ AI công cộng nào để xử lý dữ liệu công việc nếu công cụ đó có điều khoản sử dụng prompt của người dùng để huấn luyện lại mô hình (Model Re-training).

## Điều 2: Vùng cấm nhập dữ liệu (Zero-Data Ingestion Policy)

Tuyệt đối không được sao chép, tải lên hoặc làm giàu ngữ cảnh (Prompt Engineering) vào bất kỳ hệ thống AI bên ngoài nào các loại thông tin sau:

- Dữ liệu định danh cá nhân (PII), thông tin tài khoản, mật khẩu hoặc số thẻ của khách hàng.
- Khóa bí mật hạ tầng (API Keys, SSH Keys, AWS/GCP Root Credentials, Database Connection Strings).
- Mã nguồn độc quyền cốt lõi (Core Business Logic, thuật toán định giá, giải thuật xử lý thanh toán lõi).
- Số liệu tài chính nội bộ chưa công bố, kế hoạch M&amp;A hoặc biên bản họp chiến lược của Ban Lãnh đạo.

## Điều 3: Trách nhiệm giải trình đối với mã nguồn sinh bởi AI

1. AI chỉ là công cụ hỗ trợ gợi ý (Pair Programmer). Nhân viên thực hiện commit mã nguồn là người duy nhất chịu trách nhiệm pháp lý và kỹ thuật về tính đúng đắn, an toàn và ổn định của đoạn code đó.
2. Toàn bộ mã nguồn sinh bởi AI bắt buộc phải:
- Được rà soát kỹ thuật (Code Review) bởi ít nhất 01 kỹ sư khác trước khi merge vào nhánh chính.
- Vượt qua bài quét lỗ hổng bảo mật tự động (SAST/DAST) và kiểm thử chất lượng (Unit Test).
- Được quét bản quyền phần mềm để đảm bảo không vi phạm các giấy phép mã nguồn mở lây nhiễm nghiêm ngặt (như GPL v3).